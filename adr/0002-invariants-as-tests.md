# 0002. Repository invariants are tests, not shell in a workflow

Status: accepted (2026-08-02)

## Context

`CLAUDE.md` carries a verification checklist for this repository — every conventions doc opens with `## Core Rules`, no tool-call residue is committed, every doc-map link resolves. A workflow once enforced three of those, as inline shell inside `.github/workflows/checks.yml`. That workflow was deleted in `a078b30`, the commit withdrawing the first contract runner: the `toolkit` job referenced files that commit removed, and the `documents` job, which had nothing to do with the runner, went with it. Nothing noticed for the whole of the rebuild.

## Decision

The checklist lives in `tests/test_repo_invariants.py`, and both the CI job and a contract's `verify` commands execute that file. `pyproject.toml` carries two testpaths so a bare `uv run pytest` covers the toolkit and the repository together.

*Alternatives:* restoring the inline shell, which is what was there. It fails twice over — nobody can run it locally without copying commands out of YAML, and a contract cannot use it as a `verify` command, so the same rule would be written down in two places and drift.

## Consequence, and the reason it is not merely stylistic

A `command` criterion brings nothing into the base checkout — base is base. A check script created by the work that adds it does not exist at the base commit, so the red phase records `NO-BASELINE` (the check could not run) rather than `RED` (it ran and failed), and the status gate refuses that. A `pytest` criterion has its selected files copied forward from the working tree, so the check runs at base against the base tree and fails there for the reason it is meant to.

So the choice of pytest is what makes these invariants *contractible* at all. Any future check that a contract must prove red has to be a test for the same reason.

The first run of the contract that added these demonstrated the neighbouring rule: its negative criterion was declared without `red: guard`, the red phase recorded `NOT-RED`, and the gate blocked it. An absence criterion holds at base by construction and is a standing invariant, not something that can be seen failing first.
