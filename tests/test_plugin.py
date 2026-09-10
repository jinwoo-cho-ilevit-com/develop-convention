"""The plugin is the delivery path, and 15 requires the delivery path to be checked.

Reading a manifest tells you it parses. The hook checks below run it, because a guard that
was never observed refusing is indistinguishable from one that never fires
(→ conventions/20-review-gate.md).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from _repo import COMMANDS, CONVENTIONS, MARKETPLACE, PLUGIN, ROOT, SKILLS, load, read

GUARD = ROOT / "hooks" / "delegate-guard.py"
SYSTEM_PATH = "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"


def front_matter(path: Path) -> str:
    body = read(path)
    assert body.startswith("---\n"), f"{path} has no front matter"
    return body.split("---", 2)[1]


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
    """The four default component directories (commands, hooks, workflows, skills) exist.

    `plugin.json` declares no paths of its own, so these default locations are the contract.
    """
    declared = ("commands", "hooks", "workflows", "skills")
    missing = [name for name in declared if not (ROOT / name).is_dir()]
    assert not missing, f"the plugin declares components that do not exist: {missing}"


def test_the_hook_only_intercepts_reads():
    """The guard decides one thing: whether a read fits the orchestrator's budget.

    Matching the editing tools spent a prompt on every edit to enforce a norm the guard
    cannot hold, and matching Bash spent a subprocess on every command to reach a pattern
    match that called itself a speed bump (→ conventions/21-development-loop.md §3).
    """
    entries = load(ROOT / "hooks" / "hooks.json")["hooks"]["PreToolUse"]
    matchers = {entry["matcher"] for entry in entries}
    assert matchers == {"Read"}, f"the guard is wired to more than Read: {sorted(matchers)}"


def hook_scripts() -> list[Path]:
    config = load(ROOT / "hooks" / "hooks.json")
    return [
        Path(hook["command"].replace('"${CLAUDE_PLUGIN_ROOT}"', str(ROOT)).strip('"'))
        for entries in config["hooks"].values()
        for entry in entries
        for hook in entry["hooks"]
    ]


def test_hook_config_points_at_files_that_exist():
    missing = [str(target) for target in hook_scripts() if not target.is_file()]
    assert not missing, f"hook commands are not files: {missing}"


def test_every_hook_is_executable():
    """A plugin hook is invoked directly, so a non-executable script fails silently at runtime."""
    dead = [target.name for target in hook_scripts() if not target.stat().st_mode & 0o111]
    assert not dead, f"hook scripts are not executable: {dead}"


def test_the_route_map_carries_each_skill_description():
    """The map is the always-present pointer to the skills, so a skill it does not name is
    one the reminder never routes to.

    It is generated from the front matter, and the line is checked against the description
    an agent actually selects on, so a rewording cannot leave the two describing different
    work while both still name the skill.
    """
    result = subprocess.run(
        [str(ROOT / "hooks" / "route-map.sh")], input="{}", capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    missing = []
    for path in SKILLS:
        front = yaml.safe_load(read(path).split("---", 2)[1])
        # The trigger clause only: the full description already sits in the system prompt,
        # and injecting it again on every prompt would repeat what the context holds.
        _, _, clause = front["description"].partition(". Use ")
        if f"- {clause or front['description']} → {front['name']}" not in result.stdout:
            missing.append(path.parent.name)
    assert not missing, f"the routing map does not carry the trigger clause of: {missing}"


def test_the_readme_skill_table_names_every_skill():
    """The map is generated; the README's reader-facing table is the one copy left by hand."""
    body = read("README.md")
    table = body[body.index("| Skill | Loads when |") :]
    table = table[: table.index("\n\n")]
    unlisted = [p.parent.name for p in SKILLS if f"`{p.parent.name}`" not in table]
    assert not unlisted, f"README's skill table omits {unlisted}"


@pytest.mark.parametrize("path", COMMANDS, ids=lambda p: p.name)
def test_every_command_declares_a_description(path):
    """Without one the command is listed with no way to tell what it does."""
    assert "description:" in front_matter(path), f"{path.name} declares no description"


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_skill_declares_a_description(path):
    """A skill is chosen by its description, so one without it never loads at all.

    The name has to be the directory name: the two disagreeing installs a skill under
    a name nothing points at.
    """
    front = front_matter(path)
    assert "description:" in front, f"{path.parent.name} declares no description"
    assert f"name: {path.parent.name}\n" in front, (
        f"{path.parent.name} declares a name that is not its directory"
    )


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_every_skill_link_resolves(path):
    """A skill routes rather than restates, so a dead link is the content gone.

    `mkdocs build --strict` catches this too, but only on a push to main; the routing
    is worth failing a pull request over.
    """
    targets = re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8"))
    broken = [
        target
        for target in targets
        if not target.startswith(("http://", "https://", "#"))
        and not (path.parent / target).exists()
    ]
    assert not broken, f"{path.parent.name} links to files that do not exist: {broken}"


