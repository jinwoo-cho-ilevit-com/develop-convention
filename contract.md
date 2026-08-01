---
schema_version: 1
feature: contract-runner
done_level: proven
base: 95c1f81

revision:
  kind: breaking
  reason: >-
    The third gate returned one blocker, reached by all three lanes from different directions:
    the schema of record did not document the `runner` field, and out_of_scope forbade adding it.
    That is settled at base 95c1f81, before execution, rather than by wording. This revision also
    closes four coverage gaps the lanes named — feature validation, a test that passes at base,
    the human-verdict record, and masking — and fixes the guard exemption in C-05. Breaking
    rather than additive because it edits the text of C-05, C-10 and C-11; no lane had started,
    so the restart 18 §6 prescribes costs nothing.

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
    text: "THE status command SHALL exit zero only when every criterion is PASS, and SHALL NOT report PASS for a criterion that has no red result unless that criterion is verified by a human or declared a guard."
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
    text: "THE description of the runner in 18 and 19 SHALL cover exactly what this contract's machine criteria require, describing no rule the runner does not implement and leaving no implemented rule undescribed, judged by someone who wrote neither the runner nor those documents."
    verify: human
    kind: nonfunctional

  - id: C-11
    text: "THE runner SHALL have been run once against a real contract in this repository, producing all four evidence artifacts for that run, confirmed by a person."
    verify: human
    kind: nonfunctional

  - id: C-12
    text: "THE runner SHALL reject a feature name containing anything other than lowercase letters, digits and hyphens, and SHALL confine every file it writes to the artifacts directory inside the repository."
    verify: "uv run --group dev pytest templates/scripts/tests -k containment -q"
    kind: functional
    runner: pytest

  - id: C-13
    text: "WHEN a new test passes at base, THE red check SHALL record that the test proves nothing and SHALL NOT record a red result for it."
    verify: "uv run --group dev pytest templates/scripts/tests -k red_passes_at_base -q"
    kind: functional
    runner: pytest

  - id: C-14
    text: "THE runner SHALL hold a human criterion at PENDING-HUMAN until a verdict carrying its author and its timestamp is recorded."
    verify: "uv run --group dev pytest templates/scripts/tests -k human_verdict -q"
    kind: functional
    runner: pytest

  - id: C-15
    text: "THE runner SHALL mask secret values in the command line, the environment and the output before writing any of them to an artifact."
    verify: "uv run --group dev pytest templates/scripts/tests -k masking -q"
    kind: functional
    runner: pytest

  - id: C-16
    text: "THE REPORT.md from the run in C-11 SHALL be readable as a completion report without reading the runner's code, judged by a person."
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
overwrote the red phase's record, and status accepted a criterion that had never been
red-checked. Its own evidence pack was the proof — five criteria with no red key, and status
exited zero.

The withdrawn code and its 46 tests are readable at `170aa61:templates/scripts/contract.py` and
`170aa61:templates/scripts/tests/`. Read it as a catalogue of failure modes and of capabilities
this contract deliberately leaves out, not as a design to copy.

The rules the runner must enforce are [18-work-contract.md](conventions/18-work-contract.md) and
[19-evidence.md](conventions/19-evidence.md); the red-check definitions it must follow are in
[06-testing-verification.md](conventions/06-testing-verification.md) §3.

## Approach

This is a walking skeleton: one criterion travels through lint, red, verify, human and status,
and an evidence pack comes out the other end. `C-01` to `C-08` and `C-12` to `C-15` are the
properties that have to hold for that path to mean anything, `C-09` is the path itself, and
`C-10`, `C-11` and `C-16` are the judgments a machine cannot make.

Two earlier attempts specified how the tool should work — the masking scheme, the worktree
procedure, the exit-code vocabulary — and both failed their gate on contradictions between
clauses about behaviour nobody had run. The criteria here state observable outcomes and leave the
mechanism to the implementation and its code review. Everything deferred is in `out_of_scope` and
belongs to a follow-up contract written against a tool that exists.

One lane does the work, so there is no `lanes` block: 18 adds that apparatus only for two or more
parallel lanes, and the previous structure spent more of its defect budget defending the
apparatus than the tool.

Four criteria trace to the red gate specifically, which is what failed last time. `C-04` keeps
the phases from overwriting each other, `C-05` keeps status from passing an unchecked criterion,
`C-06` covers a check that cannot run and `C-13` a check that runs and passes at base. 06 §3
splits the outcomes exactly that way, and the withdrawn version got two of the three wrong.

## Schema

The runner reads one field beyond what earlier contracts used: `runner`, which is `pytest` or
`command` and is required unless `verify` is `human`. It is already documented in
`templates/contract.md` as of `95c1f81`, which is this contract's `base`, so the work changes no
shipped template.

For `C-15`, the set of values counted as secret is a pattern file the runner ships — credential
shapes plus the names of secret-bearing environment variables — and the criterion is tested with
a fixture carrying a planted credential of every shape in it. A list that can be read and
extended is a weaker claim than "mask secrets" and a far more testable one.

## Why `done_level: proven`

A module that executes commands and writes files has external effect, which puts it at `proven`
under the size-by-reversibility rule regardless of how small it is. `proven` asks for integration
smoke plus one run on real data: `C-09` is the smoke, `C-11` is the real run. `C-11` and `C-16`
are human because 19 gitignores the artifacts directory, so the pack cannot be committed and
checked mechanically.

## Review tooling

| When | Lanes | Tool |
|---|---|---|
| Before execution | criteria, project, absence — over this contract | at least one external, the rest in-session |
| During execution | Stop gate per turn | Path A, Codex plugin |
| After development | module, project, absence, security — over the diff | at least one external, the rest in-session |

The security lane is not optional: the runner executes commands taken from a file it did not
write and handles secrets while masking.

20 asks for at least one lane on a different vendor's model family, and to record the fact rather
than drop the lane where only one family is reachable. Recording it: through `cursor-agent` on
this machine, only the `gpt-5.3-codex` family answers without Max Mode — `gpt-5.6-sol-xhigh`,
`cursor-grok-4.5-high` and `cursor-grok-4.5-low` were all refused during the pre-execution gate.
Two families, not three. Model ids are resolved at use time with `cursor-agent models`.

## Notes

**Unknown being carried.** Whether a worktree per red check is fast enough to run every time is
unknown. If it is not, the answer is to make it faster: caching is what broke the previous
version, and `out_of_scope` excludes it from this one.

**Abandonment trigger.** Withdraw rather than patch if a review of the implementation confirms a
blocker in the red gate itself — the properties `C-04`, `C-05`, `C-06` and `C-13` hold — for a
second time. The previous withdrawal was decided ad hoc after a full review round had already
been spent arguing about patches.

**Abandonment surface.** `templates/scripts/`, plus `git worktree prune` for base checkouts a
crashed red check left registered. The toolchain files and the `runner` row in the schema predate
this work and stay. `contract.md` is deleted on completion either way (18 §6). `a078b30` is the
model: one revert commit whose message records the confirmed blockers.

**Deferred, not dismissed.** Three gate rounds produced a long list of real gaps — the
configuration surface as a second way past containment, lane scoping, exit-code vocabulary,
partial-failure and resumption behaviour, artifact retention, the defect the shipped templates
still carry, and the `documents` CI job that `a078b30` removed. They are in `out_of_scope` here
and go into the follow-up contract, where most can be settled by observation instead of guessing.
