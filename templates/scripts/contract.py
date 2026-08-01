#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Work contract runner.

Parses contract.md, runs completion criteria, records evidence.
Rules: <CONVENTION_PATH>/conventions/18-work-contract.md and 19-evidence.md

Subcommands: lint | verify | red | human | status | lanes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1

DEFAULTS: dict[str, Any] = {
    "artifacts_dir": "artifacts",
    "output_capture_bytes": 64_000,
    "command_timeout_sec": 1800,
    "red_cache_enabled": True,
}

VALID_DONE_LEVELS = {"auto", "reviewed", "proven", "bypassed"}
VALID_KINDS = {"functional", "nonfunctional", "negative"}
VALID_REVISION_KINDS = {"additive", "narrowing", "breaking"}
VALID_LANE_STATES = {"active", "abandoned"}
# "required": the check must fail at base, or it proves nothing about the change.
# "guard": a standing invariant that legitimately holds at base (a regression
# guard). Without this distinction any contract containing a guard can never
# clear the red gate, because the guard passing at base is the correct outcome.
VALID_RED_MODES = {"required", "guard"}

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_PENDING_HUMAN = "PENDING-HUMAN"
STATUS_NO_BASELINE = "NO-BASELINE"

# Secret shapes worth masking before anything is written to disk. Deliberately
# broad: a false mask costs a reader one lookup, a missed one leaks a credential.
SECRET_PATTERNS = [
    re.compile(
        r"(?i)\b([a-z0-9_]*(?:api[_-]?key|secret|token|password|passwd|credential)[a-z0-9_]*)"
        r"(\s*[:=]\s*|\s+)(['\"]?)([^\s'\"]{6,})\3"
    ),
    re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9._\-]{12,})"),
    re.compile(r"\b(sk-|ghp_|github_pat_|xox[abprs]-|AKIA)[A-Za-z0-9_\-]{10,}"),
]

MASK = "***MASKED***"


class ContractError(Exception):
    """Contract is unusable. Never swallowed — a parse failure must not fail open."""


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


@dataclass
class Criterion:
    id: str
    text: str
    verify: str
    kind: str = "functional"
    hermetic: bool = True
    red: str = "required"

    @property
    def is_human(self) -> bool:
        return self.verify.strip().lower() == "human"

    @property
    def is_guard(self) -> bool:
        return self.red == "guard"


@dataclass
class Lane:
    id: str
    owns: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    model_tier: str | None = None
    state: str = "active"


@dataclass
class Contract:
    path: Path
    feature: str
    done_level: str
    criteria: list[Criterion]
    out_of_scope: list[str]
    base: str | None = None
    lanes: list[Lane] = field(default_factory=list)
    sequential_owner: list[str] = field(default_factory=list)
    integration: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    evidence_todo: list[str] = field(default_factory=list)
    revision: dict[str, Any] = field(default_factory=dict)

    def criterion(self, cid: str) -> Criterion:
        for c in self.criteria:
            if c.id == cid:
                return c
        raise ContractError(f"unknown criterion id: {cid}")

    def for_lane(self, lane_id: str) -> list[Criterion]:
        for lane in self.lanes:
            if lane.id == lane_id:
                return [self.criterion(cid) for cid in lane.criteria]
        raise ContractError(f"unknown lane: {lane_id}")


def split_front_matter(text: str) -> str:
    """Return the YAML front matter block, or raise.

    Only the leading `---` fence is treated as a delimiter; a `---` later in the
    body is body content, which is why the template asks for `***` as a rule.
    """
    if not text.startswith("---"):
        raise ContractError("contract must start with a '---' front matter fence")
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return "\n".join(lines[1:i])
    raise ContractError("front matter fence was opened but never closed")


