# 06. Testing + Verification

## Core Rules

- Make the sample run the default check: execute the real entry point — a CLI or pipeline stage (`--limit N`, → [04-pipeline.md](04-pipeline.md)), a library's caller-facing flow (the public call sequence a criterion names, not each exported symbol), a service's endpoint through its test client — on a stored sample input, and assert properties derived from the specification: the output schema, counts and invariants, and the exact value for the few inputs whose answer is known. One test file per entry point holds it.
- Write any other test only for a reason the sample run cannot supply: a branch or parser edge the sample does not reach, or a check this document or another convention names on its own terms — a characterization before a rewrite, a double confirmed against the real system, a standing guard, a golden equality test ([08-llm-development.md](08-llm-development.md)). A test re-checking what the sample run already catches is deleted, and so is a per-function suite. Don't chase line-coverage numbers.
- When work splits into parallel lanes, write each boundary's contract **before** the lanes start, as a file — not a test — owned by no lane and edited by none. Disjoint file ownership stops two lanes writing the same file; it does nothing about the two of them holding contradictory assumptions about what crosses between them, and each lane's own checks pass under its own assumption. The contract written first is the one assumption both lanes build against (→ [21-development-loop.md](21-development-loop.md)).
- A boundary's contract is two files: the representative payload (`tests/fixtures/<boundary>.sample.json`) and a contract file naming each symbol crossing the boundary under the name and signature its caller uses, the value set both sides branch on, and which side calls which — the surfaces a boundary drifts on are enumerated in [18-work-contract.md](18-work-contract.md) §5. Two lanes can read a written specification differently; they have a much harder time reading the same `parser_out.sample.json` differently.
- The boundary sample holds every member of the value set its contract file names, as rows. The assembled sample run is what checks a boundary, and it checks only what the sample carries: a value no row contains is a value whose mishandling nothing catches.
- Give an object that crosses more than one lane boundary a single sample file, and have every contract file it crosses point at it. Two samples for one object are two definitions, each locally coherent and neither compared against the other.
- Build each stored payload — a lane boundary's sample or a sample run's input — so that only the correct rule reproduces it. Where two independent properties happen to coincide in the sample — a column order equal to the projection order, an identifier equal to a row index — every implementation that confuses the two passes every check. Vary one of them in the file.
- A double stands in for something outside your project, and it may not assert a shape the real system never produces: a fake index carrying a uniqueness flag the real server does not set teaches the implementation to depend on it, and the dependency breaks on the first real run. Confirm the double against the real thing once and keep that check; for a heavy external dependency, that check is a layer of its own (→ [22-framework-wrapping.md](22-framework-wrapping.md)).
- Never patch over one of your own components to make a test pass. The substitution does not merely weaken an assertion — it removes that path from the run, so the defect living there cannot be observed until the patch comes out. The sample run's "no mocking your own modules" (§1) is the same rule at its strictest.
- Derive a test's expected value from the specification, never by running the code under test and recording what it returns. A recorded output is true by construction — the test asserts that the code does what the code does — and this is the default failure mode when one session writes both the implementation and its tests. A sample run makes the capture tempting, since its output is right there; the one capture allowed is characterization, recorded from the base-commit code before a rewrite (→ [00-principles.md](00-principles.md)).
- Justify each test by three questions: is there a realistic change that would break it, does it catch that change when no other test does, and could it ever fail? Reduce the assertion to answer the third: one comparing a constant to a constant, or whose two sides pass through the same normalisation, is an identity wearing a test's name. A test that answers no to any of the three should not exist.
- A test that fails when behaviour did not change is the mirror failure: a refactor breaks it because it asserts implementation structure rather than what callers observe. Such a change-detector catches no defects and taxes every change — delete it, or re-point it at the public behaviour.
- Cover every completion criterion with an executable check or a recorded `[human]` verdict, most of them by the sample run: one test function or parametrize case per criterion inside the entry point's file, sharing one run, so each criterion can be observed red on its own. A bug-fix criterion is decided by its reproduction command and output, not by a new test function. What must reach 100% is criteria coverage, a different measure from line coverage (→ [18-work-contract.md](18-work-contract.md)).
- Observe every new test failing before it passes: run it at the base commit and keep the output. A test that was never seen red is indistinguishable from one that asserts nothing.
- A test written for code that already works has no red to observe at the base commit, and neither does an assertion whose shared run fails there before any assertion executes — verify it by sabotage instead: break the behaviour it claims to pin, watch the test fail, and revert. A characterization test never seen failing is ceremony, not verification.
- Distinguish "the check could not run" from "the check ran and failed". A missing test file, an uncollectable suite, or an external tool that is not installed is a missing baseline, not a red result.
- Exempt standing invariants from the red check explicitly. A regression guard holding at the base commit is the correct outcome, not a defect.
- A bug fix needs no dedicated regression test. It is decided by reproducing the defect before and after the fix, with the command and the decisive output lines kept in the fix commit's `## Result` (→ [17-commit-protocol.md](17-commit-protocol.md), [19-evidence.md](19-evidence.md)); where the triggering input fits the sample and an existing assertion covers the property the defect violated, adding it as a row is the cheapest way to keep it caught. Check the fix against the defect's siblings before it closes: the same mistake usually sits on the path beside the reported one — the other decoder, the second resume branch — and fixing only what was reported leaves the twin behind.
- Isolate a fixture from the machine it runs on and from the tests that already used it. A test that builds a repository, spawns a process, or writes a config inherits the developer's environment — global git hooks, signing settings, a proxy — and the failure that produces passes in clean CI and fails only on the machine that wrote it, which is the worst asymmetry a suite can have. A module-scoped fixture handed out by reference or by shallow copy carries one test's mutation into the next, and the test that then fails is not the one that broke it.
- ML tests assert against a tolerance band, not exact float comparison. Fixtures are a small number of realistic samples including NaN, mixed types, and edge cases. Seeds live in a single session-scoped fixture.
- Where output is not deterministic — text generated by an LLM — the sample run asserts only the deterministic properties: the output parses, the schema holds, required fields are present. Its quality is judged statistically over a set, never by exact match (→ [10-llm-api-inference.md](10-llm-api-inference.md)).
- CI verifies GPU code paths by running the sample run on CPU, without a GPU.
- Before declaring completion, run the verification command and read the full output. TODOs, stubs, and skipped tests are blockers, not completion.

