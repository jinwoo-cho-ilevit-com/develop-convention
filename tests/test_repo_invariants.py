"""The rules this repository states about itself, executed rather than remembered.

`CLAUDE.md` carries a verification checklist and `conventions/03` and `13` require CI
enforcement, but nothing ran either: the workflow that did was deleted as collateral in
`a078b30`, and its document checks were inline shell in YAML that no other caller could
reach. They are tests here so the contract's `verify` commands and the CI job execute the
same file, and so the red check can observe each one failing at the base commit.
"""

import copy
import functools
import re
import subprocess
import tomllib

import pytest
import yaml
from _repo import CONVENTIONS, ROOT, SKILLS, read

# 17 is the declared exception: its commit-body template and examples are Korean on
# purpose, because the commit policy is an English header over a Korean body.
RESIDUE = ("</content>", "</invoke>", "</antml")


@functools.cache
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
        for m in re.finditer(r"\]\((conventions/[^)#]+|templates/[^)#]+)\)", readme)
        if not (ROOT / m.group(1)).exists()
    ]
    assert not broken, f"README links to paths that do not exist: {broken}"


def test_every_convention_sits_under_a_doc_map_group():
    """A doc named anywhere in the README is not enough — a prose arrow would count.

    The map is grouped because the numbers are identifiers rather than a reading order,
    so a doc outside every group is unreachable by the only ordering a reader is given.
    """
    body = read("README.md")
    doc_map = body[body.index("## Document Map") : body.index("## How to Apply")]
    grouped = set()
    for block in re.split(r"^### ", doc_map, flags=re.M)[1:]:
        # Table rows only. Counting every mention inside the section lets a sentence of
        # prose stand in for a row, which is the same hole this test exists to close.
        rows = [line for line in block.splitlines() if line.startswith("| [")]
        grouped |= set(re.findall(r"conventions/(\d\d-[a-z-]+\.md)", "\n".join(rows)))
    missing = sorted({d.name for d in CONVENTIONS} - grouped)
    assert not missing, f"these docs are in no group's table: {missing}"


@pytest.mark.parametrize("doc", CONVENTIONS, ids=lambda p: p.name)
def test_links_inside_a_convention_resolve(doc):
    """Only the README's links were checked, so a doc could point at a deleted file.

    The strict site build catches this in CI by accident; a repository invariant should not
    depend on a docs job that a reader may not run.
    """
    broken = []
    for target in re.findall(r"\]\((?!https?:|#)([^)#]+)", read(doc)):
        if not (doc.parent / target).resolve().exists():
            broken.append(target)
    assert not broken, f"{doc.name} links to files that do not exist: {broken}"


def test_every_convention_is_sourced_from_the_rule_summary():
    """The "Full Rule Summary" is a paraphrased copy of every Core Rules section, and 15
    requires a copy to name its source. Paraphrase defeats the copied-line check, so what is
    pinned here is the pointer: each convention is linked from a summary heading. Two
    conventions (22, 23) were missing from it for a release with nothing to say so.
    """
    body = read("README.md")
    summary = body[body.index("## Full Rule Summary") :]
    headings = re.findall(r"^### .*$", summary, flags=re.M)
    sourced = set(re.findall(r"conventions/(\d\d-[a-z-]+\.md)", "\n".join(headings)))
    missing = sorted({d.name for d in CONVENTIONS} - sourced)
    assert not missing, f"no summary heading names these as its source: {missing}"
    unsourced = [h for h in headings if "conventions/" not in h]
    assert not unsourced, f"summary sections without a source link: {unsourced}"


def test_docsync_still_says_how_to_leave_the_shared_state_behind():
    """A repository that upgrades mid-life needs the migration step to be there, and needs
    it to say how the old keys split — the one thing a reader cannot infer once the old
    layout is gone from the document (why the shared file failed: conventions/15 §2).
    """
    body = (ROOT / "skills" / "docsync" / "SKILL.md").read_text(encoding="utf-8")
    assert "state.json" in body, "the migration step naming the old layout is gone"
    assert "<doc-path>#<section-id>" in body, "migration does not say how the old keys split"
    assert "// .docsync/src__parser__AGENTS.md.json" in body, (
        "the state file example is not flat under .docsync/, which a bare `docs/` ignore eats"
    )


# --- the published site ----------------------------------------------------------------


def test_nav_lists_every_convention_doc():
    """`templates/AGENTS.md` sends an agent with no local clone to the published site.

    While the nav stopped at 17, that agent received conventions 00-17 and no work
    contract, evidence or review-gate rules at all.
    """
    listed = {p for p in nav_paths(mkdocs_config()["nav"]) if p.startswith("conventions/")}
    missing = sorted({f"conventions/{d.name}" for d in CONVENTIONS} - listed)
    assert not missing, f"mkdocs nav omits {missing}"


def test_nav_lists_what_a_project_still_takes():
    """15: when something ships, update what distributes it in the same change.

    The published site is one of those distribution paths, and it went on listing a
    contract template and a bootstrap skill after both were retired.
    """
    listed = set(nav_paths(mkdocs_config()["nav"]))
    assert "templates/AGENTS.md" in listed
    skills = {f"skills/{p.parent.name}/SKILL.md" for p in SKILLS}
    assert skills, "no skill to publish"
    unpublished = sorted(skills - listed)
    assert not unpublished, f"mkdocs nav omits {unpublished}"


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


