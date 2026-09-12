#!/usr/bin/env python3
# Refuses a main-session Read large enough to crowd out the orchestrator's context; every other
# call, and every subagent call (they carry `agent_id`), passes. Stdlib only, and nothing may
# raise: a traceback lets the read through, so an unparseable payload is refused instead.
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
    "dev-harness cannot run: the hook payload is not a JSON object. Refusing rather than "
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
    if not isinstance(payload, dict):
        deny(UNPARSEABLE)

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

    # The plan, the lane briefs and AGENTS.md are the orchestrator's own artifacts. A `..`
    # segment forfeits the exemption, since such a path can name the exempt file and land elsewhere.
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

    # A read costs the lesser of what it asks for and what the file holds, so a window within
    # budget passes and a larger one is judged by the file below.
    requested = str(tool_input.get("limit"))
    if counts(requested) and int(requested) <= limit:
        allow()

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
            for chunk in iter(lambda: handle.read(CHUNK), b""):
                # Line counts mean nothing for images and other binaries; a NUL byte decides.
                if b"\x00" in chunk:
                    binary = True
                    break
                lines += chunk.count(b"\n")
                blank = blank and not chunk.replace(b"\n", b"")
    except OSError:
        allow()
    # A file that is empty or only newlines has nothing to meter, so it is allowed however many
    # lines or bytes it holds — there is no context to burn on blank lines.
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
