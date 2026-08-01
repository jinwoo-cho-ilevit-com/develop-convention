---
schema_version: 1
feature: contract-runner
done_level: proven
base: b14bf55

revision:
  kind: breaking
  reason: >-
    The previous text carried 27 criteria and failed its pre-execution gate twice, with the
    second round returning more findings than the first. Most of them were consequences of
    specifying behaviour nobody had run yet, and of a three-lane structure the work does not
    need. This reduces the contract to a checklist over one lane, as 18 prescribes for work of
    this size, and defers the rest to a follow-up contract written with the tool in hand.

criteria:
  - id: C-01
    text: "THE runner SHALL exit non-zero when it cannot parse or validate a contract, and SHALL NOT proceed as though the contract were empty."
    verify: "uv run --group dev pytest templates/scripts/tests -k parse -q"
    kind: functional
    runner: pytest

  - id: C-02
    text: "WHEN a verify command is executed, THE runner SHALL run it as an argument vector rather than through a shell."
    verify: "uv run --group dev pytest templates/scripts/tests -k no_shell -q"
    kind: functional
    runner: pytest

  - id: C-03
    text: "THE runner SHALL take the runner kind from the contract's runner field, never by inspecting the command string."
    verify: "uv run --group dev pytest templates/scripts/tests -k runner_kind -q"
    kind: functional
    runner: pytest

  - id: C-04
    text: "THE red result and the verify result of a criterion SHALL be separate records, and neither phase SHALL write the other's."
    verify: "uv run --group dev pytest templates/scripts/tests -k phase_isolation -q"
    kind: functional
    runner: pytest

  - id: C-05
    text: "THE status command SHALL exit zero only when every criterion is PASS, and SHALL NOT report PASS for a criterion that has no red result unless that criterion is verified by a human."
    verify: "uv run --group dev pytest templates/scripts/tests -k status_gate -q"
    kind: functional
    runner: pytest

  - id: C-06
    text: "WHEN the red check runs, THE runner SHALL execute the new test against a checkout of base, and SHALL report NO-BASELINE rather than a red result when the test cannot run there."
    verify: "uv run --group dev pytest templates/scripts/tests -k red_base -q"
    kind: functional
    runner: pytest

  - id: C-07
    text: "THE runner SHALL NOT count a test that did not execute as a pass."
    verify: "uv run --group dev pytest templates/scripts/tests -k unexecuted_not_pass -q"
    kind: negative
    runner: pytest

  - id: C-08
    text: "THE runner SHALL write REPORT.md, commands.jsonl, commands.log and manifest.json under the feature's artifacts directory, and status SHALL block completion while any of the four is missing."
    verify: "uv run --group dev pytest templates/scripts/tests -k evidence -q"
    kind: functional
    runner: pytest

  - id: C-09
    text: "THE end-to-end test SHALL drive lint, red, verify, human and status in that order against a real repository, and SHALL fail if a later phase erases an earlier phase's result."
    verify: "uv run --group dev pytest templates/scripts/tests/test_e2e.py -q"
    kind: functional
    runner: pytest

  - id: C-10
    text: "THE rules documented in 18 and 19 SHALL match what the runner enforces, judged by someone who wrote neither the runner nor those documents."
    verify: human
    kind: nonfunctional

  - id: C-11
    text: "THE runner SHALL have been run once against a real contract in this repository, and the evidence pack from that run SHALL be usable as a completion report, judged by a person."
    verify: human
    kind: nonfunctional

out_of_scope:
  - result caching for any phase
  - bypass and review-round subcommands
  - the evidence index page, visualization, and code anchors
  - Windows support
  - generating rule excerpts, and any change to the claude-config repository
  - migrating contracts written against the previous schema
  - the CI documents job, the CI secret scan, and any change to the shipped templates
  - concurrency across lanes, resumption, artifact retention, and the configuration file surface
---

# contract-runner

## Background

