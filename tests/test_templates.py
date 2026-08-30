"""`templates/` is what a project copies; the plugin is what it installs.

Since the harness carries the conventions, the hooks and the skills, what is left here is
only the part a plugin cannot supply: the tool configuration a project runs locally, and a
short AGENTS.md for tools that do not read plugins. Every check below guards the same
failure — something changed and the file that distributes it did not learn.
"""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- the retired toolkit left nothing behind ------------------------------------------------


def test_the_contract_toolkit_is_gone():
    """The contract runner was retired. A half-deleted toolkit is worse than either state."""
    left = [p for p in ("scripts", "contract.md", "skills/conv-init") if (TEMPLATES / p).exists()]
    assert not left, f"templates/ still ships retired contract-toolkit paths: {left}"


# --- the template's own instruction about ruff ----------------------------------------------


def hook_rev(config_path: Path, repo_fragment: str) -> str:
    config = yaml.safe_load(read(config_path))
    for entry in config["repos"]:
        if repo_fragment in entry["repo"]:
            return entry["rev"].lstrip("v")
    raise AssertionError(f"{config_path} has no {repo_fragment} hook")


def pinned_version(pyproject: Path, package: str) -> str | None:
    declared = tomllib.loads(read(pyproject))
    for entry in declared.get("dependency-groups", {}).get("dev", []):
        if entry.startswith(package):
            match = re.search(r"==\s*([0-9][0-9.]*)", entry)
            return match.group(1) if match else None
    return None


def test_ruff_pin_matches_the_hook_rev_in_the_template():
    """The template's own comment: keep `rev` in step with the pin — and there was none.

    pre-commit installs its own copy, so two versions format differently and the hook
    rewrites what the local check just called clean.
    """
    pinned = pinned_version(TEMPLATES / "pyproject.toml", "ruff")
    assert pinned, "templates/pyproject.toml does not pin ruff"
    assert pinned == hook_rev(TEMPLATES / ".pre-commit-config.yaml", "ruff-pre-commit")


def test_ruff_pin_matches_between_the_repository_and_the_template():
    """`templates/pyproject.toml` is the ruff config for files under templates/."""
    assert pinned_version(ROOT / "pyproject.toml", "ruff") == pinned_version(
        TEMPLATES / "pyproject.toml", "ruff"
    )


# --- AGENTS.md holds only what the harness cannot know ---------------------------------------


def test_agents_template_carries_no_convention_excerpt():
    """An excerpt is a copy, and 15 requires a copy to carry its source and be checked.

    This template carried thirty lines of rules with neither, so it drifted from the
    documents it quoted while being loaded in every project that took it. The harness reads
    `conventions/` directly, which removes the need and therefore the excerpt.
    """
    body = read(TEMPLATES / "AGENTS.md")
    assert "CONVENTION_PATH" not in body, "the template still asks for a path the plugin knows"
    for marker in ("Core Rules", "(01)", "(02)", "(15)"):
        assert marker not in body, f"templates/AGENTS.md still excerpts conventions: {marker!r}"


def test_agents_template_is_short():
    """09: a bloated instruction file causes real instructions to be ignored."""
    lines = [line for line in read(TEMPLATES / "AGENTS.md").splitlines() if line.strip()]
    assert len(lines) <= 20, f"templates/AGENTS.md is {len(lines)} non-blank lines; keep it minimal"


# --- one answer for an agent with no local clone ---------------------------------------------


SITE = "jinwoo-cho-ilevit-com.github.io/develop-convention"


def test_readme_answers_the_cloud_sandbox_case():
    """A sandbox with no clone and no plugin still needs somewhere to read the rules."""
    assert SITE in read(ROOT / "README.md")


# --- the negative criterion --------------------------------------------------------------------


def test_no_new_runtime_dependency():
    """The repository ships documents and a plugin that reads files; nothing else.

    This began as a pin of the runner's exact field set, written to express "the contract
    that changed the templates did not change the tool". That is true of one contract and
    not an invariant of the repository, so the pin failed the first time the runner was
    legitimately extended. A negative criterion belongs to its contract; what outlives it
    is the part that is still true afterwards.
    """
    declared = tomllib.loads(read(ROOT / "pyproject.toml"))
    assert declared["project"]["dependencies"] == []
