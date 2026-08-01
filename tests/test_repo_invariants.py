"""The rules this repository states about itself, executed rather than remembered.

`CLAUDE.md` carries a verification checklist and `conventions/03` and `13` require CI
enforcement, but nothing ran either: the workflow that did was deleted as collateral in
`a078b30`, and its document checks were inline shell in YAML that no other caller could
reach. They are tests here so the contract's `verify` commands and the CI job execute the
same file, and so the red check can observe each one failing at the base commit.
"""

import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONVENTIONS = sorted((ROOT / "conventions").glob("*.md"))
# 17 is the declared exception: its commit-body template and examples are Korean on
# purpose, because the commit policy is an English header over a Korean body.
RESIDUE = ("</content>", "</invoke>", "</antml")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def mkdocs_config() -> dict:
    return yaml.safe_load(read("mkdocs.yml"))


def nav_paths(node) -> list[str]:
    """Every document path in the nav tree, whatever depth it sits at."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [p for value in node.values() for p in nav_paths(value)]
    if isinstance(node, list):
        return [p for item in node for p in nav_paths(item)]
    return []


# --- document format: CLAUDE.md's own checklist --------------------------------------


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_format_core_rules_is_the_first_body_heading(doc):
    """The section other projects excerpt verbatim has to be findable at a fixed place."""
    headings = re.findall(r"^## .*$", doc.read_text(encoding="utf-8"), flags=re.M)
    assert headings, f"{doc.name} has no `##` heading"
    assert headings[0] == "## Core Rules", f"{doc.name} opens with {headings[0]!r}"


@pytest.mark.parametrize(
    "relative",
    ["README.md", "CLAUDE.md", *[f"conventions/{d.name}" for d in CONVENTIONS]],
)
def test_format_no_tool_call_residue(relative):
    """Two docs once shipped a stray `</content>`; a committed one is invisible in review."""
    body = read(relative)
    for marker in RESIDUE:
        assert marker not in body, f"{relative} carries tool-call residue {marker!r}"


def test_format_doc_map_links_resolve():
    readme = read("README.md")
    broken = [
        m.group(1)
        for m in re.finditer(r"\]\((conventions/[^)#]+|templates/[^)#]+|adr/[^)#]+)\)", readme)
        if not (ROOT / m.group(1)).exists()
    ]
    assert not broken, f"README links to paths that do not exist: {broken}"


def test_format_doc_map_lists_every_convention():
    """A doc absent from the map is a doc nobody is routed to."""
    listed = set(re.findall(r"conventions/(\d\d-[a-z-]+\.md)", read("README.md")))
    missing = sorted({d.name for d in CONVENTIONS} - listed)
    assert not missing, f"README's doc map omits {missing}"


# --- the published site ----------------------------------------------------------------


def test_nav_lists_every_convention_doc():
    """`templates/AGENTS.md` sends an agent with no local clone to the published site.

    While the nav stopped at 17, that agent received conventions 00-17 and no work
    contract, evidence or review-gate rules at all.
    """
    listed = {p for p in nav_paths(mkdocs_config()["nav"]) if p.startswith("conventions/")}
    missing = sorted({f"conventions/{d.name}" for d in CONVENTIONS} - listed)
    assert not missing, f"mkdocs nav omits {missing}"


def test_nav_lists_the_adr_directory():
    adrs = sorted(p.name for p in (ROOT / "adr").glob("*.md"))
    assert adrs, "no ADR to publish"
    listed = set(nav_paths(mkdocs_config()["nav"]))
    missing = sorted({f"adr/{name}" for name in adrs} - listed)
    assert not missing, f"mkdocs nav omits {missing}"


def test_nav_lists_the_contract_template_and_runner():
    """18 §4 and 19 §6 describe a toolkit a reader is expected to be able to look at."""
    listed = set(nav_paths(mkdocs_config()["nav"]))
    assert "templates/contract.md" in listed


# --- conventions/03's first Core Rule ---------------------------------------------------


def floor_of(requires_python: str) -> tuple[int, int]:
    match = re.search(r"(\d+)\.(\d+)", requires_python)
    assert match, f"unreadable requires-python {requires_python!r}"
    return int(match.group(1)), int(match.group(2))


@pytest.mark.parametrize("directory", ["", "templates"])
def test_python_version_agrees_with_requires_python(directory):
    """03: `pyproject.toml` + `uv.lock` (committed) + `.python-version`.

    A project bootstrapped from `templates/` could not satisfy 03's first Core Rule,
    because the template it was bootstrapped from did not either.
    """
    base = ROOT / directory if directory else ROOT
    pinned = (base / ".python-version").read_text(encoding="utf-8").strip()
    declared = tomllib.loads((base / "pyproject.toml").read_text(encoding="utf-8"))
    assert floor_of(pinned) >= floor_of(declared["project"]["requires-python"])


# --- the ADR chain ----------------------------------------------------------------------


def test_adr_path_in_15_matches_where_adrs_live():
    """`docs/` is assembled at build time and gitignored, so an ADR there is not tracked."""
    stated = re.search(r"ADR \(`([^`]+/)NNNN-title\.md`\)", read("conventions/15-doc-tracking.md"))
    assert stated, "15 no longer states an ADR path in the form it used to"
    directory = ROOT / stated.group(1)
    assert directory.is_dir(), f"15 points at {stated.group(1)}, which does not exist"
    assert sorted(directory.glob("*.md")), f"{stated.group(1)} holds no ADR"


# --- what CLAUDE.md says this repository is ---------------------------------------------


def test_claude_md_does_not_claim_there_are_no_test_commands():
    """An agent that believes this skips the only verification the repository has."""
    assert "there are no build/test commands" not in read("CLAUDE.md")


def test_claude_md_enumerates_templates_completely():
    """The same sentence instructs the reader to check consistency with `templates/`."""
    body = read("CLAUDE.md")
    for entry in ("scripts/", "skills/"):
        assert entry in body, f"CLAUDE.md never mentions templates/{entry}"


# --- conventions/03 and 13: enforcement in CI --------------------------------------------


def workflow(name: str) -> dict:
    return yaml.safe_load(read(f".github/workflows/{name}"))


def triggers(config: dict) -> dict:
    # YAML 1.1 resolves a bare `on:` key to the boolean True, which is why this is not
    # simply `config["on"]`.
    return config.get("on") or config.get(True) or {}


def run_steps(config: dict) -> str:
    return "\n".join(
        step.get("run", "") for job in config["jobs"].values() for step in job.get("steps", [])
    )


def test_workflow_runs_on_pull_requests():
    """`main`-only means the branch a change lives on is never checked."""
    assert "pull_request" in triggers(workflow("checks.yml"))


@pytest.mark.parametrize("tool", ["ruff check", "ruff format", "pytest", "gitleaks"])
def test_workflow_runs_lint_tests_and_secret_scan(tool):
    """03:20 enforces lint in CI because local hooks can be skipped; 13:12 the same for
    secret scanning. On this machine the global `core.hooksPath` blocks `pre-commit
    install` outright, so CI is not the second line of defence — it is the only one.
    """
    assert tool in run_steps(workflow("checks.yml"))


def test_workflow_fetches_history_for_the_red_check():
    """`contract.py red` checks out the contract's base commit in a worktree."""
    config = workflow("checks.yml")
    depths = [
        step.get("with", {}).get("fetch-depth")
        for job in config["jobs"].values()
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/checkout")
    ]
    assert 0 in depths, "no checkout fetches full history"


# --- the negative criterion ---------------------------------------------------------------


def test_no_new_runtime_dependency():
    """These checks read files and parse YAML. Anything more belongs to another contract."""
    declared = tomllib.loads(read("pyproject.toml"))
    assert declared["project"]["dependencies"] == []
