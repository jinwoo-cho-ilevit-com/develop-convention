---
schema_version: 1
feature: runner-followup
done_level: proven
base: 7d67041
criteria:
  - id: C-01
    text: >-
      A `verify` written as a list SHALL be executed verbatim as the argument vector, with
      no splitting and no operator check, so that a command needing a literal `;` or `|`
      can be stated at all.
    verify: uv run --group dev pytest templates/scripts/tests -k verify_list -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      WHEN a contract repeats a key, THE runner SHALL refuse it. PyYAML resolves a
      duplicate to the last occurrence, so a contract can state one `verify` and run
      another with nothing reporting the difference.
    verify: uv run --group dev pytest templates/scripts/tests -k duplicate_key -q
    runner: pytest
    kind: functional

  - id: C-03
    text: >-
      THE runner SHALL refuse a criterion id too long to become a filename, rather than
      accepting it and failing later with an unhandled OSError, which exit code 3 reports
      as the runner having broken.
    verify: uv run --group dev pytest templates/scripts/tests -k id_length -q
    runner: pytest
    kind: functional

  - id: C-04
    text: >-
      WHEN collection fails at head, THE recorded note SHALL say so, rather than
      "the criterion selects no test" — which describes a different cause and sends a
      reader looking in the wrong place.
    verify: uv run --group dev pytest templates/scripts/tests -k collection_failure_note -q
    runner: pytest
    kind: functional

  - id: C-05
    text: >-
      THE manifest SHALL carry `verify_runs[].at`, which 19 §4 requires and names as the
      field without which lead time per contract cannot be derived at all.
    verify: uv run --group dev pytest templates/scripts/tests -k verify_runs -q
    runner: pytest
    kind: functional

  - id: C-06
    text: >-
      THE runner SHALL accept `done_level: bypassed` together with a recorded reason, and
      SHALL keep refusing it without one — 18 and 19 both require a bypass to carry a
      reason, and refusing the level outright was a stand-in for having nowhere to put it.
    verify: uv run --group dev pytest templates/scripts/tests -k bypass -q
    runner: pytest
    kind: functional

  - id: C-07
    text: >-
      THE documents describing the runner SHALL describe what it now does — the list form,
      the duplicate-key refusal, the id bound, `verify_runs[].at`, and the bypass record —
      judged by someone who wrote neither the runner nor those documents.
    verify: human
    kind: nonfunctional

  - id: C-08
    text: >-
      THE runner SHALL NOT lose a behaviour this work does not name: the existing suite
      passes unchanged except where a criterion above requires a change, and this
      repository's own contracts still run.
    verify: uv run --group dev pytest -q
    runner: pytest
    kind: negative
    red: guard

out_of_scope:
  - "the `lanes` subcommand, and any handling of lanes/sequential_owner/integration"
  - a configuration surface, concurrency, resumption, and artifact retention
  - "`review_rounds`, which belongs to a review subcommand this runner does not have"
  - making `created_at` a creation time rather than a render time — it is disclosed in
    19 §6 and fixing it needs a run log this contract does not add
  - the pytest criterion pointing outside the repository root, contrived enough that
    round 11 declined to count it
---

# runner-followup

## Background

`adr/0001-contract-runner.md` records what the runner contract deferred and why. This
takes the part of that list which closes a defect or satisfies a rule 19 already states,
and leaves the part that adds a feature.

The list form for `verify` is the reason to do this now. Five separate defects in the
first contract came from one decision — that a command is stored as a shell-ish string the
runner has to parse: reading the runner kind from a substring, an operator list that
missed the merged forms, an over-refusal that blocked `find … -exec … ';'`, a `#` that
silently truncated the command, and a quoting rule that needed two parsers which then
disagreed. A list has nothing to parse. The string form stays, because most commands are
better read as one.

## Notes

C-08 is `red: guard`: the suite passes at base and must keep passing, which is a standing
invariant rather than a thing to be seen failing. `done_level: proven` because the runner
is what every other contract in this repository is judged by, and the previous contract
established that its defects are found by running it rather than reading it.
