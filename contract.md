---
schema_version: 1
feature: template-coherence
done_level: reviewed
base: 2788e3b
criteria:
  - id: C-01
    text: >-
      THE conv-init skill SHALL install the contract runner when a project adopts work
      contracts, and no step SHALL tell the reader to do by hand what the runner does —
      the skill currently states both, in one file.
    verify: uv run --group dev pytest tests/test_templates.py -k conv_init_installs_the_runner -q
    runner: pytest
    kind: functional

  - id: C-02
    text: >-
      WHEN conv-init names a path to copy, THAT path SHALL exist in this repository, so a
      bootstrap fails here rather than in the project being bootstrapped.
    verify: uv run --group dev pytest tests/test_templates.py -k conv_init_copies_only_paths_that_exist -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-03
    text: >-
      THE ruff version pinned in templates/pyproject.toml SHALL equal the rev of the
      ruff hook in templates/.pre-commit-config.yaml, which that file's own comment
      instructs and which it cannot satisfy while the dependency carries no pin.
    verify: uv run --group dev pytest tests/test_templates.py -k ruff_pin -q
    runner: pytest
    kind: functional

  - id: C-04
    text: >-
      THE project template SHALL declare every dependency the toolkit it ships needs, so
      that a criterion run as `uv run python scripts/contract.py` works in a project
      bootstrapped from it and not only under `uv run --script`.
    verify: uv run --group dev pytest tests/test_templates.py -k template_declares_runner_dependencies -q
    runner: pytest
    kind: functional

  - id: C-05
    text: >-
      THE contract template SHALL describe only what the shipped runner accepts — it
      documents `hermetic: false` as a red-check exemption while the runner refuses any
      value that is not literally true.
    verify: uv run --group dev pytest tests/test_templates.py -k template_matches_the_runner -q
    runner: pytest
    kind: functional

  - id: C-06
    text: >-
      THE instruction given to an agent with no local clone SHALL be the same wherever it
      appears — README offers a submodule or a copied summary and never mentions the
      published site, while templates/AGENTS.md offers only the published site.
    verify: uv run --group dev pytest tests/test_templates.py -k sandbox_guidance -q
    runner: pytest
    kind: functional

  - id: C-07
    text: >-
      THE toolkit suite and the repository invariants SHALL keep passing, because this
      contract edits the files the toolkit is copied from.
    verify: uv run --group dev pytest -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-09
    text: >-
      A project bootstrapped from templates/ SHALL be able to run a contract through all
      five phases and produce the four evidence artifacts, executed rather than inferred
      from the files.
    verify: uv run --group dev pytest tests/test_templates.py -k bootstrap -q
    runner: pytest
    kind: functional
    red: guard

  - id: C-08
    text: >-
      THIS contract SHALL NOT add a runtime dependency to the repository, and SHALL NOT
      change the runner's behaviour — the template is what is out of step, not the tool.
    verify: uv run --group dev pytest tests/test_templates.py -k no_runner_change -q
    runner: pytest
    kind: negative
    red: guard

revision:
  kind: breaking
  reason: >-
    C-02 was declared without `red: guard`. "Every path conv-init names exists" held at
    base and is meant to always hold; what C-01 adds is new path references that this
    invariant then protects. The red phase recorded NOT-RED and the gate blocked, which
    is the gate working. Second occurrence of the same authoring mistake in three
    contracts — the question to ask of each criterion is whether it was already true at
    base, and it belongs in 18.

    Then additive: C-09 added. The plan for this contract carried a human criterion —
    "run conv-init against an empty project and see" — and every other criterion here
    reads a file rather than running one. C-09 performs the copy steps into a temporary
    repository and drives the copied runner through all five phases, which answers the
    same question by execution. It holds at base, so it is a guard: the runner already
    worked when copied out, and this keeps it that way.

out_of_scope:
  - the conventions contradictions, dead references and duplications the audit found
  - re-verifying stale factual claims, including the Node 20 deprecation in the workflows
  - changes to ~/.claude/ or the claude-config repository
  - the runner follow-up recorded in adr/0001 (verify list form, lanes, bypass, and the rest)
  - installing conv-init anywhere, or changing how it is installed
---

# template-coherence

## Background

`templates/` is the only thing this repository hands to another project, so a defect here
is the one a next user meets. Two audits found six.

The sharpest is `conv-init/SKILL.md`, which contradicts itself in one file: line 15 offers
to copy "`contract.md` and the contract runner", and §5 says "There is no runner yet —
criteria are executed and recorded by hand". §5 predates the runner and no step copies
`templates/scripts/`, which also makes `README.md`'s claim that conv-init automates "the
whole step" false.

The rest are the same shape — something changed and the thing that distributes it did not
learn. `templates/.pre-commit-config.yaml` instructs the reader to keep its ruff `rev` in
step with a pin that `templates/pyproject.toml` does not carry. `templates/contract.md`
documents `hermetic: false` as a red-check exemption, which the shipped runner refuses
outright. `templates/pyproject.toml` omits the dependency its own copied toolkit imports.
README and `templates/AGENTS.md` give an agent with no local clone two different answers
and neither mentions the other's.

## Notes

C-07 and C-08 are `red: guard`. Both are standing invariants: the suite passes at base and
is meant to, and the repository has no runtime dependency at base either.
