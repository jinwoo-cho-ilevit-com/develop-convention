#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6"]
# ///
"""Run a work contract: lint it, red-check it, verify it, and gate on the result.

The rules this enforces are conventions/18-work-contract.md and 19-evidence.md; the
red-check definitions come from 06-testing-verification.md section 3.

Two shapes here exist because the previous version was withdrawn over them. Parsing
replaces a criterion's verify string with a tagged check, so no later code can decide
what kind of runner it is by searching the command text. And an unusable contract
raises rather than degrading to an empty one, because a gate that cannot read its own
rules must stop instead of opening.
"""

from __future__ import annotations

import argparse
import fnmatch
import functools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

import yaml

SCHEMA_VERSION = 1

FEATURE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CRITERION_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
# An id becomes `<id>.<phase>.json`, so it has to fit a filename. Without a bound a
# slug-legal 300-character id passed validation and then raised OSError, which exit 3
# reports as the runner having broken rather than the contract being unusable.
MAX_CRITERION_ID_LEN = 64

RUNNER_KINDS = ("pytest", "command")
KINDS = ("functional", "nonfunctional", "negative")
DONE_LEVELS = ("auto", "reviewed", "proven")
# 18's marker for a gate that was skipped. Kept out of DONE_LEVELS because it is not a
# level of rigour but a record that one was not reached.
BYPASSED = "bypassed"
RED_MODES = ("required", "guard")
REQUIRED_FIELDS = ("feature", "done_level", "criteria", "out_of_scope")

# Refused rather than ignored: a contract carrying one of these was written by someone
# who believes it is enforced, and this runner does not implement it. Anything outside
# KNOWN_FIELDS is refused for the same reason — silently accepting `evidence_todo`,
# which 19 tells authors to write, would be the same defect wearing a different name.
UNSUPPORTED_FIELDS: tuple[str, ...] = ()
KNOWN_FIELDS = frozenset(
    {
        "schema_version",
        "feature",
        "done_level",
        "base",
        "criteria",
        "out_of_scope",
        "revision",
        "bypass",
        "lanes",
        "sequential_owner",
        "integration",
        "checkpoints",
    }
)

MODEL_TIERS = ("light", "mid", "top")
# 18 records `owns` as directory prefixes plus individually named cross-cutting files.
# A glob is refused because it is expanded against the files that exist now and misses
# the ones the work is about to create — which is the collision the check exists for.
GLOB_CHARS = "*?[]"
KNOWN_CRITERION_FIELDS = frozenset({"id", "text", "verify", "runner", "kind", "red", "hermetic"})

# A verify command is executed as an argument vector, so an operator would become a
# literal argument rather than doing what the author meant. These are the characters
# `shlex(punctuation_chars=True)` splits operators out of, and a token made only of them
# is one. Listing the operators instead let the merged forms — `>&`, `&>`, `<>`, `|&` —
# through, and a redirect that silently did nothing still let its criterion pass.
SHELL_PUNCTUATION = "();<>|&"

# shlex separates arguments on every character in its whitespace set, so a verify holding
# two commands separated by one of them is fused into a third rather than refused. Derived
# from shlex rather than listed: writing `\n` alone let `\r` through, which is the third
# time in this file that enumerating the bad forms missed one.
LINE_SEPARATORS = frozenset(shlex.shlex().whitespace) - frozenset(" \t")

EXIT_OK = 0
EXIT_GATE = 1  # the runner answered, and the answer is no
EXIT_CONTRACT = 2  # the runner could not answer
EXIT_INTERNAL = 3  # the runner broke

# pytest's exit code for "collection ran and found nothing", as distinct from an error.
PYTEST_EXIT_NO_TESTS = 5

COMMAND_TIMEOUT_SEC = 1800
COLLECT_TIMEOUT_SEC = 300
OUTPUT_CAPTURE_CHARS = 64_000
MIN_SECRET_VALUE_LEN = 8
MASK = "***MASKED***"
SECRETS_PATH = Path(__file__).resolve().parent / "secrets.toml"

EVIDENCE_FILES = ("REPORT.md", "commands.jsonl", "commands.log", "manifest.json")

# 19 fixes these four words for a criterion's status.
PASS = "PASS"
FAIL = "FAIL"
PENDING_HUMAN = "PENDING-HUMAN"
NO_BASELINE = "NO-BASELINE"

# The red phase has its own vocabulary on purpose. The withdrawn runner wrote
# `"red": "PASS"` and left it to the reader to remember that a red PASS is not a
# criterion PASS; keeping the words disjoint makes them non-interchangeable.
RED = "RED"
NOT_RED = "NOT-RED"
EXEMPT_GUARD = "EXEMPT-GUARD"
# `NO-BASELINE` is deliberately shared with the status words: 06 §3 gives it one
# meaning — the check could not run — and a criterion that selects no test is that
# case, so it does not get a second word of its own.


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class ContractError(Exception):
    """The contract cannot be used.

    Never swallowed. Reported as EXIT_CONTRACT so a caller can tell "your contract is
    broken" from "your work is not done", which are the same exit code in most tools
    and were indistinguishable in the version this replaces.
    """


# --- what a criterion is checked by --------------------------------------------------
#
# A tagged union, not a string plus a flag. After load_contract there is no command
# text on a Criterion, so `"pytest" in verify` has nothing to run against.


@dataclass(frozen=True, slots=True)
class HumanCheck:
    """A judgment a machine cannot make."""


@dataclass(frozen=True, slots=True)
class PytestCheck:
    argv: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CommandCheck:
    argv: tuple[str, ...]


type Check = HumanCheck | PytestCheck | CommandCheck


def display_command(check: Check) -> str:
    """The command as a human reads it, rebuilt from the vector that will actually run."""
    match check:
        case HumanCheck():
            return "human"
        case PytestCheck(argv) | CommandCheck(argv):
            return shlex.join(argv)


@dataclass(frozen=True, slots=True)
class Feature:
    """A contract's feature name, validated because it becomes a directory."""

    value: str

    @staticmethod
    def parse(raw: object) -> Feature:
        if not isinstance(raw, str):
            # An unfilled `feature: [short-slug]` placeholder parses as a list.
            raise ContractError(
                f"feature must be a string, got {type(raw).__name__} — "
                "an unfilled bracket placeholder parses as a list"
            )
        if not FEATURE_RE.fullmatch(raw):
            raise ContractError(
                f"feature {raw!r} is not a plain slug "
                "(lowercase letters, digits and single hyphens)"
            )
        return Feature(raw)


