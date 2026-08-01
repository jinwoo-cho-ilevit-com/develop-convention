# 18. Work Contract

A **work contract** is one file, written before the work starts, that fixes three things in the same identifiers: what counts as done (**completion criteria**), who may edit what (**ownership**), and how far verification must go (**done level**). Without it, "done" is renegotiated every time and there is no baseline to measure drift against.

A contract is a checklist, not a specification. Its minimum form is three to five lines.

## Core Rules

- Write the contract before development starts and freeze it during execution. Record any change in `revision` with its kind (additive / narrowing / breaking); an additive change that touches no existing criterion or `owns` entry updates only the affected lane, everything else keeps running.
- Write every completion criterion in EARS or Given-When-Then with `SHALL`. Apply the judgment test: **if two agents could disagree about whether it passed, rewrite it.**
- Give every criterion an executable `verify:` command, or mark it `verify: human` explicitly. A criterion that is neither is not a criterion.
- Cover three kinds: functional, non-functional (limits, performance), and **negative** — what must *not* happen (no new dependency, no API change, no secret in logs). The negative kind is what stops over-building.
- State what is out of scope. An unstated boundary is the boundary the agent will cross.
- For a rewrite, include a characterization criterion that pins existing behaviour before the rewrite (→ [00-principles.md](00-principles.md)).
- Fill only the fields the work triggers. Always: `feature`, `done_level`, `criteria`, `out_of_scope`. Add `lanes`/`owns`/`integration` only for two or more parallel lanes, and `base` only when adding tests.
- Declare `done_level` before starting, chosen by size × reversibility. Regardless of level, three things are mandatory with no exception: every criterion passes, the evidence artifacts exist, and each new test was observed failing at the base commit.
- Restrict `owns` to disjoint directory prefixes. Expanding general globs against the current file list misses files that do not exist yet, which is precisely the collision the check exists to prevent.
- Assign lock files, migrations, and generated files to a single owner in `sequential_owner`, never to a lane.
- Record model tier per lane (`light`/`mid`/`top`), never a model id. Routing rules stay in [09-agentic-workflow.md](09-agentic-workflow.md); the contract only records which tier actually ran, so the choice can be audited afterwards.
- Make deviation visible rather than forbidding it. If a gate must be bypassed, set `done_level: bypassed` with a reason. An unrecorded bypass is the blocker, not the bypass itself.

## Details

### 1. Terms

| Term | Meaning |
|---|---|
| completion criteria (`criteria`) | Conditions fixed before the work that decide whether it is done. Identified as `C-01`, `C-02`, … |
| done level (`done_level`) | How far verification must go: `auto` / `reviewed` / `proven` |
| EARS | Easy Approach to Requirements Syntax. A sentence template that removes ambiguity: `WHEN <trigger> THE <system> SHALL <response>` |
| red check | Confirming a new test actually fails at the base commit. A test that never failed proves nothing |
| ownership (`owns`) | The file range a lane may edit |
| lane | One strand of parallel work and its owner |
| hermetic | Independent of external state (network, database, ports), so it yields the same result whenever it runs |
| characterization test | A test that pins existing behaviour, written before a rewrite |

Avoid two-letter abbreviations in contracts and in the documents that describe them. A reader who has to decode the field name will not check the field.

### 2. Schema

The contract is a single `contract.md`: YAML front matter is machine-readable, the body is human narrative. The body references criteria by id and does not restate them — a contract that repeats itself drifts inside one file.

```
schema_version, feature, done_level, base
criteria[]        id, text, verify, kind: functional|nonfunctional|negative,
                  hermetic, red: required|guard
out_of_scope[]
lanes[]           id, owns[], criteria[], model_tier: light|mid|top, state: active|abandoned
sequential_owner[]
integration       owner, order[], criteria[]
checkpoints[]     after, check[]
evidence_todo[]
revision          kind: additive|narrowing|breaking, reason
```

A lane that is given up is marked `state: abandoned` with a reason, not deleted. Deleting it makes the abandonment invisible; marking it excludes the lane from completion gates while leaving the record.

`checkpoints[]` names when a plan-versus-diff review should fire. Without an automated gate the check surfaces through `contract.py status`, which warns about checkpoints that were passed without review.

### 3. Writing completion criteria

