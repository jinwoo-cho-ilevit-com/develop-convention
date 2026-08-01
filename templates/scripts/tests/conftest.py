"""Fixtures for the contract toolkit tests.

`contract.py` is a standalone PEP 723 script, not an installed package, so it is
loaded by path. The git fixtures build throwaway repositories because `red` is
only meaningful against real commit history.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "contract.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("contract_tool", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclass resolution looks the module up in sys.modules, so register it
    # before executing rather than after.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contract_tool = _load_module()


@pytest.fixture
def tool():
    return contract_tool


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return proc.stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An initialised repo with one commit, isolated from the developer's config."""
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "test")
    git(root, "config", "commit.gpgsign", "false")
    # The developer's global core.hooksPath carries a commit-msg hook that
    # enforces Conventional Commits; fixture commits are not real commits.
    git(root, "config", "core.hooksPath", str(hooks))
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    return root


def crit(cid: str, verify: str, kind: str = "functional", **extra: str) -> str:
    """Build one criterion block. Keeps tests readable and off the line limit."""
    lines = [
        f"  - id: {cid}",
        f'    text: "{cid} placeholder"',
        f'    verify: "{verify}"',
        f"    kind: {kind}",
        *(f"    {k}: {v}" for k, v in extra.items()),
    ]
    return "\n".join(lines) + "\n"


def write_contract(root: Path, criteria: str, **fields: str) -> Path:
    extra = "".join(f"{k}: {v}\n" for k, v in fields.items())
    path = root / "contract.md"
    path.write_text(
        "---\n"
        "schema_version: 1\n"
        "feature: sample\n"
        "done_level: reviewed\n"
        f"{extra}"
        "criteria:\n"
        f"{criteria}"
        "out_of_scope:\n"
        "  - nothing else\n"
        "---\n\n"
        "# sample\n",
        encoding="utf-8",
    )
    return path


def run_tool(root: Path, *argv: str) -> int:
    """Invoke a subcommand with cwd set to the repo, as a user would."""
    import os

    prev = Path.cwd()
    os.chdir(root)
    try:
        return contract_tool.main(list(argv))
    finally:
        os.chdir(prev)


PYTEST_CMD = f"{sys.executable} -m pytest -p no:cacheprovider"
