# 0004. Retiring the contract runner

Status: accepted (2026-08-02)

Supersedes [0001](0001-contract-runner.md). Closes the runner-dependent entries of [0003](0003-deliberate-omissions.md).

## Context

The runner mechanised the subset of 18 and 19 that a program could judge: schema validity, the red check, criteria execution, human verdicts, and the status gate. It worked — seven contracts closed through it, 222 tests defended it, and the decisions in 0001 were earned against real defects.

What changed is the shape of the work around it. The loop this repository now runs ([21-development-loop.md](../conventions/21-development-loop.md)) produces a plan and one brief per lane out of an interview, and those briefs already carry what the contract carried: criteria, ownership, done level. Keeping a second artifact in a different language, validated by a separate program, meant the same facts written twice — the thing [01-structure-naming.md](../conventions/01-structure-naming.md) warns about, where the copy drifts and the drifted copy is worse than the original being wrong.

## Decisions

### 1. The contract survives; the YAML schema and the runner do not

`templates/scripts/` and `templates/contract.md` are deleted. A work contract is still written before the work, still frozen during it, and still fixes criteria, ownership and done level — as `PLAN.md` plus `lane-<name>.md`.

*Alternatives:* keep the runner as an optional path for high-risk work. Rejected because an optional second path is one nobody keeps current, and a stale validator that still runs is worse than none.

*Consequence:* nothing mechanically rejects a malformed contract any more. What replaces it is the form itself — a criterion is a sentence paired with a command, and a reviewer reading the brief can see a criterion with neither. That is weaker than a parser and it is checked by a person.

### 2. What the runner enforced, and where each part went

| Runner behaviour | Now |
|---|---|
| Refuse unimplemented fields | Gone. There is no schema to be wrong about |
| `verify` lexing, shell-operator refusal | Gone. Criteria commands are run by the agent that owns the lane |
| Red check against `base` | Still required, still in [06-testing-verification.md](../conventions/06-testing-verification.md) §3, now run by the lane |
| A pytest verdict must show a test executed | Still required, same document. The failure it prevents — an empty selection exiting zero — did not go away |
| Human verdict with author and timestamp | [18](../conventions/18-work-contract.md) and [19](../conventions/19-evidence.md); written into the brief beside the criterion |
| Recorded bypass with a reason | [19](../conventions/19-evidence.md) §5 |
| `manifest.json` provenance | Reduced to the commit and tree state. The rest was derivable from git and is no longer written twice |

### 3. The three runner-dependent omissions in 0003 are closed

- **Evidence visualisation format** — still unspecified, and now for a stronger reason: there is no field to fill and no validator to promise one. It reopens when enough evidence packs exist to show which figures a reviewer opens.
- **Lane fields read but not executed** — closed by execution. `workflows/build.js` runs the lanes, so the gap that entry recorded no longer exists.
- **`review_rounds` absent from the manifest** — closed by removal. Rounds are visible in the lane branch's commits, and the loop's exit no longer depends on counting them ([20-review-gate.md](../conventions/20-review-gate.md) §3).

### 4. What is lost, stated plainly

222 of this repository's 383 tests defended the runner and go with it. They were also the regression net for the conventions the runner encoded, so the change that removes them is a change with a thinner net than the one that added them. The replacement is a smaller set of invariants over the plugin and the documents; whether it holds is a judgment this ADR does not get to make in advance.

The decisions in 0001 stay readable and stay true of the program they describe. They are superseded as *current practice*, not as findings — in particular, 0001 §3 (a review lane must execute) survives verbatim in [20-review-gate.md](../conventions/20-review-gate.md), and the measurement behind it is not repeatable now that the runner is gone.

## Consequence

Reopening this needs new evidence, not the observation that mechanical validation is missing. That it is missing is the record.
