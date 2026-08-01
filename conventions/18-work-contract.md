# 18. Work Contract

A **work contract** is one file, written before the work starts, that fixes three things in the same identifiers: what counts as done (**completion criteria**), who may edit what (**ownership**), and how far verification must go (**done level**). Without it, "done" is renegotiated every time and there is no baseline to measure drift against. A contract is a checklist, not a specification; its minimum form is three to five lines.

## Core Rules

- Write the contract before development starts and freeze it during execution. Record any change in `revision` with its kind; an additive change touching no existing criterion or `owns` entry updates only the affected lane.
- Scale the contract to the work. Three to five lines — feature, done level, criteria, out of scope — is complete for small work, and that form is not the heavyweight spec [09-agentic-workflow.md](09-agentic-workflow.md) §4 warns against. Add `lanes`/`owns`/`integration` only for two or more parallel lanes, and `base` only when adding tests.
- Write every criterion in EARS or Given-When-Then with `SHALL`, and apply the judgment test: **if two agents could disagree about whether it passed, rewrite it.**
- Give every criterion an executable `verify:` command or mark it `verify: human`. A criterion that is neither is not a criterion.
- Cover functional, non-functional, and **negative** criteria — what must *not* happen. The negative kind is what stops over-building. State what is out of scope; an unstated boundary is the one that gets crossed.
- For a rewrite, include a characterization criterion that pins existing behaviour first (→ [00-principles.md](00-principles.md)).
- Declare `done_level` before starting, chosen by size × reversibility. At every level three things are mandatory: every criterion passes, the evidence exists, and each new test was observed failing at the base commit (the red check and its three outcomes are defined in [06-testing-verification.md](06-testing-verification.md) §3; this document does not restate them).
- Ask of every criterion whether it was already true at the base commit. If it was, it is a standing invariant — mark it exempt from the red check and say why. An absence criterion almost always is, and one declared without the exemption fails the red check for the correct reason and blocks the gate.
- Give every lane a disjoint `owns`, written as directory prefixes wherever the work divides that way. Globs expanded against the current file list miss files that do not exist yet, which is the collision the check exists to prevent.
- Name cross-cutting files individually in `owns`, one owner each. A repository has files that belong to no directory — the README, the ignore file, the site config — and a prefix rule cannot assign them, so a decomposition that only knows prefixes silently leaves them to whoever touches them first. Give the integration lane an explicit list and run it last.
- Slice by file, not by phase, when several kinds of change land in the same documents. Three lanes each doing "their kind of edit" across the same files collide by construction; one lane per file, carrying every kind of edit for that file, does not.
- Assign lock files, migrations, and generated files to a single owner, never to a lane.
- Record model tier per lane (`light`/`mid`/`top`), never a model id, so the routing choice can be audited afterwards.
- Answer the five planning questions before writing criteria, and start once the four start signals hold.
- Make deviation visible rather than forbidding it. A bypassed gate is `done_level: bypassed` with a reason; an unrecorded bypass is the blocker.

## Details

### 1. Terms

| Term | Meaning |
|---|---|
| completion criteria (`criteria`) | Conditions fixed before the work that decide whether it is done. Identified `C-01`, `C-02`, … |
| done level (`done_level`) | How far verification must go: `auto` / `reviewed` / `proven` |
| EARS | A sentence template that removes ambiguity: `WHEN <trigger> THE <system> SHALL <response>` |
| red check | Confirming a new test actually fails at the base commit |

Avoid two-letter abbreviations in contracts and in the documents describing them. A reader who has to decode a field name will not check the field.

### 2. Planning before the contract

The contract is the output. Reaching it takes answering five questions; leaving one unanswered is how a plan becomes confidently wrong.

| Question | Feeds |
|---|---|
| What problem does this solve, and what happens if it is not done? | the criteria |
| What alternatives were considered, and why were they rejected? | prevents re-litigating the same choice later |
| What is not known that **blocks progress**, and which assumption is most expensive if wrong? | what to check before starting |
| Where can this split into parallel work, and what must stay single-owned? | `lanes`, `sequential_owner` |
| How would this most plausibly fail, and what has to be undone to abandon it? | negative criteria, the abandonment path |

**Start signals** — stop planning when all four hold:

1. No criterion could be read two ways.
2. Every unknown is classified: check it now, assume it and write the assumption down, or let it surface during the work.
3. Rejected alternatives are recorded with their reason.
4. **The next question can only be answered by writing code.** This is the most reliable of the four.

There is no separate planning-depth setting. How hard a plan is challenged before execution follows `done_level`: `auto` skips it, `reviewed` gets one adversarial pass, `proven` gets the full lane set (→ [20-review-gate.md](20-review-gate.md)). A second dial would only be another thing to under-report.

**Stopping the pre-execution gate.** A gate whose exit condition is "until the reviewers stop finding things" has no fixed point, and prose review does not converge on its own. Fix the exit before the first round:

- Only a *blocker* holds the gate — something that would make the work wrong or unusable. Everything else is recorded and carried into the work.
- Between rounds, count how many of this round's findings were introduced by the previous round's fix. When that is most of them, the fix rate has become the defect source: stop and change the approach rather than run another round.
- Narrowing what counts as a blocker mid-gate is legitimate, and it is a decision — write it down, because a rule invented to end a round is invisible to the next one.

The same three apply to a review loop after execution. Round count is not an exit condition: one loop here ran eleven rounds without converging, and what ended it was noticing the findings had changed in kind — from gates opening wrongly to prose being imprecise — not their number.

When asking a person to decide something, give them the trade: what is gained, what is lost, what it costs to reverse, and why the decision is not yours to make. Options without their costs are a request for agreement, not a decision.

### 3. Schema

A single `contract.md`: YAML front matter is machine-readable, the body is human narrative, and the body references criteria by id rather than restating them. The field list lives in `templates/contract.md`; three of them need explanation.

`lanes[]` is the primary register of the parallel decomposition; 09 §2 describes how to arrive at it, and the contract is where it is recorded. A lane that is given up is marked `state: abandoned` with a reason rather than deleted — deleting makes the abandonment invisible.

`checkpoints[]` marks when a plan-versus-diff review should happen. It is a marker, not a trigger: whoever owns the work runs the review and records that it happened.

`runner` is `pytest` or `command`, required on every criterion whose `verify` is not `human` and refused on one that is — a `human` criterion runs nothing, so a `runner` line left behind when a criterion was changed to `human` means the contract no longer says what its author thinks. It is declared rather than guessed: deciding the kind by looking for the word "pytest" in the command text produced two unrelated defects in the first runner, because a `grep` command that mentioned pytest was classified as one and a project that used something else was judged by pytest's rules.

### 4. What the runner in `templates/scripts/` enforces

The toolkit is optional — a contract is a checklist first, and running it by hand is legitimate. Where it is used, this is the subset it implements. It reads a fixed set of fields and refuses a contract carrying any field outside that set, naming the field, because silently accepting one the author believes is enforced is worse than not supporting it. `lanes`, `sequential_owner`, `integration`, `checkpoints` and `hermetic: false` are refused for that reason, and `done_level: bypassed` with them — this document requires a bypass to carry a reason, and a runner that took the level while recording no reason would report a clean gate over the very state the Core Rule above calls the blocker. Two fields inside the set are accepted without being acted on: `hermetic: true`, which is the default and matches what the runner does anyway, and `revision`, which this document requires an author to keep but which no check here enforces.

`lint` validates the schema and reports the judgment rules separately — a missing `negative` criterion or an empty `out_of_scope` is exit `1`, a contract that cannot be parsed at all is exit `2`. A `verify` command is executed as an argument vector and never through a shell, so a command carrying a shell operator is refused when the contract is loaded — by every subcommand, with exit `2` — rather than silently passing `&&` to a program as an argument. The command is split once, and any resulting argument made only of operator punctuation is refused, quoting or no quoting: after the split, an author who wanted a literal `;` and one who expected a shell have written the same argument, and the runner says so rather than guessing. `find … -exec … ';'` is refused along with `a && b`, and goes in a script. That is the whole rule — an argument that merely *contains* one of those characters is executed, so `--format='%h|%s'` and `awk '{print $(NF)}'` are commands this runner runs. A `verify` whose *value* holds a line break is refused before any of this, because a criterion runs one command and shlex would otherwise fuse two into a third that the contract never states. That is the literal block scalar, `verify: |`, which is the form that keeps the break. A folded or plain scalar wrapped across lines has no break left in it by the time the runner sees it — YAML has already made it one line, which is what the author asked for — so a long command may be wrapped, and two commands written that way are one command by YAML's rules before they are anything to this runner. Trying to recover the distinction by reading the quoted text as well as the arguments produced two parsers that disagreed — most sharply on an input where one raised and the other did not, which let an unquoted `&&` through unchecked. An unquoted `#` becomes an ordinary argument: the alternative shlex offers is discarding the rest of the line, and running a shorter command than the contract states is worse than either refusing it or passing it along. A field the runner does not read is refused the same way, whether it is one this document defines or a typo: accepting it silently would leave an author believing something is enforced when nothing looks at it.