@dataclass(frozen=True, slots=True)
class Criterion:
    id: str
    text: str
    check: Check
    kind: str
    red: str

    @property
    def is_human(self) -> bool:
        return isinstance(self.check, HumanCheck)

    @property
    def is_guard(self) -> bool:
        return self.red == "guard"


@dataclass(frozen=True, slots=True)
class Contract:
    path: Path
    feature: Feature
    done_level: str
    criteria: tuple[Criterion, ...]
    out_of_scope: tuple[str, ...]
    base: str | None
    bypass: dict | None


# --- parsing -------------------------------------------------------------------------


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses a repeated key instead of keeping the last one.

    YAML resolves a duplicate silently, so a contract could state one `verify` and run
    another with nothing reporting the difference — the same shape as every other defect
    this runner exists to prevent, arriving through the parser rather than the gate.
    """


def _no_duplicate_keys(loader: StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ContractError(f"contract repeats the key {key!r}; one of the two is ignored")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: _no_duplicate_keys(loader, node),
)


def split_front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ContractError("contract has no front matter: the first line must be `---`")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    raise ContractError("contract front matter is never closed by a `---` line")


def name_list(names: set) -> str:
    """Field names for an error message, whatever YAML turned the keys into.

    YAML 1.1 resolves `on`, `no` and a bare year to a bool or an int, so an unknown key
    need not be a string. Joining them raised, and the runner exited `3` — "the runner
    broke" — where it owed the author `2` and the name of the field.
    """
    return ", ".join(repr(name) for name in sorted(names, key=repr))


def cell(text: str) -> str:
    """One value, safe to put in a table cell without ending the row or the table.

    A `|` closes the cell, and a line break closes the row — a blank one closes the
    whole table, dropping every criterion below it from what a reviewer reads. Notes
    carry whatever an author typed, so both arrive here. Whitespace is collapsed rather
    than escaped: the cell is a summary, and the full text is in the state record.
    """
    return " ".join(text.split()).replace("|", r"\|")


def lex(verify: str) -> list[str]:
    """Split a verify command into the arguments that will be executed.

    One lex, and the check below reads its output. A second lex over the quoted form was
    an attempt to tell a literal `';'` from a bare `;`, which the argv cannot show; it
    bought that distinction at the price of two parsers that disagreed — on an attached
    quote (`--format='%h|%s'`), on a backslash escape, and on an input where one raised
    and the other did not, which let an unquoted `&&` through unchecked.

    `commenters` is cleared because shlex otherwise drops an unquoted `#` and everything
    after it. Nothing here runs through a shell, so a `#` is an ordinary argument, and
    executing a shorter command than the contract states is worse than either refusing
    it or passing it along.
    """
    lexer = shlex.shlex(verify, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def shell_operators(argv: list[str]) -> list[str]:
    """Arguments made only of operator punctuation, whether or not the author quoted one.

    One criterion, and it is the whole rule. The runner cannot tell an author who wanted
    a literal `;` from one who expected a shell — after splitting they are the same
    argument — so it refuses both and says so; a command that needs such an argument goes
    in a script. A second criterion for `` ` `` and `$(` used to sit here unmentioned by
    any document, and it refused `awk '{print $(NF)}'` and ``grep -c '```' README.md``.
    An unquoted `$(…)` is caught by this rule anyway — the `(` is an argument of its own —
    and a backtick reaches the program as the ordinary argument it is, there being no
    shell here to substitute anything.
    """
    return sorted({token for token in argv if token and not token.strip(SHELL_PUNCTUATION)})


def _argv_of_list(raw: list, cid: str) -> tuple[str, ...]:
    """A list `verify` is the argument vector, verbatim.

    Nothing is split and no operator is refused, because there is nothing to parse and
    nothing that could act as an operator. This is the form for a command that needs a
    literal `;` or `|` as an argument — the string form cannot express one, since after
    splitting it cannot tell that author from one expecting a shell.
    """
    if not raw:
        raise ContractError(f"{cid}: verify is an empty list")
    for entry in raw:
        if not isinstance(entry, str):
            raise ContractError(
                f"{cid}: verify list holds {type(entry).__name__}; every argument is a string"
            )
    return tuple(raw)


def _check_of(raw_verify: object, raw_runner: object, cid: str, has_runner_key: bool) -> Check:
    if isinstance(raw_verify, list):
        if raw_runner is None:
            raise ContractError(f"{cid}: runner is required unless verify is `human`")
        if raw_runner not in RUNNER_KINDS:
            raise ContractError(f"{cid}: runner {raw_runner!r} is not one of {RUNNER_KINDS}")
        argv = _argv_of_list(raw_verify, cid)
        return PytestCheck(argv) if raw_runner == "pytest" else CommandCheck(argv)

    if not isinstance(raw_verify, str) or not raw_verify.strip():
        raise ContractError(f"{cid}: verify must be a non-empty string or list, or `human`")
    verify = raw_verify.strip()

    if verify == "human":
        # `"runner" in raw`, not `is not None`: a bare `runner:` key parses as null and
        # slipped through, which is the leftover line the refusal exists to catch.
        if has_runner_key:
            raise ContractError(f"{cid}: a human criterion takes no runner")
        return HumanCheck()

    if raw_runner is None:
        raise ContractError(f"{cid}: runner is required unless verify is `human`")
    if raw_runner not in RUNNER_KINDS:
        raise ContractError(f"{cid}: runner {raw_runner!r} is not one of {RUNNER_KINDS}")

    # POSIX counts a newline among the control operators, but shlex counts it as
    # whitespace, so a YAML block scalar holding two commands was fused into one argv
    # and passed — running a command the contract never states, which is the outcome
    # this whole check exists to prevent.
    if LINE_SEPARATORS.intersection(verify):
        raise ContractError(
            f"{cid}: verify spans more than one line; a criterion runs one command, "
            "so write two criteria or put the sequence in a script"
        )
    try:
        argv = lex(verify)
    except ValueError as exc:
        raise ContractError(f"{cid}: verify cannot be split into arguments: {exc}") from exc
    if not argv:
        raise ContractError(f"{cid}: verify is empty after splitting")
    operators = shell_operators(argv)
    if operators:
        raise ContractError(
            f"{cid}: verify contains the shell operator(s) {operators}; quoting one does "
            "not help — split it into separate criteria, or put the command in a script"
        )

    argv_tuple = tuple(argv)
    return PytestCheck(argv_tuple) if raw_runner == "pytest" else CommandCheck(argv_tuple)


def _criterion_of(raw: object, seen: set[str]) -> Criterion:
    if not isinstance(raw, dict):
        raise ContractError(f"each criterion must be a mapping, got {type(raw).__name__}")
    unknown = name_list(set(raw) - KNOWN_CRITERION_FIELDS)
    if unknown:
        raise ContractError(
            f"criterion {raw.get('id')!r} carries {unknown}, which this runner does not read"
        )
    cid = raw.get("id")
    if not isinstance(cid, str) or not CRITERION_ID_RE.fullmatch(cid):
        raise ContractError(f"criterion id {cid!r} is not a plain slug — ids become filenames")
    if len(cid) > MAX_CRITERION_ID_LEN:
        raise ContractError(
            f"criterion id {cid[:20]!r}… is {len(cid)} characters; ids become filenames and "
            f"the limit is {MAX_CRITERION_ID_LEN}"
        )
    if cid in seen:
        raise ContractError(f"duplicate criterion id {cid!r}")
    seen.add(cid)

    text = raw.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ContractError(f"{cid}: text must be a non-empty string")

    kind = raw.get("kind", "functional")
    if kind not in KINDS:
        raise ContractError(f"{cid}: kind {kind!r} is not one of {KINDS}")

    red = raw.get("red", "required")
    if red not in RED_MODES:
        raise ContractError(f"{cid}: red {red!r} is not one of {RED_MODES}")

    # `is False` alone let `hermetic: "false"`, `0`, `banana` and `null` through, which
    # is the silent acceptance this runner refuses everywhere else — an author writing
    # any of them believes an exemption is in force. Only literal `true` is inert.
    hermetic = raw.get("hermetic", True)
    if hermetic is not True:
        # templates/contract.md documents `false` as a red exemption, but C-05 admits
        # only a human criterion or `red: guard`. Refused until that is reconciled.
        raise ContractError(
            f"{cid}: hermetic {hermetic!r} is not implemented by this runner; "
            "use `red: guard` for a standing invariant"
        )

    return Criterion(
        id=cid,
        text=text,
        check=_check_of(raw.get("verify"), raw.get("runner"), cid, "runner" in raw),
        kind=kind,
        red=red,
    )


def _owns_entry(raw: object, lane_id: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError(f"lane {lane_id}: every `owns` entry is a non-empty string")
    entry = raw.strip()
    if any(ch in entry for ch in GLOB_CHARS):
        raise ContractError(
            f"lane {lane_id}: `owns` entry {entry!r} is a glob. A glob is expanded against "
            "the files that exist now and misses the ones the work is about to create, "
            "which is the collision this check exists to prevent — use a directory prefix "
            "or name the file"
        )
    return entry


def _covers(owner: str, path: str) -> bool:
    """A prefix covers everything beneath it; a named file covers only itself."""
    return path == owner or (owner.endswith("/") and path.startswith(owner))


def validate_lanes(data: dict) -> None:
    """The decomposition has to be self-consistent before any of it runs.

    18 requires disjoint ownership, and this session found out why by nearly breaking it:
    five lanes sliced by kind of change all landed in the same three documents. Sliced by
    file instead, they cannot collide. This is the check that says so before the lanes
    start rather than when they conflict.
    """
    raw_lanes = data.get("lanes")
    if raw_lanes is None:
        for field in ("sequential_owner", "integration", "checkpoints"):
            if field in data:
                raise ContractError(
                    f"`{field}` describes a decomposition, but there are no `lanes`"
                )
        return
    if not isinstance(raw_lanes, list) or len(raw_lanes) < 2:
        raise ContractError(
            "`lanes` is for two or more parallel lanes; with fewer, leave it out (18 §2)"
        )

    owned: dict[str, str] = {}
    seen_ids: set[str] = set()
    for raw in raw_lanes:
        if not isinstance(raw, dict):
            raise ContractError(f"each lane must be a mapping, got {type(raw).__name__}")
        lane_id = raw.get("id")
        if not isinstance(lane_id, str) or not lane_id.strip():
            raise ContractError("every lane needs a non-empty `id`")
        if lane_id in seen_ids:
            raise ContractError(f"duplicate lane id {lane_id!r}")
        seen_ids.add(lane_id)

        tier = raw.get("model_tier")
        if tier is not None and tier not in MODEL_TIERS:
            raise ContractError(
                f"lane {lane_id}: model_tier {tier!r} is not one of {MODEL_TIERS} — "
                "18 records a tier so the routing choice can be audited, never a model id"
            )

        entries = raw.get("owns")
        if not isinstance(entries, list) or not entries:
            raise ContractError(f"lane {lane_id}: `owns` is a non-empty list")
        for entry in (_owns_entry(item, lane_id) for item in entries):
            for existing, holder in owned.items():
                if _covers(existing, entry) or _covers(entry, existing):
                    raise ContractError(
                        f"lanes {holder} and {lane_id} both own {entry!r}/{existing!r}; "
                        "ownership must be disjoint, so slice by file rather than by the "
                        "kind of change when several kinds land in the same files"
                    )
            owned[entry] = lane_id

    for raw in data.get("sequential_owner", []) or []:
        single = str(raw).strip()
        for entry, holder in owned.items():
            if _covers(entry, single) or _covers(single, entry):
                raise ContractError(
                    f"{single!r} is in `sequential_owner` and also owned by lane {holder}; "
                    "a file with a single owner belongs to no lane"
                )


def load_contract(path: Path | str) -> Contract:
    """Read and validate a contract. Raises rather than returning something partial."""
    path = Path(path)
    if not path.is_file():
        raise ContractError(f"contract not found: {path}")

    try:
        data = yaml.load(  # noqa: S506 - StrictLoader is SafeLoader plus a duplicate check
            split_front_matter(path.read_text(encoding="utf-8")), Loader=StrictLoader
        )
    except yaml.YAMLError as exc:
        raise ContractError(f"contract front matter is not valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ContractError("contract front matter must be a mapping")

    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ContractError(
            f"schema_version {version!r} is not supported (this runner reads {SCHEMA_VERSION})"
        )

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise ContractError(f"contract is missing required field(s): {', '.join(missing)}")

    unsupported = [field for field in UNSUPPORTED_FIELDS if field in data]
    if unsupported:
        raise ContractError(
            f"this runner does not implement {', '.join(unsupported)} — "
            "refusing rather than ignoring a field you expect to be enforced"
        )
    validate_lanes(data)
    unknown = name_list(set(data) - KNOWN_FIELDS - set(UNSUPPORTED_FIELDS))
    if unknown:
        raise ContractError(
            f"this runner does not read {unknown} — "
            "refusing rather than ignoring a field you expect to be enforced"
        )

    done_level = data["done_level"]
    if done_level not in DONE_LEVELS + (BYPASSED,):
        raise ContractError(f"done_level {done_level!r} is not one of {DONE_LEVELS + (BYPASSED,)}")

    # 18 and 19 both require a bypass to carry a reason, and 19 calls one that leaves no
    # trace the blocker. The level is accepted only together with the record, so the two
    # cannot come apart; the reason reaches manifest.json and the report.
    bypass = data.get("bypass")
    if done_level == BYPASSED:
        if not isinstance(bypass, dict) or not str(bypass.get("reason", "")).strip():
            raise ContractError(
                "done_level `bypassed` needs a `bypass` mapping carrying a non-empty "
                "`reason` — an unrecorded bypass is the blocker, not the bypass"
            )
    elif bypass is not None:
        raise ContractError("`bypass` is only meaningful with done_level `bypassed`")

    raw_criteria = data["criteria"]
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise ContractError("criteria must be a non-empty list")

    seen: set[str] = set()
    criteria = tuple(_criterion_of(raw, seen) for raw in raw_criteria)

    raw_scope = data["out_of_scope"]
    if not isinstance(raw_scope, list):
        raise ContractError("out_of_scope must be a list")

    base = data.get("base")
    if base is not None and not isinstance(base, str):
        raise ContractError(f"base must be a commit-ish string, got {type(base).__name__}")

    return Contract(
        path=path,
        feature=Feature.parse(data["feature"]),
        done_level=done_level,
        criteria=criteria,
        out_of_scope=tuple(str(entry) for entry in raw_scope),
        base=base,
        bypass=dict(bypass) if isinstance(bypass, dict) else None,
    )


# --- repository layout ---------------------------------------------------------------


def git(*args: str, cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ContractError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root(contract_path: Path) -> Path:
    """The repository the contract lives in, not the one the process was started in."""
    return Path(git("rev-parse", "--show-toplevel", cwd=contract_path.resolve().parent))


def artifacts_dir(root: Path, feature: Feature) -> Path:
    return root / "artifacts" / feature.value


# --- executing a check -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Run:
    argv: tuple[str, ...]
    exit_code: int | None
    output: str
    truncated: bool
    timed_out: bool
    spawn_error: str | None
    duration_sec: float


def run_argv(
    argv: tuple[str, ...] | list[str],
    *,
    cwd: Path,
    timeout: int = COMMAND_TIMEOUT_SEC,
    env: dict[str, str] | None = None,
) -> Run:
    """Execute an argument vector. There is no shell and no switch to add one.

    A program that cannot be started reports `spawn_error` with no exit code, so
    "the check could not run" is never inferred from a number the check itself could
    have returned.
    """
    started = time.monotonic()
    argv = tuple(argv)
    try:
        proc = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env=env,
        )
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError) as exc:
        return Run(argv, None, "", False, False, str(exc), time.monotonic() - started)
    except subprocess.TimeoutExpired:
        return Run(argv, None, "", False, True, None, time.monotonic() - started)

    output = (proc.stdout or "") + (proc.stderr or "")
    truncated = len(output) > OUTPUT_CAPTURE_CHARS
    if truncated:
        output = output[:OUTPUT_CAPTURE_CHARS] + "\n...[truncated]"
    return Run(argv, proc.returncode, output, truncated, False, None, time.monotonic() - started)


# --- masking -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Shape:
    name: str
    pattern: str
    sample: str


@functools.cache
def _secrets_document() -> dict:
    try:
        return tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ContractError(f"cannot read {SECRETS_PATH}: {exc}") from exc


@functools.cache
def secret_shapes() -> tuple[Shape, ...]:
    """Shapes, with each sample reassembled from the fragments the file stores.

    A sample is a credential in the format a scanner is built to find, and storing one
    whole made this file a secret as far as the scanner was concerned — GitHub's push
    protection refused a push over the Slack sample, and every project that copied the
    toolkit inherited the same wall. The fragments are joined here and nowhere on disk,
    so the sample still matches its pattern and no scanner sees a credential.
    """
    shapes = []
    for entry in _secrets_document().get("shape", []):
        parts = entry["sample"]
        if not isinstance(parts, list) or not all(isinstance(p, str) for p in parts):
            raise ContractError(f"shape {entry.get('name')!r}: sample must be a list of strings")
        if len(parts) < 2:
            raise ContractError(
                f"shape {entry.get('name')!r}: sample must be split across at least two "
                "fragments, or the whole credential sits in the file as a literal"
            )
        shapes.append(Shape(entry["name"], entry["pattern"], "".join(parts)))
    return tuple(shapes)


@functools.cache
def secret_env_globs() -> tuple[str, ...]:
    return tuple(_secrets_document().get("env_names", []))


class Masker:
    """Redacts credential shapes and the values of secret-bearing variables."""

    def __init__(self, literals: tuple[str, ...], names: tuple[str, ...] = ()) -> None:
        self._literals = literals
        # The variables whose values are actually being redacted — not the ones whose
        # names merely matched. A manifest that named the second set would tell a
        # reviewer a value was masked when the log still carries it in the clear.
        self.names = names

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> Masker:
        source = os.environ if env is None else env
        globs = secret_env_globs()
        masked = {
            name: value
            for name, value in source.items()
            if isinstance(value, str)
            and len(value) >= MIN_SECRET_VALUE_LEN
            and any(fnmatch.fnmatchcase(name, glob) for glob in globs)
        }
        # Longest first, so a value that is a prefix of another does not half-redact it.
        return Masker(
            tuple(sorted(set(masked.values()), key=len, reverse=True)),
            tuple(sorted(masked)),
        )

    def mask(self, text: str) -> str:
        for literal in self._literals:
            text = text.replace(literal, MASK)
        for shape in secret_shapes():
            text = re.sub(shape.pattern, MASK, text)
        return text


# --- writing artifacts ---------------------------------------------------------------------


class ArtifactWriter:
    """The only thing in this module that opens a file for writing.

    Masking and containment live here rather than at the call sites, so neither is
    something a future writer can forget to do.
    """

    def __init__(self, root: Path, masker: Masker | None = None) -> None:
        self.root = Path(root)
        self.masker = masker if masker is not None else Masker.from_env()

    def _target(self, rel: str) -> Path:
        relative = PurePosixPath(rel)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ContractError(f"refusing to write outside the artifacts directory: {rel}")
        final = self.root / rel
        if not final.resolve().is_relative_to(self.root.resolve()):
            raise ContractError(f"refusing to write outside the artifacts directory: {rel}")
        final.parent.mkdir(parents=True, exist_ok=True)
        return final

    def write_text(self, rel: str, text: str) -> Path:
        target = self._target(rel)
        temp = target.with_name(f"{target.name}.tmp{os.getpid()}")
        temp.write_text(self.masker.mask(text), encoding="utf-8")
        os.replace(temp, target)
        return target

    def append_line(self, rel: str, text: str) -> Path:
        target = self._target(rel)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(self.masker.mask(text).rstrip("\n") + "\n")
        return target

    def reserve(self, rel: str) -> Path:
        """A path a child process may write to. Contained like everything else."""
        return self._target(rel)

    def ensure(self, rel: str) -> Path:
        target = self._target(rel)
        if not target.exists():
            target.write_text("", encoding="utf-8")
        return target


def record_command(writer: ArtifactWriter, criterion_id: str, phase: str, run: Run) -> None:
    at = now_iso()
    writer.append_line(
        "commands.jsonl",
        json.dumps(
            {
                "at": at,
                "criterion": criterion_id,
                "phase": phase,
                "command": shlex.join(run.argv),
                "exit_code": run.exit_code,
                "timed_out": run.timed_out,
                "spawn_error": run.spawn_error,
                "truncated": run.truncated,
                "output": run.output,
            },
            ensure_ascii=False,
        ),
    )
    writer.append_line(
        "commands.log",
        f"[{at}] {criterion_id} {phase} exit={run.exit_code}\n"
        f"$ {shlex.join(run.argv)}\n{run.output}\n{'-' * 60}",
    )


# --- phase records -------------------------------------------------------------------------


def state_rel(criterion_id: str, phase: str) -> str:
    return f"state/{criterion_id}.{phase}.json"


# 19 §4 names `verify_runs[].at` as one of the fields without which lead time per contract
# cannot be derived at all. It has to accumulate across runs, and a per-criterion record
# holds only the latest, so the phase appends here and `render` reads it back — which
# keeps manifest.json derived from the state directory rather than merged into.
RUNS_REL = "state/verify-runs.jsonl"


def append_run(writer: ArtifactWriter, phase: str) -> None:
    writer.append_line(RUNS_REL, json.dumps({"phase": phase, "at": now_iso()}))


# `created_at` used to be `now_iso()` at every render, which made it the time of the last
# write rather than of the first. 19 §4 names it as one of the fields lead time per
# contract is derived from, and a value that moves derives nothing. Written once, into the
# same state directory the rest of the manifest comes from.
CREATED_REL = "state/created.json"


def ensure_created(writer: ArtifactWriter) -> None:
    if not (writer.root / CREATED_REL).is_file():
        writer.write_text(CREATED_REL, json.dumps({"at": now_iso()}) + "\n")


def read_created(artifacts_root: Path) -> str | None:
    path = artifacts_root / CREATED_REL
    if not path.is_file():
        return None
    return str(json.loads(path.read_text(encoding="utf-8"))["at"])


def read_runs(artifacts_root: Path) -> list[dict]:
    path = artifacts_root / RUNS_REL
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_state(writer: ArtifactWriter, criterion_id: str, phase: str, payload: dict) -> Path:
    """Write one phase's record. The path comes from the record, never from the caller."""
    document = {"criterion": criterion_id, "phase": phase, "at": now_iso(), **payload}
    return writer.write_text(
        state_rel(criterion_id, phase),
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
    )


def read_state(artifacts_root: Path, criterion_id: str, phase: str) -> dict | None:
    path = artifacts_root / state_rel(criterion_id, phase)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"state record {path} is not readable: {exc}") from exc


