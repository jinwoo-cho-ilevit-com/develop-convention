# 18. Work Contract

A **work contract** fixes three things in the same identifiers before the work starts: what counts as done (**completion criteria**), who may edit what (**ownership**), and how far verification must go (**done level**). Without it, "done" is renegotiated every time and there is no baseline to measure drift against. Its form is the plan and the lane briefs the interview produces (→ [21-development-loop.md](21-development-loop.md)); a contract is a checklist, not a specification, and its minimum is three to five lines.

## Core Rules

- Write the contract before development starts and freeze it during execution. Record any change with its kind; an additive change touching no existing criterion or ownership entry updates only the affected lane.
- A plan shown for approval carries a `## Review points` table — one row per review lane of each unit the work is split by (a lane, or a commit when the work is sequential) plus one row per pass at the pre-approval and post-merge points, with columns unit, lane, input, tool, ran (commands the lane executed), exit. `exit` is the round's final state only — `no blocker`, `regression-halt`, `round-cap`, or the workflow's own outcome string when a harness ran the lane — and round history goes in a line under the table; an `auto` plan closes its two fixed-point rows as `skipped (auto)`. An empty exit on the pre-approval row blocks approval, on any other row blocks completion. The plan file keeps the table as the record; in the harness that file is `PLAN.md`.
- Scale the contract to the work. Three to five lines — what is being built, done level, criteria, out of scope — is complete for small work, and that form is not the heavyweight spec [09-agentic-workflow.md](09-agentic-workflow.md) §4 warns against.
- Write every criterion in EARS or Given-When-Then with `SHALL`, and apply the judgment test: **if two agents could disagree about whether it passed, rewrite it.**
- Pair every criterion with the command that checks it, or mark it `[human]`. A criterion that is neither is not a criterion. The sentence is not decoration: without it nothing can be judged against the criterion, and a test that checks the wrong thing still passes.
- The command must reach a verdict inside the lane that owns the criterion, against that lane's work alone. A command that imports a sibling lane's module fails on import and says nothing about the lane it was given to, so cross-lane contract tests and the end-to-end condition are the integration step's criteria rather than a lane's (→ [06-testing-verification.md](06-testing-verification.md) §1).
- A `[human]` criterion passes only once the verdict record in [19-evidence.md](19-evidence.md) §3 exists (verdict, author, timestamp); an unanswered human check is a blocker.
- Cover functional, non-functional, and **negative** criteria — what must *not* happen. The negative kind is what stops over-building. State what is out of scope; an unstated boundary is the one that gets crossed.
- For a rewrite, include a characterization criterion that pins existing behaviour first (→ [00-principles.md](00-principles.md)).
- Declare the done level before starting, chosen by size × reversibility. At every level three things are mandatory: every criterion passes, the evidence exists, and each new test was observed failing at the base commit (the red check and its three outcomes are defined in [06-testing-verification.md](06-testing-verification.md) §3; this document does not restate them).
- Ask of every criterion whether it was already true at the base commit. If it was, it is a standing invariant — mark it exempt from the red check and say why. An absence criterion almost always is (→ [06-testing-verification.md](06-testing-verification.md) §3).
- Enumerate the boundaries by asking where two lanes could believe differently, not by asking what data passes between them. Four surfaces drift independently: the shape of a shared payload, the name and signature of every symbol one lane calls in another, the accepted value set of a field both sides branch on, and the call graph itself. A lane that only consumes sends nothing outward, so a payload-derived list leaves the lane with the widest call surface holding no contract at all (§5, → [06-testing-verification.md](06-testing-verification.md) §1).
- Give every lane a disjoint set of owned paths, written as directory prefixes wherever the work divides that way. Globs expanded against the current file list miss files that do not exist yet, which is the collision the rule exists to prevent.
- Name cross-cutting files individually, one owner each. A repository has files that belong to no directory — the README, the ignore file, the site config — and a prefix rule cannot assign them, so a decomposition that only knows prefixes silently leaves them to whoever touches them first. Give the integration lane an explicit list and run it last.
- Slice by file, not by phase, when several kinds of change land in the same documents. Three lanes each doing "their kind of edit" across the same files collide by construction; one lane per file, carrying every kind of edit for that file, does not.
- Assign lock files, migrations, and generated files to a single owner, never to a lane.
- Record the model tier per lane (`light`/`mid`/`top`), never a model id, so the routing choice can be audited afterwards.

## Details

### 1. Terms

| Term | Meaning |
|---|---|
| completion criteria | Conditions fixed before the work that decide whether it is done. Identified `C-01`, `C-02`, … |
| done level | How far verification must go: `auto` / `reviewed` / `proven` |
| EARS | A sentence template that removes ambiguity: `WHEN <trigger> THE <system> SHALL <response>` |
| red check | Confirming a new test actually fails at the base commit |

Avoid two-letter abbreviations in contracts and in the documents describing them. A reader who has to decode a field name will not check the field.

### 2. Writing criteria

EARS constrains a sentence into trigger, condition, system, and response. Given-When-Then does the same through precondition, action, expected result. Either is fine; mixing them in one contract is not.