`feature` and every criterion id must be a plain slug — letters, digits and single hyphens, lowercase for the feature — because both are joined into filenames under `artifacts/`. The rule is a charset rather than a scan for dangerous characters, so an underscore or a dot is refused along with a path separator: `C_01` is not an id. A value that is not a string is rejected for the same reason: an unfilled `[short-slug]` placeholder parses as a list, and the first runner turned that into a directory literally named after it. Every file the runner writes is then resolved and confirmed to sit inside that directory, with one declared exception: the detached checkout `red` needs — which is outside the repository by construction, carries the registration git makes for it, and is removed when the phase ends.

`red` checks each machine criterion against the commit named in `base`, in a detached worktree outside the repository that is removed afterwards. A `verify: human` criterion is skipped, and one declared `red: guard` is recorded as exempt without being run — a standing invariant cannot be made to fail at base. For a `pytest` criterion the runner asks pytest which files the criterion selects and copies those into the checkout, along with every `conftest.py` above them — from the working tree, so a test written but not yet committed is what gets checked, and so is an uncommitted change to a fixture it depends on. A `command` criterion has nothing brought forward: base is base. The outcomes follow [06-testing-verification.md](06-testing-verification.md) §3 — a check that fails at base is `RED`, one that passes there proves nothing, and one that cannot run is a missing baseline rather than either.

A pytest verdict never rests on the exit code alone. A selection containing only skipped tests exits zero, so the runner reads the test report and requires at least one test to have executed. `command` criteria have no equivalent signal, and the runner does not pretend otherwise: whether a command criterion is backed by a test at all is a judgment left to review.

### 5. Writing criteria

EARS constrains a sentence into trigger, condition, system, and response. Given-When-Then does the same through precondition, action, expected result. Either is fine; mixing them in one contract is not.

```
C-01: WHEN the input CSV contains NaN in `score`,
      THE loader SHALL drop the row and log a WARNING with the row index.
  verify: uv run pytest tests/test_c01_drops_nan_rows.py -q
  kind: functional
```

The anti-patterns are criteria that cannot fail: "handle errors gracefully", "must load quickly", "should be relevant". Each defers a judgment to verification time, which is what the contract exists to remove.

`verify: human` is legitimate — some judgments genuinely are. It is not an escape hatch: a recorded verdict is required before the criterion passes (→ [19-evidence.md](19-evidence.md)).

Sources: [EARS, fifteen years on](https://joshmcdonald.medium.com/ears-fifteen-years-on-the-requirements-format-built-for-the-agent-era-0f78f8ff35a0), [acceptance criteria an agent can verify](https://www.braingrid.ai/blog/how-to-write-acceptance-criteria-ai-agent-can-verify)

### 6. Done level

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

### 7. Changing and closing a contract

Freezing prevents drift across parallel lanes, but a rule forcing every lane to restart over one added criterion gets quietly ignored, and a contract nobody follows is worse than none.

- **additive**, touching no existing criterion or `owns` entry: update the affected lane, others continue
- **narrowing**: stop the lanes that owned the removed scope
- **breaking**: stop everything, update, restart

Record kind and reason in `revision` either way.

A contract has the lifetime of one piece of work. On completion it is committed with that work and then deleted — git history is the archive, and a stale contract in the tree is worse than none. Decisions that outlive the work move to the ADR chain before deletion (→ [15-doc-tracking.md](15-doc-tracking.md)); a contract is not an ADR.

Criteria map to tests and the red check via [06-testing-verification.md](06-testing-verification.md); evidence and human verdicts via [19-evidence.md](19-evidence.md); decomposition, isolation, and model routing stay in [09-agentic-workflow.md](09-agentic-workflow.md), review lanes and fan-in in [20-review-gate.md](20-review-gate.md). The contract records decisions, not the rules behind them.
