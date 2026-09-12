"""The sample run of `scripts/check-docs.py`, the entry point that holds the document invariants.

Two runs of the real script through a subprocess: this repository, which must be clean, and a
copy carrying one deliberate break per check, which must report every one of them and nothing
else. The sabotage table is what keeps a check from quietly becoming an assertion nothing can
fail — a check that stops firing shows up here as a missing row, not as a still-green run.
"""

import subprocess
import sys

import pytest
from _repo import ROOT

CLI = ROOT / "scripts" / "check-docs.py"

# (the check, file, text to replace, replacement, the (file, message) pairs the run must
# report). The replacement is applied to the first occurrence, so `old` need not be unique.
SABOTAGE = [
    (
        "core rules is the first body heading",
        "conventions/02-config.md",
        "## Core Rules",
        "## Rules",
        [("conventions/02-config.md", "the first body heading is '## Rules'")],
    ),
    (
        "no tool-call residue",
        "CLAUDE.md",
        "## Verification\n",
        "## Verification\n\n</invoke>\n",
        [("CLAUDE.md", "tool-call residue '</invoke>'")],
    ),
    (
        "doc map links resolve",
        "README.md",
        "](templates/pyproject.toml)",
        "](templates/pyproject-gone.toml)",
        [("README.md", "links to templates/pyproject-gone.toml, which does not exist")],
    ),
    (
        "every convention sits under a doc map group",
        "README.md",
        "| [00-principles.md](conventions/00-principles.md) |",
        "| 00-principles.md |",
        [("README.md", "no group table row names conventions/00-principles.md")],
    ),
    (
        "links inside a convention resolve",
        "conventions/00-principles.md",
        "(→ [01-structure-naming.md](01-structure-naming.md))",
        "(→ [01-structure-naming.md](01-structure-naming-gone.md))",
        [
            (
                "conventions/00-principles.md",
                "links to 01-structure-naming-gone.md, which does not exist",
            )
        ],
    ),
    (
        "every convention is sourced from the rule summary",
        "README.md",
        "### Config ([02](conventions/02-config.md))",
        "### Config",
        [
            ("README.md", "no summary heading names conventions/02-config.md as its source"),
            ("README.md", "summary section links no source: '### Config'"),
        ],
    ),
    (
        "the nav lists every convention",
        "mkdocs.yml",
        "      - conventions/05-performance.md\n",
        "",
        [("mkdocs.yml", "the nav omits conventions/05-performance.md")],
    ),
    (
        "the nav lists what a project still takes",
        "mkdocs.yml",
        "      - templates/AGENTS.md\n",
        "",
        [("mkdocs.yml", "the nav omits templates/AGENTS.md")],
    ),
    (
        "nothing names a retired mechanism",
        "templates/AGENTS.md",
        "# AGENTS.md",
        "# AGENTS.md\n\nBootstrap this project with conv-init.",
        [("templates/AGENTS.md", "names the retired mechanism 'conv-init'")],
    ),
    (
        "the README skill table names every skill",
        "README.md",
        "| `commit` | A commit",
        "| `commit-protocol` | A commit",
        [("README.md", "the skill table omits `commit`")],
    ),
    (
        "every command declares a description",
        "commands/setup.md",
        "description:",
        "summary:",
        [("commands/setup.md", "declares no description")],
    ),
    (
        "every skill declares its directory as its name",
        "skills/commit/SKILL.md",
        "name: commit\n",
        "name: commits\n",
        [("skills/commit/SKILL.md", "declares a name that is not its directory 'commit'")],
    ),
    (
        "every skill link resolves",
        "skills/commit/SKILL.md",
        "](../code-and-config/SKILL.md)",
        "](../code-and-config/SKILL-gone.md)",
        [
            (
                "skills/commit/SKILL.md",
                "links to ../code-and-config/SKILL-gone.md, which does not exist",
            )
        ],
    ),
    (
        "no skill or command copies convention text",
        "skills/ml-pipeline/SKILL.md",
        "# ml-pipeline — Stages, Throughput, Experiments, Self-Hosted Models\n",
        "# ml-pipeline — Stages, Throughput, Experiments, Self-Hosted Models\n\n"
        "CI verifies GPU code paths by running the sample run on CPU, without a GPU.\n",
        [("skills/ml-pipeline/SKILL.md", "copies convention text")],
    ),
    (
        "every convention is routed by exactly one skill",
        "skills/verify-and-review/SKILL.md",
        "# verify-and-review",
        "# verify-and-review\n\nAlso [17](../../conventions/17-commit-protocol.md).",
        [
            (
                "skills/commit/SKILL.md",
                "17-commit-protocol.md is routed by more than one skill: commit, verify-and-review",
            )
        ],
    ),
    (
        "section cross references resolve",
        "conventions/06-testing-verification.md",
        "[18-work-contract.md](18-work-contract.md) §5, and its sample",
        "[18-work-contract.md](18-work-contract.md) §55, and its sample",
        [
            (
                "conventions/06-testing-verification.md",
                "18-work-contract.md has no §55 to point at",
            )
        ],
    ),
    (
        "section numbering is contiguous",
        "conventions/05-performance.md",
        "### 5.",
        "### 6.",
        [("conventions/05-performance.md", "section numbering skips: [1, 2, 3, 4, 6]")],
    ),
    (
        "an as-of stamp is inside the reverification window",
        "conventions/02-config.md",
        "## Details",
        "## Details\n\nA claim last checked long ago (as of: 2024-01).",
        [("conventions/02-config.md", "the stamp 2024-01 is older than 3 months")],
    ),
]


