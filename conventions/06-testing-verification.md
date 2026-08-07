# 06. Testing + Verification

## Core Rules

- Write the smallest set of tests that catches real regressions. Don't chase line-coverage numbers, and don't write a test per function.
- Use three layers: unit tests for non-trivial logic, one contract test per module boundary, and 1-3 end-to-end smoke tests that exercise the assembled project through its real entry point.
- When work splits into parallel lanes, write each boundary's contract test **before** the lanes start, and give it no lane as owner. Disjoint file ownership stops two lanes writing the same file; it does nothing about the two of them holding contradictory assumptions about what crosses between them, and each lane's own tests pass under its own assumption. The test written first is that assumption in executable form (→ [21-development-loop.md](21-development-loop.md)).
- Store each boundary's representative payload as a file and have the fixture factory load it, rather than building the boundary shape in code. Two lanes can read a written specification differently; they have a much harder time reading the same `parser_out.sample.json` differently. The file is the truth and the factory supplies the variations — NaN, edge values, bulk.
- Give an object that crosses more than one boundary a single fixture and a single source for its field names and literal values, and have the other boundaries' contracts load that file. Two fixtures for one object are two definitions, each locally coherent, neither compared against the other, and both green because a contract test reads only its own fixture.
- Justify each test by three questions: is there a realistic change that would break it, does another test already catch that, and could it ever fail? A test that answers no to any of them should not exist.
- Cover every completion criterion with an executable check, but not one test per criterion — one test may satisfy several. What must reach 100% is criteria coverage, a different measure from line coverage (→ [18-work-contract.md](18-work-contract.md)).
- Observe every new test failing before it passes: run it at the base commit and keep the output. A test that was never seen red is indistinguishable from one that asserts nothing.
- Distinguish "the check could not run" from "the check ran and failed". A missing test file, an uncollectable suite, or an unavailable command is a missing baseline, not a red result.
- Exempt standing invariants from the red check explicitly. A regression guard holding at the base commit is the correct outcome, not a defect.
- Every fixed bug gains exactly one regression test that reproduces it.
- Isolate a fixture from the machine it runs on. A test that builds a repository, spawns a process, or writes a config inherits the developer's environment — global git hooks, signing settings, a proxy — and the failure that produces passes in clean CI and fails only on the machine that wrote it, which is the worst asymmetry a suite can have.
- ML tests assert against a tolerance band, not exact float comparison. Fixtures are a small number of realistic samples including NaN, mixed types, and edge cases. Seeds live in a single session-scoped fixture.
- CI verifies GPU code paths with small-sample smoke tests on CPU, without a GPU.
- Before declaring completion, run the verification command and read the full output. TODOs, stubs, and skipped tests are blockers, not completion.

## Details

### 1. Three layers, and what each is for

| Layer | Subject | How many | Catches |
|---|---|---|---|
| Unit | branches, loops, parsers, boundaries | per module, only the non-trivial ones | logic errors |
| Contract | the input/output schema at a module boundary | one per boundary | interface drift between modules |
| End-to-end smoke | the assembled project | 1-3 per project | integration failures nothing else sees |

The layers are not redundant. Unit tests pass while the pieces fail to fit; a contract test pins the shape of a boundary but not the behaviour across it. Only the third layer answers "does the thing work when it is all connected".

One per boundary counts contracts, not objects. An object that crosses two boundaries appears in two contract tests, and if each carries its own fixture that object now has two definitions — both locally coherent, neither compared against the other, both green, because a contract test reads only its own fixture. Nothing in the suite can express the disagreement; it surfaces later as lanes built against shapes that cannot both be satisfied. Give the object one fixture and one source for its field names and literals, and have the second contract load the first's file.

**What makes a test end-to-end.** All four, or it is a unit test wearing the name:

- It enters where a user or CI enters. Calling an internal function directly is not end-to-end.
- It does not mock your own modules. Mock external services only.
- It runs on a small sample (`--limit N` → [04-pipeline.md](04-pipeline.md)), so it is cheap enough to run every time.
- It follows the real sequence of stateful commands. Testing each command alone hides defects in their order — a later step overwriting what an earlier one recorded is invisible until they run together.

An end-to-end failure does not have to say which module broke. Detection is its job; diagnosis belongs to the unit tests.

