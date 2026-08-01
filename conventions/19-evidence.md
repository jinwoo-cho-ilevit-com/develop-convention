# 19. Evidence Artifacts

A completion claim is only as good as what backs it. This document fixes the format of that backing so the same three questions — did every criterion pass, what actually ran, who approved the parts a machine cannot judge — are answered the same way every time.

Evidence is produced by execution, not by writing. A file the model composed to look like output is not evidence.

## Core Rules

- Report completion as artifact paths plus the criteria table. **No narrative summary.** Prose is where a hallucinated completion hides; a table with a FAIL row cannot hide one.
- Write `commands.jsonl` (machine-readable) and `commands.log` (human-readable) by teeing real execution: the command, exit code, and full output. Never author them by hand.
- **Mask secrets in both.** Command lines and environment variables are recorded verbatim otherwise, and evidence is meant to be shared (→ [13-secret-management.md](13-secret-management.md)).
- Record status as a word — `PASS`, `FAIL`, `PENDING-HUMAN`, `NO-BASELINE` — never a symbol or emoji, so status survives grep and diff. The four are not interchangeable; `NO-BASELINE` in particular is defined in [06-testing-verification.md](06-testing-verification.md) §3.
- Block completion on `PENDING-HUMAN` regardless of done level. A criterion marked `verify: human` passes only once a verdict, its author, and its timestamp are recorded — an unanswered human check is a TODO, and TODOs are blockers (→ [06-testing-verification.md](06-testing-verification.md)).
- Record in `manifest.json`: the commit the run was made against, human verdicts, bypass history, and the timestamps `created_at`, `verify_runs[].at`, `review_rounds`.
- Record every gate bypass with its reason. A bypass that leaves no trace is a blocker; a recorded one is a decision.

## Details

### 1. Layout

```
artifacts/<feature>/
  REPORT.md        criteria table: id / status / verify command / output summary
  commands.jsonl   structured execution record
  commands.log     the same, human-readable
  manifest.json    provenance, timestamps, human verdicts, bypasses
```

`REPORT.md` is written incrementally — each criterion appends as it turns green. By the time the work is finished the review material already exists, so there is no gap between "done" and "reviewable".

### 2. The criteria table

`REPORT.md` carries one row per criterion and nothing else:

```
| id   | status        | verify                                  | note |
|------|---------------|-----------------------------------------|------|
| C-01 | PASS          | uv run pytest tests/test_c01.py -q      |      |
| C-03 | FAIL          | scripts/checks/no_new_deps.sh           | pyproject.toml +1 |
| C-04 | PENDING-HUMAN | human                                   | figures/dist.svg |
```

A human reading this looks at the non-`PASS` rows and stops. That is the entire intended cost of verification for the reader.

### 3. Execution records

`commands.jsonl` holds one object per executed command: criterion id, command, exit code, and output, marked where truncated. `commands.log` is the same content laid out for reading.

Masking applies to the command line and the environment, not only to output. A `verify:` command that passes a token as an argument leaks it into the record otherwise. Mask by pattern before writing, and scan the artifacts directory before the evidence leaves the machine. Artifacts are gitignored, so the pre-commit scan (→ [13-secret-management.md](13-secret-management.md)) never sees them — pasting a report into a review is the path that leaks.

### 4. Provenance and timestamps

`manifest.json` answers "what produced this":

- the commit the run was made against, and whether the tree was clean at the time
- `created_at`, `verify_runs[].at`, `review_rounds`

The three timestamp fields exist so the process can be measured later. Lead time per contract, review rounds, and blockers that escaped review are all derivable from them and from nothing else — without them, no retrospective calculation is possible at all. The cost of recording them is close to zero, and the alternative is claiming an improvement without measuring it, which is not allowed (→ [00-principles.md](00-principles.md)).

### 5. Human verdicts

A `verify: human` criterion has three states: `PENDING-HUMAN` until someone answers, then `PASS` or a rejection that becomes a blocker.

The verdict record carries the verdict, who gave it, when, and an optional note. Recording the author matters more than it looks: a criterion whose verdict has no author is indistinguishable from one the tooling marked passed on its own.

A rejection is not a failed test — the criterion may well pass mechanically while the approach is still wrong. Treat it as a blocker with a stated reason, and resolve it by changing the work or the contract, not by re-running the check.