def run(repo) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo", str(repo)], capture_output=True, text=True
    )


def test_the_repository_passes_every_document_check():
    """The sample run. Whatever the checks are, this repository is what they describe."""
    result = run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "document checks clean" in result.stdout


@pytest.fixture(scope="module")
def broken(tmp_path_factory):
    """A copy of the tracked tree with every break applied, run once and shared.

    Tracked files only, re-initialised as a repository, because the retired-mechanism check
    reads `git ls-files`. The copy carries `scripts/check-docs.py` too, so that the check's
    exclusion of its own tombstone list is exercised rather than assumed.
    """
    copy = tmp_path_factory.mktemp("broken")
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    for name in filter(None, listed):
        source = ROOT / name
        if not source.is_file():
            continue
        target = copy / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    (copy / "scripts").mkdir(exist_ok=True)
    (copy / "scripts" / CLI.name).write_bytes(CLI.read_bytes())

    for check, name, old, new, _ in SABOTAGE:
        path = copy / name
        body = path.read_text(encoding="utf-8")
        assert old in body, f"the sabotage for {check} no longer matches: {old!r}"
        path.write_text(body.replace(old, new, 1), encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=copy, check=True)
    subprocess.run(["git", "add", "-A"], cwd=copy, check=True)
    return run(copy)


@pytest.mark.parametrize("case", SABOTAGE, ids=lambda case: case[0])
def test_the_run_reports_every_deliberate_break(case, broken):
    """A row per check, so each can be observed failing on its own
    (→ conventions/06-testing-verification.md §2).
    """
    assert broken.returncode == 1, broken.stdout + broken.stderr
    for path, message in case[4]:
        found = [
            line
            for line in broken.stdout.splitlines()
            if line.startswith(f"{path}:") and message in line
        ]
        assert found, f"{case[0]}: no line reports {message!r} against {path}\n{broken.stdout}"


def test_the_run_reports_nothing_beyond_the_deliberate_breaks(broken):
    """The count is what separates a check that fired from one that fires on anything."""
    expected = sum(len(case[4]) for case in SABOTAGE)
    reported = [line for line in broken.stdout.splitlines() if line.strip()]
    assert len(reported) == expected, "\n".join(reported)
