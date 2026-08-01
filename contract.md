---
schema_version: 1
feature: contract-runner
done_level: proven
base: 951de38

revision:
  kind: breaking
  reason: >-
    Three review lanes run over the previous text before any code was written returned nine
    blockers. Three of them (no red baseline mechanism, no status exit gate, no evidence
    artifacts) needed criteria that did not exist rather than edits to ones that did, and the
    lane structure itself produced six ownership gaps. No implementation existed, so the
    restart cost was zero.

criteria:
  - id: C-01
    text: "THE runner SHALL reject a contract it cannot parse or validate, with a non-zero exit, and SHALL NOT treat an unreadable contract as an empty one."
    verify: "uv run --group dev pytest templates/scripts/tests -k parse -q"
    kind: functional
    runner: pytest

  - id: C-02
    text: "WHEN a verify command is executed, THE runner SHALL run it as an argument vector and never through a shell, and SHALL reject at lint time any verify command containing a shell metacharacter or written as a multi-line block."
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
    verify: "uv run --group dev pytest templates/scripts/tests -k red_no_baseline -q"
    kind: functional
    runner: pytest

  - id: C-05
    text: "THE verify phase SHALL NOT alter a red result, and status SHALL block a criterion that has no red result unless it is a guard or a human criterion."
    verify: "uv run --group dev pytest templates/scripts/tests -k state_isolation -q"
    kind: functional
    runner: pytest

  - id: C-06
    text: "THE runner SHALL NOT lose or truncate a recorded result, whether two lanes write concurrently or a run dies between opening a file and completing the write."
    verify: "uv run --group dev pytest templates/scripts/tests -k durability -q"
    kind: functional
    runner: pytest

  - id: C-07
    text: "THE runner SHALL confine every file it writes to the artifacts directory, resolved and confirmed to sit inside the repository whether the path came from the default or from configuration, SHALL reject a feature name that is not a plain slug, and SHALL treat the red check's base checkout as the single declared exception."
    verify: "uv run --group dev pytest templates/scripts/tests -k containment -q"
    kind: functional
    runner: pytest

  - id: C-08
    text: "THE runner SHALL record every executed command, its exit code and its full output by teeing real execution, SHALL mask secret values in the command line, the environment and the output before anything is written, and SHALL mark where output was truncated."
    verify: "uv run --group dev pytest templates/scripts/tests -k evidence_record -q"
    kind: functional
    runner: pytest

  - id: C-09
    text: "THE end-to-end test SHALL drive lint, red, verify, human and status in that order against a real repository, and SHALL fail if a later phase erases an earlier phase's result."
    verify: "uv run --group dev pytest templates/scripts/tests/test_e2e.py -q"
    kind: functional
    runner: pytest

  - id: C-10
    text: "THE secret scan in this repository's CI SHALL detect a committed credential, and SHALL fail if the scan is configured so that it inspects no files."
    verify: "uv run --group dev pytest .github/tests -k secret_scan -q"
    kind: functional
    runner: pytest

  - id: C-11
    text: "THE toolkit SHALL pass lint and format checks."
    verify:
      - "uv run --group dev ruff check ."
      - "uv run --group dev ruff format --check ."
    kind: functional
    runner: command
    red: guard

  - id: C-12
    text: "THE red check SHALL re-execute its command on every run, and THE runner SHALL NOT read or write a stored verdict for any phase."
    verify: "uv run --group dev pytest templates/scripts/tests -k red_no_cache -q"
    kind: negative
    runner: pytest

  - id: C-13
    text: "THE documented rules SHALL match what the runner enforces, checked against docs 18 and 19 by someone who did not write either."
    verify: human
    kind: nonfunctional

  - id: C-14
    text: "THE schema in templates/contract.md and the field set the runner reads SHALL name the same fields, checked in both directions."
    verify: "uv run --group dev pytest templates/scripts/tests -k schema_agreement -q"
    kind: functional
    runner: pytest

  - id: C-15
    text: "WHEN a criterion declares a list of verify commands, THE runner SHALL run them in order and SHALL fail the criterion at the first command whose exit code does not equal its expect_exit, without running the rest."
    verify: "uv run --group dev pytest templates/scripts/tests -k verify_list -q"
    kind: functional
    runner: pytest

  - id: C-16
    text: "THE lint command SHALL reject a contract that violates any rule in the enumerated lint set, and SHALL name the violated rule in its output."
    verify: "uv run --group dev pytest templates/scripts/tests -k lint_rules -q"
    kind: functional
    runner: pytest

  - id: C-17
    text: "WHEN the red check runs, THE runner SHALL execute each new test against a checkout of base with only the declared test files brought forward, and SHALL report NO-BASELINE when that checkout cannot be made or the command cannot run inside it."
    verify: "uv run --group dev pytest templates/scripts/tests -k red_base -q"
    kind: functional
    runner: pytest

  - id: C-18
    text: "WHEN a new test passes at base, THE red check SHALL record that the test proves nothing and SHALL NOT record a red result for it."
    verify: "uv run --group dev pytest templates/scripts/tests -k red_passes_at_base -q"
    kind: functional
    runner: pytest

  - id: C-19
    text: "THE status command SHALL exit zero only when every criterion is PASS, and SHALL exit non-zero when any criterion is FAIL, NO-BASELINE or PENDING-HUMAN."
    verify: "uv run --group dev pytest templates/scripts/tests -k status_gate -q"
    kind: functional
    runner: pytest

  - id: C-20
    text: "THE runner SHALL write REPORT.md, commands.jsonl, commands.log and manifest.json under the feature's artifacts directory, SHALL record every status as one of the four status words and never as a symbol, and status SHALL block completion when any of the four files is missing."
    verify: "uv run --group dev pytest templates/scripts/tests -k evidence_artifacts -q"
    kind: functional
    runner: pytest

  - id: C-21
    text: "THE manifest SHALL record the commit the run was made against, whether the tree was clean at the time, the human verdicts, the bypass history, and the timestamps created_at, verify_runs[].at and review_rounds."
    verify: "uv run --group dev pytest templates/scripts/tests -k manifest -q"
    kind: functional
    runner: pytest

  - id: C-22
    text: "THE runner SHALL hold a human criterion at PENDING-HUMAN until a verdict carrying its author and its timestamp is recorded, at every done level."
    verify: "uv run --group dev pytest templates/scripts/tests -k human_verdict -q"
    kind: functional
    runner: pytest

  - id: C-23
    text: "THE runner SHALL abandon a verify command that exceeds the configured timeout and record it as FAIL, and SHALL NOT let a command inherit the runner's standard input."
    verify: "uv run --group dev pytest templates/scripts/tests -k timeout -q"
    kind: functional
    runner: pytest

  - id: C-24
    text: "THE documents job in CI SHALL fail when a convention doc does not open with Core Rules, when a doc-map link does not resolve, or when tool-call residue is present."
    verify: "uv run --group dev pytest .github/tests -k documents_job -q"
    kind: functional
    runner: pytest

  - id: C-25
    text: "THE contract template this repository ships SHALL pass the runner's own lint once its placeholders are filled, and SHALL fail lint while they are not."
    verify: "uv run --group dev pytest templates/scripts/tests -k template_lint -q"
    kind: functional
    runner: pytest

  - id: C-26
    text: "THE secret scan the templates ship SHALL detect a planted credential in a repository bootstrapped from them."
    verify: "uv run --group dev pytest templates/scripts/tests -k template_secret_scan -q"
    kind: functional
    runner: pytest

  - id: C-27
    text: "THE runner SHALL complete a full run against this repository's own contract and produce the four evidence artifacts for it."
    verify: "uv run --group dev pytest templates/scripts/tests -k real_data -q"
    kind: functional
    runner: pytest

