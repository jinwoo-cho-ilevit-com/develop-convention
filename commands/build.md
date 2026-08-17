---
description: Run the lanes in a plan — fan out to worktree-isolated agents, review each lane the moment it finishes, then merge and verify end to end
argument-hint: '[feature name — defaults to the only plan under .plans/]'
---

Build: $ARGUMENTS

Read `.plans/<feature>/PLAN.md` and the lane briefs. If the feature is not named and more than one plan exists, ask which.

The conventions this command refers to are in `${CLAUDE_PLUGIN_ROOT}/conventions/`. Read them from there — the project you are working in does not have a copy.

**Before fan-out, freeze the boundaries.** Spawn one agent (isolation: worktree) for every boundary the plan lists — one agent for all of them, not one each — and have it write each boundary's contract test plus the representative payload at the `sample` path that row names. Two rows naming the same path share one file: that is how the plan records an object reaching both boundaries, and the agent writes it once. These files belong to no lane, so no lane can quietly change the interface while working against it, and the sample file is the frozen interface in the form two lanes are least able to read differently (→ `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md`). You do not write them yourself; you are the orchestrator and you do not edit (→ `09-agentic-workflow.md`).

One agent, because a domain object rarely stays inside one boundary. An agent whose whole world is a single row draws that object from one consumer's point of view; a second agent draws the same object from another's, and both are locally coherent. Each contract test then reads only its own fixture, so nothing in the suite ever compares them, and the lanes develop against shapes that cannot both be satisfied. One agent holding every boundary at once is what makes the disagreement visible while it is still cheap. Require of it: field names and literal values resolved from one importable source rather than respelled per contract file, and an answer naming every object it found in more than one boundary. If it finds one the plan gave two separate `sample` paths, stop and fix the plan — merging the files here would leave a path the workflow's existence check cannot find, and it refuses the whole fan-out for a missing sample.

Then run the workflow at `${CLAUDE_PLUGIN_ROOT}/workflows/build.js` with the Workflow tool, passing `{ planDir, base, lanes, boundaries, conventionsDir, boundariesFrozen: true }` read from the plan as `args`. `base` is what the reviewers diff against and what each lane is told to reset to: a worktree is cut from `origin/main` rather than from `base`, so nothing else puts a lane on that commit. `conventionsDir` is the expanded `${CLAUDE_PLUGIN_ROOT}/conventions` — the lanes run in the user's repository, where a bare `conventions/` resolves to nothing. `boundariesFrozen` is your declaration that the step above is done: the workflow refuses to fan out without it, since it is also invokable as a skill and that path skips the freeze. It then checks that each boundary's `test` and `sample` file actually exists and refuses if any is missing, so the declaration on its own does not get a build through.

The script is what guarantees the shape: lanes pipeline rather than wait on each other, and review starts when its own lane finishes instead of when all of them do. Do not reimplement that inline — a model asked to "run these in parallel and then review" drifts into a barrier, and the barrier is the bottleneck the design exists to remove (→ `14-context-management.md`).

## When the workflow returns

It returns `{ passed, halted, unanswered, escalations, vendorDiversity }`. **Handle `halted` and `unanswered` before you touch `passed`** — a report that merges the passing lanes and omits the rest is the failure this split exists to prevent.

1. **Stop on anything in `halted`.** Report each one to the user with its `outcome` and `note`, and do not merge that lane. What each outcome means:
   - `criteria-failed` — the lane's own completion criteria did not pass. It is not done.
   - `pending-human` — the lane is clean but a `[human]` criterion has no verdict. **Ask for it now, before merging.** Record verdict, author and timestamp in the lane brief. A merged lane is past the point where a rejection can act (→ `19-evidence.md`).
   - `review-incomplete` — a review lens returned nothing. Re-run it; do not merge a short review.
   - `review-unexecuted` — a review lens ran zero commands. That verdict is a reading, not a review.
   - `verification-incomplete` — the verifier's answer did not map one to one onto the blockers it was given: missing, duplicated, unknown or self-contradicting rows. A verification that did not happen decides nothing, so nothing was decided.
   - `regression-halt` — the findings are repeating or coming from the last fix. This needs a different approach, not another round.
   - `round-cap` — the runaway guard fired. **This is a call for a person, not a completion.**
   - `develop-failed` / `fix-failed` — the agent died. Re-run or investigate.
2. **`unanswered` > 0 means a lane never returned at all.** A lane that finished is not a lane that answered — re-run it rather than reporting a short build.
3. **`escalations` is the list that needs a person.** Every entry must be answered or reported; none of them is a completion.
4. Merge each lane in `passed`. Run the integration lane last.
5. Run the whole-project completion condition from `PLAN.md`.
6. Close the merged lanes: `git worktree remove <path>` (no `--force`) and `git branch -d <branch>` (not `-D`) for each lane in `passed`. Either command refusing is a safety check firing — investigate before touching the flag. Leave every halted lane's worktree and branch in place; fix rounds continue in them (→ `09-agentic-workflow.md` §2).
7. Report the criteria table with the commands that were run and their output — not a narrative summary (→ `19-evidence.md`). Include every lane's `carried` findings; the merge may downgrade a finding but never silently drops one. Report `vendorDiversity` verbatim: every review lens ran on one model family, and a report that stays quiet about it reads as if the rule were met.

Claim completion only when `halted` is empty, `unanswered` is zero, and `escalations` is empty.