def is_iso_utc(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == UTC.utcoffset(None)


# --- pytest reports ------------------------------------------------------------------------


def parse_junit(path: Path) -> dict | None:
    """Counts from a junit report, or None when there is no usable report.

    A pytest exit code cannot separate "every test was skipped" from "the tests
    passed" — both are 0. C-07 needs that separation, so the verdict is taken from the
    report and the exit code is only one of the inputs.
    """
    if not path.is_file():
        return None
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    counts = {"total": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            counts["total" if key == "tests" else key] += int(suite.get(key, 0))
    counts["executed"] = counts["total"] - counts["skipped"]
    return counts


def run_check(
    crit: Criterion, *, cwd: Path, writer: ArtifactWriter, phase: str
) -> tuple[Run, dict | None]:
    """Run a criterion's check, collecting a test report where the kind provides one."""
    match crit.check:
        case PytestCheck(argv):
            report = writer.reserve(f"state/reports/{crit.id}.{phase}.xml")
            report.unlink(missing_ok=True)
            run = run_argv((*argv, f"--junitxml={report}"), cwd=cwd)
            try:
                return run, parse_junit(report)
            finally:
                report.unlink(missing_ok=True)
        case CommandCheck(argv):
            return run_argv(argv, cwd=cwd), None
        case HumanCheck():
            raise ContractError(f"{crit.id}: a human criterion is not executed")


# --- verify ----------------------------------------------------------------------------------


def verify_verdict(crit: Criterion, run: Run, report: dict | None) -> tuple[str, str]:
    if run.spawn_error is not None:
        return FAIL, f"could not start: {run.spawn_error}"
    if run.timed_out:
        return FAIL, f"timed out after {COMMAND_TIMEOUT_SEC}s"
    if isinstance(crit.check, PytestCheck):
        if report is None:
            return FAIL, "no test report was produced"
        if report["executed"] < 1:
            return FAIL, f"no test executed ({report['skipped']} skipped)"
        if report["failures"] or report["errors"]:
            return FAIL, f"{report['failures']} failed, {report['errors']} errored"
    if run.exit_code != 0:
        return FAIL, f"exit {run.exit_code}"
    return PASS, ""


def cmd_verify(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    root = repo_root(contract_path)
    writer = ArtifactWriter(artifacts_dir(root, contract.feature))

    ensure_created(writer)
    append_run(writer, "verify")
    failed = False
    for crit in contract.criteria:
        if crit.is_human:
            continue
        run, report = run_check(crit, cwd=root, writer=writer, phase="verify")
        status, note = verify_verdict(crit, run, report)
        record_command(writer, crit.id, "verify", run)
        write_state(
            writer,
            crit.id,
            "verify",
            {
                "status": status,
                "note": note,
                "argv": list(run.argv),
                "exit_code": run.exit_code,
                "report": report,
            },
        )
        print(f"{status} {crit.id}")
        failed |= status != PASS

    render(writer, contract, root)
    return EXIT_GATE if failed else EXIT_OK


# --- human verdicts ---------------------------------------------------------------------------


def cmd_human(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    root = repo_root(contract_path)
    writer = ArtifactWriter(artifacts_dir(root, contract.feature))
    ensure_created(writer)

    matches = [c for c in contract.criteria if c.id == args.id]
    if not matches:
        raise ContractError(f"no criterion {args.id!r} in this contract")
    crit = matches[0]
    if not crit.is_human:
        raise ContractError(f"{crit.id} is not a `verify: human` criterion")

    # Checked here as well as when the record is read: without this, `--author ""` was
    # accepted, printed PASS, and exited 0 while the REPORT.md the same call rendered
    # said PENDING-HUMAN. argparse requires the flag, not a value behind it.
    author = args.author.strip()
    if not author:
        raise ContractError("a verdict needs an author — one without it is not a verdict")

    status = PASS if args.verdict == "pass" else FAIL
    write_state(
        writer,
        crit.id,
        "human",
        {
            "status": status,
            "verdict": args.verdict,
            "author": author,
            "note": args.note or "",
        },
    )
    # No row in commands.jsonl: 19 defines that file as one object per executed command,
    # and a verdict is not one. It lives in its own phase record and in manifest.json.
    print(f"{status} {crit.id} ({args.verdict} by {args.author})")
    render(writer, contract, root)
    return EXIT_OK if status == PASS else EXIT_GATE


# --- the criterion view shared by report and gate ------------------------------------------------


def criterion_status(artifacts_root: Path, crit: Criterion) -> tuple[str, bool, str]:
    """(status, red requirement satisfied, note) for one criterion.

    `red_ok` starts false for a machine criterion and is only made true by a record
    that says RED. There is no branch where a missing record counts as satisfied, and
    that branch is what let the withdrawn runner's gate open.
    """
    if crit.is_human:
        record = read_state(artifacts_root, crit.id, "human")
        if record is None:
            return PENDING_HUMAN, True, "awaiting a verdict"
        if record.get("verdict") == "reject":
            return FAIL, True, str(record.get("note") or "rejected")
        # The same predicate the write path applies, not a weaker one: bare truthiness
        # let a hand-edited `"   "` — the exact value `human` refuses — read as a pass,
        # and so did a mapping. A read check laxer than the write check checks nothing.
        author = record.get("author")
        if (
            record.get("verdict") == "pass"
            and isinstance(author, str)
            and author.strip()
            and is_iso_utc(record.get("at"))
        ):
            return PASS, True, ""
        return PENDING_HUMAN, True, "verdict lacks an author or a UTC timestamp"

    verify = read_state(artifacts_root, crit.id, "verify")
    # 19 fixes the status vocabulary at four words, so "verify has not run" is reported
    # as FAIL with the reason in the note rather than as a fifth word of our own.
    status = str(verify["status"]) if verify else FAIL
    note = str(verify.get("note", "")) if verify else "verify has not run"

    if crit.is_guard:
        return status, True, note
    red = read_state(artifacts_root, crit.id, "red")
    red_ok = red is not None and red.get("status") == RED
    if not red_ok:
        note = (f"{note}; " if note else "") + f"red={red['status'] if red else 'not run'}"
    return status, red_ok, note


# --- report and manifest -----------------------------------------------------------------------


def render(writer: ArtifactWriter, contract: Contract, root: Path) -> None:
    """Rebuild REPORT.md and manifest.json from the state directory.

    Both are derived, so nothing is merged into them and no phase can lose another's
    entry by writing its own.
    """
    rows = []
    for crit in contract.criteria:
        status, red_ok, note = criterion_status(writer.root, crit)
        if status == PASS and not red_ok:
            # It passed its own check but the red gate does not back it, so it is not
            # done. Reported with a sanctioned word; the note carries the reason.
            status = FAIL
        rows.append(
            f"| {crit.id} | {status} | `{cell(display_command(crit.check))}` | {cell(note)} |"
        )

    writer.write_text(
        "REPORT.md",
        "\n".join(
            [
                f"# {contract.feature.value}",
                "",
                "| id | status | verify | note |",
                "|---|---|---|---|",
                *rows,
                "",
            ]
        ),
    )
    writer.write_text(
        "manifest.json",
        json.dumps(
            {
                "created_at": read_created(writer.root) or now_iso(),
                "commit": git("rev-parse", "HEAD", cwd=root),
                "tree_clean": not git("status", "--porcelain", cwd=root),
                "base": contract.base,
                "done_level": contract.done_level,
                "human_verdicts": [
                    {
                        "criterion": crit.id,
                        "verdict": record.get("verdict"),
                        "author": record.get("author"),
                        "at": record.get("at"),
                        "note": record.get("note", ""),
                    }
                    for crit in contract.criteria
                    if crit.is_human
                    and (record := read_state(writer.root, crit.id, "human")) is not None
                ],
                "verify_runs": read_runs(writer.root),
                "bypass": contract.bypass,
                "environment": {"python": sys.version.split()[0], "platform": sys.platform},
                "masked_env_names": list(writer.masker.names),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
    )
    for name in ("commands.jsonl", "commands.log"):
        writer.ensure(name)


# --- the red check ------------------------------------------------------------------------


def git_quiet(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@contextmanager
def base_worktree(root: Path, base_sha: str) -> Iterator[Path]:
    """A detached checkout of base, outside the repository and removed afterwards.

    This is C-12's one declared exception. The working tree is never touched, so a
    crashed run leaves nothing to recover — `remove --force` alone leaves the
    registration behind, which is why `prune` follows it.
    """
    holder = Path(tempfile.mkdtemp(prefix="conv-red-"))
    worktree = holder / "base"
    git("worktree", "add", "--detach", "--quiet", str(worktree), base_sha, cwd=root)
    try:
        yield worktree
    finally:
        git_quiet("worktree", "remove", "--force", str(worktree), cwd=root)
        git_quiet("worktree", "prune", cwd=root)
        shutil.rmtree(holder, ignore_errors=True)


def pytest_selection(
    argv: tuple[str, ...], cwd: Path, writer: ArtifactWriter, criterion_id: str
) -> list[str] | None:
    """The files a pytest criterion selects, asked of pytest rather than guessed.

    Guessing test paths from a name pattern is the same species of mistake as reading
    the runner kind out of the command string: it works for one project's layout.

    The probe is a command the runner executes, so it gets a row in `commands.jsonl`
    like any other. A criterion ruled out here has no other row at all, and its verdict
    rests entirely on this one — leaving it unrecorded made that verdict unauditable.
    """
    # --rootdir pins what the printed paths are relative to. Without it pytest reports
    # against its own discovered rootdir — the nearest pyproject.toml above the test
    # paths — and a repository with a nested one hands back paths that resolve to
    # nothing here. It changes no test selection, only the reporting base.
    probe = (*argv, "--collect-only", "-q", f"--rootdir={cwd}")
    run = run_argv(probe, cwd=cwd, timeout=COLLECT_TIMEOUT_SEC)
    record_command(writer, criterion_id, "red-collect", run)
    if run.spawn_error is not None or run.timed_out:
        return None
    # pytest exits 5 for "collected nothing" and non-zero otherwise for an error. Without
    # that split a test file that fails to import was recorded as a criterion selecting no
    # test, which names a different cause and sends a reader to the wrong place.
    if run.exit_code not in (0, PYTEST_EXIT_NO_TESTS):
        return None
    # Quiet collection prints `path::name`, and a command that already carried -q makes
    # it `-qq`, which prints `path: count` instead. Both are read for the path, and
    # `is_file` is what decides — a line that is not a path cannot survive it.
    files = set()
    for raw in run.output.splitlines():
        line = raw.strip()
        if not line:
            continue
        candidate = line.split("::", 1)[0]
        if candidate == line and ":" in line:
            candidate = line.rsplit(":", 1)[0]
        if (cwd / candidate).is_file():
            files.add(candidate)
    return sorted(files)


def bring_forward(root: Path, worktree: Path, relatives: list[str]) -> list[str]:
    """Copy the criterion's own test files into the base checkout.

    Copied from the working tree rather than checked out of HEAD, so a test written
    but not yet committed is what the red check runs — which is the ordinary moment
    the red check exists for.
    """
    wanted: set[str] = set()
    for relative in relatives:
        if not (root / relative).is_file():
            continue
        wanted.add(relative)
        parent = PurePosixPath(relative).parent
        while True:
            candidate = parent / "conftest.py"
            if (root / candidate).is_file():
                wanted.add(str(candidate))
            if str(parent) in (".", ""):
                break
            parent = parent.parent
    for relative in sorted(wanted):
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    return sorted(wanted)


def red_verdict_command(run: Run) -> tuple[str, str]:
    if run.spawn_error is not None:
        return NO_BASELINE, f"could not start at base: {run.spawn_error}"
    if run.timed_out:
        return NO_BASELINE, "timed out at base"
    if run.exit_code == 0:
        return NOT_RED, "passed at base — this check proves nothing about the change"
    return RED, f"failed at base (exit {run.exit_code}) as required"


def red_verdict_pytest(run: Run, report: dict | None) -> tuple[str, str]:
    if run.spawn_error is not None:
        return NO_BASELINE, f"could not start at base: {run.spawn_error}"
    if run.timed_out:
        return NO_BASELINE, "timed out at base"
    # The verdict comes from the report, never from matching words in the output: a test
    # whose own subject is an exception type prints that name when it fails, and reading
    # it as a broken file turned an ordinary RED into a permanently unpassable criterion.
    if report is None:
        return NO_BASELINE, "no test report was produced at base"
    if report["total"] == 0:
        return NO_BASELINE, "no test was collected at base"
    if report["executed"] == 0:
        return NO_BASELINE, f"every test skipped at base ({report['skipped']})"
    if report["failures"] or report["errors"]:
        return RED, f"{report['failures']} failed, {report['errors']} errored at base"
    return NOT_RED, "passed at base — this test proves nothing about the change"


def cmd_red(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    root = repo_root(contract_path)
    if not contract.base:
        raise ContractError("contract has no `base`; the red check needs a commit to check against")
    base_sha = git("rev-parse", "--verify", f"{contract.base}^{{commit}}", cwd=root)
    writer = ArtifactWriter(artifacts_dir(root, contract.feature))
    ensure_created(writer)

    failed = False
    with base_worktree(root, base_sha) as worktree:
        for crit in contract.criteria:
            if crit.is_human:
                continue
            if crit.is_guard:
                write_state(
                    writer,
                    crit.id,
                    "red",
                    {
                        "status": EXEMPT_GUARD,
                        "note": "standing invariant: legitimately holds at base",
                        "base": base_sha,
                    },
                )
                print(f"{EXEMPT_GUARD} {crit.id}")
                continue

            git_quiet("reset", "--hard", "--quiet", base_sha, cwd=worktree)
            git_quiet("clean", "-fdq", cwd=worktree)

            brought: list[str] = []
            match crit.check:
                case PytestCheck(argv):
                    selection = pytest_selection(argv, root, writer, crit.id)
                    if selection is None:
                        status, note, report = NO_BASELINE, "could not collect at head", None
                    elif not selection:
                        status, note, report = NO_BASELINE, "the criterion selects no test", None
                    else:
                        brought = bring_forward(root, worktree, selection)
                        report_path = writer.reserve(f"state/reports/{crit.id}.red.xml")
                        report_path.unlink(missing_ok=True)
                        run = run_argv((*argv, f"--junitxml={report_path}"), cwd=worktree)
                        try:
                            report = parse_junit(report_path)
                        finally:
                            # The report is not evidence and is not masked, so it does
                            # not outlive the phase that asked for it.
                            report_path.unlink(missing_ok=True)
                        record_command(writer, crit.id, "red", run)
                        status, note = red_verdict_pytest(run, report)
                case CommandCheck(argv):
                    run = run_argv(argv, cwd=worktree)
                    report = None
                    record_command(writer, crit.id, "red", run)
                    status, note = red_verdict_command(run)

            write_state(
                writer,
                crit.id,
                "red",
                {
                    "status": status,
                    "note": note,
                    "base": base_sha,
                    "argv": list(crit.check.argv),
                    "brought_forward": brought,
                    "report": report,
                },
            )
            print(f"{status} {crit.id}")
            failed |= status != RED

    render(writer, contract, root)
    return EXIT_GATE if failed else EXIT_OK


# --- the status gate ----------------------------------------------------------------------


def other_pending_features(root: Path, current: Feature) -> list[str]:
    """Features under `artifacts/` still holding a human verdict, other than this one.

    The runner sees one contract at a time, so a contract awaiting verdicts can be
    replaced by the next one with nothing noticing — which happened three times in the
    session that added this. It cannot refuse: a workflow that collects every verdict at
    the end has several contracts pending on purpose. So it says what it sees.
    """
    base = root / "artifacts"
    if not base.is_dir():
        return []
    pending = []
    for state in sorted(base.glob("*/state")):
        feature = state.parent.name
        if feature == current.value:
            continue
        for record in state.glob("*.human.json"):
            try:
                document = json.loads(record.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if document.get("status") == PENDING_HUMAN:
                pending.append(feature)
                break
        else:
            # A criterion with no human record at all is pending too, but this function
            # only sees the artifacts — the other contract's criteria are not readable
            # from here, so an absent record cannot be distinguished from an absent
            # criterion. Reporting what is recorded is the honest half.
            continue
    return pending


def report_other_pending(root: Path, current: Feature) -> None:
    for feature in other_pending_features(root, current):
        print(f"NOTE {feature} still awaits a human verdict — close it before deleting it")


def cmd_status(args: argparse.Namespace) -> int:
    """Read-only on purpose.

    A status command that writes REPORT.md can never observe REPORT.md missing, and
    C-08 requires exactly that observation.
    """
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    root = repo_root(contract_path)
    report_other_pending(root, contract.feature)
    artifacts = artifacts_dir(root, contract.feature)

    blocking = []
    for crit in contract.criteria:
        status, red_ok, note = criterion_status(artifacts, crit)
        if status != PASS:
            blocking.append(f"{crit.id}: {status}" + (f" — {note}" if note else ""))
        elif not red_ok:
            blocking.append(f"{crit.id}: PASS but the red check does not back it — {note}")
    blocking += [
        f"evidence artifact missing: {name}"
        for name in EVIDENCE_FILES
        if not (artifacts / name).is_file()
    ]

    for problem in blocking:
        print(f"BLOCK {problem}")
    if blocking:
        return EXIT_GATE
    print(f"OK {contract.feature.value}: {len(contract.criteria)} criteria")
    return EXIT_OK


# --- lint ----------------------------------------------------------------------------


def quality_problems(contract: Contract) -> list[str]:
    """Rules a contract can break while still being readable — reported, not raised."""
    problems = []
    if not any(c.kind == "negative" for c in contract.criteria):
        problems.append("no criterion has `kind: negative` — nothing states what must not happen")
    if not contract.out_of_scope:
        problems.append("out_of_scope is empty — an unstated boundary is the one that gets crossed")
    return problems


def cmd_lint(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)
    report_other_pending(repo_root(contract_path), contract.feature)
    problems = quality_problems(contract)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        return EXIT_GATE
    print(f"OK {contract.feature.value}: {len(contract.criteria)} criteria")
    return EXIT_OK


# --- cli -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    # --contract is accepted before or after the subcommand. SUPPRESS on the child copy
    # keeps an absent option from overwriting a value given before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--contract", default=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(prog="contract", description="Run a work contract.")
    parser.add_argument("--contract", default="contract.md", help="path to contract.md")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("lint", parents=[common], help="validate the contract").set_defaults(
        func=cmd_lint
    )
    sub.add_parser("red", parents=[common], help="check each test fails at base").set_defaults(
        func=cmd_red
    )
    sub.add_parser("verify", parents=[common], help="run every machine check").set_defaults(
        func=cmd_verify
    )
    sub.add_parser("status", parents=[common], help="gate on the recorded result").set_defaults(
        func=cmd_status
    )

    human = sub.add_parser("human", parents=[common], help="record a human verdict")
    human.add_argument("--id", required=True)
    human.add_argument("--verdict", required=True, choices=("pass", "reject"))
    human.add_argument("--author", required=True)
    human.add_argument("--note", default="")
    human.set_defaults(func=cmd_human)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return EXIT_CONTRACT
    except Exception:
        # Distinct from EXIT_GATE on purpose: an uncaught exception exits 1 by default,
        # which would read as "a criterion failed".
        traceback.print_exc()
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
