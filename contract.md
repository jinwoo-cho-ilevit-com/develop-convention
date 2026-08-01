---
schema_version: 1
feature: final-coherence
done_level: reviewed
base: 5fec9cc
criteria:
  - id: C-01
    text: >-
      NO conventions doc SHALL instruct an author to write a contract field the shipped
      runner refuses. 19 §7 tells them to record visualization intent in `evidence_todo`,
      and 18 §4 states that the runner refuses it — following one breaks the other.
    verify: uv run --group dev pytest tests/test_conventions.py -k fields_the_runner_refuses -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      WHERE a convention depends on a setting that can be switched off, THE doc SHALL say
      what carries the load when it is. 14 makes auto memory half of its persistence
      strategy without naming the case where it is disabled.
    verify: uv run --group dev pytest tests/test_conventions.py -k optional_mechanism -q
    runner: pytest
    kind: functional

  - id: C-03
    text: >-
      THE repository invariants and the toolkit suite SHALL keep passing.
    verify: uv run --group dev pytest -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-04
    text: >-
      THIS work SHALL NOT specify the evidence visualization format. Its absence is a
      recorded decision, and inventing a format with no evidence about what works is the
      thing 19 §7 exists to prevent.
    verify: uv run --group dev pytest tests/test_conventions.py -k still_unspecified -q
    runner: pytest
    kind: negative
    red: guard
out_of_scope:
  - anything under ~/.claude or the claude-config repository, which follows separately
  - the review-tool selection rules, closed already by 20 sections 64 and 68
  - third-party plugin and skill state this repository does not govern
---

# final-coherence

## Background

Two items remain from the original follow-up list, and both turn out to be smaller than
they looked.

The review-tool rules (item 4) are already in place: 20 refuses to pin a model id and
resolves one at use time, and it gives the two paths separate jobs drawn on separate
quotas so that exhausting one does not silently make the other absorb both. The fail-open
contradiction the original plan flagged belonged to a tool-probe design that was never
built.

Evidence visualization (item 5) stays unspecified, and that is the decision rather than an
omission: specifying a required field before its format exists means every contract fills
it differently and nothing can validate it. What is wrong is the instruction attached to
it — 19 §7 tells an author to record the intent in `evidence_todo`, a field 18 §4 says the
runner refuses outright. One document tells you to do what the other says will be rejected.

The third finding is of the same shape. 14 puts half its persistence strategy in auto
memory, which is a setting that can be turned off — and is off on the machine this
repository is written on.