### 6. What the runner in `templates/scripts/` records

The toolkit a project copies out writes the four files above, plus the per-phase records described below. Its `manifest.json` carries the run's commit and whether the tree was clean, the contract's `base` and `done_level`, the interpreter and platform, the names of the environment variables whose values it masks wherever they appear — those whose names match and whose values clear the length floor below, not every name that matched, which would tell a reviewer a value was hidden while the log still carried it — and the human verdicts; it does not carry a bypass history, because this runner has no bypass to record. Five subcommands — `lint`, `red`, `verify`, `human`, `status` — and four exit codes: `0` the phase's answer is yes, `1` the answer is no, `2` the runner could not answer at all, `3` the runner itself broke and printed a traceback. A broken contract is `2` rather than `1` so a caller can tell "your contract is unusable" from "your work is not done"; the two were the same number in the version this replaces, and that is how a gate opened on an unreadable contract. `3` exists for the same reason one step further out: an uncaught exception exits `1` by default, which would read as a criterion having failed.

Each of `red`, `verify` and `human` writes its own record at `artifacts/<feature>/state/<criterion>.<phase>.json`, and the path is derived from the record rather than passed in. `lint` and `status` write no record at all. No phase can overwrite another's result because no phase names another's file. `REPORT.md` and `manifest.json` are then re-rendered from that directory, so neither accumulates and neither can lose an entry. `status` writes nothing at all — a status command that produced `REPORT.md` could never observe `REPORT.md` missing, which is part of the check it exists to perform. It blocks while any of the four artifacts above is absent, as well as on any criterion that is not `PASS` or that is `PASS` without a red record behind it.

A red record says `RED`, `NOT-RED`, `EXEMPT-GUARD` or `NO-BASELINE`. The first three belong to the red phase alone; `NO-BASELINE` is deliberately the same word 19 lists among a criterion's status words, because 06 §3 gives it one meaning — the check could not run — and a red check that could not run is that case, including a criterion whose command selects no test at all. This runner only ever emits it on a red record; the statuses it gives a criterion are `PASS`, `FAIL` and `PENDING-HUMAN`. What a red record never says is `PASS`: the value that satisfies the gate is `RED`, so the two can never be read as the same thing, and `NO-BASELINE` is never treated as evidence of anything.

A criterion's own status stays inside 19's four words. Where the gate blocks something that passed its own check — a `PASS` with no red record behind it, or a criterion whose verify has not run — the report says `FAIL` and the note carries the reason, rather than inventing a fifth word.

Two kinds of criterion need no red record: one whose `verify` is `human`, and one declared `red: guard`, which is a standing invariant that legitimately holds at base and so can never be made to fail there. Every other criterion needs a record saying `RED` before it can pass, and a missing record is not a substitute for one.

Masking covers the command line, the environment and the output, and happens inside the writer through which every artifact passes, rather than at each call site, so it is not something a later caller can forget. What counts as a secret is a pattern file the toolkit ships (`templates/scripts/secrets.toml`): credential shapes, each carrying a sample its own test suite checks the pattern against, plus globs matching the names of secret-bearing environment variables, whose values are redacted wherever they appear. A value shorter than eight characters is left alone — a variable set to `1` would otherwise redact every digit in every artifact — so a short secret is not covered by the environment rule and has to be caught by a shape.

Inside the artifacts directory one file is written by something other than that writer: the test report pytest is asked to produce. It is created under the state directory, read for its counts, and removed within the same phase, and only the counts reach a record. It is not evidence and is not masked, so a run killed part-way can leave one behind — the artifacts directory is gitignored precisely because things like this land in it.

A human verdict is required to carry its author and an ISO-8601 UTC timestamp, and that is checked when the verdict is read, not only when it is written — a record edited by hand does not buy a pass.

### 7. Deliberately unspecified

Visualization tiers, `figure ↔ criterion ↔ code anchor` linking, and a self-contained `index.html` are **not specified here yet**. Where a contract wants them, it records the intent in `evidence_todo` and leaves the format open.

Specifying a required field before its format exists is worse than leaving it out: every contract fills it differently, nothing can validate it, and the accumulated files all need rewriting once the real format lands.