Each criterion is a sentence and the command that checks it:

```markdown
## Completion criteria

- C-01: WHEN the input CSV contains NaN in `score`,
  THE loader SHALL drop the row and log a WARNING with the row index.
  → uv run pytest tests/test_c01_drops_nan_rows.py -q
- C-02: The loader→scorer boundary holds.
  → uv run pytest tests/contract/test_loader_scorer.py -q
- C-03: [human] The warning is actionable for someone reading the log at 3am.
  → verdict: ____  by: ____  at: ____

## Out of scope
- Score normalisation (lane-b owns it)
```

The two halves fail differently, which is why both are required. A command with no sentence cannot be wrong — it passes or it does not — so nobody ever asks whether it checks the right thing, and a test asserting the wrong behaviour reports green forever. A sentence with no command defers the judgment to verification time, which is what the contract exists to remove.

The anti-patterns are criteria that cannot fail: "handle errors gracefully", "must load quickly", "should be relevant".

`[human]` is legitimate — some judgments genuinely are. It is not an escape hatch: the verdict, its author and its time are written into the same file before the criterion counts as passed.

Sources: [EARS, fifteen years on](https://joshmcdonald.medium.com/ears-fifteen-years-on-the-requirements-format-built-for-the-agent-era-0f78f8ff35a0), [acceptance criteria an agent can verify](https://www.braingrid.ai/blog/how-to-write-acceptance-criteria-ai-agent-can-verify)

### 3. Done level

| Level | Adds to the mandatory three | Use for |
|---|---|---|
| `auto` | nothing | docs, formatting, behaviour-preserving refactors |
| `reviewed` | zero confirmed blockers from a review that did not author the change | the default |
| `proven` | integration smoke + one run on real data | new modules, pipelines, anything with external effect |

Choose by **size × reversibility**:

|  | Easy to reverse | Hard to reverse (migration, deploy, data transform, public API) |
|---|---|---|
| Single module | `auto` | **`proven`** |
| Two or more modules, or an interface/schema change | `reviewed` | `proven` |

The upper-right cell is what a size-only rule misses: a one-line change to a published signature is small and nearly impossible to take back.

Evidence sits outside the dial deliberately. If it were a property of the higher levels, "this is only `auto`" would become the way to skip it.

There is no separate planning-depth setting. How hard a plan is challenged follows the done level, at the two points [20-review-gate.md](20-review-gate.md) §2 fixes by time: `auto` skips both, `reviewed` runs the point's lane once, `proven` runs it twice. A second dial would only be another thing to under-report.

### 4. Changing and closing a contract

Freezing prevents drift across parallel lanes, but a rule forcing every lane to restart over one added criterion gets quietly ignored, and a contract nobody follows is worse than none.

- **additive**, touching no existing criterion or owned path: update the affected lane, others continue
- **narrowing**: stop the lanes that owned the removed scope
- **breaking**: stop everything, update, restart

Record kind and reason either way.

A contract with a verdict still outstanding is not complete and is not deleted. Where another begins before it closes, give each one its own path rather than reusing a single well-known filename — a contract awaiting judgment that is overwritten by the next one leaves its criteria unjudged and its evidence unattached to anything.

A contract has the lifetime of one piece of work. On completion it is committed with that work and then deleted — git history is the archive, and a stale contract in the tree is worse than none. Before deleting, check that every decision that outlives the work made it into a structured commit body — write it into the closing commit if it did not (→ [15-doc-tracking.md](15-doc-tracking.md)); a contract is not a decision record.

### 5. Boundaries, and where a criterion runs

A boundary is a place two lanes can hold different beliefs. Data flow finds only one of the four kinds:

| Surface | The disagreement |
|---|---|
| Payload shape | the producer writes a field the consumer does not read, or writes it under another name |
| Symbol | the caller names a function the owner never defined, or calls it at a different signature |
| Value set | the producer emits a value the consumer's validation refuses, in either direction |
| Call graph | a module nobody calls, or a caller the owner was never told about |

Derive the list from imports and calls in both directions rather than from what crosses as data. A lane that only consumes — a CLI over the other lanes' modules, a reporting layer — passes nothing outward, so it disappears from a payload-derived list while owning more of the call surface than any producer does.

Contracts freezing these boundaries belong to no lane, and therefore run nowhere inside one. Give each lane criteria its own worktree can decide, and give the cross-lane contracts and the end-to-end condition to the integration step. The alternative this forbids is weakening the criterion to fit the lane — mocking a sibling module, importing through a shim — which yields a lane that passes and an assembly that does not (→ [06-testing-verification.md](06-testing-verification.md) §1).

Criteria map to tests and the red check via [06-testing-verification.md](06-testing-verification.md); evidence and human verdicts via [19-evidence.md](19-evidence.md); how the plan and briefs are produced in the first place via [21-development-loop.md](21-development-loop.md); decomposition, isolation, and model routing stay in [09-agentic-workflow.md](09-agentic-workflow.md), review lanes and fan-in in [20-review-gate.md](20-review-gate.md). The contract records decisions, not the rules behind them.