CONVENTION_TEXT = " ".join(read(p) for p in CONVENTIONS)


@pytest.mark.parametrize(
    "path", SKILLS + COMMANDS, ids=lambda p: p.parent.name if p.name == "SKILL.md" else p.name
)
def test_a_skill_does_not_copy_convention_text(path):
    """A skill or command routes to a convention the same way; the rule text itself stays there.

    This catches copied sentences, not paraphrase — a short restatement still needs the
    review lens (CLAUDE.md, verification item 6). A guard, so it holds at the base commit
    by design (→ conventions/06-testing-verification.md), and a standing invariant kept
    green by the absence of copied text rather than by an exemption.
    """
    copied = [
        line
        for raw in read(path).splitlines()
        if len(line := raw.strip().lstrip("|-*# ").strip()) >= 40 and line in CONVENTION_TEXT
    ]
    assert not copied, f"{path.name} copies convention text: {copied}"


def test_every_convention_is_routed_by_exactly_one_skill():
    """The skills are how a convention reaches an agent, so one nothing routes to is one
    nobody loads. Two skills claiming it is the same rule arriving under two triggers.

    00 is the exception by design: it takes precedence over all of them, so every skill
    points back at it.
    """
    routed: dict[str, set[str]] = {}
    for path in SKILLS:
        body = path.read_text(encoding="utf-8")
        for name in re.findall(r"\.\./\.\./conventions/(\d\d-[a-z-]+\.md)", body):
            routed.setdefault(name, set()).add(path.parent.name)

    everything = {p.name for p in CONVENTIONS} - {"00-principles.md"}
    orphaned = sorted(everything - set(routed))
    assert not orphaned, f"no skill routes to {orphaned}"

    contested = sorted(
        f"{name} claimed by {sorted(owners)}"
        for name, owners in routed.items()
        if name in everything and len(owners) > 1
    )
    assert not contested, f"more than one skill routes to the same convention: {contested}"


# --- the guard, executed --------------------------------------------------------------------


def run_guard(payload: dict, env: dict | None = None) -> dict | None:
    result = subprocess.run(
        [str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": SYSTEM_PATH, **(env or {})},
    )
    assert result.returncode == 0, f"the guard exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout) if result.stdout.strip() else None


def decision(payload: dict, env: dict | None = None) -> str:
    out = run_guard(payload, env)
    return out["hookSpecificOutput"]["permissionDecision"] if out else "allow"


def test_a_subagent_may_read_past_the_budget(tmp_path):
    """`agent_id` is present only inside a subagent call. That is the whole test.

    The budget belongs to the orchestrator. A lane reading the module it was given is the
    thing the budget exists to make affordable, not the thing it guards against.
    """
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    payload = {
        "agent_id": "a1",
        "agent_type": "executor",
        "tool_name": "Read",
        "tool_input": {"file_path": str(big)},
    }
    assert decision(payload) == "allow"


def test_a_large_read_is_refused_and_a_small_one_is_not(tmp_path):
    big, small = tmp_path / "big.py", tmp_path / "small.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    small.write_text("x = 1\n" * 10, encoding="utf-8")
    read = lambda p: {"tool_name": "Read", "tool_input": {"file_path": str(p)}}  # noqa: E731
    assert decision(read(big)) == "deny"
    assert decision(read(small)) == "allow"


def test_the_read_budget_is_the_one_the_environment_asks_for(tmp_path):
    """The refusal message advertises this variable, so it has to move the threshold.

    Metering reads is now the whole hook, and the override had no test at all.
    """
    page = tmp_path / "page.py"
    page.write_text("x = 1\n" * 300, encoding="utf-8")
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(page)}}
    assert decision(payload, {"DEV_HARNESS_READ_LIMIT": "100"}) == "deny"
    assert decision(payload, {"DEV_HARNESS_READ_LIMIT": "900"}) == "allow"


@pytest.mark.parametrize("limit", ["", "lots", "500x"])
def test_an_unusable_read_budget_falls_back_and_still_decides(limit, tmp_path):
    """A limit that is not a line count must not leave the comparison to run on it.

    An empty `limit` is not a number; comparing against it would either raise (a non-blocking
    hook error, so the read proceeds) or fall through to allow — either way a silent global
    allow, from a typo in a settings file.
    """
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(big)}}
    assert decision(payload, {"DEV_HARNESS_READ_LIMIT": limit}) == "deny"


