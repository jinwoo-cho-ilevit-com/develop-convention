# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A development-conventions repository that also ships the harness running them. The rules live in `conventions/NN-*.md`; `README.md` is the doc map (grouped, numbers being stable identifiers rather than a reading order) plus the full rules summary.

The code is the `dev-harness` plugin: `.claude-plugin/` manifests, `hooks/delegate-guard.sh`, `commands/`, `workflows/build.js`, `skills/`. `uv run --group dev pytest` runs the repository invariants under `tests/`, which drive the guard and the workflow rather than reading them. `templates/` is down to what a plugin cannot supply — a short `AGENTS.md` and the local tool configuration.

Projects consume this by installing the plugin, not by copying rules out. An excerpt is a copy, and 15 requires a copy to carry its source and be checked; when changing a rule, check whether the plugin that delivers it needs the same change.

## Document format (must follow when editing/adding docs)

- Every `conventions/*.md` must have `## Core Rules` as its first body heading: a list of imperative rules excerptable verbatim into agent instruction files. It is followed by `## Details` (human-oriented explanation + source links).
- Body in English; code/identifiers/tool names in English. Exception: the commit body template and examples in `conventions/17-commit-protocol.md` are intentionally Korean (commit-message policy: English header, Korean body).
- Specific factual claims (a tool's deprecated status, research numbers, comparison results) must carry a source URL in that section. Numbers/claims not verified by research are omitted or marked "unverified". General engineering advice needs no source.
- When editing a doc, check that README.md's doc map and full rules summary do not contradict it, and update them together.
- New docs follow the `NN-topic.md` numbering scheme and are added to the README doc map.

## Verification

- Cross-check before completion: (1) every conventions doc has `## Core Rules` as its first body heading, (2) the body is in English (17 is the only exception), (3) no contradiction between the README summary and individual docs, (4) no unsourced specific claims, (5) no tool-call residue and every doc-map link resolves.
- A claim that two rules conflict, or that a rule lives somewhere, quotes the actual file. The same holds for refuting one: name the tool version you tested with, and make it the version this repo pins.
- Sizable changes go through fresh-context review lanes (→ `conventions/20-review-gate.md`), which this repo applies to itself.

## Commits

- Commit messages: Conventional Commits header (English type/scope) + Korean body (`## Why/What/How/Result`) — see `conventions/17-commit-protocol.md`. Doc changes use the `docs(conventions): ...` form.
- `.omc/` and `.claude/` are gitignored operational artifacts — never commit them.
