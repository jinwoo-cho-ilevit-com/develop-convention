#!/usr/bin/env bash
# Keeps the main session an orchestrator: it plans, splits and judges, and delegates
# the work. Subagents carry `agent_id`; the main session does not, which is the whole
# test (→ conventions/09-agentic-workflow.md, 21-development-loop.md).
set -uo pipefail

READ_LINE_LIMIT="${DEV_HARNESS_READ_LIMIT:-500}"
PLAN_DIR="/.plans/"

payload=$(cat)

emit_deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

# A subagent is already the delegate. Nothing to guard.
if [ -n "$(jq -r '.agent_id // empty' <<<"$payload")" ]; then
  exit 0
fi

# Declared bypass. Recorded on stderr so it is never silent (→ 19-evidence.md).
if [ "${DEV_HARNESS_ALLOW_MAIN:-}" = "1" ]; then
  echo "dev-harness: main-session guard bypassed via DEV_HARNESS_ALLOW_MAIN" >&2
  exit 0
fi

tool=$(jq -r '.tool_name // empty' <<<"$payload")

case "$tool" in
  Edit | Write | NotebookEdit)
    emit_deny "The main session does not edit files. Spawn a lane with the Agent tool using isolation: worktree, hand it the brief from .plans/<feature>/lane-*.md, and fan the result back in. One-off bypass: DEV_HARNESS_ALLOW_MAIN=1"
    ;;
  Read)
    path=$(jq -r '.tool_input.file_path // empty' <<<"$payload")
    # The orchestrator's own artifacts are what it is supposed to read.
    case "$path" in *"$PLAN_DIR"*) exit 0 ;; esac
    [ -f "$path" ] || exit 0
    # Line counts mean nothing for images and other binaries.
    grep -Iq . "$path" 2>/dev/null || exit 0
    lines=$(wc -l <"$path" | tr -d ' ')
    if [ "$lines" -gt "$READ_LINE_LIMIT" ]; then
      emit_deny "$path is $lines lines; reading it here burns orchestrator context. Send an Explore subagent and take its summary instead. Raise DEV_HARNESS_READ_LIMIT (now $READ_LINE_LIMIT) or set DEV_HARNESS_ALLOW_MAIN=1 to override."
    fi
    ;;
esac

exit 0
