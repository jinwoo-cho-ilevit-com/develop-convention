---
schema_version: 1
feature: remaining-defects
done_level: reviewed
base: 82def13
criteria:
  - id: C-01
    text: >-
      THE `created_at` in a manifest SHALL be the time the evidence began, not the time it
      was last rewritten. 19 section 4 derives lead time per contract from it, and a value
      that moves with every render derives nothing.
    verify: uv run --group dev pytest templates/scripts/tests -k created_at -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      WHEN another feature under `artifacts/` still holds a PENDING-HUMAN record, `lint`
      and `status` SHALL say so. A contract awaiting verdicts was replaced by the next one
      three times in the session that found this, with nothing noticing.
    verify: uv run --group dev pytest templates/scripts/tests -k awaiting_a_verdict -q
    runner: pytest
    kind: functional

  - id: C-03
    text: >-
      THE runner SHALL refuse a parallel decomposition that cannot hold — overlapping
      `owns`, a glob in `owns`, a file claimed by both a lane and `sequential_owner`, a
      model id where a tier belongs, or a decomposition field with no lanes beside it.
    verify: uv run --group dev pytest templates/scripts/tests -k lanes -q
    runner: pytest
    kind: functional

  - id: C-04
    text: >-
      THE runner SHALL accept a decomposition that does hold, including `owns` entries
      naming a cross-cutting file individually, which a directory-prefix rule cannot
      assign and which 18 requires to be named.
    verify: uv run --group dev pytest templates/scripts/tests -k "named_cross_cutting or sequential_owner_outside or integration_and" -q
    runner: pytest
    kind: functional

  - id: C-05
    text: >-
      THE repository invariants and the toolkit suite SHALL keep passing across a change
      that adds two state files and moves four fields out of the refused set.
    verify: uv run --group dev pytest -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-06
    text: >-
      THE runner SHALL NOT execute a lane or enforce ownership at run time. What this adds
      is a check that says the decomposition is self-contradictory before it starts;
      running lanes is a separate mechanism with its own contract.
    verify: uv run --group dev pytest templates/scripts/tests -k no_lane_execution -q
    runner: pytest
    kind: negative
    red: guard

  - id: C-07
    text: >-
      THE rule in 20 about a verification gate SHALL describe something the tool can
      actually do, and the documents describing the runner SHALL describe what it now
      does, judged by someone who wrote neither.
    verify: human
    kind: nonfunctional

  - id: C-08
    text: >-
      THE four remaining third-party citations SHALL be judged individually rather than
      removed as a class, since 16 bars a blog as proof of a factual claim and not as a
      pointer beside general engineering advice.
    verify: human
    kind: nonfunctional

out_of_scope:
  - the unverified claim markers, which 12 section 10 already routes to a smoke test at use time
  - implementing a Stop hook; C-07 fixes the rule instead, per the documented behaviour
  - the evidence visualization format, which has no material in this repository to design against
  - changes to ~/.claude or the claude-config repository, which follow in their own contract
---

# remaining-defects

## Background

The follow-up list the original plan left behind is empty. What remains is what this
session created or found, and four of them are the same shape: a rule and the thing it
governs disagree.

`created_at` moved with every render, so the field 19 names as the basis for lead time
measured nothing. A contract awaiting a verdict could be overwritten by the next one with
no signal — it happened three times here. `20` instructed attaching a Stop hook that
blocks exit until verification passes, which the documented behaviour cannot do: a blocked
Stop does not end a run, there is no documented recursion limit, and no signal distinguishes
an unattended run, so the rule's own scope is not expressible. And the runner refused the
whole `lanes` family, so a contract for parallel work had to have its decomposition stripped
out before the tool would read it.

That last one is worth the space. This session nearly broke `18`'s ownership rule — five
lanes sliced by kind of change, all landing in the same three documents — and avoided it by
re-slicing per file. The rule that came out of it is now in `18`, and this makes it
mechanical, so the next decomposition is told before it starts rather than when it collides.

## Notes

C-05 and C-06 are `red: guard`: both hold at base and are meant to. C-06 in particular
asserts an absence — there is no lane execution — which is true at base by construction.
