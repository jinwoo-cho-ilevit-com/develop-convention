# 19. Evidence Artifacts

A completion claim is only as good as what backs it. This document fixes the format of that backing so the same three questions — did every criterion pass, what actually ran, who approved the parts a machine cannot judge — are answered the same way every time.

Evidence is produced by execution, not by writing. A file the model composed to look like output is not evidence.

## Core Rules

- Report completion as the criteria table plus the output the commands produced. **No narrative summary.** Prose is where a hallucinated completion hides; a table with a FAIL row cannot hide one.
- Fill the table in the lane brief as each criterion turns green, not at the end. By the time the lane finishes, the review material already exists, so there is no gap between "done" and "reviewable".
- Record status as a word — `PASS`, `FAIL`, `PENDING-HUMAN`, `NO-BASELINE` — never a symbol or emoji, so status survives grep and diff. The four are not interchangeable; `NO-BASELINE` in particular is defined in [06-testing-verification.md](06-testing-verification.md) §3.
- Paste what the command printed, not a description of it. Where the output is too large, keep it under `artifacts/<feature>/` and cite the path — that directory is gitignored, so nothing there is a commit-size concern.
- **Mask secrets before evidence leaves the machine.** Command lines and environment values are recorded verbatim otherwise, and evidence is meant to be shared. The pre-commit scan never sees gitignored artifacts, so pasting a report into a review is the path that leaks (→ [13-secret-management.md](13-secret-management.md)).
- Block completion on `PENDING-HUMAN` regardless of done level. A `[human]` criterion passes only once a verdict, its author, and its timestamp are recorded — an unanswered human check is a TODO, and TODOs are blockers (→ [06-testing-verification.md](06-testing-verification.md), [18-work-contract.md](18-work-contract.md)).
- Name the commit the run was made against and whether the tree was clean. A passing table against an unknown tree proves nothing about the tree that gets merged.
- Record every gate bypass with its reason. A bypass that leaves no trace is a blocker; a recorded one is a decision.

## Details

### 1. The criteria table

The lane brief carries one row per criterion and nothing else:

```
| id   | status        | verify                                  | note |
|------|---------------|-----------------------------------------|------|
| C-01 | PASS          | uv run pytest tests/test_c01.py -q      |      |
| C-03 | FAIL          | scripts/checks/no_new_deps.sh           | pyproject.toml +1 |
| C-04 | PENDING-HUMAN | [human]                                 | figures/dist.svg |
```

A human reading this looks at the non-`PASS` rows and stops. That is the entire intended cost of verification for the reader.

The whole-project claim is the union of the lane tables plus the end-to-end condition from the plan (→ [21-development-loop.md](21-development-loop.md)). Nothing is summarised on the way up; a lane whose row says FAIL says FAIL in the final report too.

### 2. Execution output

The command and its output travel together. A row saying `PASS` next to a command nobody can see the output of is a claim, not evidence, and the distinction matters most exactly where it is least visible — a test selection that matched nothing exits zero (→ [06-testing-verification.md](06-testing-verification.md) §3).

Masking applies to the command line and the environment, not only to the output. A verify command that passes a token as an argument leaks it into the record otherwise.

### 3. Human verdicts

A `[human]` criterion has three states: `PENDING-HUMAN` until someone answers, then `PASS` or a rejection that becomes a blocker.

The verdict record carries the verdict, who gave it, when, and an optional note. Recording the author matters more than it looks: a criterion whose verdict has no author is indistinguishable from one the tooling marked passed on its own.

A rejection is not a failed test — the criterion may well pass mechanically while the approach is still wrong. Treat it as a blocker with a stated reason, and resolve it by changing the work or the contract, not by re-running the check.

### 4. Provenance

Name the commit and the tree state in the report. Everything else about *when* is already in git: a lane's branch carries its commits and their times, so lead time and round count are derivable without a second bookkeeping system. What git cannot supply is the human verdict and the bypass, which is why those two are written down explicitly and nothing else is.

### 5. Recorded bypasses

A gate that was skipped and a gate that passed must never look alike in the record. Where a check is waived — a guard turned off for one run, a criterion accepted without its command — the waiver, its reason, and who made it go in the report next to the row it affects. This is what keeps "we skipped it deliberately" distinguishable from "it never ran", which is the distinction a reader of a green report has no other way to make.
