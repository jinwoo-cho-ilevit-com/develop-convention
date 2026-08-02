# 21. The Development Loop

One pass from "I want to build this" to a merged, verified change. Every step is specified in another document; this one is the order they run in and the seams between them. The `dev-harness` plugin in this repository runs the loop, and running it by hand against the same documents is legitimate.

## Core Rules

- The main session orchestrates and does not develop. It interviews, splits the work, judges results, and delegates every edit to a subagent — reading and writing in the main context spends the budget the orchestration needs (→ [09-agentic-workflow.md](09-agentic-workflow.md), [14-context-management.md](14-context-management.md)).
- Specify by interview, not by template. What to ask about is derived from this project — infer the axes from the request and the repository, check once for what recent practice adds, then keep only those that name a way this project could fail. A fixed axis list can only cover what someone already knew to list.
- Keep the axis list open during the interview. When an answer reveals an axis you did not have, add it. Record every axis and its state — decided, not applicable, still open — because that record is the only account of what was never asked.
- The interview ends when the person says it ends, and its output is a plan plus one brief per lane, not prose.
- Split as far as disjoint file ownership allows, and freeze every boundary the split creates with a contract test written **before** the lanes start. The test file belongs to no lane. Lanes that own separate files can still hold contradictory assumptions about what crosses between them; the test is the assumption in the form least open to reinterpretation (→ [06-testing-verification.md](06-testing-verification.md) §1).
- Write each completion criterion as a sentence paired with the command that checks it. A criterion with no possible command is marked `[human]` and carries a verdict, an author, and a timestamp before the lane closes (→ [18-work-contract.md](18-work-contract.md), [19-evidence.md](19-evidence.md)).
- Review a lane the moment that lane finishes, not when all of them do. Waiting for the last lane manufactures the bottleneck; overlapping review with the lanes still running removes it (→ [20-review-gate.md](20-review-gate.md), [14-context-management.md](14-context-management.md) §1).
- Send findings back to the lane that wrote the code, in the tree it already has, and re-review. The loop has three exits and no others, defined in [20-review-gate.md](20-review-gate.md) §3.
- Merge a lane only after its criteria pass, run the integration lane last, and verify the assembled project end to end before claiming completion (→ [09-agentic-workflow.md](09-agentic-workflow.md), [06-testing-verification.md](06-testing-verification.md)).

## Details

### 1. The loop

| Step | What happens | Specified in |
|---|---|---|
| Interview | Axes derived from the project, one question at a time, every proposal sourced | §2 below, [16-research-protocol.md](16-research-protocol.md) |
| Plan | `PLAN.md` (decisions, rejected alternatives, axis table, boundaries, lanes, whole-project condition) + `lane-<name>.md` per lane | [18-work-contract.md](18-work-contract.md) |
| Freeze | One contract test per boundary, plus its sample payload. Owned by no lane | [06-testing-verification.md](06-testing-verification.md) §1 |
| Fan out | One worktree-isolated agent per lane, disjoint `owns` | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |
| Review | Starts per lane on that lane's finish; lanes defined by input; fix and recheck | [20-review-gate.md](20-review-gate.md) |
| Merge | Criteria pass → merge; integration lane last | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |
| Verify | Whole-project condition, `[human]` criteria answered, evidence reported as a criteria table | [19-evidence.md](19-evidence.md) |

### 2. Deriving what to ask

Three steps, in this order, because they fail differently.

**Infer first.** Read the request and, where one exists, the repository itself — dependencies, layout, CI, data paths — and work out what decisions will shape this work. An axis is a hypothesis about where to look, not a claim about the world, which is exactly what [16-research-protocol.md](16-research-protocol.md) permits prior knowledge to produce. The costs are asymmetric: a wrong fact reaches the deliverable, while a wrong axis is asked once and answered "not applicable".

**Then check for absence.** One narrow research pass whose question is "what has recently become standard that my list is missing", not "what is the answer". Practices newer than the model's training data appear no other way, and a query built from memory cannot find a tool whose name has changed since.

**Then filter by failure.** Keep an axis only if this project could plausibly fail because of it. This is what makes the list fit the project without anyone maintaining a taxonomy: a CLI tool yields no design-failure scenario and gets no design axis, while a pipeline yields an evaluation one and gets an evaluation axis.

A greenfield project has no repository to ground the first step, which is where the list is weakest and where keeping it open matters most.

### 3. Why the loop has these seams

**Ownership is not agreement.** The split rule guarantees two lanes never write the same file. It guarantees nothing about the two of them agreeing on what passes between them, and the more finely the work divides the more such boundaries exist. Freezing each one as an executable test before either lane starts is the only step that closes this, and it has to happen before, not after — a boundary discovered at merge time costs both lanes.

**A barrier is a choice, not a fact.** Lanes finish at different times. Reviewing on each finish means a lane's review overlaps with other lanes still working, and the wait disappears rather than being filled. Collecting all lanes before reviewing any creates the pause and then invites the question of what to do during it. Prefer the pipeline (→ [14-context-management.md](14-context-management.md) §1).

**A fix is a change, and changes have defects.** A review loop with no exit but "reviewers stopped finding things" has no fixed point. The signal that ends it is not the count of rounds — one loop in this repository ran eleven without converging — but the finding that this round's defects came from last round's fix. At that point another round adds defects faster than it removes them.

**The delegation guard is a speed bump on the shell, not a wall.** It refuses the file-editing tools outright, which is exact, and it refuses the shell commands that obviously write — redirection to a file, `tee`, an in-place `sed`, `git apply`. It cannot refuse every shell command that writes, because deciding that needs a shell parser, and [18-work-contract.md](18-work-contract.md) records what happened here when two parsers over one command string disagreed: the stricter one raised where the real one did not, the error was swallowed, and an unquoted operator went through unchecked. Treat the shell path as convention rather than enforcement, and do not read a passing hook as proof the main session stayed out of the tree.

Sources: this document records the loop this repository runs on itself; each step's evidence is in the document it links to.
