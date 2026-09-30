# 06. Testing + Verification

## Core Rules

- Start with the narrowest existing check that reaches the changed behavior. For a new data flow or entry point, a representative sample run through the real entry point is the default check (§1); do not add a test file merely because an entry point exists.
- Write any other test only for a reason the sample run cannot supply: a branch or parser edge the sample does not reach, or a check this document or another convention names on its own terms — a characterization before a rewrite, a double confirmed against the real system, a standing guard, a golden equality test ([08-llm-development.md](08-llm-development.md)). A test re-checking what the sample run already catches is deleted, and so is a per-function suite. Don't chase line-coverage numbers.
- When work splits into parallel lanes, write each boundary's contract **before** the lanes start, as a file — not a test — owned by no lane and edited by none (§1).
- A boundary's contract is two files: the representative payload (`tests/fixtures/<object>.sample.json`, one per object crossing it) and a contract file naming each symbol crossing the boundary under its caller's name and signature, the value set both sides branch on, and which side calls which (§1).
- A boundary whose payload lands as JSON, YAML or TOML also gets a JSON Schema beside its contract file, which the sample passes at freeze and the producing lane's fresh dump passes in one command (§7).
- The boundary sample holds every member of the value set its contract file names, as rows (§1).
- Give an object that crosses more than one lane boundary a single sample file, and have every contract file it crosses point at it. Two samples for one object are two definitions, each locally coherent and neither compared against the other.
- Build each stored payload — a lane boundary's sample or a sample run's input — so that only the correct rule reproduces it. Where two independent properties happen to coincide in the sample — a column order equal to the projection order, an identifier equal to a row index — every implementation that confuses the two passes every check. Vary one of them in the file.
- A sample or stored input taken from real data or traffic has its personal and customer fields replaced before it is committed; the secret scan does not catch them (§5).
- A double stands in for something outside your project, and it may not assert a shape the real system never produces: a fake index carrying a uniqueness flag the real server does not set teaches the implementation to depend on it, and the dependency breaks on the first real run. Confirm the double against the real thing once and keep that check; for a heavy external dependency, that check is a layer of its own (→ [22-framework-wrapping.md](22-framework-wrapping.md)).
- Never patch over one of your own components to make a test pass. The substitution does not merely weaken an assertion — it removes that path from the run, so the defect living there cannot be observed until the patch comes out. The sample run's "no mocking your own modules" (§1) is the same rule at its strictest.
- Derive a test's expected value from the specification, never by running the code under test and recording what it returns; the one capture allowed is characterization from the base-commit code before a rewrite (§3, → [00-principles.md](00-principles.md)).
- Justify each test by three questions: is there a realistic change that would break it, does it catch that change when no other test does, and could it ever fail? Reduce the assertion to answer the third: one comparing a constant to a constant, or whose two sides pass through the same normalisation, is an identity wearing a test's name. A test that answers no to any of the three should not exist.
- A test that fails when behaviour did not change is the mirror failure: a refactor breaks it because it asserts implementation structure rather than what callers observe. Such a change-detector catches no defects and taxes every change — delete it, or re-point it at the public behaviour.
- Cover each planned completion criterion with an executable check or recorded `[human]` verdict. Reuse a check that already detects the relevant failure. A new test is warranted for new behavior, a recurring defect, or a critical invariant only when the existing checks miss a realistic failure; keep one test function or parametrized case per criterion it alone decides (→ [18-work-contract.md](18-work-contract.md)).
- For each justified new test, observe it failing at the base commit before it passes, or use sabotage when the behavior already exists (§3). Existing checks do not need a new red run.
- A test written for code that already works has no red to observe at the base commit, and neither does an assertion whose shared run fails there before any assertion executes — verify it by sabotage instead: break the behaviour it claims to pin, watch the test fail, and revert. A characterization test never seen failing is ceremony, not verification.
- Check every diff that turns a failing test green for the shortcuts that pass a test without meeting its specification — an edited, deleted or skipped test or a loosened CI threshold, an overloaded comparison operator, state recorded across calls, a special case for the test's inputs — each by the check that exposes it (§3). Any one of them is a review finding.
- Distinguish "the check could not run" from "the check ran and failed". A missing test file, an uncollectable suite, or an external tool that is not installed is a missing baseline, not a red result.
- Existing standing invariants need no red check. A regression guard holding at the base commit is the correct outcome.
- Decide a bug fix by reproducing the defect before and after, keeping the command and decisive output in the fix commit's `## Result`. If a serious defect can recur and no existing check catches it, add a durable regression guard (§4, → [17-commit-protocol.md](17-commit-protocol.md), [19-evidence.md](19-evidence.md)).
- Check a fix against the defect's siblings on neighbouring paths before it closes (§4).
- Isolate a fixture from the machine it runs on and from the tests that already used it (§1).
- ML tests assert against a tolerance band, not exact float comparison. Fixtures are a small number of realistic samples including NaN, mixed types, and edge cases. Seeds live in a single session-scoped fixture.
- Where output is not deterministic — text generated by an LLM — the sample run asserts only the deterministic properties: the output parses, the schema holds, required fields are present. Its quality is judged statistically over a set, never by exact match (→ [10-llm-api-inference.md](10-llm-api-inference.md)).
- Where CPU fallback is a project requirement, CI verifies the shared entry path with a bounded CPU sample run.
- Before declaring completion, run the narrowest relevant verification and inspect its decisive output and exit status. Broaden execution only for a concrete remaining risk or required gate. TODOs and stubs on the changed path, and skipped checks needed for the criterion, block completion.

