---
schema_version: 1
feature: repo-checks
done_level: reviewed
base: 5f64e63
criteria:
  - id: C-01
    text: >-
      THE repository SHALL carry executable invariant checks for the document format rules
      in CLAUDE.md — Core Rules as the first body heading, no tool-call residue, and a doc
      map whose links all resolve — so that the rules are enforced rather than remembered.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k format -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      WHEN a conventions doc exists, THE mkdocs nav SHALL list it, so that a reader sent to
      the published site by templates/AGENTS.md receives the whole convention set rather
      than the subset that existed when the nav was last edited.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k nav -q
    runner: pytest
    kind: functional

  - id: C-03
    text: >-
      THE repository and the project template SHALL each carry a .python-version agreeing
      with their requires-python, which conventions/03-environment.md states as its first
      Core Rule and neither currently satisfies.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k python_version -q
    runner: pytest
    kind: functional

  - id: C-04
    text: >-
      THE ADR path stated in conventions/15-doc-tracking.md SHALL resolve to a tracked
      directory, and every ADR in it SHALL reach the published site.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k adr -q
    runner: pytest
    kind: functional

  - id: C-05
    text: >-
      THE description of this repository in CLAUDE.md SHALL agree with the repository —
      it states there are no build or test commands while 181 tests run, and enumerates
      templates/ without scripts/, skills/ or .pre-commit-config.yaml.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k claude_md -q
    runner: pytest
    kind: functional

  - id: C-06
    text: >-
      THE continuous integration workflow SHALL run linting, the test suite and a secret
      scan on every pull request, which conventions/03-environment.md and
      13-secret-management.md both require and no workflow currently does.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k workflow -q
    runner: pytest
    kind: functional

  - id: C-07
    text: >-
      THE repository SHALL NOT gain a runtime dependency from this work — the invariant
      checks read files and parse YAML, and anything beyond that belongs to a later
      contract rather than to a checks lane.
    verify: uv run --group dev pytest tests/test_repo_invariants.py -k no_new_runtime_dependency -q
    runner: pytest
    kind: negative
    red: guard

  - id: C-08
    text: >-
      THE contract runner's own test suite SHALL keep passing, because this contract adds
      a second testpath and a workflow that runs it, and neither may disturb the toolkit
      that the previous contract proved.
    verify: uv run --group dev pytest templates/scripts/tests -q
    runner: pytest
    kind: functional
    red: guard

revision:
  kind: breaking
  reason: >-
    C-07 was declared without `red: guard` although an absence criterion holds at base by
    construction. The red phase recorded NOT-RED and the status gate blocked it, which is
    the gate working; the fix is the declaration, not the criterion. It edits an existing
    criterion, so it is breaking rather than additive — no lane had started, so the
    restart 18 §7 prescribes costs nothing.

out_of_scope:
  - fixing anything under templates/ other than adding .python-version (that is the next contract)
  - the conventions contradictions, dead references and duplications the audit found
  - re-verifying stale factual claims
  - changes to ~/.claude/ or the claude-config repository
  - installing pre-commit hooks locally, which the global core.hooksPath blocks
  - merging the branch, which happens after this contract closes and CI is green
---

# repo-checks

## Background

The audit that followed the contract-runner work found that this repository does not
apply its own rules to itself. `conventions/03-environment.md:20` and
`13-secret-management.md:12` both require CI enforcement; the only workflow builds the
documentation site. `03-environment.md:5` requires a `.python-version`; neither the root
nor `templates/` has one. `CLAUDE.md:8` states there are no build or test commands while
`pyproject.toml` declares a testpath and 181 tests run.

The workflow that ran those checks existed. `.github/workflows/checks.yml` was deleted in
`a078b30`, the commit that withdrew the first contract runner: its `toolkit` job
referenced files that commit removed, and the `documents` job — which had nothing to do
with the runner — was deleted along with it.

Restoring it as it was would rebuild the same fragility, because its document checks were
inline shell in YAML and nothing else could run them. Here they are pytest tests instead,
so the contract's `verify` commands and the CI job execute the same file.

## Why the checks are tests rather than scripts

A `command` criterion brings nothing into the base checkout — base is base. A check script
created by this work would therefore not exist at `5f64e63`, and the red phase would
record `NO-BASELINE` (the check could not run) rather than `RED` (the check ran and
failed), which the status gate refuses. A `pytest` criterion has its selected files copied
forward from the working tree, so each check runs at base against the base tree and fails
there for the reason it is meant to.

## Notes

`C-08` is `red: guard`: the runner's suite passes at base and is supposed to, so it is a
standing invariant rather than a check that must be seen failing first.
