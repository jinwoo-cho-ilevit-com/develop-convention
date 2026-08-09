"""15's Core Rule applied to the plugin: what distributes a change is updated with it.

Claude Code resolves a plugin's version from `plugin.json` first and skips the update when
that string has not moved (→ https://code.claude.com/docs/en/plugin-marketplaces, "Version
resolution and release channels"). `0.1.0` therefore survived thirteen commits to the hook,
the commands and the workflow, and `/plugin update dev-harness` printed nothing at all —
indistinguishable from success while the installed copy stayed at the state before them.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
# What `/plugin install` puts on a user's machine. A change under any of these is a change
# the user can only receive through a new version. `conventions` belongs here for the same
# reason the rest do, and by the count is the most load-bearing of them: the commands and
# skills resolve `${CLAUDE_PLUGIN_ROOT}/conventions` seventeen times, against one for
# `workflows`. Omitted, a conventions-only edit shipped nothing and no check said so.
SHIPPED = ("hooks", "commands", "workflows", "skills", "conventions", ".claude-plugin")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


# --- the two files a human edits ---------------------------------------------------------


def test_the_marketplace_entry_agrees_with_the_plugin_manifest():
    """`plugin.json` always wins and nothing warns, so a stale entry is invisible at runtime.

    The entry may omit `version` — that is the documented way to keep one source of truth.
    Declaring a different one is the failure.
    """
    declared = load(PLUGIN)["version"]
    name = load(PLUGIN)["name"]
    entry = next(e for e in load(MARKETPLACE)["plugins"] if e["name"] == name)
    assert entry.get("version", declared) == declared, (
        f"marketplace entry says {entry.get('version')!r}, plugin.json says {declared!r}"
    )


def test_the_marketplace_document_version_agrees_with_the_plugin():
    """The third copy of the version, and the one the check above does not reach.

    It is a separate literal from the entry, moved by hand at every release since 0.2.4. A
    release that bumps the other two and forgets this one leaves both suites green while the
    document advertises a version matching nothing. Omitting it is fine for the same reason
    it is fine on the entry: one source of truth. Declaring a different one is the failure.
    """
    declared = load(PLUGIN)["version"]
    document = load(MARKETPLACE).get("version", declared)
    assert document == declared, (
        f"marketplace document version says {document!r}, plugin.json says {declared!r}"
    )


# --- a release that no longer describes what it ships --------------------------------------


def unreadable_history() -> str | None:
    """Why git cannot answer here, or None. An export or a shallow clone is not a failure."""
    if shutil.which("git") is None:
        return "git is not installed"
    if git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        return "this tree is not a git checkout"
    if git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        return "the clone is shallow"
    return None


def commit_that_set_the_version(version: str) -> str | None:
    """The newest commit that changed how often the current version literal appears.

    Pickaxe rather than tags: this repository has none, and a tag would be a second thing
    to forget. The literal must be in the file as written, so a reformatted manifest fails
    loudly here instead of quietly skipping the check below.
    """
    literal = f'"version": "{version}"'
    assert literal in read(".claude-plugin/plugin.json"), (
        f"plugin.json does not spell the version as {literal!r}; this check cannot find it"
    )
    return git("log", "-1", "--format=%H", f"-S{literal}", "--", str(PLUGIN)).stdout.strip() or None


def test_the_shipped_components_have_not_moved_since_the_version_did():
    """Committed content only: an edit in progress is not yet a release anybody can miss."""
    if reason := unreadable_history():
        pytest.skip(f"cannot judge the release: {reason}")
    version = load(PLUGIN)["version"]
    bumped_at = commit_that_set_the_version(version)
    if bumped_at is None:
        pytest.skip(f"no commit in this clone sets version {version}")

    changed = git("diff", "--name-only", bumped_at, "HEAD", "--", *SHIPPED).stdout.split()
    culprits = git("log", "--format=  %h %s", f"{bumped_at}..HEAD", "--", *SHIPPED).stdout
    assert not changed, (
        f"version {version} was last set in {bumped_at[:12]}, and the plugin has shipped "
        f"changes since:\n{culprits}"
        f"files: {changed}\n"
        f"`/plugin update` keys on the version string and exits silently when it has not "
        f"moved. Bump it in .claude-plugin/plugin.json and the marketplace entry."
    )


def test_ci_fetches_the_history_the_check_above_needs():
    """`actions/checkout` fetches one commit by default — "Number of commits to fetch. 0
    indicates all history for all branches and tags. Default: 1"
    (https://github.com/actions/checkout). At that depth the check skips, and a guard that
    only ever runs on the machine that wrote the change is not a guard.
    """
    assert "fetch-depth: 0" in read(".github/workflows/checks.yml"), (
        "checks.yml checks out one commit, so the release-staleness check skips in CI"
    )