## Details

### 1. The sample run, and when to add a test

| Check | Subject | How many | Catches |
|---|---|---|---|
| Sample run | the real entry point on a stored sample input | one file per flow that warrants a sample run | completion criteria and joins between the modules it passes through |
| Unit | a branch or parser edge the sample does not reach | only with that reason | logic the sample never exercises |
| Contract (a file, not a test) | a boundary where parallel lanes meet | one per lane boundary | nothing by itself — it is what both lanes build against, checked by the producer's schema check, the consumer's sample run, each lane's review and, after the merge, the integration run and merged-whole review |
| Integration run | the assembled project's sample run | 1-3 per project split into lanes, after the last merge | failures only the assembly shows |

The sample run comes first because it grows with the requirements, not with the code. One run through the real entry point exercises parsing, configuration, each stage and the joins between them, and its assertions read like the specification. A per-function suite exercises the same code in pieces: each piece passes while the pieces fail to fit, and the suite multiplies with every function added.

**What it executes and asserts.** The entry point is a CLI or pipeline stage (`--limit N`, → [04-pipeline.md](04-pipeline.md)), a library's caller-facing flow (the public call sequence a criterion names, not each exported symbol), or a service's endpoint through its test client. The assertions are properties derived from the specification: the output schema, counts and invariants, and the exact value for the few inputs whose answer is known.

**What makes a sample run.** All four, or it is a unit test wearing the name:

- It enters where a user or caller enters: the CLI, the library's caller-facing flow, the service's endpoint. Calling an internal function directly is not a sample run.
- It does not mock your own modules. Mock external services only.
- It runs on a small stored sample (`--limit N` → [04-pipeline.md](04-pipeline.md)), so it is cheap enough to run every time. The sample is a file a reviewer can open and see what went in.
- It follows the real sequence of stateful commands. Testing each command alone hides defects in their order — a later step overwriting what an earlier one recorded is invisible until they run together.

**When a unit test earns its place.** The sample cannot reach an error path, or a malformed input it would have to be corrupted to hold — first try adding the case as a row of the sample, and write a unit test only where it cannot live there. A fixed bug is the same choice: its reproduction is the evidence, and a sample row, where it fits and an assertion covers it, keeps it caught. A sample-run failure does not have to say which module broke; detection is its job, and the diagnosis is done by reading the dumped stage outputs (→ [04-pipeline.md](04-pipeline.md)), not by a unit suite kept in advance.

**Contracts are for lanes, and they are files.** Work done in one flow needs no contract: its sample run crosses every internal boundary and fails when two sides disagree. Contracts exist because parallel lanes build the two sides apart, each green under its own assumption (→ [21-development-loop.md](21-development-loop.md)). Disjoint file ownership stops two lanes writing the same file; it does nothing about the two of them holding contradictory assumptions about what crosses between them, so the contract written before the lanes start is the one assumption both build against. Its contract file names the surfaces a boundary drifts on, enumerated in [18-work-contract.md](18-work-contract.md) §5, and its sample is the part two lanes are least able to read differently: a written specification can be read two ways, the same `parser_out.sample.json` much less so. A contract cannot run inside a lane — the other side is not in the worktree — so it is written as a file both lanes read, and checked by reading and by running what each side can run: the producing lane checks its fresh dump against the boundary's schema, the consumer lane runs on the sample that carries the whole value set, each lane's reviewers compare that lane's side against the contract file for what the schema does not cover (names, signatures, call direction), and after the merge the integration run exercises the boundary on real input while the merged-whole review compares both sides against the file for what no run reaches — a symbol only an error path calls, a signature. One per lane boundary counts contracts, not objects. An object that crosses two lane boundaries appears in two contract files, and if each points at its own sample that object now has two definitions — both locally coherent, neither compared against the other. Give the object one sample file and have both contract files point at it.

