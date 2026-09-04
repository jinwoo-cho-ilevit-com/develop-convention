# 21. The Development Loop

One pass from "I want to build this" to a merged, verified change. Every step is specified in another document; this one is the order they run in and the seams between them. The `dev-harness` plugin in this repository runs the loop, and running it by hand against the same documents is legitimate.

## Core Rules

Run the steps in this order, each governed by the document beside it. Only the interview rules below belong to this document; everything else is a pointer, because a rule written twice drifts and the first draft of this file proved it — its copy of the loop's exits had already lost one before the change that added it was merged.

| Step | Governed by |
|---|---|
| Orchestrate, do not develop | [09-agentic-workflow.md](09-agentic-workflow.md), [14-context-management.md](14-context-management.md) |
| Interview to a plan and one brief per lane | this document |
| Split by disjoint file ownership | [18-work-contract.md](18-work-contract.md) |
| Freeze each boundary with a contract test before the lanes start | [06-testing-verification.md](06-testing-verification.md) |
| Write criteria as sentence plus command, `[human]` where no command exists | [18-work-contract.md](18-work-contract.md), [19-evidence.md](19-evidence.md) |
| Challenge the plan before asking for approval | [18-work-contract.md](18-work-contract.md) §3, [20-review-gate.md](20-review-gate.md) |
| Review each lane on its own finish, then fix and re-review | [20-review-gate.md](20-review-gate.md) |
| Merge, integrate last | [09-agentic-workflow.md](09-agentic-workflow.md) |
| Review the merged whole, then verify end to end | [20-review-gate.md](20-review-gate.md), [06-testing-verification.md](06-testing-verification.md) |

- Specify by interview, not by template. What to ask about is derived from this project — infer the axes from the request and the repository, check once for what recent practice adds, then keep only those that name a way this project could fail. A fixed axis list can only cover what someone already knew to list.
- Keep the axis list open during the interview. When an answer reveals an axis you did not have, add it. Record every axis and its state — decided, not applicable, still open — because that record is the only account of what was never asked.
- The interview ends when the person says it ends, and its output is a plan plus one brief per lane, not prose.

## Details

### 1. The loop

| Step | What happens | Specified in |
|---|---|---|
| Interview | Axes derived from the project, one question at a time, every proposal sourced | §2 below, [16-research-protocol.md](16-research-protocol.md) |
| Plan | `PLAN.md` (decisions, rejected alternatives, axis table, boundaries, lanes, review points, whole-project condition) + `lane-<name>.md` per lane | [18-work-contract.md](18-work-contract.md) |
| Freeze | One contract test per boundary, plus its sample payload. Owned by no lane | [06-testing-verification.md](06-testing-verification.md) §1 |
| Fan out | One worktree-isolated agent per lane, disjoint `owns` | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |
| Review | Starts per lane on that lane's finish; lanes defined by input; fix and recheck | [20-review-gate.md](20-review-gate.md) |
| Merge | Criteria pass → merge; integration lane last | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |
| Verify | Whole-project condition, `[human]` criteria answered, evidence reported as a criteria table | [19-evidence.md](19-evidence.md) |
| Clean up | Merged lanes lose worktree and branch; halted lanes keep theirs | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |

### 2. Deriving what to ask

Three steps, in this order, because they fail differently.

**Infer first.** Read the request and, where one exists, the repository itself — dependencies, layout, CI, data paths — and work out what decisions will shape this work. An axis is a hypothesis about where to look, not a claim about the world, which is exactly what [16-research-protocol.md](16-research-protocol.md) permits prior knowledge to produce. The costs are asymmetric: a wrong fact reaches the deliverable, while a wrong axis is asked once and answered "not applicable".

**Then check for absence.** One narrow research pass whose question is "what has recently become standard that my list is missing", not "what is the answer". Practices newer than the model's training data appear no other way, and a query built from memory cannot find a tool whose name has changed since.

**Then filter by failure.** Keep an axis only if this project could plausibly fail because of it. This is what makes the list fit the project without anyone maintaining a taxonomy: a CLI tool yields no design-failure scenario and gets no design axis, while a pipeline yields an evaluation one and gets an evaluation axis.

A greenfield project has no repository to ground the first step, which is where the list is weakest and where keeping it open matters most.

### 3. Why the loop has these seams

**Ownership is not agreement.** The split rule guarantees two lanes never write the same file. It guarantees nothing about the two of them agreeing on what passes between them, and the more finely the work divides the more such boundaries exist. Freezing each one as an executable test before either lane starts is the only step that closes this, and it has to happen before, not after — a boundary discovered at merge time costs both lanes.

**A barrier is a choice, not a fact.** Lanes finish at different times. Reviewing on each finish means a lane's review overlaps with other lanes still working, and the wait disappears rather than being filled. Collecting all lanes before reviewing any creates the pause and then invites the question of what to do during it. Prefer the pipeline (→ [14-context-management.md](14-context-management.md) §1).

**Two review points are fixed by time, not by risk.** Every other lane is chosen by what the change touches; the plan review and the merged-whole review are chosen by when they run. Before approval is the last moment a direction can change cheaply, and after the last merge is the first moment the seams between units exist to be read — a unit review passes each piece against itself, and what only appears where pieces meet has no earlier reader.

**A fix is a change, and changes have defects.** A review loop with no exit but "reviewers stopped finding things" has no fixed point. The signal that ends it is not the count of rounds — one loop in this repository ran eleven without converging — but the finding that this round's defects came from last round's fix. At that point another round adds defects faster than it removes them.

**Delegation is convention; the guard holds only the context budget.** It refuses a read past that budget, where no false positive exists and the alternative — a narrower read, or a subagent that returns the answer instead of the file — is strictly better. It does not gate the editing tools, and it does not try to recognise a shell command that writes. Both tests have legitimate exceptions, and the shell one cannot be made exact: deciding it needs a shell parser, and [18-work-contract.md](18-work-contract.md) records what happened here when two parsers over one command string disagreed, the stricter one raising where the real one did not, the error swallowed, and an unquoted operator going through unchecked. A prompt on every edit is a standing cost paid on the common path for a rule the hook cannot actually hold, so the rule is stated where rules live and the hook keeps the one judgement it can make exactly. Do not read a passing hook as proof the main session stayed out of the tree — it was never evidence of that, and now it does not even look like it.

Sources: this document records the loop this repository runs on itself; each step's evidence is in the document it links to.