out_of_scope:
  - result caching for any phase
  - bypass and review-round subcommands
  - the evidence index page, visualization, and code anchors
  - Windows support
  - generating rule excerpts, and any change to the claude-config repository
  - changes to conventions docs other than describing runner behaviour in 18 and 19
  - migrating contracts written against the previous schema
  - any file not named in a lane's owns or in sequential_owner

lanes:
  - id: runner
    owns: ["templates/scripts/"]
    criteria: [C-01, C-02, C-03, C-04, C-05, C-06, C-07, C-08, C-11, C-12, C-14, C-15, C-16, C-17, C-18, C-19, C-20, C-21, C-22, C-23, C-25, C-26, C-27]
    model_tier: top
  - id: ci
    owns: [".github/"]
    criteria: [C-10, C-24]
    model_tier: mid
  - id: docs
    owns: ["conventions/"]
    criteria: [C-13]
    model_tier: mid

sequential_owner:
  - contract.md
  - .gitignore
  - .python-version
  - pyproject.toml
  - uv.lock
  - .pre-commit-config.yaml
  - README.md
  - CLAUDE.md
  - templates/contract.md
  - templates/AGENTS.md
  - templates/pyproject.toml
  - templates/.pre-commit-config.yaml
  - templates/skills/conv-init/SKILL.md