EARS constrains a sentence into trigger, condition, system, and response — a shape an agent parses without guessing. Given-When-Then does the same work through precondition, action, expected result. Either is fine; mixing them inside one contract is not.

```
C-01: WHEN the input CSV contains NaN in `score`,
      THE loader SHALL drop the row and log a WARNING with the row index.
  verify: uv run pytest tests/test_c01_drops_nan_rows.py -q
  kind: functional

C-03: THE change SHALL NOT add a runtime dependency.
  verify: scripts/checks/no_new_deps.sh
  kind: negative

C-04: The output distribution SHALL be visually equivalent to the previous release.
  verify: human
  kind: nonfunctional
```

Anti-patterns are the criteria that cannot fail: "handle errors gracefully", "the page must load quickly", "should be relevant". Each requires a judgment call at verification time, which is the thing the contract exists to remove.

`verify: human` is legitimate — some judgments are genuinely human. It is not an escape hatch: a human verdict must be recorded before the criterion can pass (→ [19-evidence.md](19-evidence.md)).

Sources: [EARS, fifteen years on](https://joshmcdonald.medium.com/ears-fifteen-years-on-the-requirements-format-built-for-the-agent-era-0f78f8ff35a0), [acceptance criteria an agent can verify](https://www.braingrid.ai/blog/how-to-write-acceptance-criteria-ai-agent-can-verify)

### 4. Which fields to fill

| Field | Filled when |
|---|---|
| `feature`, `done_level`, `criteria`, `out_of_scope` | Always. Three to five lines is a complete contract |
| `lanes` / `owns` / `integration` | Two or more parallel lanes |
| `base` + red check | The work adds tests |
| `evidence_todo` | A visual artifact is wanted but its format is not yet specified — record the intent, defer the form |

This is what keeps the contract compatible with [09-agentic-workflow.md](09-agentic-workflow.md) §6, which permits lightweight iteration without a written plan for small work. A three-line contract is not a heavyweight spec; the measured 10x overhead in that section came from full spec pipelines, not from writing down what "done" means.

### 5. Done level

Mandatory at every level, no exceptions: every criterion passes, the evidence artifacts exist, and each new test was observed failing at `base`.

| Level | Adds | Use for |
|---|---|---|
| `auto` | nothing beyond the mandatory | docs, formatting, behaviour-preserving refactors |
| `reviewed` | zero confirmed blockers from a review that did not author the change | the default |
| `proven` | integration smoke + one run on real data | new modules, pipelines, anything with external effect |

Choose by **size × reversibility**:

|  | Easy to reverse | Hard to reverse (migration, deploy, data transform, public API) |
|---|---|---|
| Single module | `auto` | **`proven`** |
| Two or more modules, or an interface/schema change | `reviewed` | `proven` |

The upper-right cell is the one a size-only rule misses. A one-line change to a published signature is small and nearly impossible to take back.

Keeping evidence outside the dial is deliberate. If evidence were a property of the higher levels, "this is only `auto`" would become a way to skip it, and the gate would be negotiable exactly where it matters least to negotiate.

Where a `proven` criterion calls for visual inspection and no visualization format has been fixed yet, express it as a `verify: human` criterion. A level nobody can satisfy is worse than a level that leans on a recorded human verdict.

### 6. Changing a frozen contract

Freezing prevents context drift across parallel lanes, but a rule that forces every lane to restart for one added criterion will be quietly ignored, and a contract nobody follows is worse than none.

- **additive**, touching no existing criterion or `owns` entry: update the affected lane only, others continue
- **narrowing** (scope removed): stop the lanes that owned the removed scope
- **breaking** (an existing criterion or ownership boundary changes): stop everything, update, restart

Record the kind and the reason in `revision` either way. The record is what makes a later "why did this change mid-flight" answerable.

### 7. Relationship to other documents

- Completion criteria map to tests, and the red check is defined in [06-testing-verification.md](06-testing-verification.md).
- Evidence artifacts and the human-verdict record are defined in [19-evidence.md](19-evidence.md).
- Lane decomposition, worktree isolation, review lanes, and model routing stay in [09-agentic-workflow.md](09-agentic-workflow.md). The contract records decisions; it does not restate the rules behind them.
- A contract is not an ADR. It has the lifetime of one piece of work and is archived when that work completes; decisions that outlive the work belong in the ADR chain (→ [15-doc-tracking.md](15-doc-tracking.md)).