## Details

### 1. The sample run, and when to add a test

| Check | Subject | How many | Catches |
|---|---|---|---|
| Sample run | the real entry point on a stored sample input | one file per entry point | most completion criteria, and the joins between the modules it passes through |
| Unit | a branch or parser edge the sample does not reach | only with that reason | logic the sample never exercises |
| Contract (a file, not a test) | a boundary where parallel lanes meet | one per lane boundary | nothing by itself — it is what both lanes build against, checked by the integration run and the merged-whole review |
| Integration run | the assembled project's sample run | 1-3 per project split into lanes, after the merge | failures only the assembly shows |

The sample run comes first because it grows with the requirements, not with the code. One run through the real entry point exercises parsing, configuration, each stage and the joins between them, and its assertions read like the specification. A per-function suite exercises the same code in pieces: each piece passes while the pieces fail to fit, and the suite multiplies with every function added.

**What makes a sample run.** All four, or it is a unit test wearing the name:

- It enters where a user or caller enters: the CLI, the library's caller-facing flow, the service's endpoint. Calling an internal function directly is not a sample run.
- It does not mock your own modules. Mock external services only.
- It runs on a small stored sample (`--limit N` → [04-pipeline.md](04-pipeline.md)), so it is cheap enough to run every time. The sample is a file a reviewer can open and see what went in.
- It follows the real sequence of stateful commands. Testing each command alone hides defects in their order — a later step overwriting what an earlier one recorded is invisible until they run together.

**When a unit test earns its place.** The sample cannot reach an error path, or a malformed input it would have to be corrupted to hold — first try adding the case as a row of the sample, and write a unit test only where it cannot live there. A fixed bug is the same choice: its reproduction is the evidence, and a sample row, where it fits and an assertion covers it, keeps it caught. A sample-run failure does not have to say which module broke; detection is its job, and the diagnosis is done by reading the dumped stage outputs (→ [04-pipeline.md](04-pipeline.md)), not by a unit suite kept in advance.

