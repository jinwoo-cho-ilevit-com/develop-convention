#!/usr/bin/env bash
# Injects the convention routing map once per user prompt. A pointer, not a gate: it judges
# nothing, so the per-edit judgement cost 21 §3 rejects does not arise here, and it carries
# no rule text — the rules stay in conventions/ behind the named skill (→ 15-doc-tracking.md).
set -euo pipefail

cat >/dev/null

cat <<'MAP'
<convention-routing>
Before starting work, load the dev-harness skill that governs it:
- planning, splitting work, delegating, defining "done" → plan-and-delegate
- creating/moving/renaming files, config values, dependencies, secrets → code-and-config
- preprocessing/training/evaluation pipelines on weights you run → ml-pipeline
- third-party LLM APIs, upstream docs, factual-spec research → external-sources
- writing or running tests, reviewing a diff, claiming completion → verify-and-review
- about to `git commit` → commit
- code changed and docs may be stale → docsync
A trivial single edit may proceed without one; anything larger reads the routed Core Rules first.
</convention-routing>
MAP
