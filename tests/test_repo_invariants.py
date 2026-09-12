"""The rules this repository states about its toolchain and its CI, executed rather than read.

`conventions/03` and `13` require enforcement in CI, and 03's first Core Rule pins the
interpreter. They live here as tests rather than as inline shell in a CI workflow so that the
contract's `verify` commands and the CI job execute the same file.

The document and skill invariants moved to `scripts/check-docs.py`; its sample run is
`tests/test_check_docs.py`.
"""

import copy
import functools
import re
import tomllib

import pytest
import yaml
from _repo import ROOT, read

# --- conventions/03's first Core Rule ---------------------------------------------------


def floor_of(requires_python: str) -> tuple[int, int]:
    match = re.search(r"(\d+)\.(\d+)", requires_python)
    assert match, f"unreadable requires-python {requires_python!r}"
    return int(match.group(1)), int(match.group(2))


@pytest.mark.parametrize("directory", ["", "templates"])
def test_python_version_agrees_with_requires_python(directory):
    """03: `pyproject.toml` + `uv.lock` (committed) + `.python-version`.

    Checked in `templates/` as well as here: a project bootstrapped from the template can
    only satisfy 03's first Core Rule if the template it came from does.
    """
    base = ROOT / directory if directory else ROOT
    pinned = (base / ".python-version").read_text(encoding="utf-8").strip()
    declared = tomllib.loads((base / "pyproject.toml").read_text(encoding="utf-8"))
    assert floor_of(pinned) >= floor_of(declared["project"]["requires-python"])


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


@pytest.mark.parametrize("tool", ["ruff check", "ruff format", "pytest", "gitleaks", "check-docs"])
def test_workflow_runs_lint_tests_and_secret_scan(tool):
    """03:20 enforces lint in CI because local hooks can be skipped; 13:12 the same for
    secret scanning; the document checker is the same argument for the checklist it holds.
    Some of these the workflow names itself and some it reaches by running the whole
    pre-commit set, which is why the assertion is against `ci_tools` rather than the run
    steps alone.
    """
    assert tool in ci_tools(workflow("checks.yml"), precommit_config())


def test_secret_scan_survives_only_while_the_hook_exists():
    """The check above passes on a hook id, so removing the hook has to remove the tool. A
    `ci_tools` that reports `gitleaks` from the run-step text, or whatever the config says,
    satisfies it just as well — then the green above comes from somewhere other than a hook.
    """
    stripped = copy.deepcopy(precommit_config())
    for repo in stripped["repos"]:
        repo["hooks"] = [hook for hook in repo["hooks"] if hook["id"] != "gitleaks"]
    assert "gitleaks" not in ci_tools(workflow("checks.yml"), stripped)


def test_workflow_installs_the_cli_the_manifest_test_needs():
    """`tests/test_plugin.py::test_the_cli_accepts_the_manifests` skips when `claude` is
    absent, so without the install step CI reports green over an unvalidated manifest.
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
