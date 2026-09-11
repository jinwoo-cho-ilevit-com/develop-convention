# 20. Review Gate

Every change goes through a review that its author did not perform. This document covers what the reviewer reads, how many reviewers to run, how their findings are merged, and which tools to run them on. How the work was split and executed in the first place is [09-agentic-workflow.md](09-agentic-workflow.md).

## Core Rules

- Every agent goes through a review separated from its author after development. Choose the review tool before development starts and record it in the review report next to the findings, where the reader of a verdict can see what produced it. Claim completion only with execution evidence.
- A lane judging code runs the code. Give it a way to execute — the test command, the tool under review, a scratch checkout — and have it report how many commands it ran; a verdict from a lane that ran none is a reading, and says so. Measured on one document at one commit, a read-only lane returned "no findings" where an executing lane returned ten, one of them a violation of a stated rule.
- Ask what the author's evidence executed, and whether any of it ran outside the module under change. A suite exercising only the changed module shows that module consistent with itself; a defect crossing a boundary appears when something runs both sides, and reading the two never produces it.
- The reviewer starts from the diff and the criteria and never receives the author's reasoning. Reference context it needs to judge the diff — callers, schemas, convention docs — is fair game; the chain of thought that produced the diff is not.
- Scale review lanes to change risk: a change spanning 2+ modules or touching an interface/schema gets three parallel lanes, each defined by its input — module (diff + changed files), project (diff + callers/callees + convention docs), absence (requirement/plan + diff, hunting for what the diff omits); anything smaller gets one lane. Add a security lane (diff + trust boundaries + input-validation points) only when auth, secrets, or external input is touched.
- Add a fresh-reader lane only when the deliverable is an explainer document (→ [24-explainer-docs.md](24-explainer-docs.md)): its input is the document alone plus the intended reader named in the review request — no code, no author context — and it answers by re-explaining each mechanism in its own words. A mechanism it cannot re-explain, or a term used without a gloss, is a finding.
- Lanes are independent — no lane sees another's output — and the dispatching orchestrator must fan them back in: confirm every lane answered *with content*, dedupe by `file:line`, resolve conflicting advice, verify each finding against the code, and rank by severity. A lane that finished is not a lane that answered (why: → [09-agentic-workflow.md](09-agentic-workflow.md) §2). Unsynthesized parallel output is noise, not a review.
- Mark every finding with what was run, in three states rather than two: confirmed by a run, refuted by a run that reproduced nothing, and unverified because nothing ran. A refutation is a result and is reported as one — a lane that closes its own suspicion honestly is what keeps the next round out of the wrong file.
- A reproduction that will not run refutes nothing. Where a gate the change added rejects the input, or the state the defect needed can no longer be constructed, that is a finding about the procedure: reach the defect another way, or record it as unreproducible. Never record it as fixed.
- Lanes never switch branches in a shared worktree — one checkout erases every other lane's subject. Read the change with `git diff <base>..<branch>` and `git show <ref>:<path>`, or take a separate worktree.
- Pin the review to two explicit commits, and do not move the branch while lanes are reading it. A review tool that takes only a base and diffs it against whatever HEAD currently is will silently re-target itself when the dispatcher commits, so the lane reports on a subject nobody asked about — and the dispatcher is the one moving it, because acting on the first findings is what produces the next commit. Give each lane `<base>..<head>` and have it read through `git show <ref>:<path>` rather than the working tree.
- A finding that depends on a tool's behaviour names the version you tested with, and that version must be the one the project pins. A refutation produced by a different version refutes nothing.
- Two review points are fixed by time rather than by risk, at the depth [18-work-contract.md](18-work-contract.md) §3 sets: **plan** — input is the plan text plus the repository it names; the lane is subject to the executing and no-author-reasoning rules above like any other; **merged-whole** — a lane of its own, absence-shaped but widened to the changed lines at the seams: input is the assembled change pinned to two commits, plus the plan, each lane boundary's contract file, and each unit's pinned range (a unit is a lane, or a commit when the work is sequential), and it hunts for what appears only where units meet. Its findings cross lanes, so the orchestrator dispatches one agent without a worktree to fix in the main tree, re-pins the range to the fix commit for the re-review, and closes the round before any lane's worktree is removed.
- Start a lane's review the moment that lane finishes, not when every lane has. Reviewing on each finish overlaps the review with the lanes still working and the wait never forms; collecting all lanes first creates the pause and then raises the question of what to do during it (→ [14-context-management.md](14-context-management.md) §1).
- A review terminates on evidence, not on output: confirmed blocker-severity findings are fixed and re-reviewed by the lane that raised them, and the remainder is reported with the completion evidence. Producing a findings list is not completing a review.
- Send a lane review's findings back to the agent that wrote the code, in the tree it already has, and end the fix-and-recheck loop — the merged-whole round included — three ways: no blocker remains, or most of this round's findings are defects the previous round's fix introduced — stop and change the approach — or the round cap is reached, which calls a person rather than declaring the lane done. Ask each reviewer to mark whether a finding came from the previous fix; that mark is what makes the second exit measurable. The three exits and why round count is not one of them are in §3.
- Vendor diversity is required at the plan and merged-whole points (below). A unit's own review lanes may run on one model family; record which family ran them in its review points row.
- At the plan and merged-whole points, at the depth [18-work-contract.md](18-work-contract.md) §3 sets, run a Claude Code reviewer lane and Path A (Codex plugin) in parallel rather than choosing one by cadence — running the same input past two vendors is what §2's diversity rule asks for, and these two points are where that cost is worth paying. Substitute Path B (Cursor CLI) for the point only on an enumerated Path A failure — login failure or rate limit, not disagreement with its verdict — and pick its family different from the Claude Code lane's, since Path A did not run to be the reference. Record which tool(s) answered as a combined value in that point's review-points row (e.g. "Claude + Codex", or "Claude + Cursor" on substitution), in the review report. While the plan is being written, ask the user which cursor-agent tier to use if Path B ends up substituting at either point — regardless of whether it does — and record the answer in the plan.

