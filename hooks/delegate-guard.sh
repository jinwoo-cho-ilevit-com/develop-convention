#!/usr/bin/env bash
# Keeps the main session an orchestrator: it plans, splits and judges, and delegates the
# work. Subagents carry `agent_id`; the main session does not, which is the whole test
# (→ conventions/09-agentic-workflow.md, 21-development-loop.md).
#
# A guard that cannot decide must not be the one that says yes. Every path below either
# reaches a decision or denies with a reason — none of them fall through to allow.
set -uo pipefail

DEFAULT_READ_LINE_LIMIT=500
PLAN_DIR_NAME=".plans"
AGENTS_FILE_NAME="AGENTS.md"

payload=$(cat)

emit_decision() {
  # Written without jq so this still works when jq is the thing that is missing.
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":%s}}\n' \
    "$1" "$(printf '%s' "$2" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/^/"/' -e 's/$/"/' | tr -d '\n')"
  exit 0
}
emit_deny() { emit_decision deny "$1"; }
emit_ask() { emit_decision ask "$1"; }

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

if ! jq -e . >/dev/null 2>&1 <<<"$payload"; then
  emit_deny "dev-harness cannot run: the hook payload did not parse as JSON. Refusing rather than allowing — an unreadable payload is not evidence that the call is safe."
fi

# `agent_id` is present only inside a subagent call, and only a non-blank string counts.
# Without the type test any JSON value except null/false/"" reads as truthy and opens the
# gate the whole guard hangs on.
agent_id=$(jq -r 'if (.agent_id | type) == "string" then .agent_id else "" end' <<<"$payload")
case "$(printf '%s' "$agent_id" | tr -d '[:space:]')" in
# A runtime that stringifies a missing id sends one of these; no agent is named them.
'' | null | undefined | false | 0) ;;
*) exit 0 ;;
esac

tool=$(jq -r '.tool_name // ""' <<<"$payload")
path=$(jq -r '.tool_input.file_path // ""' <<<"$payload")

# The plan, the lane briefs and AGENTS.md are the orchestrator's own artifacts: it writes
# them and reads them, and refusing any of them defeats what the guard exists for. A `..`
# segment forfeits the exemption instead of being resolved, because `.plans/../src/app.js`
# holds the exempt name and lands outside it. Matching two dots anywhere was too wide — it
# refused `.plans/f/release..notes.md`, a plan file named after its feature.
case "$path" in
.. | ../* | */../* | */..) ;;
"$PLAN_DIR_NAME"/* | */"$PLAN_DIR_NAME"/*) exit 0 ;;
"$AGENTS_FILE_NAME" | */"$AGENTS_FILE_NAME") exit 0 ;;
esac

# Ask where the test is a guess, refuse where it is exact. The editing tools name
# themselves, but legitimate exceptions exist and a session-scoped bypass is a heavy price
# for one of them; the shell test cannot tell a real write from a `>` inside a commit
# message. A headless run has nobody to prompt and the permission system denies there, so
# asking costs nothing when no human is present.
case "$tool" in
Edit | MultiEdit | Write | NotebookEdit)
  emit_ask "This edits a file from the main session, which orchestrates rather than develops. The usual path is a lane: an Agent with isolation: worktree, handed the brief from ${PLAN_DIR_NAME}/<feature>/lane-*.md. Approve it if this is a one-off the split does not cover."
  ;;
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
  requested=$(jq -r '.tool_input.limit // empty' <<<"$payload")
  case "$requested" in
  '' | *[!0-9]*) ;;
  *)
    if [ "$requested" -le "$limit" ]; then exit 0; fi
    emit_deny "That Read asks for $requested lines, over the $limit-line budget for the main session. Narrow it, or send an Explore subagent and take its summary."
    ;;
  esac
  [ -f "$path" ] || exit 0
  # Line counts mean nothing for images and other binaries.
  grep -Iq . -- "$path" 2>/dev/null || exit 0
  lines=$(wc -l <"$path" | tr -d ' ')
  bytes=$(wc -c <"$path" | tr -d ' ')
  # A minified bundle is one line and still costs the context the limit exists to protect.
  if [ "$lines" -gt "$limit" ] || [ "$bytes" -gt $((limit * 200)) ]; then
    emit_deny "$path is $lines lines / $bytes bytes; reading it here burns orchestrator context. Send an Explore subagent and take its summary instead. Both overrides are session-scoped, read from the environment before the call runs: raise DEV_HARNESS_READ_LIMIT (now $limit) or set DEV_HARNESS_ALLOW_MAIN=1 in the settings env block, then restart."
  fi
  ;;
Bash)
  # Best-effort only, and deliberately so. Recognising every way a shell can write a file
  # needs a shell parser, and 18 §4 records what happens when two parsers over one string
  # disagree. This catches the forms an agent actually reaches for; it is a speed bump,
  # not a wall, and 21 §3 says so rather than implying otherwise.
  command_line=$(jq -r '.tool_input.command // ""' <<<"$payload")
  # Discard redirections to the null and standard devices first, so the redirection test
  # below does not fire on `… 2>/dev/null`, which every second command carries.
  scrubbed=$(printf '%s' "$command_line" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/[A-Za-z0-9]+##g')
  if printf '%s' "$scrubbed" | grep -Eq \
    '(^|[[:space:]])(tee|patch|truncate|touch|install|mkdir|rmdir)([[:space:]]|$)|(^|[[:space:]])(cp|mv|rm|ln)[[:space:]]+-?|(^|[[:space:]])(sed|perl|ruby)[[:space:]]+-[A-Za-z]*i|(^|[[:space:]])dd[[:space:]][^|]*of=|(^|[[:space:]])git[[:space:]]+(apply|restore|checkout)([[:space:]]|$)|(^|[^0-9&])>[^&]'; then
    emit_ask "This shell command looks like it writes a file, and the main session orchestrates rather than develops. Pattern matching cannot tell a real write from a redirection character inside a commit message or a quoted string, so approve it if that is what this is; otherwise send it to a lane."
  fi
  ;;
esac

exit 0