def load_contract(path: Path) -> Contract:
    if not path.exists():
        raise ContractError(f"contract not found: {path}")
    try:
        raw = yaml.safe_load(split_front_matter(path.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:
        raise ContractError(f"front matter is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError("front matter must be a mapping")

    version = raw.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ContractError(
            f"schema_version {version!r} is not supported by this tool (expects {SCHEMA_VERSION})"
        )

    for required in ("feature", "done_level", "criteria", "out_of_scope"):
        if required not in raw:
            raise ContractError(f"missing required field: {required}")

    criteria: list[Criterion] = []
    seen: set[str] = set()
    for item in raw["criteria"] or []:
        if not isinstance(item, dict):
            raise ContractError("each criterion must be a mapping")
        for required in ("id", "text", "verify"):
            if required not in item:
                raise ContractError(f"criterion missing '{required}': {item!r}")
        cid = str(item["id"])
        if cid in seen:
            raise ContractError(f"duplicate criterion id: {cid}")
        seen.add(cid)
        criteria.append(
            Criterion(
                id=cid,
                text=str(item["text"]),
                verify=str(item["verify"]),
                kind=str(item.get("kind", "functional")),
                hermetic=bool(item.get("hermetic", True)),
                red=str(item.get("red", "required")),
            )
        )
    if not criteria:
        raise ContractError("a contract needs at least one criterion")

    lanes = [
        Lane(
            id=str(item["id"]),
            owns=[str(o) for o in item.get("owns", [])],
            criteria=[str(c) for c in item.get("criteria", [])],
            model_tier=item.get("model_tier"),
            state=str(item.get("state", "active")),
        )
        for item in (raw.get("lanes") or [])
    ]

    return Contract(
        path=path,
        feature=str(raw["feature"]),
        done_level=str(raw["done_level"]),
        criteria=criteria,
        out_of_scope=[str(x) for x in (raw.get("out_of_scope") or [])],
        base=str(raw["base"]) if raw.get("base") else None,
        lanes=lanes,
        sequential_owner=[str(x) for x in (raw.get("sequential_owner") or [])],
        integration=raw.get("integration") or {},
        checkpoints=raw.get("checkpoints") or [],
        evidence_todo=[str(x) for x in (raw.get("evidence_todo") or [])],
        revision=raw.get("revision") or {},
    )


# --------------------------------------------------------------------------- #
# Config, masking, process
# --------------------------------------------------------------------------- #


def load_config(root: Path) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    conf_path = root / ".conv.toml"
    if conf_path.exists():
        try:
            data = tomllib.loads(conf_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ContractError(f".conv.toml is not valid TOML: {exc}") from exc
        cfg.update(data.get("contract", {}))
    return cfg


def mask(text: str) -> str:
    """Redact secret-shaped substrings. Applied to commands, env, and output."""
    out = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 4:
            out = pattern.sub(
                lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{MASK}{m.group(3)}", out
            )
        elif pattern.groups == 2:
            out = pattern.sub(lambda m: f"{m.group(1)}{MASK}", out)
        else:
            out = pattern.sub(MASK, out)
    return out


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class RunResult:
    exit_code: int
    output: str
    truncated: bool


def run_command(cmd: str, cwd: Path, cfg: dict[str, Any]) -> RunResult:
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=cfg["command_timeout_sec"],
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        code = proc.returncode
    except subprocess.TimeoutExpired:
        return RunResult(124, f"timed out after {cfg['command_timeout_sec']}s", False)
    limit = cfg["output_capture_bytes"]
    truncated = len(combined) > limit
    if truncated:
        combined = combined[:limit] + "\n...[truncated]"
    return RunResult(code, mask(combined), truncated)


# --------------------------------------------------------------------------- #
# Artifacts
# --------------------------------------------------------------------------- #


def artifacts_dir(root: Path, contract: Contract, cfg: dict[str, Any]) -> Path:
    path = root / cfg["artifacts_dir"] / contract.feature
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_manifest(adir: Path) -> dict[str, Any]:
    path = adir / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "created_at": now_iso(),
        "toolkit_schema_version": SCHEMA_VERSION,
        "commit": git("rev-parse", "HEAD", check=False).strip() or None,
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "verify_runs": [],
        "human_verdicts": [],
        "bypasses": [],
        "review_rounds": 0,
    }


def save_manifest(adir: Path, manifest: dict[str, Any]) -> None:
    atomic_write(adir / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def load_statuses(adir: Path) -> dict[str, dict[str, Any]]:
    path = adir / "status.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_statuses(adir: Path, statuses: dict[str, dict[str, Any]]) -> None:
    atomic_write(adir / "status.json", json.dumps(statuses, indent=2, ensure_ascii=False) + "\n")


def append_command_record(adir: Path, record: dict[str, Any]) -> None:
    with (adir / "commands.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (adir / "commands.log").open("a", encoding="utf-8") as fh:
        fh.write(
            f"[{record['at']}] {record['criterion']} exit={record['exit_code']}\n"
            f"$ {record['command']}\n{record['output']}\n{'-' * 60}\n"
        )


def write_report(adir: Path, contract: Contract, statuses: dict[str, dict[str, Any]]) -> None:
    rows = ["| id | status | verify | note |", "|---|---|---|---|"]
    for c in contract.criteria:
        st = statuses.get(c.id, {})
        status = st.get("status", "not-run")
        note = st.get("note", "")
        rows.append(f"| {c.id} | {status} | `{c.verify}` | {note} |")
    body = "\n".join(
        [
            f"# {contract.feature}",
            "",
            f"done_level: `{contract.done_level}`  ",
            f"generated: {now_iso()}",
            "",
            *rows,
            "",
            "Execution records: `commands.jsonl`, `commands.log`. Provenance: `manifest.json`.",
            "",
        ]
    )
    atomic_write(adir / "REPORT.md", body)


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise ContractError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())


def red_cache_dir() -> Path:
    """Cache lives in the shared git dir so parallel worktrees reuse it.

    A per-worktree cache would multiply base checkouts and full test reruns by
    the number of lanes, which is the opposite of what the red check is for.
    """
    common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    path = common / "conv-cache" / "red"
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #


def prefix_conflict(a: str, b: str) -> bool:
    pa, pb = a.rstrip("/") + "/", b.rstrip("/") + "/"
    return pa.startswith(pb) or pb.startswith(pa)


def cmd_lint(args: argparse.Namespace) -> int:
    contract = load_contract(Path(args.contract))
    problems: list[str] = []

    if contract.done_level not in VALID_DONE_LEVELS:
        problems.append(
            f"done_level {contract.done_level!r} is not one of {sorted(VALID_DONE_LEVELS)}"
        )
    if contract.done_level == "bypassed" and not contract.revision.get("reason"):
        problems.append("done_level 'bypassed' requires revision.reason")

    for c in contract.criteria:
        if c.kind not in VALID_KINDS:
            problems.append(f"{c.id}: kind {c.kind!r} is not one of {sorted(VALID_KINDS)}")
        if not c.verify.strip():
            problems.append(f"{c.id}: verify is empty (use a command or 'human')")
        if c.red not in VALID_RED_MODES:
            problems.append(f"{c.id}: red {c.red!r} is not one of {sorted(VALID_RED_MODES)}")
    if not any(c.kind == "negative" for c in contract.criteria):
        problems.append("no negative criterion: nothing states what must NOT happen")
    if not contract.out_of_scope:
        problems.append("out_of_scope is empty: an unstated boundary is the one that gets crossed")

    if contract.revision:
        kind = contract.revision.get("kind")
        if kind not in VALID_REVISION_KINDS:
            problems.append(f"revision.kind {kind!r} is not one of {sorted(VALID_REVISION_KINDS)}")

    known = {c.id for c in contract.criteria}
    for lane in contract.lanes:
        if lane.state not in VALID_LANE_STATES:
            problems.append(f"lane {lane.id}: state {lane.state!r} is invalid")
        for cid in lane.criteria:
            if cid not in known:
                problems.append(f"lane {lane.id}: unknown criterion {cid}")
        for own in lane.owns:
            if "*" in own or "?" in own or "[" in own:
                problems.append(
                    f"lane {lane.id}: owns entry {own!r} is a glob. "
                    "Use a disjoint directory prefix instead — expanding globs against the "
                    "current file list misses files that do not exist yet."
                )
    for cid in contract.integration.get("criteria", []) or []:
        if cid not in known:
            problems.append(f"integration: unknown criterion {cid}")

    problems.extend(_lane_conflicts(contract))

    for line in problems:
        print(f"FAIL {line}")
    if problems:
        return 1
    print(f"OK {contract.path}: {len(contract.criteria)} criteria, {len(contract.lanes)} lanes")
    return 0


def _lane_conflicts(contract: Contract) -> list[str]:
    active = [ln for ln in contract.lanes if ln.state == "active"]
    problems = []
    for i, a in enumerate(active):
        for b in active[i + 1 :]:
            for pa in a.owns:
                for pb in b.owns:
                    if prefix_conflict(pa, pb):
                        problems.append(
                            f"lanes {a.id} and {b.id} both own overlapping paths "
                            f"({pa!r} vs {pb!r}); they cannot run in parallel"
                        )
    owned = {p.rstrip("/") + "/" for ln in active for p in ln.owns}
    for res in contract.sequential_owner:
        for own in owned:
            if prefix_conflict(res, own):
                problems.append(
                    f"sequential_owner {res!r} falls inside lane-owned {own!r}; "
                    "single-owner resources must not be assigned to a lane"
                )
    return problems


def cmd_lanes(args: argparse.Namespace) -> int:
    contract = load_contract(Path(args.contract))
    problems = _lane_conflicts(contract)
    for line in problems:
        print(f"FAIL {line}")
    if problems:
        return 1
    print(f"OK {len(contract.lanes)} lanes, ownership disjoint")
    return 0


def _select(contract: Contract, args: argparse.Namespace) -> list[Criterion]:
    if getattr(args, "id", None):
        return [contract.criterion(cid) for cid in args.id]
    if getattr(args, "lane", None):
        return contract.for_lane(args.lane)
    return list(contract.criteria)


def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = load_contract(Path(args.contract))
    cfg = load_config(root)
    adir = artifacts_dir(root, contract, cfg)
    statuses = load_statuses(adir)
    manifest = load_manifest(adir)

    failed = False
    for c in _select(contract, args):
        if c.is_human:
            if statuses.get(c.id, {}).get("status") != STATUS_PASS:
                statuses[c.id] = {"status": STATUS_PENDING_HUMAN, "note": "awaiting human verdict"}
            continue
        if args.resume and statuses.get(c.id, {}).get("status") == STATUS_PASS:
            continue

        result = run_command(c.verify, root, cfg)
        at = now_iso()
        append_command_record(
            adir,
            {
                "at": at,
                "criterion": c.id,
                "command": mask(c.verify),
                "exit_code": result.exit_code,
                "output": result.output,
                "truncated": result.truncated,
            },
        )
        manifest["verify_runs"].append({"at": at, "criterion": c.id, "exit_code": result.exit_code})
        status = STATUS_PASS if result.exit_code == 0 else STATUS_FAIL
        statuses[c.id] = {
            "status": status,
            "note": "" if status == STATUS_PASS else f"exit {result.exit_code}",
        }
        failed |= status == STATUS_FAIL
        print(f"{status} {c.id}")

    save_statuses(adir, statuses)
    save_manifest(adir, manifest)
    write_report(adir, contract, statuses)
    return 1 if failed else 0


BROKEN_TEST_RE = re.compile(r"\b(SyntaxError|IndentationError|TabError)\b")


def _pytest_collect_verdict(cmd: str, cwd: Path, cfg: dict[str, Any]) -> dict[str, Any] | None:
    """Classify what a pytest collection at the base commit means.

    Collection is checked separately from execution so that "no tests exist at
    base" is never mistaken for "tests exist and fail at base" — that mistake is
    what lets a contract with zero tests pass the red check.

    A collection error is ambiguous on its own: a test that cannot import the
    module it is about is the normal TDD case and counts as red, while a test
    file that does not parse is a broken test and proves nothing. They are split
    on the parse-error text, which is the only signal available without running.
    """
    collect = run_command(f"{cmd} --collect-only -q", cwd, cfg)
    if collect.exit_code == 0:
        return None
    if collect.exit_code == 5:
        return {"status": STATUS_NO_BASELINE, "note": "no tests collected at base"}
    if collect.exit_code == 4:
        return {
            "status": STATUS_NO_BASELINE,
            "note": "pytest usage error at base — test path missing, so no test was written",
        }
    if BROKEN_TEST_RE.search(collect.output):
        return {"status": STATUS_NO_BASELINE, "note": "test file does not parse at base"}
    return {
        "status": STATUS_PASS,
        "note": "collection failed at base (subject missing) as required",
    }


def cmd_red(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = load_contract(Path(args.contract))
    cfg = load_config(root)
    adir = artifacts_dir(root, contract, cfg)
    statuses = load_statuses(adir)

    base = args.base or contract.base
    if not base:
        raise ContractError("no base commit: pass --base or set `base` in the contract")
    base_sha = git("rev-parse", base).strip()
    head_sha = git("rev-parse", "HEAD").strip()

    selected = [c for c in _select(contract, args) if not c.is_human]
    targets = [c for c in selected if c.hermetic and not c.is_guard]
    for c in selected:
        if c.is_guard:
            print(f"SKIP {c.id} (red: guard — a standing invariant, not a change)")
        elif not c.hermetic:
            print(f"SKIP {c.id} (hermetic: false — excluded from red check)")

    cache = red_cache_dir() if cfg["red_cache_enabled"] else None
    failed = False

    with tempfile.TemporaryDirectory(prefix="conv-red-") as tmp:
        wt = Path(tmp) / "base"
        git("worktree", "add", "--detach", "--quiet", str(wt), base_sha)
        try:
            # Bring the tests themselves forward. Without this the test file does
            # not exist at base, pytest reports a usage/collection error, and a
            # naive "non-zero means red" rule would pass a contract with no tests.
            changed = git("diff", "--name-only", f"{base_sha}..{head_sha}").split()
            tests = [p for p in changed if _looks_like_test(p) and (root / p).exists()]
            if tests:
                # Use the resolved sha, not the literal "HEAD": inside a detached
                # worktree HEAD is the base commit, so "HEAD" would copy the very
                # files we are trying to bring forward.
                git("checkout", head_sha, "--", *tests, cwd=wt)

            for c in targets:
                key = hashlib.sha256(f"{base_sha}|{c.id}|{c.verify}".encode()).hexdigest()[:32]
                cached = cache / f"{key}.json" if cache else None
                if cached and cached.exists():
                    verdict = json.loads(cached.read_text(encoding="utf-8"))
                    print(f"{verdict['status']} {c.id} (cached)")
                    _apply_red(statuses, c, verdict)
                    # Anything short of PASS blocks. NO-BASELINE in particular:
                    # "the check could not establish a baseline" must never read
                    # as "the check passed", or a contract with no tests clears
                    # its own gate.
                    failed |= verdict["status"] != STATUS_PASS
                    continue

                verdict = _red_verdict(c, wt, cfg)
                if cached:
                    cached.write_text(json.dumps(verdict, ensure_ascii=False), encoding="utf-8")
                print(f"{verdict['status']} {c.id} — {verdict['note']}")
                _apply_red(statuses, c, verdict)
                failed |= verdict["status"] != STATUS_PASS
        finally:
            git("worktree", "remove", "--force", str(wt), check=False)

    save_statuses(adir, statuses)
    write_report(adir, contract, statuses)
    return 1 if failed else 0


def _looks_like_test(path: str) -> bool:
    name = Path(path).name
    return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in f"/{path}"


def _red_verdict(c: Criterion, wt: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    is_pytest = "pytest" in c.verify
    if is_pytest:
        verdict = _pytest_collect_verdict(c.verify, wt, cfg)
        if verdict is not None:
            return verdict

    result = run_command(c.verify, wt, cfg)
    if result.exit_code == 0:
        return {
            "status": STATUS_FAIL,
            "note": "passed at base — this check proves nothing about the change",
        }
    if result.exit_code in (126, 127):
        return {"status": STATUS_NO_BASELINE, "note": "verify command not runnable at base"}
    if is_pytest and result.exit_code in (2, 3, 4, 5):
        return {
            "status": STATUS_NO_BASELINE,
            "note": f"pytest could not run (exit {result.exit_code})",
        }
    return {"status": STATUS_PASS, "note": f"failed at base (exit {result.exit_code}) as required"}


def _apply_red(statuses: dict[str, dict[str, Any]], c: Criterion, verdict: dict[str, Any]) -> None:
    entry = statuses.setdefault(c.id, {})
    entry["red"] = verdict["status"]
    entry["red_note"] = verdict["note"]
    if verdict["status"] != STATUS_PASS:
        entry.setdefault("status", verdict["status"])


def cmd_human(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = load_contract(Path(args.contract))
    cfg = load_config(root)
    adir = artifacts_dir(root, contract, cfg)
    criterion = contract.criterion(args.id)
    if not criterion.is_human:
        raise ContractError(f"{args.id} is not a `verify: human` criterion")

    manifest = load_manifest(adir)
    author = args.author or os.environ.get("USER") or "unknown"
    verdict = {
        "criterion": args.id,
        "verdict": args.verdict,
        "author": author,
        "at": now_iso(),
        "note": args.note or "",
    }
    manifest["human_verdicts"].append(verdict)
    save_manifest(adir, manifest)

    statuses = load_statuses(adir)
    if args.verdict == "pass":
        statuses[args.id] = {"status": STATUS_PASS, "note": f"human: {author}"}
    else:
        statuses[args.id] = {
            "status": STATUS_FAIL,
            "note": f"human rejected: {args.note or 'no reason given'}",
        }
    save_statuses(adir, statuses)
    write_report(adir, contract, statuses)
    print(f"recorded {args.verdict} for {args.id} by {author}")
    return 0 if args.verdict == "pass" else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = load_contract(Path(args.contract))
    cfg = load_config(root)
    adir = artifacts_dir(root, contract, cfg)
    statuses = load_statuses(adir)

    targets = contract.for_lane(args.lane) if args.lane else list(contract.criteria)
    if not args.lane and contract.integration.get("criteria"):
        extra = [contract.criterion(cid) for cid in contract.integration["criteria"]]
        targets = targets + [c for c in extra if c not in targets]

    blocking: list[str] = []
    for c in targets:
        entry = statuses.get(c.id, {})
        status = entry.get("status", "not-run")
        red = entry.get("red")
        print(f"{status:<14} {c.id}" + (f"  red={red}" if red else ""))
        if status != STATUS_PASS:
            blocking.append(f"{c.id}: {status}")
        elif not c.is_human and not c.is_guard and red not in (STATUS_PASS, None):
            blocking.append(f"{c.id}: red check {red}")

    for cp in contract.checkpoints:
        after = cp.get("after")
        if after and statuses.get(str(after), {}).get("status") == STATUS_PASS:
            print(f"WARN checkpoint after {after} was passed — run the plan-versus-diff review")

    if not (adir / "commands.jsonl").exists():
        blocking.append("no execution records: evidence artifacts are missing")

    if blocking:
        print("\nblocking:")
        for line in blocking:
            print(f"  {line}")
        return 1
    print(f"\nOK all criteria pass ({contract.done_level})")
    return 0


# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="contract", description=__doc__)
    parser.add_argument("--contract", default="contract.md", help="path to contract.md")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("lint", help="validate schema and ownership").set_defaults(func=cmd_lint)
    sub.add_parser("lanes", help="check lane ownership is disjoint").set_defaults(func=cmd_lanes)

    p_verify = sub.add_parser("verify", help="run criteria and record evidence")
    p_verify.add_argument("--id", nargs="*", help="criterion ids to run")
    p_verify.add_argument("--lane", help="run one lane's criteria")
    p_verify.add_argument("--resume", action="store_true", help="skip criteria already passing")
    p_verify.set_defaults(func=cmd_verify)

    p_red = sub.add_parser("red", help="confirm each check fails at the base commit")
    p_red.add_argument("--base", help="base commit (defaults to contract `base`)")
    p_red.add_argument("--id", nargs="*")
    p_red.add_argument("--lane")
    p_red.set_defaults(func=cmd_red)

    p_human = sub.add_parser("human", help="record a human verdict")
    p_human.add_argument("--id", required=True)
    p_human.add_argument("--verdict", required=True, choices=["pass", "reject"])
    p_human.add_argument("--note")
    p_human.add_argument("--author")
    p_human.set_defaults(func=cmd_human)

    p_status = sub.add_parser("status", help="exit 0 only when everything passes")
    p_status.add_argument("--lane")
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        # A contract that cannot be parsed must stop the caller. Treating this as
        # "nothing to check" would turn every gate into a no-op at exactly the
        # moment the contract is broken.
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
