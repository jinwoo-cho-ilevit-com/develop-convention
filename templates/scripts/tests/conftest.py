"""Fixtures for the contract runner tests.

Every test works inside a throwaway git repository so the runner's real behaviour —
committing, resolving a base, writing under artifacts/ — is exercised rather than mocked.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))


def git(*args: str, cwd: Path) -> str:
    out = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An initialised git repository with one commit, usable as a base."""
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "--quiet", "--initial-branch", "main", cwd=root)
    git("config", "user.email", "test@example.invalid", cwd=root)
    git("config", "user.name", "test", cwd=root)
    (root / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
    git("add", ".gitignore", cwd=root)
    git("commit", "--quiet", "-m", "base", cwd=root)
    return root


@pytest.fixture
def base_sha(repo: Path) -> str:
    return git("rev-parse", "HEAD", cwd=repo)


def write_contract(repo: Path, criteria: list[dict], **front) -> Path:
    """Write a contract.md whose front matter carries the given criteria."""
    import yaml

    doc = {
        "schema_version": 1,
        "feature": front.pop("feature", "sample"),
        "done_level": front.pop("done_level", "reviewed"),
        "criteria": criteria,
        "out_of_scope": front.pop("out_of_scope", ["nothing"]),
        **front,
    }
    path = repo / "contract.md"
    path.write_text(
        "---\n" + yaml.safe_dump(doc, sort_keys=False) + "---\n\n# sample\n",
        encoding="utf-8",
    )
    return path


def passing_at_head_only(repo: Path, name: str = "marker") -> str:
    """Commit a file after base and return a verify command that only passes with it.

    A criterion whose command behaves the same at base and at HEAD can never be red,
    so a red-gate test needs the two to differ the way a real new test does.
    """
    (repo / name).write_text("present\n", encoding="utf-8")
    git("add", name, cwd=repo)
    git("commit", "--quiet", "-m", f"add {name}", cwd=repo)
    return f"test -f {name}"


def criterion(cid: str, **over) -> dict:
    """A minimal valid criterion, overridable per test."""
    base = {
        "id": cid,
        "text": f"THE system SHALL satisfy {cid}.",
        "verify": "true",
        "kind": "functional",
        "runner": "command",
    }
    base.update(over)
    return base