**The sample carries the value set.** The boundary sample is the consumer lane's sample-run input, and that run checks only what the sample carries: a value no row contains is a value whose mishandling nothing catches. What no schema covers — names, signatures, call direction, and every surface of a boundary with no schema — is checked by review: its lanes' reviewers and the merged-whole review compare the code against the contract file.

**Inside a lane.** A lane's sample run is its own stage's entry point run on a stored sample: the frozen boundary sample, read-only, where the lane consumes one, and the lane's own input sample where its stage comes first. Rows the lane wants to add to a frozen sample go in a separate `<entry>.input.*` file under the lane's owned paths; the frozen file stays frozen. A lane whose entry point imports its siblings' modules — a CLI over the other lanes — cannot run in its own worktree: the run fails on import, or is faked by mocking a sibling, which the second condition forbids. That run, like the assembled project's, belongs to no lane and happens once, on the merged head after the last merge; it is part of the end-to-end condition [18-work-contract.md](18-work-contract.md) §1 defines. Work done in one flow has no separate integration run: its entry point's sample run already is one.

Don't write: trivial one-liner tests, getter/setter tests, tests that re-verify framework behaviour, mechanical per-function suites, a unit test repeating what the sample run asserts. Keep pytest config in pyproject.toml with `--strict-markers`, shared fixtures in `conftest.py`, and remove duplication with `parametrize`.

**Fixture isolation.** A test that builds a repository, spawns a process, or writes a config inherits the developer's environment — global git hooks, signing settings, a proxy — and the failure that produces passes in clean CI and fails only on the machine that wrote it, which is the worst asymmetry a suite can have. A module-scoped fixture handed out by reference or by shallow copy carries one test's mutation into the next, and the test that then fails is not the one that broke it.

