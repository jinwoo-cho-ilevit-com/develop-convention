# 21. The Development Loop

The planned loop runs from a work proposal to a merged, verified change. Narrow, reversible `auto` work follows the direct path in [18-work-contract.md](18-work-contract.md) §3 and does not enter `/spec` or `/build`. The `dev-harness` plugin runs the planned loop; running it by hand against the same documents is legitimate.

## Core Rules

- For `reviewed` and `proven` planned work, run the applicable steps in this order, each governed by the document named beside it. `reviewed` requires one independent unit review and a merged-seam review only when multiple lanes merge; `proven` adds the risk-based plan and review depth in [20-review-gate.md](20-review-gate.md).
  - Orchestrate, do not develop: [09-agentic-workflow.md](09-agentic-workflow.md), [14-context-management.md](14-context-management.md).
  - Interview to a plan and one brief per lane: this document.
  - Split by disjoint file ownership: [18-work-contract.md](18-work-contract.md).
  - Write criteria as sentence plus command, `[human]` where no command exists: [18-work-contract.md](18-work-contract.md), [19-evidence.md](19-evidence.md).
  - Choose the done level: [18-work-contract.md](18-work-contract.md) §3.
  - Challenge a `proven` plan before asking for approval: [18-work-contract.md](18-work-contract.md) §3, [20-review-gate.md](20-review-gate.md).
  - Freeze each boundary with a contract file and its sample before the lanes start: [06-testing-verification.md](06-testing-verification.md).
  - Review each lane on its own finish, then fix and re-review: [20-review-gate.md](20-review-gate.md).
  - Merge, integration lane last: [09-agentic-workflow.md](09-agentic-workflow.md).
  - After multiple lanes merge, review their seams, then check the end-to-end condition: [20-review-gate.md](20-review-gate.md), [06-testing-verification.md](06-testing-verification.md).
- Specify by interview, not by template. What to ask about is derived from this project — infer the axes from the request and the repository, check once for what recent practice adds, then keep only those that name a way this project could fail. A fixed axis list can only cover what someone already knew to list.
- Keep the axis list open during the interview. When an answer reveals an axis you did not have, add it. Record every axis and its state — decided, not applicable, still open — because that record is the only account of what was never asked.
- The interview ends when the person says it ends, and its output is a plan plus one brief per lane, not prose.

## Details

### 1. The loop

| Step | What happens | Specified in |
|---|---|---|
| Interview | Axes derived from the project, one question at a time, every proposal sourced | §2 below, [16-research-protocol.md](16-research-protocol.md) |
| Plan | `PLAN.md` (done level, decisions, rejected alternatives, axis table, boundaries, lanes, review points, end-to-end condition) + `lane-<name>.md` per lane | [18-work-contract.md](18-work-contract.md) |
| Challenge | For `proven`, review the plan against its risks before approval | [20-review-gate.md](20-review-gate.md) §2 |
| Freeze | One contract file per boundary, plus its sample payload and, where the payload lands as JSON, YAML or TOML, its schema. Owned by no lane | [06-testing-verification.md](06-testing-verification.md) §1, §7 |
| Fan out | One worktree-isolated agent per lane, disjoint `owns`. An unattended lane reads no untrusted text: what the work needs from outside was fetched at plan time and reaches it as the brief | [09-agentic-workflow.md](09-agentic-workflow.md) §2, [25-agent-sandboxing.md](25-agent-sandboxing.md) §3 |
| Review | Starts per lane on that lane's finish; lanes defined by input; fix and recheck | [20-review-gate.md](20-review-gate.md) |
| Merge | Criteria and CI checks pass, review closed on no blocker → merge; integration lane last | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |
| Merged-whole | When multiple lanes merged, one review over the assembled seams, pinned to two commits, before worktrees are removed | [20-review-gate.md](20-review-gate.md) §2 |
| Verify | End-to-end condition ([18-work-contract.md](18-work-contract.md) §1), `[human]` criteria answered, evidence reported as a criteria table | [19-evidence.md](19-evidence.md) |
| Clean up | Merged lanes lose worktree and branch; halted lanes keep theirs | [09-agentic-workflow.md](09-agentic-workflow.md) §2 |

### 2. Deriving what to ask

Three steps, in this order, because they fail differently.

**Infer first.** Read the request and, where one exists, the repository itself — dependencies, layout, CI, data paths — and work out what decisions will shape this work. An axis is a hypothesis about where to look, not a claim about the world, which is exactly what [16-research-protocol.md](16-research-protocol.md) permits prior knowledge to produce. The costs are asymmetric: a wrong fact reaches the deliverable, while a wrong axis is asked once and answered "not applicable".

**Then check for absence.** One narrow research pass whose question is "what has recently become standard that my list is missing", not "what is the answer". Practices newer than the model's training data appear no other way, and a query built from memory cannot find a tool whose name has changed since.

**Then filter by failure.** Keep an axis only if this project could plausibly fail because of it. This is what makes the list fit the project without anyone maintaining a taxonomy: a CLI tool yields no design-failure scenario and gets no design axis, while a pipeline yields an evaluation one and gets an evaluation axis.

A greenfield project has no repository to ground the first step, which is where the list is weakest and where keeping it open matters most.

### 3. Why the loop has these seams

**Ownership is not agreement.** The split rule guarantees two lanes never write the same file. It guarantees nothing about the two of them agreeing on what passes between them, and the more finely the work divides the more such boundaries exist. Freezing each one as a contract file and a sample both lanes read before either starts is the only step that closes this, and it has to happen before, not after — a boundary discovered at merge time costs both lanes.

**A barrier is a choice, not a fact.** Lanes finish at different times; when each lane's review starts, and why waiting for all of them costs more than it saves, is [20-review-gate.md](20-review-gate.md) Core Rules.

**Review points follow risk and assembly.** `proven` work challenges its plan before approval, when direction can still change cheaply. Multi-lane work reviews the assembled seams after the last merge, when both sides can be read together.

**A fix is a change, and changes have defects.** A review loop with no exit but "reviewers stopped finding things" has no fixed point. The signal that ends it is not the count of rounds but the finding that this round's defects came from last round's fix (→ [20-review-gate.md](20-review-gate.md) §3). At that point another round adds defects faster than it removes them.

**Delegation is a planned-work convention; the guard holds only the context budget.** `auto` follows the direct path. The hook refuses reads beyond its budget and does not gate edits or parse shell commands for writes. A passing hook does not prove who edited the tree.

Sources: this document records the loop this repository runs on itself; each step's evidence is in the document it links to.
