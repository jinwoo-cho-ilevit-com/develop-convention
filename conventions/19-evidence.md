# 19. Evidence Artifacts

A completion claim is only as good as what backs it. This document fixes the format of that backing so the same three questions — did every check pass, what actually ran, who approved the parts a machine cannot judge — are answered the same way every time.

Execution evidence is produced by running a command, not by composing output that resembles one. Reading-only reviews are evidence of what was inspected, with no claim that behavior was executed. This document records both without conflating them.

## Core Rules

- Record status as a word — `PASS`, `FAIL`, `PENDING-HUMAN`, `NO-BASELINE` — never a symbol or emoji, so status survives grep and diff. The four are not interchangeable; `NO-BASELINE` in particular is defined in [06-testing-verification.md](06-testing-verification.md) §2.
- Keep the command, exit status, and decisive output lines. Store full output under `artifacts/<feature>/` only when a failure, high-risk change, or required gate needs it; cite the path and mask sensitive fields before sharing.
- **Mask secrets before evidence leaves the machine.** Command lines and environment values are recorded verbatim otherwise, and evidence is meant to be shared. The pre-commit scan never sees gitignored artifacts, so pasting a report into a review is the path that leaks.
- Block completion on `PENDING-HUMAN`. A `[human]` check passes only once a verdict, its author, and its timestamp are recorded — an unanswered human check is a TODO, and TODOs are blockers (§2, → [06-testing-verification.md](06-testing-verification.md)).
- Name the commit the run was made against and whether the tree was clean. A passing record against an unknown tree proves nothing about the tree that gets merged.
- Record every gate bypass with its reason. A bypass that leaves no trace is a blocker; a recorded one is a decision.

## Details

### 1. Execution output

A `PASS` with no exit status or decisive output is only a claim; a test selection that matched nothing is not a pass (→ [06-testing-verification.md](06-testing-verification.md) §2). Masking covers the command line and the environment as well as the output: a command that passes a token as an argument leaks it into the record otherwise.

### 2. Human verdicts

A `[human]` check has three states: `PENDING-HUMAN` until someone answers, then `PASS`, or `FAIL` where the answer is a rejection. A verdict whose author is not recorded is indistinguishable from one the tooling marked passed on its own.

That `FAIL` is not a failed test — the check may well pass mechanically while the approach is still wrong. Treat it as a blocker with a stated reason, and resolve it by changing the work, not by re-running the check.

### 3. Provenance

Everything about *when* beyond the commit and tree state is already in git: the branch carries its commits and their times. What git cannot supply is the human verdict and the bypass, which is why those two are written down explicitly and nothing else is.
