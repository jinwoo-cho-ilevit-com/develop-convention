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

payload=$(cat)

emit_deny() {
  # Written without jq so this still works when jq is the thing that is missing.
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/^/"/' -e 's/$/"/' | tr -d '\n')"
  exit 0
}

if ! command -v jq >/dev/null 2>&1; then
  emit_deny "dev-harness cannot run: jq is not on PATH, and without it this guard cannot read the hook payload. Install jq, or set DEV_HARNESS_ALLOW_MAIN=1 to work unguarded. Refusing rather than allowing, because a guard that silently stops guarding is worse than no guard."
fi

if ! jq -e . >/dev/null 2>&1 <<<"$payload"; then
  emit_deny "dev-harness cannot run: the hook payload did not parse as JSON. Refusing rather than allowing — an unreadable payload is not evidence that the call is safe."
fi

# The bypass is declared and recorded on stderr, so it is never silent (→ 19-evidence.md).
if [ "${DEV_HARNESS_ALLOW_MAIN:-}" = "1" ]; then
  echo "dev-harness: main-session guard bypassed via DEV_HARNESS_ALLOW_MAIN" >&2
  exit 0
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

# The plan and the lane briefs are the orchestrator's own artifacts — it writes them and
# reads them, and blocking either defeats what the guard exists for. Matched on the path
# segment so an absolute and a relative spelling of the same file get the same verdict.
case "$path" in
"$PLAN_DIR_NAME"/* | */"$PLAN_DIR_NAME"/*) exit 0 ;;
esac

case "$tool" in
Edit | MultiEdit | Write | NotebookEdit)
  emit_deny "The main session does not edit files. Spawn a lane with the Agent tool using isolation: worktree, hand it the brief from ${PLAN_DIR_NAME}/<feature>/lane-*.md, and fan the result back in. One-off bypass: DEV_HARNESS_ALLOW_MAIN=1"
  ;;
Read)
  limit="${DEV_HARNESS_READ_LIMIT:-$DEFAULT_READ_LINE_LIMIT}"
  case "$limit" in
  '' | *[!0-9]*)
    echo "dev-harness: DEV_HARNESS_READ_LIMIT=$limit is not a line count; using $DEFAULT_READ_LINE_LIMIT" >&2
    limit=$DEFAULT_READ_LINE_LIMIT
    ;;
  esac
  [ -f "$path" ] || exit 0
  # Line counts mean nothing for images and other binaries.
  grep -Iq . -- "$path" 2>/dev/null || exit 0
  lines=$(wc -l <"$path" | tr -d ' ')
  bytes=$(wc -c <"$path" | tr -d ' ')
  # A minified bundle is one line and still costs the context the limit exists to protect.
  if [ "$lines" -gt "$limit" ] || [ "$bytes" -gt $((limit * 200)) ]; then
    emit_deny "$path is $lines lines / $bytes bytes; reading it here burns orchestrator context. Send an Explore subagent and take its summary instead. Raise DEV_HARNESS_READ_LIMIT (now $limit) or set DEV_HARNESS_ALLOW_MAIN=1 to override."
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
    '(^|[[:space:]])(tee|patch|truncate)([[:space:]]|$)|(^|[[:space:]])(sed|perl|ruby)[[:space:]]+-[A-Za-z]*i|(^|[[:space:]])dd[[:space:]][^|]*of=|(^|[[:space:]])git[[:space:]]+(apply|restore)([[:space:]]|$)|(^|[^0-9&])>[^&]'; then
    emit_deny "That shell command writes files, and the main session does not edit. Delegate it to a lane with the Agent tool, or set DEV_HARNESS_ALLOW_MAIN=1 for this one call. Read-only shell work (git, ls, grep, test runs) is not affected."
  fi
  ;;
esac

exit 0