Don't write: trivial one-liner tests, getter/setter tests, tests that re-verify framework behaviour, mechanical per-function suites. Keep pytest config in pyproject.toml with `--strict-markers`, shared fixtures in `conftest.py`, and remove duplication with `parametrize`.

Sources: [pytest best practices 2026](https://qaskills.sh/blog/pytest-best-practices-2026)

### 2. Criteria coverage is not line coverage

A work contract states what "done" means as completion criteria, each carrying a command that decides it (→ [18-work-contract.md](18-work-contract.md)). The target is that every criterion is decided by something executable — not that every line is exercised.

The two measures pull in opposite directions. Line coverage rewards adding tests; criteria coverage rewards stating the goal precisely. One criterion is usually one test, but three criteria about the same parser may share one parametrized test. Splitting them to hit a one-to-one count rebuilds the mechanical per-function suite this document forbids.

Name a test after the criterion it decides (`test_c01_drops_nan_rows`) when the mapping is one-to-one. When one test covers several, say so in the contract, not in the test name.

### 3. Observing red before green

Run the check at the commit the work started from and keep the output as evidence (→ [19-evidence.md](19-evidence.md)). Three outcomes, not interchangeable:

| At the base commit | Meaning |
|---|---|
| the check fails | the intended red — the test detects the absence of the change |
| the check passes | the test proves nothing about this change. Fix the test, not the record |
| the check cannot run | no baseline: a missing test file, an uncollectable suite, a command that is not installed |

The third row is the one that gets mishandled. Treating any non-zero exit as red makes *writing no test at all* look like a passing check, because a missing test path also exits non-zero. Separate collection from execution: if nothing was collected, the answer is no baseline.

A collection error needs one more split. A test that cannot import the module it is about is the ordinary case when that module does not exist yet, and counts as red. A test file that does not parse is a broken test and counts as no baseline.

Standing invariants are the exception. "Every module exports a schema", "no secret pattern appears in the tree" — these are guards, and they hold at the base commit by design. Mark them (`red: guard` in a contract) rather than letting the gate fail them. Requiring red of a guard makes the gate unusable; leaving guards implicit makes it meaningless.

### 4. Budget

State the budget rather than discovering it. Per module: unit tests for the non-trivial branches, one contract test, one smoke test on a small sample. Beyond that needs a reason — usually a bug that escaped, arriving with its own regression test.

A test that has never failed, in any run, is a deletion candidate. Either it guards something no change can break, or it does not assert what its name claims.

### 5. ML test patterns

- **Small-sample fixtures**: a realistic ~100-row sample (NaN, skew, mixed types), never a toy dict. Keep the representative payload in `tests/fixtures/<boundary>.sample.json` — one file per boundary, or one file named by every boundary that carries the same object — and have the factory load and vary it — a stored sample is reviewable and is what two lanes can both look at, while a factory alone hides what actually crosses the boundary. Samples extracted from real data go through the masking rules in [13-secret-management.md](13-secret-management.md) before they are committed.
- **Tolerance bands**: `assert 0.85 <= auc <= 0.90`, not `assert auc == 0.874`. Bit-exact reproducibility is not guaranteed across hardware (→ [07-ml-development.md](07-ml-development.md)).
- **Golden files**: store reference outputs and compare with a tolerant diff. Update only via an explicit flag (`--update-golden`).
- **Seeds**: `PYTHONHASHSEED`, numpy, torch, and CUDA determinism in one session-scoped fixture. Non-deterministic code cannot be tested.
- **Schema contract tests**: pin the match between training input and inference input to prevent train-serve skew.
- **GPU paths on CPU**: all GPU code goes through the device helper (→ [03-environment.md](03-environment.md)), so CI runs the smoke tests with `device: cpu` and `--limit 10`. These verify behaviour, not performance: shape errors, device mismatches, config errors.

Sources: [ML testing — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 6. Completion verification

- Run the verification command and check the exit code and full output before claiming completion.
- Blockers, not completion: TODO comments, unimplemented branches, stub tests, skipped tests, "probably works".
- For a rewrite or refactor, completion includes passing the characterization tests (→ [00-principles.md](00-principles.md)).
- The verifier is not the author: review runs in a fresh context that starts from the diff and the criteria and never sees the author's reasoning (→ [20-review-gate.md](20-review-gate.md)).
- Integration is verified once after merging the parallel lanes, by the end-to-end layer above. That run is what a contract's `integration` criteria point at (→ [18-work-contract.md](18-work-contract.md)).