## Details

### 1. What makes a gate work

- **Author is not verifier.** Anchoring is the reason: once a conclusion is in context, a second pass over the same context tends to validate it. Instruct the reviewer to flag correctness and requirement gaps only — asked merely to "find problems", a reviewer manufactures them in sound code and drives over-engineering.
- **Provide runnable checks.** Give the reviewer verification it can execute itself (tests, builds, smoke runs). Without them "looks right" becomes the only signal and the human becomes the verification loop.
- **Evidence-based completion.** A completion report carries the commands run and their output. Evidence is tool execution, not produced prose (→ [06-testing-verification.md](06-testing-verification.md), [19-evidence.md](19-evidence.md)).
- **A gate that passes is not evidence the gate works.** Confirm at least once that it fails when it should. A green gate over a broken check is indistinguishable from a green gate over correct work.
- **Check doc-code synchronization** where docsync tracking is adopted: were the managed docs for the changed module updated with it (→ [15-doc-tracking.md](15-doc-tracking.md))?
- Have a hook run the verification and feed the result back, rather than trying to hold the session open until it passes. A blocked `Stop` hook does not end a run — the model takes another turn and the hook fires again — and the documentation describes no recursion limit and no field that reveals how many times it has already blocked, so a check the model cannot satisfy loops. Nor is there a documented signal for whether a run is unattended, so "only on unattended runs" is not expressible in the hook at all. Inject the failure as context and leave the blocking to a gate a person reads: CI, or the review itself ([Claude Code hooks reference](https://code.claude.com/docs/en/hooks), as of 2026-08).

### 2. Parallel review lanes

A lane is defined by its **input**, not by its attitude. Telling three reviewers to "be critical" over the same input yields three copies of the same findings; the value of parallelism comes from context isolation, which is wasted when the contexts are identical.

| Lane | Input | Looks for |
|---|---|---|
| Module | diff + changed files only | correctness, edge cases, error handling, a criterion with no check, a bug fix whose commit carries no before/after reproduction, a test the sample run already covers |
| Project | diff + callers/callees + convention docs + the contract files of the lane's boundaries | duplicate implementations, layer violations, contract drift, doc-code sync, naming/structure consistency |
| Absence | **requirement/plan + diff** | negative space — whether the stated problem was actually solved, and what is missing (rollback path, failure modes, observability) |
| Plan *(before approval)* | the plan text + the repository it names | constraints the plan breaks (a test it would fail, a rule it restates, a file it omits), and whether its review points cover every unit |
| Merged-whole *(after the last merge)* | the assembled change pinned to two commits + the plan + each unit's pinned range | seams — the same helper changed twice, a rule rewritten in one place and quoted in another, a unit that passed against a subject the merge changed |
| Security *(conditional)* | diff + trust boundaries + input-validation points + [13-secret-management.md](13-secret-management.md) | unvalidated external input, secret handling, authorization gaps on newly reachable paths |
| Fresh reader *(conditional)* | the explainer document alone + the intended reader named in the review request ([24-explainer-docs.md](24-explainer-docs.md)) | mechanisms that cannot be re-explained from the document, unglossed terms, concepts without examples, structure described without a visual |

- **The absence lane's job is what is missing.** Scope it away from re-reading the changed lines, or it degrades into a second module lane. It needs a stated requirement to measure absence against; when the work carried no written plan, write the task statement down before dispatching.
- **Lanes stay independent.** No lane receives another lane's output, and none receives the author's reasoning.
- **Diversify the vendor, not the persona.** Personas layered on one model share that model's blind spots. The plan and merged-whole points (§4) are where the diversity is paid for, by running Path A alongside the Claude Code lane; a unit's own lanes may share one family, and when a different-vendor lane is added there it takes the module role, whose input — just the diff — carries across tools cleanly.
- **The fresh-reader lane judges the document, not the work.** Handing it the code or the author's notes defeats it: the lane would fill comprehension gaps from material the real reader will not have, and the verdict stops measuring the document.

### 3. Fan-in

Fan-out without fan-in is not a review, and the orchestrator that dispatched the lanes owns the merge:

0. Confirm every dispatched lane actually answered. Zero findings is a valid result; a lane that died is not, so re-run it rather than merging a short review.
1. Dedupe by `file:line`, keeping the highest severity any lane gave that location.
2. Resolve contradictory advice into one recommendation, weighting the lane whose input covers the disputed ground — structure and duplication belong to the project lane, edge cases to the module lane.
3. **Check each finding against the actual code**, and mark it in one of three states: confirmed by a run, refuted by a run that reproduced nothing, unverified because nothing ran. A document lane's finding is checked the same way against the cited passage of the document.
4. Rank by severity.

Step 3 matters most. The "reviewers manufacture issues" failure mode is amplified once per lane, so an unfiltered merge hands the noise to the human. The merge may downgrade a finding but never silently drops one — unverified findings are reported as unverified, and refutations are reported too, or the next round re-opens ground already covered.

The third state is not the second. A run that reproduced nothing is a measurement; a reproduction that could not be attempted is not, and the two look alike in a report that records only "not confirmed". Where the attempt was blocked — the input no longer passes a gate the change added, the state the defect needed can no longer be constructed — what has been learned is about the procedure, and the defect is still open.

Severity carries an action, not just a label: **blocker** blocks the merge and is re-reviewed by the lane that raised it, **major** is fixed in the same work, **minor** becomes a follow-up, **nit** may be ignored. A finding with no concrete failing scenario is a nit regardless of how it was filed.

Fix the exit before the first round, because a loop whose condition is "until the reviewers stop finding things" has no fixed point and prose review does not converge on its own:

- Only a **blocker** holds the gate. Everything else is recorded and carried into the work.
- Between rounds, count how many of this round's findings are defects the previous round's fix introduced. When that is most of them, the fix rate has become the defect source: stop and change the approach rather than run another round.
- Narrowing what counts as a blocker mid-gate is legitimate, and it is a decision — write it down, because a rule invented to end a round is invisible to the next one.

Round count is not an exit condition. One loop here ran eleven rounds without converging, and what ended it was noticing the findings had changed in kind — from gates opening wrongly to prose being imprecise — not their number. A round cap is still worth setting as a runaway guard, but reaching it calls a person rather than declaring the lane done.

### 4. Review tools

Choose before development starts. Outside the two fixed points below, a unit's lanes may all use one path; the two fixed points run both.

**Path A — Codex plugin (inside the development session).** With the Stop review gate on (`/codex:setup --enable-review-gate`), an automatic `ALLOW`/`BLOCK` review runs at the end of every turn that changed code, using whatever model the Codex CLI is configured with. After the work is complete, `/codex:review` (standard) and `/codex:adversarial-review` (design-adversarial) are available. The plugin returns the review verbatim and does not auto-fix, so the orchestrator reads and applies it.

**Path B — cursor CLI (external tool).** Shape: `cursor-agent -p --mode ask --model <id> --output-format text "<review prompt for the diff>"`. `--mode ask` (or `--plan`) forces read-only — both allow analysis and read commands but block edits.

- **Do not pin a model id in this document.** Lineups turn over faster than the doc is revised, and a pinned id fails closed: the command errors and the lane simply does not run. Resolve the id at use time with `cursor-agent models` (also `--list-models`, or `/models` interactively), then pick by role — the highest reasoning tier for depth, the cheapest tier that still reads a diff for speed, and a family *different* from Path A's for diversity.
- Always run reviews read-only. Never use `-p` alone: it opens writes and shell access, letting the reviewer modify what it is inspecting.

**The plan and merged-whole points, at the depth 18 §3 sets, run both instead of picking one by cadence.** Dispatch a Claude Code reviewer lane (no author context, per §1) alongside Path A at each of these two points — the redundancy is what §2's vendor-diversity rule already asks for, so it pays for itself only here. Substitute Path B for the point only on an enumerated Path A failure — login failure or rate limit, not disagreement with its verdict — and pick its family different from the Claude Code lane's, since Path A did not run to be the diversity reference. Record which tool(s) actually answered as a combined value next to that point's row (e.g. "Claude + Codex", or "Claude + Cursor" on substitution), in the review report (→ [18-work-contract.md](18-work-contract.md)). Because Path B's model is resolved at use time rather than pinned (above), ask the user for the cursor-agent tier while the plan is being written — regardless of whether the substitution ends up happening — and write the answer into the plan.

For every other lane, the two paths draw on separate quotas, so give them separate jobs rather than ranking them — Path A as the frequent cheap gate while a lane is still being developed, Path B as the deeper pass once that lane's own review runs. When one is exhausted, the other keeps its own role rather than absorbing both.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices), [Cursor — headless CLI](https://cursor.com/docs/cli/headless)
