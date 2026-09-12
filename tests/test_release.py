"""15's Core Rule applied to the plugin: what distributes a change is updated with it.

Claude Code resolves a plugin's version from `plugin.json` first and skips the update when
that string has not moved (→ https://code.claude.com/docs/en/plugin-marketplaces, "Version
resolution and release channels"). A shipped change under an unmoved version therefore makes
`/plugin update dev-harness` print nothing at all — indistinguishable from success while the
installed copy stays at the state before it.
"""

import shutil
import subprocess

import pytest
from _repo import MARKETPLACE, PLUGIN, ROOT, load, read

# What `/plugin install` puts on a user's machine. A change under any of these is a change
# the user can only receive through a new version. `conventions` belongs here for the same
# reason the rest do, and by the count is the most load-bearing of them: the commands and
# skills resolve `${CLAUDE_PLUGIN_ROOT}/conventions` seventeen times, against one for
# `workflows`. Omitted, a conventions-only edit would ship nothing with no check saying so.
# `templates` because `setup` reads its AGENTS.md skeleton from there.
SHIPPED = ("hooks", "commands", "workflows", "skills", "conventions", "templates", ".claude-plugin")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


# --- one version literal ------------------------------------------------------------------


def test_the_marketplace_declares_no_version_of_its_own():
    """`plugin.json` always wins and nothing warns, so a marketplace `version` is at best a
    copy and at worst a stale one. Omitting it is the documented way to keep one source of
    truth (→ https://code.claude.com/docs/en/plugin-marketplaces, "Version resolution and
    release channels"), and it spares a release from hand-moving a second literal.
    """
    market = load(MARKETPLACE)
    entry = next(e for e in market["plugins"] if e["name"] == load(PLUGIN)["name"])
    assert "version" not in market, "the marketplace document carries a second version literal"
    assert "version" not in entry, "the marketplace entry carries a second version literal"


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
    if not changed:
        return
    culprits = git("log", "--format=  %h %s", f"{bumped_at}..HEAD", "--", *SHIPPED).stdout
    raise AssertionError(
        f"version {version} was last set in {bumped_at[:12]}, and the plugin has shipped "
        f"changes since:\n{culprits}"
        f"files: {changed}\n"
        f"`/plugin update` keys on the version string and exits silently when it has not "
        f"moved. Bump it in .claude-plugin/plugin.json."
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
