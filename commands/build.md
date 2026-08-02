---
description: Run the lanes in a plan — fan out to worktree-isolated agents, review each lane the moment it finishes, then merge and verify end to end
argument-hint: '[feature name — defaults to the only plan under .plans/]'
---

Build: $ARGUMENTS

Read `.plans/<feature>/PLAN.md` and the lane briefs. If the feature is not named and more than one plan exists, ask which.

**Before fan-out**, write the contract test for every boundary the plan lists. These files belong to no lane, so no lane can quietly change the interface while working against it. Store the representative payload for each boundary as `tests/fixtures/<boundary>.sample.json` and have the factory load it — the sample file *is* the frozen interface, in the form two lanes are least able to read differently (→ `conventions/06-testing-verification.md`).

Then run the workflow at `${CLAUDE_PLUGIN_ROOT}/workflows/build.js` with the Workflow tool, passing `{ planDir, lanes, boundaries, doneCondition }` read from the plan as `args`.

The script is what guarantees the shape: lanes pipeline rather than wait on each other, and review starts when its own lane finishes instead of when all of them do. Do not reimplement that inline — a model asked to "run these in parallel and then review" drifts into a barrier, and the barrier is the bottleneck the design exists to remove (→ `conventions/14-context-management.md`).

You are the orchestrator. You do not edit files; the lanes do (→ `conventions/09-agentic-workflow.md`).

When the workflow returns:

1. Merge each lane branch whose criteria passed. Run the integration lane last.
2. Run the whole-project completion condition from `PLAN.md`.
3. Report the criteria table with the commands that were run and their output — not a narrative summary (→ `conventions/19-evidence.md`).
4. Any criterion marked `[human]` is still open. Ask for the verdict and record it with author and timestamp in the lane brief. An unanswered human check is a TODO, and TODOs block completion.
