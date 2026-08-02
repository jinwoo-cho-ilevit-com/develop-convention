---
description: Run the lanes in a plan — fan out to worktree-isolated agents, review each lane the moment it finishes, then merge and verify end to end
argument-hint: '[feature name — defaults to the only plan under .plans/]'
---

Build: $ARGUMENTS

Read `.plans/<feature>/PLAN.md` and the lane briefs. If the feature is not named and more than one plan exists, ask which.

The conventions this command refers to are in `${CLAUDE_PLUGIN_ROOT}/conventions/`. Read them from there — the project you are working in does not have a copy.

**Before fan-out, freeze the boundaries.** Spawn one agent (isolation: worktree) per boundary the plan lists and have it write that boundary's contract test plus its representative payload at `tests/fixtures/<boundary>.sample.json`. These files belong to no lane, so no lane can quietly change the interface while working against it, and the sample file is the frozen interface in the form two lanes are least able to read differently (→ `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md`). You do not write them yourself; you are the orchestrator and you do not edit (→ `09-agentic-workflow.md`).

Then run the workflow at `${CLAUDE_PLUGIN_ROOT}/workflows/build.js` with the Workflow tool, passing `{ planDir, base, lanes, boundaries, conventionsDir }` read from the plan as `args`. `base` is the commit the lanes branch from; the reviewers diff against it. `conventionsDir` is the expanded `${CLAUDE_PLUGIN_ROOT}/conventions` — the lanes run in the user's repository, where a bare `conventions/` resolves to nothing.

The script is what guarantees the shape: lanes pipeline rather than wait on each other, and review starts when its own lane finishes instead of when all of them do. Do not reimplement that inline — a model asked to "run these in parallel and then review" drifts into a barrier, and the barrier is the bottleneck the design exists to remove (→ `14-context-management.md`).

## When the workflow returns

It returns `{ passed, halted, unanswered, humanCriteria }`. **Handle `halted` and `unanswered` before you touch `passed`** — a report that merges the passing lanes and omits the rest is the failure this split exists to prevent.

1. **Stop on anything in `halted`.** Report each one to the user with its `outcome` and `note`, and do not merge that lane. What each outcome means:
   - `criteria-failed` — the lane's own completion criteria did not pass. It is not done.
   - `review-incomplete` — a review lane returned nothing. Re-run it; do not merge a short review.
   - `review-unexecuted` — every reviewer ran zero commands. Those verdicts are readings, not reviews.
   - `regression-halt` — most of the last round's findings came from the previous fix. This needs a different approach, not another round.
   - `round-cap` — the runaway guard fired. **This is a call for a person, not a completion.**
   - `develop-failed` / `fix-failed` — the agent died. Re-run or investigate.
2. **`unanswered` > 0 means a lane never returned at all.** A lane that finished is not a lane that answered — re-run it rather than reporting a short build.
3. Merge each lane in `passed`. Run the integration lane last.
4. Run the whole-project completion condition from `PLAN.md`.
5. Report the criteria table with the commands that were run and their output — not a narrative summary (→ `19-evidence.md`). Include every lane's `carried` findings; the merge may downgrade a finding but never silently drops one.
6. Any criterion in `humanCriteria` is still open. Ask for the verdict and record it with author and timestamp in the lane brief. An unanswered human check is a TODO, and TODOs block completion.

Claim completion only when `halted` is empty, `unanswered` is zero, and every `[human]` criterion carries a verdict.
