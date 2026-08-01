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
import re
import shlex
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

import yaml

SCHEMA_VERSION = 1

FEATURE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CRITERION_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")

RUNNER_KINDS = ("pytest", "command")
KINDS = ("functional", "nonfunctional", "negative")
DONE_LEVELS = ("auto", "reviewed", "proven", "bypassed")
RED_MODES = ("required", "guard")
REQUIRED_FIELDS = ("feature", "done_level", "criteria", "out_of_scope")

# Refused rather than ignored: a contract carrying one of these was written by someone
# who believes it is enforced, and this runner does not implement it.
UNSUPPORTED_FIELDS = ("lanes", "sequential_owner", "integration", "checkpoints")

# A verify command is executed as an argument vector, so these would become literal
# arguments rather than doing what the author meant.
SHELL_TOKENS = frozenset({"|", "||", "&&", ";", ";;", "&", ">", ">>", "<", "<<", "(", ")"})
SHELL_FRAGMENTS = ("`", "$(")

EXIT_OK = 0
EXIT_GATE = 1  # the runner answered, and the answer is no
EXIT_CONTRACT = 2  # the runner could not answer
EXIT_INTERNAL = 3  # the runner broke


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


# --- parsing -------------------------------------------------------------------------


def split_front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ContractError("contract has no front matter: the first line must be `---`")
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    raise ContractError("contract front matter is never closed by a `---` line")


def _check_of(raw_verify: object, raw_runner: object, cid: str) -> Check:
    if not isinstance(raw_verify, str) or not raw_verify.strip():
        raise ContractError(f"{cid}: verify must be a non-empty string, or `human`")
    verify = raw_verify.strip()

    if verify == "human":
        if raw_runner is not None:
            raise ContractError(f"{cid}: a human criterion takes no runner")
        return HumanCheck()

    if raw_runner is None:
        raise ContractError(f"{cid}: runner is required unless verify is `human`")
    if raw_runner not in RUNNER_KINDS:
        raise ContractError(f"{cid}: runner {raw_runner!r} is not one of {RUNNER_KINDS}")

    for fragment in SHELL_FRAGMENTS:
        if fragment in verify:
            raise ContractError(
                f"{cid}: verify contains {fragment!r}, which needs a shell; "
                "this runner executes an argument vector"
            )
    # punctuation_chars splits shell operators into tokens of their own while leaving a
    # quoted `-k 'a; b'` as one argument, so an operator is detected only where it would
    # actually have acted as one.
    lexer = shlex.shlex(verify, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        argv = list(lexer)
    except ValueError as exc:
        raise ContractError(f"{cid}: verify cannot be split into arguments: {exc}") from exc
    if not argv:
        raise ContractError(f"{cid}: verify is empty after splitting")
    shell_tokens = sorted(SHELL_TOKENS.intersection(argv))
    if shell_tokens:
        raise ContractError(
            f"{cid}: verify contains the shell operator(s) {shell_tokens}; "
            "split it into separate criteria or a script"
        )

    argv_tuple = tuple(argv)
    return PytestCheck(argv_tuple) if raw_runner == "pytest" else CommandCheck(argv_tuple)


def _criterion_of(raw: object, seen: set[str]) -> Criterion:
    if not isinstance(raw, dict):
        raise ContractError(f"each criterion must be a mapping, got {type(raw).__name__}")
    cid = raw.get("id")
    if not isinstance(cid, str) or not CRITERION_ID_RE.fullmatch(cid):
        raise ContractError(f"criterion id {cid!r} is not a plain slug — ids become filenames")
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

    if raw.get("hermetic") is False:
        # templates/contract.md documents this as a red exemption, but C-05 admits only
        # a human criterion or `red: guard`. Refused until that is reconciled.
        raise ContractError(
            f"{cid}: `hermetic: false` is not implemented by this runner; "
            "use `red: guard` for a standing invariant"
        )

    return Criterion(
        id=cid,
        text=text,
        check=_check_of(raw.get("verify"), raw.get("runner"), cid),
        kind=kind,
        red=red,
    )


def load_contract(path: Path | str) -> Contract:
    """Read and validate a contract. Raises rather than returning something partial."""
    path = Path(path)
    if not path.is_file():
        raise ContractError(f"contract not found: {path}")

    try:
        data = yaml.safe_load(split_front_matter(path.read_text(encoding="utf-8")))
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

    done_level = data["done_level"]
    if done_level not in DONE_LEVELS:
        raise ContractError(f"done_level {done_level!r} is not one of {DONE_LEVELS}")

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


# --- lint ----------------------------------------------------------------------------


def quality_problems(contract: Contract) -> list[str]:
    """Rules a contract can break while still being readable — reported, not raised."""
    problems = []
    if not any(c.kind == "negative" for c in contract.criteria):
        problems.append("no criterion has `kind: negative` — nothing states what must not happen")
    if not contract.out_of_scope:
        problems.append("out_of_scope is empty — an unstated boundary is the one that gets crossed")
    return problems


def cmd_lint(contract_path: Path) -> int:
    contract = load_contract(contract_path)
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

    lint = sub.add_parser("lint", parents=[common], help="validate the contract")
    lint.set_defaults(func=cmd_lint)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(Path(args.contract))
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