The previous implementation was withdrawn after four review lanes found seven blockers in it,
recorded in `a078b30`. The core of it was that the red gate did not hold: the verify phase
overwrote the red phase's record, and status accepted a criterion that had never been red-checked.
Its own evidence pack was the proof — five criteria with no red key, and status exited zero.

The withdrawn code and its 46 tests are readable at `170aa61:templates/scripts/contract.py` and
`170aa61:templates/scripts/tests/`. Read it as a catalogue of failure modes and of capabilities
this contract deliberately leaves out, not as a design to copy.

The rules the runner must enforce are [18-work-contract.md](conventions/18-work-contract.md) and
[19-evidence.md](conventions/19-evidence.md); the red-check definitions it must follow are in
[06-testing-verification.md](conventions/06-testing-verification.md) §3.

## Approach

This is a walking skeleton: one criterion travels through lint, red, verify, human and status,
and an evidence pack comes out the other end. `C-01` to `C-08` are the properties that have to
hold for that path to mean anything, `C-09` is the path itself, and `C-10` and `C-11` are the two
judgments a machine cannot make.

Two earlier attempts at this contract specified how the tool should work — the masking scheme,
the worktree mechanism, the exit-code vocabulary — and both failed their gate on contradictions
between clauses about behaviour nobody had run. The criteria here state observable outcomes and
leave the mechanism to the implementation and to its code review. Everything deferred is listed
in `out_of_scope` and belongs to a follow-up contract, which will be written against a tool that
exists rather than against a guess.

One lane does the work, so there is no `lanes` block: 18 adds that apparatus only for two or more
parallel lanes, and the previous structure spent more of its defect budget defending the
apparatus than the tool.

## Schema

The runner reads one field the schema of record does not yet document: `runner`, which is
`pytest` or `command` and is required unless `verify` is `human`. Adding it to
`templates/contract.md` is part of the work; whether it landed is part of what `C-10` judges.
Nothing else in `templates/contract.md` changes.

## Why `done_level: proven`

A module that executes commands and writes files has external effect, which puts it at `proven`
under the size-by-reversibility rule regardless of how small it is. `proven` asks for integration
smoke plus one run on real data: `C-09` is the smoke, `C-11` is the real run. `C-11` is a human
criterion because 19 gitignores the artifacts directory, so the evidence pack it produces cannot
be committed and checked mechanically.

## Review tooling

20 requires the review tool to be chosen before development starts and recorded with the
decomposition.

| When | Lanes | Tool |
|---|---|---|
| Before execution | criteria, project, absence — over this contract | at least one on `cursor-agent --mode ask`, the rest in-session |
| During execution | Stop gate per turn | Path A, Codex plugin |
| After development | module, project, absence, security — over the diff | at least one on `cursor-agent --mode ask`, the rest in-session |

The security lane is not optional: the runner executes commands taken from a file it did not
write and handles secrets while masking. Model ids are resolved at use time with
`cursor-agent models`, never pinned here.

The pre-execution gate's job is to find contradictions between criteria and criteria that cannot
be achieved as scoped. An undefined term in behaviour that does not exist yet is cheaper to
settle in review of the implementation than in another round over this file.

## Notes

**Unknowns being carried.** Whether a worktree per red check is fast enough to run rather than
cache — if it is not, the answer is to make it faster, since a cache is what broke the last
version. Whether the four evidence artifacts need a reporting layer of their own; the withdrawn
implementation produced them from one file.

**Abandonment.** The revert surface is `templates/scripts/` and the `runner` row in
`templates/contract.md`. The toolchain files predate this work and stay. `a078b30` is the model:
one revert commit whose message records the confirmed blockers.

**Two rounds of findings are deferred, not dismissed.** The gate over the previous text produced
a long list of real gaps — the configuration surface as a second way past containment, lane
scoping, exit-code vocabulary, partial-failure and resumption behaviour, artifact retention, the
defect the shipped templates still carry. They are in `out_of_scope` here and go into the
follow-up contract, where most of them can be settled by observation instead of guessing.