**Contracts are for lanes, and they are files.** Work done in one flow needs no contract: its sample run crosses every internal boundary and fails when two sides disagree. Contracts exist because parallel lanes build the two sides apart, each green under its own assumption (→ [21-development-loop.md](21-development-loop.md)). A contract cannot run inside a lane — the other side is not in the worktree — so it is written as a file both lanes read, and checked once the sides meet: the integration run exercises every boundary on samples that carry the whole value set, and the merged-whole review compares the merged code against each contract file for what no sample reaches — a symbol only an error path calls, a signature. One per lane boundary counts contracts, not objects. An object that crosses two lane boundaries appears in two contract files, and if each points at its own sample that object now has two definitions — both locally coherent, neither compared against the other. Give the object one sample file and have both contract files point at it.

**Inside a lane.** A lane's sample run is its own stage's entry point run on a stored sample: the frozen boundary sample, read-only, where the lane consumes one, and the lane's own input sample where its stage comes first. Rows the lane wants to add to a frozen sample go in a separate `<entry>.input.*` file under the lane's owned paths; the frozen file stays frozen. A lane whose entry point imports its siblings' modules — a CLI over the other lanes — cannot run in its own worktree: the run fails on import, or is faked by mocking a sibling, which the second condition forbids. That run, like the assembled project's, belongs to the integration step and happens once, after the merge; it is what the end-to-end condition of [18-work-contract.md](18-work-contract.md) §5 names. Work done in one flow has no separate integration run: its entry point's sample run already is one.

Don't write: trivial one-liner tests, getter/setter tests, tests that re-verify framework behaviour, mechanical per-function suites, a unit test repeating what the sample run asserts. Keep pytest config in pyproject.toml with `--strict-markers`, shared fixtures in `conftest.py`, and remove duplication with `parametrize`.