integration:
  owner: runner
  order: [runner, ci, docs]
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
It is also the record of what a second withdrawal would cost: fifteen files and 1682 lines.

The rules the runner must enforce are [18-work-contract.md](conventions/18-work-contract.md) and
[19-evidence.md](conventions/19-evidence.md); the test layers it must satisfy are in
[06-testing-verification.md](conventions/06-testing-verification.md).

## Approach

Three lanes own three disjoint directory prefixes and nothing else. Every file the work touches
that is not under one of those prefixes is named in `sequential_owner` and written by the
integration owner. The previous text tried to give scattered single files to lanes and produced
six places where a needed change had no author — including this contract itself, which meant
nobody was authorised to update `base`.

The criteria fall into six groups: contract handling (`C-01`, `C-02`, `C-03`, `C-14`, `C-16`),
execution (`C-15`, `C-23`), the red check (`C-04`, `C-12`, `C-17`, `C-18`), state and status
(`C-05`, `C-06`, `C-19`), evidence (`C-08`, `C-20`, `C-21`, `C-22`), and the surfaces this
repository ships to others (`C-10`, `C-24`, `C-25`, `C-26`). `C-09` and `C-27` sit above them.

## Design decisions that remove blockers rather than patch them

**No shell.** A verify command is parsed into an argument vector and executed directly. Shell
metacharacters stop being an execution path, and the program being run becomes inspectable —
which is also what makes the next decision possible. `C-02` also rejects such commands at lint
time rather than silently passing `&&` to a program as an argument.

**Shell operators become schema.** Removing the shell removes `&&` and `!` with it, so the two
jobs they were doing move into the contract instead. `verify:` accepts a list of commands run in
order, and `expect_exit:` declares the code a command must return, defaulting to `0`. Both are
declared rather than parsed out of the command text, for the same reason `C-03` exists.

**The contract declares the runner kind.** `runner: pytest` or `runner: command`, never inferred
from the command text. Deciding "this is pytest" by substring made two unrelated blockers: a
`grep` command containing the word was classified as pytest, and a project not using pytest got
its red check judged by the wrong rules.

**One writer per file.** Each phase writes `state/<criterion>.<phase>.json` and reads the others.
No phase can erase another's result because no phase opens another's file, and two lanes writing
different criteria never touch the same path. Writes are atomic, so a run that dies mid-write
leaves the previous content rather than a truncated file (`C-06`).

**No stored verdict anywhere.** The old cache existed to save time and cost a blocker: a weakened
test kept its earlier pass. `C-12` is written against the behaviour rather than against a
directory name, because the previous wording would have passed a cache that was merely renamed.

**Evidence is not optional.** The runner tees real execution into `commands.jsonl` and
`commands.log`, writes `REPORT.md` and `manifest.json`, and status refuses to complete when any
of the four is missing. This reverses the previous draft, which made output recording opt-in —
see "Why the evidence decision changed" below.

**Containment is checked, not assumed.** `feature` must be a plain slug, and every write path is
resolved and confirmed to sit inside the artifacts directory — including when the directory came
from configuration, which was the second way out that the previous text did not name.

## The red check needs a base it can actually reach

`C-17` exists because the previous text said the red check must happen and never said how. A new
test cannot be run at `base` by running it where it sits: at `base` the test does not exist. The
withdrawn implementation solved this with a detached worktree at `base` in a temporary directory
and `git checkout <head> -- <test files>` to bring only the tests forward, and its comment
recorded why. That mechanism is now a criterion instead of an implementation detail.

Two consequences the previous text left contradictory:

- The worktree lives outside the repository, which `C-07` otherwise forbids. It is now the single
  declared exception, and `C-07` tests that it is the only one.
- `base` must be a commit where the toolchain exists. At `c8899d7` there was no root
  `pyproject.toml`, so every `uv run` command was an unavailable command — which
  [06](conventions/06-testing-verification.md) §3 defines as NO-BASELINE, not red. `base` is now
  `951de38`, where the toolchain is present and `templates/scripts/` still is not, so a new test
  fails there for the reason 06 §3 calls red: it cannot import a module that does not exist yet.

