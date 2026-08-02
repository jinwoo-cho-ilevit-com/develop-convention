"""The plugin is the delivery path, and 15 requires the delivery path to be checked.

Reading a manifest tells you it parses. The hook checks below run it, because a guard that
was never observed refusing is indistinguishable from one that never fires
(→ conventions/20-review-gate.md).
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
GUARD = ROOT / "hooks" / "delegate-guard.sh"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --- manifests ------------------------------------------------------------------------------


def test_marketplace_entry_matches_the_plugin_name():
    """The marketplace entry name is what `enabledPlugins` keys and `/plugin` uses.

    A mismatch installs under one name and namespaces its commands under another.
    """
    entries = {entry["name"] for entry in load(MARKETPLACE)["plugins"]}
    assert load(PLUGIN)["name"] in entries


@pytest.mark.skipif(shutil.which("claude") is None, reason="the Claude Code CLI is not installed")
def test_the_cli_accepts_the_manifests():
    """Our own parse agreeing with the schema is not the runtime agreeing with it."""
    result = subprocess.run(
        ["claude", "plugin", "validate", str(ROOT), "--strict"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_declared_component_paths_exist():
    """A manifest naming a directory that is not there installs a plugin with nothing in it."""
    declared = ("commands", "hooks", "workflows", "skills")
    missing = [name for name in declared if not (ROOT / name).is_dir()]
    assert not missing, f"the plugin declares components that do not exist: {missing}"


def test_hook_config_points_at_a_file_that_exists():
    config = load(ROOT / "hooks" / "hooks.json")
    for entry in config["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            target = hook["command"].replace('"${CLAUDE_PLUGIN_ROOT}"', str(ROOT)).strip('"')
            assert Path(target).is_file(), f"hook command is not a file: {target}"


def test_the_guard_is_executable():
    """A plugin hook is invoked directly, so a non-executable script fails silently at runtime."""
    assert GUARD.stat().st_mode & 0o111, "hooks/delegate-guard.sh is not executable"


@pytest.mark.parametrize("path", sorted((ROOT / "commands").glob("*.md")), ids=lambda p: p.name)
def test_every_command_declares_a_description(path):
    """Without one the command is listed with no way to tell what it does."""
    body = path.read_text(encoding="utf-8")
    assert body.startswith("---\n"), f"{path.name} has no front matter"
    front = body.split("---", 2)[1]
    assert "description:" in front, f"{path.name} declares no description"


# --- the guard, executed --------------------------------------------------------------------


def run_guard(payload: dict, env: dict | None = None) -> dict | None:
    result = subprocess.run(
        [str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", **(env or {})},
    )
    assert result.returncode == 0, f"the guard exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout) if result.stdout.strip() else None


def decision(payload: dict, env: dict | None = None) -> str:
    out = run_guard(payload, env)
    return out["hookSpecificOutput"]["permissionDecision"] if out else "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_the_main_session_may_not_edit(tool):
    assert decision({"tool_name": tool, "tool_input": {"file_path": "a.py"}}) == "deny"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize("tool", ["Edit", "Write", "NotebookEdit"])
def test_a_subagent_may_edit(tool):
    """`agent_id` is present only inside a subagent call. That is the whole test."""
    payload = {"agent_id": "a1", "agent_type": "executor", "tool_name": tool, "tool_input": {}}
    assert decision(payload) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_a_large_read_is_refused_and_a_small_one_is_not(tmp_path):
    big, small = tmp_path / "big.py", tmp_path / "small.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    small.write_text("x = 1\n" * 10, encoding="utf-8")
    read = lambda p: {"tool_name": "Read", "tool_input": {"file_path": str(p)}}  # noqa: E731
    assert decision(read(big)) == "deny"
    assert decision(read(small)) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_the_orchestrator_may_read_its_own_plan(tmp_path):
    """Blocking the orchestrator from its own brief defeats what the guard exists for."""
    plan = tmp_path / ".plans" / "feature"
    plan.mkdir(parents=True)
    brief = plan / "PLAN.md"
    brief.write_text("# plan\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(brief)}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_a_binary_read_is_not_judged_by_line_count(tmp_path):
    """Line counts are meaningless for an image; a small screenshot must not be refused."""
    image = tmp_path / "shot.png"
    image.write_bytes(bytes([0x89, 0x50, 0x4E, 0x47]) + bytes([0, 10]) * 3000)
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(image)}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize(
    "agent_id",
    [[], {}, 0, "null", " ", "\t"],
    ids=["array", "object", "zero", "str-null", "space", "tab"],
)
def test_only_a_real_agent_id_counts_as_a_subagent(agent_id):
    """The gate hangs on this one field, so anything but a non-blank string must not open it.

    jq renders `[]`, `{}` and `0` as non-empty text, so a bare emptiness test read every one
    of them as a subagent marker and allowed the edit.
    """
    payload = {"agent_id": agent_id, "tool_name": "Edit", "tool_input": {"file_path": "a.py"}}
    assert decision(payload) == "deny"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize(
    "command",
    ["echo x > f", "cat a >> b", "sed -i '' s/a/b/ f", "cat x | tee f", "git apply p.patch"],
)
def test_the_shell_write_forms_it_claims_to_catch_are_caught(command):
    """Editing through Bash is editing. The guard cannot catch every form (→ 21 §3), but a
    form it advertises and misses is worse than an admitted gap."""
    assert decision({"tool_name": "Bash", "tool_input": {"command": command}}) == "deny"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "uv run pytest -q 2>/dev/null",
        "grep -q x f >/dev/null",
        "make 2>&1 | tail -5",
    ],
)
def test_read_only_shell_work_is_not_blocked(command):
    """The orchestrator lives in the shell. A guard that stops `git status` gets turned off."""
    assert decision({"tool_name": "Bash", "tool_input": {"command": command}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize(
    "path", [".plans/f/release..notes.md", ".plans/f/v1..2.md", ".plans/f/PLAN.md"]
)
def test_a_plan_file_with_two_dots_in_its_name_is_not_traversal(path):
    """The first traversal guard matched two dots anywhere, not a `..` path segment.

    Feature names come from the user and nothing forbids this spelling, so the orchestrator
    was refused the plan file it was told to write — a fix that shut the door it opened and
    one next to it.
    """
    assert decision({"tool_name": "Write", "tool_input": {"file_path": path}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize(
    "path",
    [
        ".plans/../src/app.js",
        "/x/.plans/../../etc/passwd",
        ".plans/a/../../src/b.py",
        "../.plans/x.md",
    ],
)
def test_the_plan_exemption_does_not_reach_outside_the_plan(path):
    """The exemption made the one exact refusal in this guard bypassable.

    `.plans/../src/app.js` contains the exempt segment and resolves outside it, so a Write
    that the guard refuses by name was allowed by spelling it through a parent.
    """
    assert decision({"tool_name": "Write", "tool_input": {"file_path": path}}) == "deny"


def test_the_declared_bypass_works_without_jq(tmp_path):
    """Its own refusal message told the reader to set this variable, and the check that
    read the variable sat below the refusal. With Bash hooked too, a jq-less machine denied
    the command that would have installed jq."""
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    for tool in ("bash", "cat", "grep", "sed", "wc", "tr", "printf"):
        for root in ("/bin", "/usr/bin"):
            if Path(root, tool).exists():
                (empty_bin / tool).symlink_to(Path(root, tool))
                break
    if not (empty_bin / "bash").exists():
        pytest.skip("no bash to build an isolated PATH with")

    result = subprocess.run(
        [str(empty_bin / "bash"), str(GUARD)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "brew install jq"}}),
        capture_output=True,
        text=True,
        env={"PATH": str(empty_bin), "DEV_HARNESS_ALLOW_MAIN": "1"},
    )
    assert result.returncode == 0
    assert not result.stdout.strip(), "the advertised bypass is unreachable without jq"
    assert "bypassed" in result.stderr


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_the_orchestrator_may_write_its_own_plan(tmp_path):
    """The plugin's own commands tell the main session to write these files.

    The exemption used to sit inside the Read branch, so `/dev-harness:spec` was instructed
    to produce a plan the same plugin's hook refused to let it write.
    """
    brief = tmp_path / ".plans" / "feature" / "PLAN.md"
    for path in (str(brief), ".plans/feature/PLAN.md"):
        assert decision({"tool_name": "Write", "tool_input": {"file_path": path}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize("path", ["AGENTS.md", "/x/y/AGENTS.md", "src/parser/AGENTS.md"])
def test_the_orchestrator_may_write_agents_md(path):
    """`/dev-harness:setup` writes this file from the main session, and the other two
    commands ask for it when a command is missing. Refusing it made the guard block the
    artifact the rest of the plugin depends on."""
    assert decision({"tool_name": "Write", "tool_input": {"file_path": path}}) == "allow"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
@pytest.mark.parametrize("path", ["AGENTS.md.bak", "src/AGENTS.mdx", "notAGENTS.md"])
def test_the_agents_exemption_matches_the_whole_name(path):
    """A prefix or suffix match would exempt any file whose name merely contains it."""
    assert decision({"tool_name": "Write", "tool_input": {"file_path": path}}) == "deny"


def test_the_guard_refuses_rather_than_vanishes_without_jq(tmp_path):
    """Without jq every branch read empty and the call fell through to allow — and the
    other guard tests skip in exactly that environment, so CI was green where the gate was
    dead. A guard that cannot decide must not be the one that says yes.
    """
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    for tool in ("bash", "cat", "grep", "sed", "wc", "tr", "printf"):
        for root in ("/bin", "/usr/bin"):
            if Path(root, tool).exists():
                (empty_bin / tool).symlink_to(Path(root, tool))
                break
    if not (empty_bin / "bash").exists():
        pytest.skip("no bash to build an isolated PATH with")

    result = subprocess.run(
        [str(empty_bin / "bash"), str(GUARD)],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}),
        capture_output=True,
        text=True,
        env={"PATH": str(empty_bin)},
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "jq" in result.stdout


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_an_unparseable_payload_is_refused_not_waved_through():
    result = subprocess.run(
        [str(GUARD)],
        input="not json",
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
    )
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.skipif(shutil.which("jq") is None, reason="the guard needs jq")
def test_the_bypass_is_recorded_not_silent():
    """19: a bypass that leaves no trace is a blocker; a recorded one is a decision."""
    result = subprocess.run(
        [str(GUARD)],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}),
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "DEV_HARNESS_ALLOW_MAIN": "1",
        },
    )
    assert result.returncode == 0
    assert not result.stdout.strip(), "the bypass still denied the call"
    assert "bypassed" in result.stderr, "the bypass left no trace"


# --- the build workflow ----------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("node") is None, reason="the harness needs node")
def test_the_review_loop_ends_three_ways():
    """Blockers cleared, the fix became the defect source, or the cap called a person.

    Driven by tests/workflow_harness.mjs against scripted review rounds, because the three
    exits are the part of workflows/build.js that a reader cannot confirm by reading.
    """
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "workflow_harness.mjs")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
