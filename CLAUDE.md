# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A development-conventions documentation repository. The deliverable is documents, and the only code is the work-contract toolkit under `templates/scripts/`, which projects copy out — so there is a test suite, and `uv run --group dev pytest` runs both it and the repository invariants under `tests/`.
`README.md` is the doc map + full rules summary; the actual rules live in `conventions/NN-*.md`, split by topic. Other projects consume these docs by excerpting the "Core Rules" sections into their CLAUDE.md/AGENTS.md, and `templates/` (AGENTS.md, CLAUDE.md, pyproject.toml, contract.md, `.pre-commit-config.yaml`, `.python-version`, `scripts/`, `skills/`) is the starting point for new projects. When changing a convention rule, also check consistency with templates/.

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