def test_a_bounded_read_costs_what_it_asks_for(tmp_path):
    """Judging a 20-line window by the size of the file refuses the cheap request and
    leaves raising the limit or bypassing the guard as the only ways through."""
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 5000, encoding="utf-8")
    windowed = lambda n: {  # noqa: E731
        "tool_name": "Read",
        "tool_input": {"file_path": str(big), "limit": n},
    }
    assert decision(windowed(20)) == "allow"
    assert decision(windowed(900)) == "deny"


def test_one_enormous_line_is_judged_by_bytes(tmp_path):
    """A minified bundle is one line and still costs the context the limit protects.

    Every other fixture here is short lines, so the line clause always decided first and
    the byte ceiling never did.
    """
    bundle = tmp_path / "bundle.min.js"
    bundle.write_text("var a=1;" * 20_000, encoding="utf-8")
    assert len(bundle.read_text().splitlines()) == 1
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(bundle)}}) == "deny"


def test_the_orchestrator_may_read_its_own_plan(tmp_path):
    """Blocking the orchestrator from its own brief defeats what the guard exists for."""
    plan = tmp_path / ".plans" / "feature"
    plan.mkdir(parents=True)
    brief = plan / "PLAN.md"
    brief.write_text("# plan\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(brief)}}) == "allow"


def test_a_binary_read_is_not_judged_by_line_count(tmp_path):
    """Line counts are meaningless for an image; a small screenshot must not be refused."""
    image = tmp_path / "shot.png"
    image.write_bytes(bytes([0x89, 0x50, 0x4E, 0x47]) + bytes([0, 10]) * 3000)
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(image)}}) == "allow"


@pytest.mark.parametrize(
    "agent_id",
    [[], {}, 0, "null", " ", "\t"],
    ids=["array", "object", "zero", "str-null", "space", "tab"],
)
def test_only_a_real_agent_id_counts_as_a_subagent(agent_id, tmp_path):
    """The gate hangs on this one field, so anything but a non-blank string must not open it.

    A bare emptiness test reads `[]`, `{}` and `0` as a subagent marker and waves the read
    through, which is why the guard tests the field's type before its value.
    """
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    payload = {
        "agent_id": agent_id,
        "tool_name": "Read",
        "tool_input": {"file_path": str(big)},
    }
    assert decision(payload) == "deny"


@pytest.mark.parametrize("name", ["release..notes.md", "v1..2.md", "PLAN.md"])
def test_a_plan_file_with_two_dots_in_its_name_is_not_traversal(name, tmp_path):
    """The first traversal guard matched two dots anywhere, not a `..` path segment.

    Feature names come from the user and nothing forbids this spelling, so the orchestrator
    was refused the plan file it was told to work from — a fix that shut the door it opened
    and one next to it.
    """
    brief = tmp_path / ".plans" / "f" / name
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("# plan\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(brief)}}) == "allow"


@pytest.mark.parametrize("path", [".plans/f/PLAN.md", "AGENTS.md"])
def test_the_exemptions_match_a_relative_path_too(path, tmp_path, monkeypatch):
    """The exemptions match a relative spelling as well as an absolute one.

    Every other fixture here is built under `tmp_path` and absolute, so the relative
    branch could be deleted with the suite still green.
    """
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# long\n" * 900, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert decision({"tool_name": "Read", "tool_input": {"file_path": path}}) == "allow"


def test_a_leading_parent_segment_forfeits_the_exemption(tmp_path, monkeypatch):
    """`../.plans/x.md` holds the exempt name; the `..` segment is what forfeits the exemption."""
    brief = tmp_path / ".plans" / "x.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# plan\n" * 900, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    monkeypatch.chdir(tmp_path / "sub")
    assert Path("../.plans/x.md").is_file(), "the spelling must resolve, or this proves nothing"
    assert decision({"tool_name": "Read", "tool_input": {"file_path": "../.plans/x.md"}}) == "deny"


@pytest.mark.parametrize("spelling", [".plans/../src/app.js", ".plans/a/../../src/app.js"])
def test_the_plan_exemption_does_not_reach_outside_the_plan(spelling, tmp_path):
    """The exemption made a guarded path bypassable.

    `.plans/../src/app.js` contains the exempt segment and resolves outside it, so a read
    the guard would otherwise refuse was allowed by spelling it through a parent.
    """
    (tmp_path / ".plans" / "a").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.js").write_text("x = 1\n" * 900, encoding="utf-8")
    path = f"{tmp_path}/{spelling}"
    assert Path(path).is_file(), "the spelling must resolve, or the test proves nothing"
    assert decision({"tool_name": "Read", "tool_input": {"file_path": path}}) == "deny"


@pytest.mark.parametrize("where", ["AGENTS.md", "src/parser/AGENTS.md"])
def test_the_orchestrator_may_read_agents_md(where, tmp_path):
    """`/dev-harness:setup` writes this file and the other two commands read it back.

    A project that documented its commands at length was then refused the file that holds
    them, which is the one artifact the rest of the plugin depends on.
    """
    path = tmp_path / where
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# commands\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(path)}}) == "allow"


@pytest.mark.parametrize("name", ["AGENTS.md.bak", "AGENTS.mdx", "notAGENTS.md"])
def test_the_agents_exemption_matches_the_whole_name(name, tmp_path):
    """A prefix or suffix match would exempt any file whose name merely contains it."""
    path = tmp_path / name
    path.write_text("# notes\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(path)}}) == "deny"


def test_the_guard_refuses_and_never_prompts(tmp_path):
    """One refusal, no prompt.

    It used to ask before the editing tools and before shell commands that looked like
    writes, which spent a prompt on the common path to enforce a norm it could not actually
    hold (→ conventions/21-development-loop.md §3). What is left has no false positive and a
    strictly better alternative, so it refuses rather than asking.
    """
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(big)}}) == "deny"
    ungated = (
        {"tool_name": "Edit", "tool_input": {"file_path": str(big)}},
        {"tool_name": "MultiEdit", "tool_input": {"file_path": str(big)}},
        {"tool_name": "Write", "tool_input": {"file_path": "src/app.py"}},
        {"tool_name": "NotebookEdit", "tool_input": {"file_path": "nb.ipynb"}},
        {"tool_name": "Bash", "tool_input": {"command": "echo hi > out.txt"}},
    )
    for payload in ungated:
        assert decision(payload) == "allow", f"{payload['tool_name']} is still gated"