`C-18` covers the row of 06 §3 that neither the previous text nor the withdrawn implementation
addressed: a test that *passes* at base. Without it, `assert True` earns a red result and closes
a criterion.

## Why the evidence decision changed

The previous draft made output recording opt-in, on the reasoning that a leak channel should be
switched on deliberately. That conflicts with a Core Rule of 19, which requires the full output
of every executed command to be recorded by teeing real execution, and with 19 §3, which requires
masking to cover the command line and the environment rather than only the output. A runner
built to the previous draft would have violated 19 by default, and `C-13` — whether the documents
describe what the runner does — could not have passed without amending 19, which is out of scope.

`C-08` now follows 19. The masking that made opt-in attractive becomes mandatory rather than
avoidable, and "secret-shaped" is no longer left to the reader: the runner ships one file holding
the credential patterns and the secret-bearing environment-variable names, and `C-08` is tested
with a fixture carrying a planted credential of every shape in it. A pattern set that can be read
and extended is a weaker claim than "mask secrets" and a much more testable one.

## Contract fields the runner reads

18 §3 delegates the field list to `templates/contract.md`, which is why that file is in
`sequential_owner` rather than left to drift. `C-14` checks the two against each other in both
directions — the previous version checked only that the documentation covered the runner, which
would have let a documented field the runner ignores sit there indefinitely.

| Field | Values | Default |
|---|---|---|
| `verify` | one command, a list of commands, or `human` | required |
| `runner` | `pytest` or `command` | required unless `verify: human` |
| `expect_exit` | the exit code each command must return | `0` |
| `red` | `required` or `guard` | `required`, and not applicable to a human criterion |
| `hermetic` | `false` excludes the criterion from the red check | `true` |

No criterion here is non-hermetic — none touches the network, a database or a port — so
`hermetic` appears nowhere in the front matter and every criterion takes the default.

## Review tooling

20 requires the review tool to be chosen before development starts and recorded alongside the
decomposition, so it is recorded here rather than in the front matter — it is a routing decision,
not a field the runner reads.

| When | Lanes | Tool |
|---|---|---|
| Before execution | criteria, project, absence — over this contract, since the contract is the plan | one lane on `cursor-agent --mode ask`, the rest in-session |
| During execution | Stop gate per turn | Path A, Codex plugin |
| After development | module, project, absence, **security** — over the diff | at least one on `cursor-agent --mode ask`, the rest in-session |

The security lane is not optional here: the runner parses a contract it did not write, executes
commands taken from it, resolves paths from it, and handles secrets while masking. 20 triggers a
security lane on exactly those. Model ids are resolved at use time with `cursor-agent models`,
never pinned here.

## Why `done_level: proven`

This introduces a module with external effect — it executes commands and writes files. Under the
size-by-reversibility rule that is `proven`: integration smoke plus one run on real data. The
integration criterion is `C-09`; the real-data run is `C-27`, which names this repository's own
contract rather than leaving "a real repository" to be satisfied by a fixture.

## Notes

**Unknowns.** Two are being carried rather than resolved first. Whether `git worktree add` per
red check is fast enough to be run rather than cached is unknown, and the cheapest wrong
assumption if it is not: the answer is to make it faster, not to reintroduce a cache, since
`C-12` is what a cache broke last time. Whether the four evidence artifacts can be produced
without the runner growing a reporting layer of its own is unknown; the withdrawn implementation
managed it in one file.

**Abandonment.** If this is withdrawn again, the revert surface is `templates/scripts/`,
`.github/`, and the `sequential_owner` list, minus the four toolchain files, which predate the
work and stay. `a078b30` is the model: revert as one commit, record the confirmed blockers in its
message, and leave the branch history reachable.

**`C-13` is a human judgment** — whether docs 18 and 19 describe what the runner actually does.
The previous version's documents specified fields nothing produced, which is the same failure in
the other direction, and `C-14` now guards that direction mechanically so `C-13` is left with the
part a string comparison cannot settle. Its judge must be someone who did not write the prose,
which excludes the docs lane.

**Deviations recorded.** `sequential_owner` in 18 is described for lock files, migrations and
generated files; it is used here for every cross-cutting single file, because the alternative was
putting file paths in `owns`, which 18 restricts to directory prefixes. Whether 18 should say so
is a question for a later contract, not this one.
