#!/usr/bin/env python3
# Protects the orchestrator's context budget, and nothing else. A read large enough to crowd
# out the session is refused with the cheaper alternative named; every other tool call goes
# through untouched. Subagents carry `agent_id` and the main session does not.
#
# Delegating the work is a norm this hook does not enforce (→ conventions/09-agentic-workflow.md,
# 21-development-loop.md). Nothing here stops the main session from editing, so a run that
# passed the hook is not evidence it stayed out of the tree.
#
# Runs on whatever `python3` the session's PATH offers, not on the project's interpreter:
# standard library only, and no syntax newer than the oldest python3 a machine may ship.
# Nothing here may raise — a traceback is a non-blocking hook error, and the read proceeds.
#
# Falling through to allow is the normal outcome and always was the majority of them. The one
# path that must never do it is a payload that will not parse: a guard that cannot decide must
# not be the one that says yes.
import json
import os
import re
import sys

DEFAULT_READ_LINE_LIMIT = 500
# What a line of source costs when the limit is expressed in lines but the file is minified.
BYTES_PER_LINE = 200
CHUNK = 1 << 20
PLAN_DIR_NAME = ".plans"
AGENTS_FILE_NAME = "AGENTS.md"
UNPARSEABLE = (
    "dev-harness cannot run: the hook payload did not parse as JSON. Refusing rather than "
    "allowing — an unreadable payload is not evidence that the call is safe."
)
# A runtime that stringifies a missing id sends one of these; no agent is named them.
NOT_AN_AGENT = ("", "null", "undefined", "false", "0")


def allow():
    sys.exit(0)


def deny(reason):
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    # Bytes, not text: the reason carries non-ASCII, and a text stream under a non-UTF-8
    # locale would raise here — a traceback is the one exit that lets the read through.
    line = json.dumps(decision, ensure_ascii=False, separators=(",", ":")) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.exit(0)


def warn(message):
    sys.stderr.buffer.write((message + "\n").encode("utf-8"))


def counts(value):
    """Non-empty and ASCII digits only, so the comparison never runs on a typo."""
    return bool(re.fullmatch(r"[0-9]+", value))


def main():
    # The declared bypass is read from this hook's own environment, which a PreToolUse hook has
    # before the tool call runs: session-scoped, set at launch or through the settings env
    # block, with no per-call form. Recorded on stderr (→ conventions/19-evidence.md).
    if os.environ.get("DEV_HARNESS_ALLOW_MAIN") == "1":
        warn("dev-harness: main-session guard bypassed via DEV_HARNESS_ALLOW_MAIN")
        allow()

    try:
        payload = json.loads(sys.stdin.buffer.read())
    except (ValueError, OSError):
        deny(UNPARSEABLE)
    if payload is None or payload is False:
        deny(UNPARSEABLE)
    if not isinstance(payload, dict):
        # A parseable non-object leaves every field absent rather than refusing the call.
        payload = {}

    # `agent_id` is present only inside a subagent call, and only a non-blank string counts.
    # Without the type test any JSON value except null/false/"" reads as truthy and opens the
    # gate the whole guard hangs on.
    agent_id = payload.get("agent_id")
    agent_id = agent_id if isinstance(agent_id, str) else ""
    if "".join(agent_id.split()) not in NOT_AN_AGENT:
        allow()

    tool = payload.get("tool_name")
    tool = tool if isinstance(tool, str) else ""
    tool_input = payload.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    path = tool_input.get("file_path")
    path = path if isinstance(path, str) else ""

    # The plan, the lane briefs and AGENTS.md are the orchestrator's own artifacts, and refusing
    # it the file it was told to write from defeats what the guard exists for. A `..` segment
    # forfeits the exemption instead of being resolved, because a path can hold the exempt name
    # and still land outside it.
    if ".." not in path.split("/"):
        if path.startswith(PLAN_DIR_NAME + "/") or "/" + PLAN_DIR_NAME + "/" in path:
            allow()
        if path == AGENTS_FILE_NAME or path.endswith("/" + AGENTS_FILE_NAME):
            allow()

    # One refusal and no prompt. A read over budget has no false positive — the file is the size
    # it is — and the alternative is strictly better, so it is refused outright. Every judgement
    # that would have been a guess belongs to the person, not to a pattern match.
    if tool != "Read":
        allow()

    limit = os.environ.get("DEV_HARNESS_READ_LIMIT") or str(DEFAULT_READ_LINE_LIMIT)
    if not counts(limit):
        warn(
            f"dev-harness: DEV_HARNESS_READ_LIMIT={limit} is not a line count; "
            f"using {DEFAULT_READ_LINE_LIMIT}"
        )
        limit = str(DEFAULT_READ_LINE_LIMIT)
    limit = int(limit)

    # A bounded read costs what it asks for, not what the file holds. Judging a 20-line window
    # by the size of a 5000-line file refuses the cheap request and leaves raising the limit or
    # bypassing the guard as the only ways through, both worse than the read.
    requested = tool_input.get("limit")
    requested = "" if requested is None or requested is False else str(requested)
    if counts(requested):
        if int(requested) <= limit:
            allow()
        deny(
            f"That Read asks for {requested} lines, over the {limit}-line budget for the main "
            "session. Narrow it, or send an Explore subagent and take its summary."
        )

    if not os.path.isfile(path):
        allow()
    # Streamed in chunks: the file may be far larger than the budget, and holding it in memory
    # is the one way this hook could die and let the read through.
    try:
        size = os.path.getsize(path)
        lines = 0
        binary = False
        blank = True
        with open(path, "rb") as handle:
            first = True
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                # Line counts mean nothing for images and other binaries; the head decides.
                if first and b"\x00" in chunk:
                    binary = True
                    break
                first = False
                lines += chunk.count(b"\n")
                blank = blank and not chunk.replace(b"\n", b"")
    except OSError:
        allow()
    # A file that is empty or only newlines has nothing to meter.
    if binary or blank:
        allow()
    # A minified bundle is one line and still costs the context the limit exists to protect.
    if lines > limit or size > limit * BYTES_PER_LINE:
        deny(
            f"{path} is {lines} lines / {size} bytes; reading it here burns orchestrator "
            "context. Send an Explore subagent and take its summary instead. Both overrides "
            "are session-scoped, "
            "read from the environment before the call runs: raise DEV_HARNESS_READ_LIMIT (now "
            f"{limit}) or set DEV_HARNESS_ALLOW_MAIN=1 in the settings env block, then restart."
        )

    allow()


main()
