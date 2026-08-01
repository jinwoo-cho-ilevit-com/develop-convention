# 06. Testing + Verification

## Core Rules

- Don't create unnecessary pytest tests. Don't chase line-coverage numbers.
- Test composition: unit tests for core logic + 1-3 E2E smoke tests for the full pipeline. Don't write a test for every function.
- Cover every completion criterion with an executable check, but do not pair them one-to-one with tests — one test may satisfy several criteria. What must reach 100% is criteria coverage, which is a different measure from line coverage and does not replace the rule above (→ [18-work-contract.md](18-work-contract.md)).
- Observe every new test failing before it passes. Run it at the base commit and keep the output; a test that was never seen red proves nothing about the change it claims to cover.
- Distinguish "the check could not run" from "the check ran and failed". A missing test file, an uncollectable suite, or an unavailable command is a missing baseline, not a red result.
- Every fixed bug gains exactly one regression test that reproduces it.
- ML tests assert against a tolerance band instead of exact float comparison.
- Test data uses a small number of realistic sample fixtures (including NaN, mixed types, edge cases).
- Seeds are centrally managed in a single session-scoped fixture.
- CI verifies GPU code paths with small-sample smoke tests on CPU, without a GPU.
- Before declaring completion, actually run the verification command and check the full output. TODOs/stubs/`test.skip` are blockers, not completion.

## Details

### 1. Minimal-but-meaningful test philosophy

Tests are "the minimal set that catches real regressions." The trend line is also minimal-but-meaningful.

- Do write: unit tests for non-trivial logic such as branches/loops/parsers, and 1-3 smoke tests that run the full pipeline through a small sample.
- Don't write: trivial one-liner tests, getter/setter tests, tests that re-verify framework behavior, mechanical per-function test suites.
- Keep pytest config in pyproject.toml with `--strict-markers`, put shared fixtures in `conftest.py`, and remove duplication with `parametrize`.

Sources: [pytest best practices 2026](https://qaskills.sh/blog/pytest-best-practices-2026)

### 2. Criteria coverage, and why it is not line coverage

A work contract states what "done" means as a list of completion criteria; each one carries a command that decides it (→ [18-work-contract.md](18-work-contract.md)). The target is that **every criterion is decided by something executable** — not that every line is exercised.

The two pull in opposite directions, which is why they are named separately. Line coverage rewards adding tests; criteria coverage rewards stating the goal precisely. A criterion like "the loader drops NaN rows and warns" is usually one test. Three criteria about the same parser may share one parametrized test. Splitting them apart to hit a one-to-one count reintroduces exactly the mechanical per-function suite the previous section forbids.

Name tests after the criterion they decide (`test_c01_drops_nan_rows`) when the mapping is one-to-one. When one test covers several, say so in the contract rather than in the test name.

### 3. Observing red before green

An agent-written test that has never failed is indistinguishable from a test that asserts nothing. The check is cheap: run it at the commit the work started from and keep the output as evidence (→ [19-evidence.md](19-evidence.md)).

Three outcomes, and they are not interchangeable:

| At the base commit | Meaning |
|---|---|
| the check fails | the intended red. The test detects the absence of the change |
| the check passes | the test proves nothing about this change. Fix the test, not the record |
| the check cannot run | no baseline — a missing test file, an uncollectable suite, a command that is not installed |

The third row is the one that gets mishandled. Treating any non-zero exit as "red" makes *writing no test at all* look like a passing red check, because a missing test path also exits non-zero. Separate collection from execution: if nothing was collected, the answer is "no baseline", not "red".

A collection error is itself ambiguous and needs one more split. A test that cannot import the module it is about is the ordinary case when that module does not exist yet, and counts as red. A test file that does not parse is a broken test and counts as no baseline.

Not every check is a change-detector. A **standing invariant** — "every module exports a schema", "no secret pattern appears in the tree" — is a regression guard, and it holding at the base commit is the correct outcome, not a defect. Mark those explicitly (`red: guard` in a work contract) rather than letting the gate fail them. Requiring red of a guard makes the gate unusable; leaving guards implicit makes it meaningless, so the distinction is written down per criterion.

### 4. Test budget per module

State the budget instead of discovering it. For one module: unit tests for the non-trivial branches only, one contract test that pins the input/output schema, and one smoke test that runs it end to end on a small sample. Anything beyond that needs a reason — usually a bug that escaped, which arrives with its own regression test.

### 5. ML code test patterns

- **Small-sample fixtures**: build a realistic ~100-row sample (including NaN, skew, mixed types) as a fixture factory, not a toy dict.
- **Tolerance bands**: use `assert 0.85 <= auc <= 0.90`, not `assert auc == 0.874`. Bit-exact reproducibility is not guaranteed across hardware (→ [07-ml-development.md](07-ml-development.md)).
- **Golden files**: store reference outputs (preprocessing results, sample predictions) and compare with a tolerant diff. Update only via an explicit flag (`--update-golden`) — no silent updates.
- **Centralized seed fixture**: set `PYTHONHASHSEED`/numpy/torch seeds and CUDA determinism in a single session-scoped fixture. Non-deterministic code cannot be tested.
- **Schema contract tests**: pin the schema match between training input and inference input with a test (prevents train-serve skew).

Sources: [ML testing — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 6. Verifying GPU code paths with CPU smoke tests

- Since all GPU code paths go through the device helper (→ [03-environment.md](03-environment.md)), CI should run training/inference smoke tests with `device: cpu` + `--limit 10`.
- These smoke tests verify "behavior," not "performance": they catch shape errors, device mismatches, and config errors without GPU cost.

### 7. Completion verification (applying the evidence principle)

- To claim completion: actually run the verification command (tests, smoke run) and check the exit code and full output first.
- Report the following as blockers, not completion: TODO comments, unimplemented branches, stub tests, `test.skip`/`.only`, "probably works" status.
- Completion judgment for rewrites/refactors includes passing characterization tests (→ [00-principles.md](00-principles.md)).
- Separate the verifier from the author: review is performed by a fresh-context agent/session that starts from the diff and the criteria and never sees the author's reasoning (→ [09-agentic-workflow.md](09-agentic-workflow.md)).
