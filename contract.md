---
schema_version: 1
feature: contract-runner
done_level: proven

criteria:
  - id: C-01
    text: "THE runner SHALL reject a contract it cannot parse or validate, with a non-zero exit, and SHALL NOT treat an unreadable contract as an empty one."
    verify: "uv run --group dev pytest templates/scripts/tests -k parse -q"
    kind: functional
    runner: pytest

  - id: C-02
    text: "WHEN a criterion's verify command is executed, THE runner SHALL run it as an argument vector, never through a shell."
    verify: "uv run --group dev pytest templates/scripts/tests -k no_shell -q"
    kind: functional
    runner: pytest

  - id: C-03
    text: "THE runner SHALL take the runner kind from the contract, never by inspecting the command string."
    verify: "uv run --group dev pytest templates/scripts/tests -k runner_kind -q"
    kind: functional
    runner: pytest

  - id: C-04
    text: "WHEN no test was written, THE red check SHALL report NO-BASELINE and SHALL NOT report a pass, for every declared runner kind."
    verify: "uv run --group dev pytest templates/scripts/tests -k red -q"
    kind: functional
    runner: pytest

  - id: C-05
    text: "THE verify phase SHALL NOT alter a red result, and status SHALL block a criterion that has no red result unless it is a guard or a human criterion."
    verify: "uv run --group dev pytest templates/scripts/tests -k state_isolation -q"
    kind: functional
    runner: pytest

  - id: C-06
    text: "WHEN two lanes run concurrently, THE runner SHALL NOT lose either lane's result."
    verify: "uv run --group dev pytest templates/scripts/tests -k concurrent -q"
    kind: functional
    runner: pytest

  - id: C-07
    text: "THE runner SHALL confine every file it writes to the artifacts directory inside the repository, and SHALL reject a feature name that is not a plain slug."
    verify: "uv run --group dev pytest templates/scripts/tests -k containment -q"
    kind: functional
    runner: pytest

  - id: C-08
    text: "THE runner SHALL NOT record command output unless the contract opts in, and SHALL mask secret-shaped values in whatever it does record."
    verify: "uv run --group dev pytest templates/scripts/tests -k output_optin -q"
    kind: functional
    runner: pytest

  - id: C-09
    text: "THE end-to-end test SHALL drive lint, red, verify, human, and status in that order against a real repository, and SHALL fail if a later phase erases an earlier phase's result."
    verify: "uv run --group dev pytest templates/scripts/tests/test_e2e.py -q"
    kind: functional
    runner: pytest

  - id: C-10
    text: "THE secret scan in CI SHALL detect a committed credential."
    verify: "uv run --group dev pytest templates/scripts/tests -k secret_scan_config -q"
    kind: functional
    runner: pytest

  - id: C-11
    text: "THE toolkit SHALL pass lint and format checks."
    verify: "uv run --group dev ruff check . && uv run --group dev ruff format --check ."
    kind: functional
    runner: command
    red: guard

  - id: C-12
    text: "THE runner SHALL NOT reintroduce a result cache."
    verify: "! grep -rq 'conv-cache' templates/scripts/"
    kind: negative
    runner: command
    red: guard

  - id: C-13
    text: "THE documented rules SHALL match what the runner enforces, checked against docs 18 and 19 by someone who did not write either."
    verify: human
    kind: nonfunctional

out_of_scope:
  - result caching for the red check
  - bypass and review-round subcommands
  - the evidence index page, visualization, and code anchors
  - Windows support
  - generating rule excerpts, and any change to the claude-config repository

lanes:
  - id: runner
    owns: ["templates/scripts/"]
    criteria: [C-01, C-02, C-03, C-04, C-05, C-06, C-07, C-08, C-09, C-11, C-12]
    model_tier: top
  - id: ci
    owns: [".github/"]
    criteria: [C-10]
    model_tier: mid

sequential_owner: ["pyproject.toml", "uv.lock", ".pre-commit-config.yaml"]

integration:
  owner: runner
  order: [runner, ci]
  criteria: [C-09]
---

# contract-runner

## Background

The previous runner was withdrawn after four review lanes found seven blockers in it. Six of
them were state and execution defects, not missing features: the verify phase overwrote the red
phase's result, status accepted a criterion that had never been red-checked, the red cache keyed
on everything except the test content, the runner decided it was looking at pytest by searching
the command string for the word, concurrent lanes overwrote each other, and the feature name went
into a filesystem path unchecked.

Patching those one at a time would leave the shapes that produced them. This rebuild removes the
shapes.

The withdrawn implementation and its 46 tests are recoverable:
`git show 170aa61:templates/scripts/contract.py`, `git show 170aa61:templates/scripts/tests/`.
Commit `a078b30` records why it was withdrawn and lists the blockers. Read it as a source of
failure modes to avoid, not as a starting point — several of them are consequences of its shape.

The rules the runner must enforce are [18-work-contract.md](conventions/18-work-contract.md) and
[19-evidence.md](conventions/19-evidence.md); the test layers it must satisfy are in
[06-testing-verification.md](conventions/06-testing-verification.md).

## Design decisions that remove blockers rather than patch them

**No shell.** A verify command is parsed into an argument vector and executed directly. Shell
metacharacters stop being an execution path, and the program being run becomes inspectable —
which is also what makes the next decision possible.

**The contract declares the runner kind.** `runner: pytest` or `runner: command`, never inferred
from the command text. Deciding "this is pytest" by substring made two unrelated blockers: a
`grep` command containing the word was classified as pytest, and a project not using pytest got
its red check judged by the wrong rules.

**One writer per file.** Each phase writes `state/<criterion>.<phase>.json` and reads the others.
No phase can erase another's result because no phase opens another's file, and two lanes writing
different criteria never touch the same path.

**No cache.** The cache existed to save time and cost a blocker: a weakened test kept its earlier
pass. Correctness first; if the red check turns out to be too slow in practice, cache it then,
with evidence and a key that includes the test content.

**Output recording is opt-in.** By default the runner records the command, its exit code, and the
resulting status — not the output. A contract that wants output sets `record_output: true` per
criterion. The leak channel becomes something you switch on deliberately rather than something you
remember to mask.

**Containment is checked, not assumed.** `feature` must be a plain slug, and every write path is
resolved and confirmed to sit inside the artifacts directory.

## Why `done_level: proven`

This introduces a module with external effect — it executes commands and writes files. Under the
size-by-reversibility rule that is `proven`: integration smoke plus one run on real data. The
integration criterion is `C-09`, and the real-data run is this repository's own convention set.

## The end-to-end criterion

`C-09` exists because its absence is what let the previous version ship broken. Every phase had a
unit test and all of them passed; nothing ran the phases in the order the documents prescribe, so
nobody noticed that `verify` deleted what `red` had written. The end-to-end test drives the real
sequence and asserts that each phase's result survives the ones after it.

## Notes

`C-13` is a human judgment: whether docs 18 and 19 describe what the runner actually does. The
previous version's documents specified fields nothing produced, which is the same failure in the
other direction.