@pytest.mark.parametrize(
    "payload",
    ["not json", "null", "[]", "0", '"x"'],
    ids=["not json", "null", "[]", "0", '"x"'],
)
def test_an_unparseable_payload_is_refused_not_waved_through(payload):
    """Valid JSON that is not an object (`null`, an array, a number, a string) must be refused
    the same way malformed JSON is — the guard cannot read fields off any of them either."""
    result = subprocess.run(
        [str(GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": SYSTEM_PATH},
    )
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_file_of_only_newlines_is_not_metered(tmp_path):
    """Standing invariant, pinned as-is: a large file with nothing but blank lines has nothing
    to meter, so it is allowed regardless of size. Green at base and here alike."""
    blank = tmp_path / "blank.txt"
    blank.write_text("\n" * 5000, encoding="utf-8")
    assert decision({"tool_name": "Read", "tool_input": {"file_path": str(blank)}}) == "allow"


def test_a_refusal_survives_a_non_utf8_stdout():
    """The reason carries non-ASCII. A text stdout under an ASCII locale raised on it, and a
    hook that dies is a non-blocking error — the read went through unguarded.
    """
    result = subprocess.run(
        [str(GUARD)],
        input=b"not json",
        capture_output=True,
        env={"PATH": SYSTEM_PATH, "PYTHONIOENCODING": "ascii", "LANG": "C"},
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    out = json.loads(result.stdout.decode("utf-8"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_the_bypass_is_recorded_not_silent(tmp_path):
    """19: a bypass that leaves no trace is a blocker; a recorded one is a decision.

    The payload has to be one the guard would otherwise refuse. Sent an ungated tool this
    passes whether or not the bypass fires, which is a test that cannot fail.
    """
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 900, encoding="utf-8")
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(big)}})
    assert decision(json.loads(payload)) == "deny", "the payload must be refused without the bypass"

    result = subprocess.run(
        [str(GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        env={
            "PATH": SYSTEM_PATH,
            "DEV_HARNESS_ALLOW_MAIN": "1",
        },
    )
    assert result.returncode == 0
    assert not result.stdout.strip(), "the bypass still denied the call"
    assert "bypassed" in result.stderr, "the bypass left no trace"


# --- the build workflow ----------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("node") is None, reason="the harness needs node")
def test_the_review_loop_exits_are_observed():
    """Every exit commands/build.md lists is driven by tests/workflow_harness.mjs against
    scripted review rounds, because the exits are the part of workflows/build.js that a
    reader cannot confirm by reading.
    """
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "workflow_harness.mjs")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