Lead (a third-party blog, not a primary source): [pytest best practices 2026](https://qaskills.sh/blog/pytest-best-practices-2026)

### 2. Criteria coverage is not line coverage

A planned work contract states what "done" means as completion criteria, each carrying a command that decides it (→ [18-work-contract.md](18-work-contract.md)). The target is that every criterion is decided by something executable, or by a recorded `[human]` verdict — not that every line is exercised. `auto` work records the relevant existing check and its result directly.

The two measures pull in opposite directions. Line coverage rewards adding tests; criteria coverage rewards stating the goal precisely.

When a new sample-run test is justified, run the entry point once — a fixture returns an output path or immutable result, never a shared mutable object (§1). Give each criterion the test uniquely needed to decide it. If the shared run itself fails at the base commit before an assertion executes, confirm each new assertion by sabotage once the run succeeds. Related cases may share one parametrized test.

### 3. Observing red before green

For a justified new test, run it at the commit the work started from and keep the decisive output as evidence (→ [19-evidence.md](19-evidence.md)). Three outcomes, not interchangeable:

| At the base commit | Meaning |
|---|---|
| the check fails | the intended red — the test detects the absence of the change |
| the check passes | the test proves nothing about this change. Fix the test, not the record |
| the check cannot run | no baseline: a missing test file, an uncollectable suite, an external tool that is not installed |

The third row is the one that gets mishandled. Treating any non-zero exit as red makes *writing no test at all* look like a passing check, because a missing test path also exits non-zero. Separate collection from execution: if nothing was collected, the answer is no baseline.

A collection error needs one more split. A test that cannot import the module it is about is the ordinary case when that module does not exist yet, and counts as red. A test file that does not parse is a broken test and counts as no baseline. A sample run whose entry point the change creates — the project's command or function is not there yet — is red on the same reasoning, though a red every criterion shares proves only that the run could not happen; each assertion is then confirmed by sabotage (§2). An external tool the run needs that is not installed is no baseline.

Standing invariants such as "no secret pattern appears in the tree" may already hold at the base commit. Record their current check and result without a red run. A new test that pins an existing critical invariant may use sabotage to show that it detects a violation.

The criteria table's `red` column applies to justified new tests only. `observed` means the test failed for the intended reason at the base commit; `sabotage` means it failed when the behavior it pins was deliberately broken. Existing checks use `—` ([19-evidence.md](19-evidence.md) §1).

Two gaps the base-commit check does not close. A test whose expected value was recorded from the implementation goes red at the base commit like any other — the module is missing there — yet asserts nothing about correctness: the author ran the new code, captured its output, and pasted it back as the expectation, so a bug in the implementation is reproduced in the expectation verbatim — the test asserts that the code does what the code does. A sample run makes the capture tempting, since its output is right there. This is the default failure mode when one session writes both the code and its tests, which is why the expected value must come from the specification. And a characterization test written for code that already works is green at the base commit by design, so red-before-green never fires for it — sabotage replaces it: break the behaviour the test claims to pin, watch it fail, revert, and keep that observation as the evidence.

Leads (practitioner blogs, not primary sources): [AI-generated tests that pass but don't assert](https://getautonoma.com/blog/ai-generated-tests-pass-but-dont-assert), [AI-generated tests as ceremony](https://blog.ploeh.dk/2026/01/26/ai-generated-tests-as-ceremony/)

**Passing a test without meeting it.** ImpossibleBench gave coding agents tasks whose tests contradict the specification, so any pass is a shortcut, and named four kinds. The model "directly modifies tests despite being explicitly instructed not to"; "overloads the comparison operators so they always return desired values"; "records extra states in order to obtain different results for the same input"; or "special-cases the test cases to pass them". Making the tests read-only stopped the first and, the paper reports, "does not eliminate other cheating methods such as special-casing or operator overloading" — so each is checked by what exposes it rather than prevented by one permission:

| Shortcut | What exposes it |
|---|---|
| a test edited, deleted, skipped or marked expected-to-fail; a CI threshold lowered or a check removed (the paper's first kind, widened to the CI gate) | the diff itself — review reads the test and CI files first |
| a comparison operator overloaded to always agree | sabotage: break the behaviour, and the test still passes |
| state recorded across calls | the same input run twice, or in another order |
| a special case for the test's inputs | an input the test does not carry — a fresh sample row |

The module lane of [20-review-gate.md](20-review-gate.md) §2 is where review looks for these.

Source: [Zhong, Raghunathan, Carlini — ImpossibleBench: Measuring LLMs' Propensity of Exploiting Test Cases](https://arxiv.org/abs/2510.20270) — Abstract (any pass is a shortcut), §4.1 (the four kinds), §5.2 (read-only tests) (checked 2026-09-12)

### 4. Budget

Keep only checks that detect a realistic failure missed by the existing checks. A new entry point may need one sample-run file; a lane boundary needs its contract and sample, not an extra test. An escaped bug is first reproduced with its triggering input; add a sample row if an existing assertion covers the property. Add a durable test for a serious recurring failure when no current check catches it. Before the fix closes, check the defect's siblings on neighboring paths.

A test that has never failed, in any run, is a deletion candidate. Either it guards something no change can break, or it does not assert what its name claims.

The deletion candidate has a mirror: a test that fails when behaviour did not change. A refactor breaks it because it asserts the implementation's structure — the exact call sequence, a private shape — rather than what callers observe. It catches no defects and adds a cost to every change, which is negative value: delete it, or rewrite it against the public behaviour.

Sources: [Change-detector tests considered harmful](https://testing.googleblog.com/2015/01/testing-on-toilet-change-detector-tests.html)

### 5. ML test patterns

- **Small-sample fixtures**: a realistic ~100-row sample (NaN, skew, mixed types), never a toy dict. It is the sample run's input. At a lane boundary it is also the frozen payload, kept in `tests/fixtures/<object>.sample.json` — one file per object, named by every boundary that carries it — which the factory loads and varies; a stored sample is reviewable and is what two lanes can both look at, while a factory alone hides what actually crosses the boundary.
- **Real-data samples**: a sample or stored input extracted from real data or traffic has every personal or customer field — names, contact details, account and order identifiers, free text a person typed — replaced with a synthetic value of the same type and shape before it is committed (Core Rules). The secret scan of [13-secret-management.md](13-secret-management.md) matches credential patterns and passes these fields untouched. Keep the replacement consistent within the file (one real value maps to one synthetic value) so joins and counts the assertions rely on still hold.
- **Tolerance bands**: `assert 0.85 <= auc <= 0.90`, not `assert auc == 0.874`. Bit-exact reproducibility is not guaranteed across hardware (→ [07-ml-development.md](07-ml-development.md)).
- **Golden files**: store reference outputs and compare with a tolerant diff. The values must come from somewhere other than the code under test — a hand-checked answer, a reference implementation, the base-commit code for a characterization — and where no such source exists, assert properties instead. Update only via an explicit flag (`--update-golden`), and review that diff against the specification like code: an update is exactly where a regression gets re-recorded as the expectation.
- **Seeds**: `PYTHONHASHSEED`, numpy, torch, and CUDA determinism in one session-scoped fixture. Code that is non-deterministic under a fixed seed cannot be tested by value; output that is non-deterministic by nature (an API-served LLM) gets property assertions only (Core Rules).
- **Train/serve schema**: assert inside the sample run that training input and inference input share one schema, and that one stored input through both preprocessing paths comes out element-wise equal — its own input file, not the known-answer sample, since the paths are compared to each other ([07-ml-development.md](07-ml-development.md) §2) — to prevent train-serve skew — an assertion in the run, not a separate test.
- **GPU paths on CPU**: when CPU fallback is a project requirement (→ [03-environment.md](03-environment.md)), CI uses the sample run with `device: cpu` and a bounded input. This verifies shape, device, and config behavior, not GPU performance. When the entry point carries a `--smoke` mode (→ [23-remote-gpu-iteration.md](23-remote-gpu-iteration.md)), CI can invoke that mode rather than a second recipe.

Lead (a Medium post, not a primary source): [ML testing — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 6. Completion verification

- Run the relevant verification command and check its exit code and decisive output before claiming completion.
- TODOs, unimplemented branches and stubs on the changed path, plus skipped checks needed for its criteria, block completion.
- For a rewrite or refactor, completion includes passing the behavior checks selected before the change (→ [00-principles.md](00-principles.md)).
- Who decides completion, and what they are given to decide it with, is [00-principles.md](00-principles.md) §3 and [20-review-gate.md](20-review-gate.md).
- Integration is verified by the integration runs — one to three per project, each the assembled project's sample run, which belong to no lane and run on the merged head after the last merge (§1). They are one part of the end-to-end condition, whose full definition is [18-work-contract.md](18-work-contract.md) §1.

### 7. Boundary schema check

The schema file sits beside the contract file, and boundaries sharing a sample share it. It pins `$schema` to draft 2020-12, gives arrays `minItems: 1`, closes objects with `required` and `additionalProperties: false`, and states the value set as an `enum`. The sample must pass it at freeze, and the producing lane — named as the boundary's `producer` — carries a criterion that deletes its dump directory, re-runs its sample run, and checks the fresh dump against it — one command, so a stale dump cannot pass.

The check runs through `check-jsonschema`, pinned to one version so the freeze check and every lane measure with the same tool: `uvx check-jsonschema@0.38.0 --schemafile <schema> <instance>`. It reads JSON, YAML and TOML instances — its `--force-filetype` accepts only `json`, `toml` and `yaml` — so a boundary whose payload lands in any other format — JSON Lines, Parquet, CSV — or crosses only as a call has no schema, and stays with review. It exits 1 when an instance fails, and also when the instance file is missing, which is what makes a stage that wrote no dump fail its criterion rather than pass it.

A producing lane's criterion, written in one command:

```
rm -rf runs/sample && uv run python -m parser --limit 100 --dump runs/sample \
  && uvx check-jsonschema@0.38.0 --schemafile .plans/ingest/contracts/parser_out.schema.json runs/sample/parser_out.json
```

The workflow accepts a producer's check only in this form — steps chained with `&&` alone, the pinned tool, a checked file under the directory cleared first, never the sample — and it reads the command's form, not what the shell actually did; a lane that reports a passing criterion it did not run is review's to catch, as with any criterion.

At the base commit this fails because the stage does not exist yet — red under §3's rule for an entry point the change creates, which proves only that the run could not happen. Confirm the schema check itself by sabotage once the stage runs: one row with a value outside the `enum` must fail it.

What the check does not reach stays with review: a symbol's name and signature, which side calls which, whether the sample carries every `enum` member, and a schema too loose to fail anything (`{}` passes every instance). The merged-whole review compares each of these against the contract file.

Measured on 2026-09-11 with 0.38.0: a conforming sample exits 0; a value outside the `enum`, an extra field under `additionalProperties: false`, an empty array under `minItems: 1`, a string where the schema says number, and a missing instance file each exit 1.

Sources: [check-jsonschema usage](https://check-jsonschema.readthedocs.io/en/latest/usage.html), [check-jsonschema on PyPI](https://pypi.org/project/check-jsonschema/), [JSON Schema — array](https://json-schema.org/understanding-json-schema/reference/array), [JSON Schema — object](https://json-schema.org/understanding-json-schema/reference/object) (checked 2026-09-11)