# --- what CLAUDE.md says this repository is ---------------------------------------------


def test_claude_md_names_the_code_this_repository_ships():
    """It told an agent the only code was a toolkit that no longer exists.

    An agent that believes the repository is documents-only will not run, or update, the
    plugin that now delivers them.
    """
    body = read("CLAUDE.md")
    for entry in ("hooks/", "commands/", "workflows/", ".claude-plugin/"):
        assert entry in body, f"CLAUDE.md never mentions {entry}"


# --- nothing in the tree still names a mechanism that was retired ------------------------

RETIRED = (
    "templates/scripts",
    "contract.py",
    "conv-init",
    "templates/contract.md",
    "verify: human",
    "schema_version",
    "last_sync_commit",
    "last_audit_commit",
    "`revision`",
)


def tracked_text() -> list[tuple[str, str]]:
    """Every tracked text file as (path, body). This suite is left out: it spells the
    tokens itself, and a tombstone list cannot be its own violation."""
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    files = []
    for name in filter(None, listed):
        path = ROOT / name
        if name.startswith("tests/") or not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "\0" not in body:
            files.append((name, body))
    return files


def test_nothing_in_the_tree_names_a_retired_mechanism():
    """A document sending a reader to a tool that no longer exists is the worst shape a rule
    takes: readable, and doing as told fails.

    One list checked against every tracked file, path as well as body, so a retired directory
    reappearing and a document naming it fail the same way. Per-directory checks each covered
    one corner and left the next file added uncovered.
    """
    named = sorted(
        f"{name}: {token}"
        for name, body in tracked_text()
        for token in RETIRED
        if token in name or token in body
    )
    assert not named, f"retired mechanisms are still named: {named}"


# --- conventions/03 and 13: enforcement in CI --------------------------------------------


@functools.cache
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


@functools.cache
def precommit_config() -> dict:
    return yaml.safe_load(read(".pre-commit-config.yaml"))


def ci_tools(workflow: dict, precommit: dict) -> str:
    """What CI actually runs: the run-step text, plus the pre-commit hook ids when a step
    runs the whole hook set. A tool reached only through pre-commit is enforced as much as
    one the workflow names itself, so moving one there must not read as dropping it.
    """
    text = run_steps(workflow)
    if "pre-commit run --all-files" in text:
        ids = [hook["id"] for repo in precommit["repos"] for hook in repo["hooks"]]
        text = "\n".join([text, *ids])
    return text


def test_workflow_runs_on_pull_requests():
    """`main`-only means the branch a change lives on is never checked."""
    assert "pull_request" in triggers(workflow("checks.yml"))


@pytest.mark.parametrize("tool", ["ruff check", "ruff format", "pytest", "gitleaks"])
def test_workflow_runs_lint_tests_and_secret_scan(tool):
    """03:20 enforces lint in CI because local hooks can be skipped; 13:12 the same for
    secret scanning. Some of these the workflow names itself and some it reaches by running
    the whole pre-commit set, which is why the assertion is against `ci_tools` rather than
    the run steps alone.
    """
    assert tool in ci_tools(workflow("checks.yml"), precommit_config())


def test_secret_scan_survives_only_while_the_hook_exists():
    """The check above passes on a hook id, so deleting the hook has to remove the tool.

    A run step that names a tool without running it, or a helper that reports one whatever
    the config says, satisfies that check just as well — the workflow this replaced named
    `gitleaks` in its own text. Removing the hook has to remove the tool, or the green above
    is coming from somewhere other than a hook that runs.
    """
    stripped = copy.deepcopy(precommit_config())
    for repo in stripped["repos"]:
        repo["hooks"] = [hook for hook in repo["hooks"] if hook["id"] != "gitleaks"]
    assert "gitleaks" not in ci_tools(workflow("checks.yml"), stripped)


def test_workflow_installs_the_cli_the_manifest_test_needs():
    """`tests/test_plugin.py::test_the_cli_accepts_the_manifests` skips when `claude` is
    absent, so CI reported green over a manifest that nothing had validated.
    """
    assert "claude.ai/install.sh" in run_steps(workflow("checks.yml"))


def docs_assembly(config: dict) -> list[str]:
    return [
        step["run"]
        for job in config["jobs"].values()
        for step in job.get("steps", [])
        if step.get("name") == "Assemble docs dir"
    ]


def test_pull_requests_build_the_site_the_deploy_builds():
    """docs.yml builds the site only after merge; checks.yml repeats its build on the pull
    request. The two assemble `docs/` from one recipe, or the pull request passes a site
    that is not the one deployed.
    """
    checks = workflow("checks.yml")
    assert docs_assembly(checks), "checks.yml does not assemble docs/"
    assert docs_assembly(checks) == docs_assembly(workflow("docs.yml"))
    assert "mkdocs build --strict" in run_steps(checks)


# --- the negative criterion ---------------------------------------------------------------


def test_no_new_runtime_dependency():
    """These checks read files and parse YAML. Anything more belongs to another contract."""
    declared = tomllib.loads(read("pyproject.toml"))
    assert declared["project"]["dependencies"] == []
