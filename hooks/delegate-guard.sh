#!/usr/bin/env bash
# Protects the orchestrator's context budget, and nothing else. A read large enough to crowd
# out the session is refused with the cheaper alternative named; every other tool call goes
# through untouched. Subagents carry `agent_id` and the main session does not, which is the
# whole test for whose budget this is.
#
# Delegating the work is a norm this hook does not enforce (→ conventions/09-agentic-workflow.md,
# 21-development-loop.md). Nothing here stops the main session from editing, so a run that
# passed the hook is not evidence it stayed out of the tree.
#
# Falling through to allow is the normal outcome. The two paths that must never do it are
# the ones where the guard cannot see: no jq, or a payload that will not parse. A guard that
# cannot decide must not be the one that says yes.
set -uo pipefail

DEFAULT_READ_LINE_LIMIT=500
PLAN_DIR_NAME=".plans"
AGENTS_FILE_NAME="AGENTS.md"

IFS= read -r -d '' payload || :

emit_deny() {
  # Written without jq so this still works when jq is the thing that is missing.
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/^/"/' -e 's/$/"/' | tr -d '\n')"
  exit 0
}

# The declared bypass is read from this hook's own environment, which a PreToolUse hook has
# before the tool call runs: it is session-scoped, set at launch or through the settings env
# block, and has no per-call form. Checked first so it needs nothing — the jq check below
# would otherwise refuse the very call that installs jq. Recorded on stderr (→ 19-evidence.md).
if [ "${DEV_HARNESS_ALLOW_MAIN:-}" = "1" ]; then
  echo "dev-harness: main-session guard bypassed via DEV_HARNESS_ALLOW_MAIN" >&2
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  emit_deny "dev-harness cannot run: jq is not on PATH, and without it this guard cannot read the hook payload. Install jq from a lane (the Agent tool). To work unguarded instead, the session needs DEV_HARNESS_ALLOW_MAIN=1 in its environment — the settings env block, then restart; there is no per-call form. Refusing rather than allowing, because a guard that silently stops guarding is worse than no guard."
fi

# One jq call reads every field this guard uses; the leading "ok" line doubles as the parse
# check. `agent_id` is present only inside a subagent call, and only a string counts: any
# other JSON value except null/false/"" would read as truthy and open the gate.
{ read -r ok; read -r agent_id; read -r tool; read -r path; read -r requested; } < <(
  jq -r '"ok",
    (if (.agent_id | type) == "string" then .agent_id else "" end),
    (.tool_name // ""), (.tool_input.file_path // ""),
    (.tool_input.limit // "" | tostring)' <<<"$payload" 2>/dev/null
)
if [ "${ok:-}" != "ok" ]; then
  emit_deny "dev-harness cannot run: the hook payload did not parse as JSON. Refusing rather than allowing — an unreadable payload is not evidence that the call is safe."
fi

case "$(printf '%s' "$agent_id" | tr -d '[:space:]')" in
# A runtime that stringifies a missing id sends one of these; no agent is named them.
'' | null | undefined | false | 0) ;;
*) exit 0 ;;
esac

# The plan, the lane briefs and AGENTS.md are the orchestrator's own artifacts, and refusing
# it the file it was told to write from defeats what the guard exists for — a long PLAN.md is
# exactly the read it has to make. A `..` segment forfeits the exemption instead of being
# resolved, because `.plans/../src/app.js` holds the exempt name and lands outside it; a
# `..` inside a file name (`release..notes.md`) is not a segment and stays exempt.
case "$path" in
.. | ../* | */../* | */..) ;;
"$PLAN_DIR_NAME"/* | */"$PLAN_DIR_NAME"/*) exit 0 ;;
"$AGENTS_FILE_NAME" | */"$AGENTS_FILE_NAME") exit 0 ;;
esac

# One refusal and no prompt. A read over budget has no false positive — the file is the size
# it is — and the alternative is strictly better, so it is refused outright. Every judgement
# that would have been a guess belongs to the person, not to a pattern match.
case "$tool" in
Read)
  limit="${DEV_HARNESS_READ_LIMIT:-$DEFAULT_READ_LINE_LIMIT}"
  case "$limit" in
  '' | *[!0-9]*)
    echo "dev-harness: DEV_HARNESS_READ_LIMIT=$limit is not a line count; using $DEFAULT_READ_LINE_LIMIT" >&2
    limit=$DEFAULT_READ_LINE_LIMIT
    ;;
  esac
  # A bounded read costs what it asks for, not what the file holds. Judging a 20-line
  # window by the size of a 5000-line file refuses the cheap request and leaves raising the
  # limit or bypassing the guard as the only ways through, both worse than the read.
  case "$requested" in
  '' | *[!0-9]*) ;;
  *)
    if [ "$requested" -le "$limit" ]; then exit 0; fi
    emit_deny "That Read asks for $requested lines, over the $limit-line budget for the main session. Narrow it, or send an Explore subagent and take its summary."
    ;;
  esac
  [ -f "$path" ] || exit 0
  read -r lines bytes _ < <(wc -lc <"$path")
  # A minified bundle is one line and still costs the context the limit exists to protect.
  if [ "$lines" -gt "$limit" ] || [ "$bytes" -gt $((limit * 200)) ]; then
    # Line counts mean nothing for images and other binaries.
    grep -Iq . -- "$path" 2>/dev/null || exit 0
    emit_deny "$path is $lines lines / $bytes bytes; reading it here burns orchestrator context. Send an Explore subagent and take its summary instead. Both overrides are session-scoped, read from the environment before the call runs: raise DEV_HARNESS_READ_LIMIT (now $limit) or set DEV_HARNESS_ALLOW_MAIN=1 in the settings env block, then restart."
  fi
  ;;
esac

exit 0
