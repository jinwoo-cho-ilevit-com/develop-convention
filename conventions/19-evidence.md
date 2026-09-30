# 19. Evidence Artifacts

A completion claim is only as good as what backs it. This document fixes the format of that backing so the same three questions — did every criterion pass, what actually ran, who approved the parts a machine cannot judge — are answered the same way every time.

Execution evidence is produced by running a command, not by composing output that resembles one. Reading-only reviews are evidence of what was inspected, with no claim that behavior was executed. This document records both without conflating them.

## Core Rules

- For planned work, report the criteria table with commands, exit status, and decisive output. A short summary may explain the result; it cannot replace a failing or pending row. For `auto`, record the change and the relevant check directly without creating a table or plan file.
- Fill the table in the lane brief as each criterion turns green, not at the end. By the time the lane finishes, the review material already exists, so there is no gap between "done" and "reviewable".
- Record status as a word — `PASS`, `FAIL`, `PENDING-HUMAN`, `NO-BASELINE` — never a symbol or emoji, so status survives grep and diff. The four are not interchangeable; `NO-BASELINE` in particular is defined in [06-testing-verification.md](06-testing-verification.md) §3.
- Keep the command, exit status, and decisive output lines. Store full output under `artifacts/<feature>/` only when a failure, high-risk change, or required gate needs it; cite the path and mask sensitive fields before sharing.
- **Mask secrets before evidence leaves the machine.** Command lines and environment values are recorded verbatim otherwise, and evidence is meant to be shared. The pre-commit scan never sees gitignored artifacts, so pasting a report into a review is the path that leaks (→ [13-secret-management.md](13-secret-management.md)).
- Block completion on `PENDING-HUMAN` regardless of done level. A `[human]` criterion passes only once a verdict, its author, and its timestamp are recorded — an unanswered human check is a TODO, and TODOs are blockers (§3, → [06-testing-verification.md](06-testing-verification.md)).
- Name the commit the run was made against and whether the tree was clean. A passing table against an unknown tree proves nothing about the tree that gets merged.
- Record every gate bypass with its reason. A bypass that leaves no trace is a blocker; a recorded one is a decision.

## Details

### 1. The criteria table

For planned work, the lane brief carries one row per criterion:

```
| id   | status        | verify                                                                    | red      | note |
|------|---------------|---------------------------------------------------------------------------|----------|------|
| C-01 | PASS          | uv run pytest tests/test_sample_run_loader.py::test_c01_drops_nan_rows    | observed |      |
| C-03 | FAIL          | scripts/checks/no_new_deps.sh                                             | —        | pyproject.toml +1 |
| C-04 | PENDING-HUMAN | [human]                                                                   | —        | figures/dist.svg |
```

A human reading this looks at the non-`PASS` rows and stops. That is the entire intended cost of verification for the reader.

The `red` column applies only when a criterion introduces a justified new test: `observed` or `sabotage` records how that test was shown to detect a failure ([06-testing-verification.md](06-testing-verification.md) §3). Use `—` for an existing check, a standing guard that needs no new test, or a `[human]` row. `NO-BASELINE` means a required new-test check could not run; it is a status, not a red kind.

The final report covers the end-to-end condition ([18-work-contract.md](18-work-contract.md) §1) and every required run. A short summary may accompany the rows; a lane whose row says FAIL says FAIL in the final report too.

### 2. Execution output

Record the command, exit status, and decisive output together. A `PASS` with no exit status or decisive output is only a claim; a test selection that matched nothing is not a pass (→ [06-testing-verification.md](06-testing-verification.md) §3).

Masking applies to the command line and the environment, not only to the output. A verify command that passes a token as an argument leaks it into the record otherwise.

### 3. Human verdicts

A `[human]` criterion has three states: `PENDING-HUMAN` until someone answers, then `PASS`, or `FAIL` where the answer is a rejection. There is no fourth word for a rejected human verdict, and an unanswered one blocks completion at every done level.

The verdict record carries the verdict, who gave it, when, and an optional note. Recording the author matters more than it looks: a criterion whose verdict has no author is indistinguishable from one the tooling marked passed on its own.

That `FAIL` is not a failed test — the criterion may well pass mechanically while the approach is still wrong. Treat it as a blocker with a stated reason, and resolve it by changing the work or the contract, not by re-running the check.

### 4. Provenance

Name the commit and the tree state in the report. Everything else about *when* is already in git: a lane's branch carries its commits and their times, so lead time and round count are derivable without a second bookkeeping system. What git cannot supply is the human verdict and the bypass, which is why those two are written down explicitly and nothing else is.

### 5. Recorded bypasses

A gate that was skipped and a gate that passed must never look alike in the record. Where a check is waived — a guard turned off for one run, a criterion accepted without its command — the waiver, its reason, and who made it go in the report next to the row it affects. This is what keeps "we skipped it deliberately" distinguishable from "it never ran", which is the distinction a reader of a green report has no other way to make.
