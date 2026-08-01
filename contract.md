---
schema_version: 1
feature: conventions-coherence
done_level: reviewed
base: 0cb565d
criteria:
  - id: C-01
    text: >-
      EVERY section cross-reference between conventions docs SHALL point at a section that
      exists — `18` sent readers to `09 §5` while 09 has four sections.
    verify: uv run --group dev pytest tests/test_conventions.py -k cross_references -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      EVERY conventions doc's section numbering SHALL be contiguous. `15` ran 1,2,3,4,5,7,
      and a reader looking for §6 finds nothing and cannot tell whether it was removed.
    verify: uv run --group dev pytest tests/test_conventions.py -k numbering -q
    runner: pytest
    kind: functional

  - id: C-03
    text: >-
      NO factual stamp SHALL sit outside the re-verification window `12` itself sets, so
      that the rule governing stamps is enforced rather than remembered.
    verify: uv run --group dev pytest tests/test_conventions.py -k stamps -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-04
    text: >-
      THE repository's own invariants and the toolkit suite SHALL keep passing across a
      change that touches fourteen documents in parallel.
    verify: uv run --group dev pytest -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-05
    text: >-
      THE contradiction between `09` and `18` on what stops when a frozen contract changes
      SHALL be gone, with one document stating the rule and the other pointing at it, and
      README SHALL carry that one version rather than both.
    verify: human
    kind: functional

  - id: C-06
    text: >-
      EVERY factual claim re-verified in this work SHALL trace to a source fetched during
      it, and every claim that could not SHALL be marked rather than dropped or filled in
      from memory, judged against the lane reports by someone who did not run the lanes.
    verify: human
    kind: nonfunctional

  - id: C-07
    text: >-
      THE rules added from this session's measurements SHALL be rules a reader can act on,
      and SHALL NOT have made `18` heavier than the work it governs.
    verify: human
    kind: nonfunctional

  - id: C-08
    text: >-
      THIS work SHALL NOT delete a claim merely because a source could not be found — the
      recorded decision is to mark and keep, so that a true claim is not lost to a failed
      search.
    verify: uv run --group dev pytest tests/test_conventions.py -k stamp_check_would_catch -q
    runner: pytest
    kind: negative
    red: guard

out_of_scope:
  - the runner follow-up recorded in adr/0001
  - hook, skill and plugin hygiene beyond what the excerpt work already closed
  - templates/, closed by the template-coherence contract
  - third-party blog citations that back general engineering advice rather than a version,
    date or status claim — 16 exempts those, and removing them is a separate judgment
---

# conventions-coherence

## Background

Two audits over the conventions found twenty-six items: contradictions between documents,
references to sections that do not exist, duplicated rules, stale factual claims and
claims with no source at all. This contract closes them, together with the rules this
session's own work produced evidence for.

The parallel decomposition is the part worth recording. Three kinds of change — coherence,
fact re-verification, and new rules from measurement — all land in the same documents, so
slicing by kind would have put three lanes in `18`, `20` and `README` at once. Sliced by
file instead, with every kind of edit for a document belonging to whoever owns it, the
lanes cannot collide. That constraint is now written into `18` as a rule, because arriving
at it by nearly getting it wrong is the only reason it is stated.

## Deviation to record

The contract was written after the work began rather than before it, which `18` forbids.
The base commit and the red checks are unaffected — they run against `0cb565d` either way
— but the criteria were chosen with the changes in hand, which is exactly the bias the
rule exists to prevent. Recorded here rather than quietly fixed.

## Notes

C-03, C-04 and C-08 are `red: guard`. The stamps were inside `12`'s three-month window at
base — the audit called them expiring, and by the letter of the rule they were not — so
the check is a standing invariant that stops the next one from slipping, not a failure
being repaired. C-05 through C-07 are `verify: human` because whether a rule reads as
actionable, and whether a re-verification was honest, are judgments a test cannot make.
