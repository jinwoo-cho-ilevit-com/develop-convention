# 06. Testing + Verification

## Core Rules

- Don't create unnecessary pytest tests. Don't chase coverage numbers.
- Test composition: unit tests for core logic + 1-3 E2E smoke tests for the full pipeline. Don't write a test for every function.
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

### 2. ML code test patterns

- **Small-sample fixtures**: build a realistic ~100-row sample (including NaN, skew, mixed types) as a fixture factory, not a toy dict.
- **Tolerance bands**: use `assert 0.85 <= auc <= 0.90`, not `assert auc == 0.874`. Bit-exact reproducibility is not guaranteed across hardware (→ [07-ml-development.md](07-ml-development.md)).
- **Golden files**: store reference outputs (preprocessing results, sample predictions) and compare with a tolerant diff. Update only via an explicit flag (`--update-golden`) — no silent updates.
- **Centralized seed fixture**: set `PYTHONHASHSEED`/numpy/torch seeds and CUDA determinism in a single session-scoped fixture. Non-deterministic code cannot be tested.
- **Schema contract tests**: pin the schema match between training input and inference input with a test (prevents train-serve skew).

Sources: [ML testing — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 3. Verifying GPU code paths with CPU smoke tests

- Since all GPU code paths go through the device helper (→ [03-environment.md](03-environment.md)), CI should run training/inference smoke tests with `device: cpu` + `--limit 10`.
- These smoke tests verify "behavior," not "performance": they catch shape errors, device mismatches, and config errors without GPU cost.

### 4. Completion verification (applying the evidence principle)

- To claim completion: actually run the verification command (tests, smoke run) and check the exit code and full output first.
- Report the following as blockers, not completion: TODO comments, unimplemented branches, stub tests, `test.skip`/`.only`, "probably works" status.
- Completion judgment for rewrites/refactors includes passing characterization tests (→ [00-principles.md](00-principles.md)).
- Separate the verifier from the author: review is performed by a fresh-context agent/session that sees only the diff and the criteria (→ [09-agentic-workflow.md](09-agentic-workflow.md)).