Sources: [pytest best practices 2026](https://qaskills.sh/blog/pytest-best-practices-2026)

### 2. Criteria coverage is not line coverage

A work contract states what "done" means as completion criteria, each carrying a command that decides it (→ [18-work-contract.md](18-work-contract.md)). The target is that every criterion is decided by something executable, or by a recorded `[human]` verdict — not that every line is exercised.

The two measures pull in opposite directions. Line coverage rewards adding tests; criteria coverage rewards stating the goal precisely.

Most criteria are decided inside the sample run's file. The run happens once — a module-scoped fixture that returns the output's path or an immutable result, never a shared mutable object (Core Rules) — and each criterion gets its own test function against it: `test_c01_drops_nan_rows`, `test_c02_writes_schema_v2` in `tests/test_sample_run_<entry>.py`, or under whatever test path the lane owns. A function per criterion, not a file per criterion. The separate function is what lets each criterion be observed red on its own at the base commit (§3); one assertion block covering five criteria goes red on the first and hides whether the other four already held. When the shared run itself fails at the base commit — the change creates the entry point, or adds the option the run uses — no assertion executes and every function is red for that one reason; confirm each assertion by sabotage once the run succeeds. Three criteria about the same parser may share one parametrized test, since each case is observed red on its own.

### 3. Observing red before green

Run the check at the commit the work started from and keep the output as evidence (→ [19-evidence.md](19-evidence.md)). Three outcomes, not interchangeable:

| At the base commit | Meaning |
|---|---|
| the check fails | the intended red — the test detects the absence of the change |
| the check passes | the test proves nothing about this change. Fix the test, not the record |
| the check cannot run | no baseline: a missing test file, an uncollectable suite, an external tool that is not installed |

The third row is the one that gets mishandled. Treating any non-zero exit as red makes *writing no test at all* look like a passing check, because a missing test path also exits non-zero. Separate collection from execution: if nothing was collected, the answer is no baseline.

A collection error needs one more split. A test that cannot import the module it is about is the ordinary case when that module does not exist yet, and counts as red. A test file that does not parse is a broken test and counts as no baseline. A sample run whose entry point the change creates — the project's command or function is not there yet — is red on the same reasoning, though a red every criterion shares proves only that the run could not happen; each assertion is then confirmed by sabotage (§2). An external tool the run needs that is not installed is no baseline.

Standing invariants are the exception. "Every module exports a schema", "no secret pattern appears in the tree" — these are guards, and they hold at the base commit by design. Mark them (`red: guard` in a contract) rather than letting the gate fail them. Requiring red of a guard makes the gate unusable; leaving guards implicit makes it meaningless.

Two gaps the base-commit check does not close. A test whose expected value was recorded from the implementation goes red at the base commit like any other — the module is missing there — yet asserts nothing about correctness: the author ran the new code, captured its output, and pasted it back as the expectation, so a bug in the implementation is reproduced in the expectation verbatim. This is the default failure mode when one session writes both the code and its tests, which is why the expected value must come from the specification. And a characterization test written for code that already works is green at the base commit by design, so red-before-green never fires for it — sabotage replaces it: break the behaviour the test claims to pin, watch it fail, revert, and keep that observation as the evidence.

Sources: [AI-generated tests that pass but don't assert](https://getautonoma.com/blog/ai-generated-tests-pass-but-dont-assert), [AI-generated tests as ceremony](https://blog.ploeh.dk/2026/01/26/ai-generated-tests-as-ceremony/)

### 4. Budget

State the budget rather than discovering it. Per entry point: one sample-run file, one test function per criterion it decides. Per lane boundary: one contract file and its sample, no test. Per project split into lanes: the 1-3 integration runs, owned by the integration step (§1), not part of any lane's budget. Anything beyond that needs a reason the sample run cannot supply — a branch it does not reach, or a check the Core Rules name on its own terms. A bug that escaped adds a sample row where it fits, not a test.

A test that has never failed, in any run, is a deletion candidate. Either it guards something no change can break, or it does not assert what its name claims.

The deletion candidate has a mirror: a test that fails when behaviour did not change. A refactor breaks it because it asserts the implementation's structure — the exact call sequence, a private shape — rather than what callers observe. It catches no defects and adds a cost to every change, which is negative value: delete it, or rewrite it against the public behaviour.

Sources: [Change-detector tests considered harmful](https://testing.googleblog.com/2015/01/testing-on-toilet-change-detector-tests.html)

### 5. ML test patterns

- **Small-sample fixtures**: a realistic ~100-row sample (NaN, skew, mixed types), never a toy dict. It is the sample run's input. At a lane boundary it is also the frozen payload, kept in `tests/fixtures/<boundary>.sample.json` — one file per boundary, or one file named by every boundary that carries the same object — which the factory loads and varies; a stored sample is reviewable and is what two lanes can both look at, while a factory alone hides what actually crosses the boundary. Samples extracted from real data go through the masking rules in [13-secret-management.md](13-secret-management.md) before they are committed.
- **Tolerance bands**: `assert 0.85 <= auc <= 0.90`, not `assert auc == 0.874`. Bit-exact reproducibility is not guaranteed across hardware (→ [07-ml-development.md](07-ml-development.md)).
- **Golden files**: store reference outputs and compare with a tolerant diff. The values must come from somewhere other than the code under test — a hand-checked answer, a reference implementation, the base-commit code for a characterization — and where no such source exists, assert properties instead. Update only via an explicit flag (`--update-golden`), and review that diff against the specification like code: an update is exactly where a regression gets re-recorded as the expectation.
- **Seeds**: `PYTHONHASHSEED`, numpy, torch, and CUDA determinism in one session-scoped fixture. Code that is non-deterministic under a fixed seed cannot be tested by value; output that is non-deterministic by nature (an API-served LLM) gets property assertions only (Core Rules).
- **Train/serve schema**: assert inside the sample run that training input and inference input share one schema, to prevent train-serve skew — an assertion in the run, not a separate test.
- **GPU paths on CPU**: all GPU code goes through the device helper (→ [03-environment.md](03-environment.md)), so CI runs the sample run with `device: cpu` and `--limit 10`. These verify behaviour, not performance: shape errors, device mismatches, config errors. When the entry point carries a `--smoke` mode (→ [23-remote-gpu-iteration.md](23-remote-gpu-iteration.md)), CI invokes that same mode rather than a second recipe.

Sources: [ML testing — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 6. Completion verification

- Run the verification command and check the exit code and full output before claiming completion.
- Blockers, not completion: TODO comments, unimplemented branches, stub tests, skipped tests, "probably works".
- For a rewrite or refactor, completion includes passing the characterization tests (→ [00-principles.md](00-principles.md)).
- The verifier is not the author: review runs in a fresh context that starts from the diff and the criteria and never sees the author's reasoning (→ [20-review-gate.md](20-review-gate.md)).
- Integration is verified by the integration run — the assembled project's sample run, which belongs to no lane and runs once after the merge (§1). That run, with every lane's criteria re-run on the merged head, is what a work contract's `integration` criteria point at (→ [18-work-contract.md](18-work-contract.md)).
