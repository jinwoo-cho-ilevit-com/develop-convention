# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A development-conventions documentation repository. The deliverable is documents, not code — there are no build/test commands.
`README.md` is the doc map + full rules summary; the actual rules live in `conventions/NN-*.md`, split by topic. Other projects consume these docs by excerpting the "Core Rules" sections into their CLAUDE.md/AGENTS.md, and `templates/` (AGENTS.md, CLAUDE.md, pyproject.toml) is the starting point for new projects. When changing a convention rule, also check consistency with templates/.

## Document format (must follow when editing/adding docs)

- Every `conventions/*.md` must have `## Core Rules` as its first body heading: a list of imperative rules excerptable verbatim into agent instruction files. It is followed by `## Details` (human-oriented explanation + source links).
- Body in English; code/identifiers/tool names in English. Exception: the commit body template and examples in `conventions/17-commit-protocol.md` are intentionally Korean (commit-message policy: English header, Korean body).
- Specific factual claims (a tool's deprecated status, research numbers, comparison results) must carry a source URL in that section. Numbers/claims not verified by research are omitted or marked "unverified". General engineering advice needs no source.
- When editing a doc, check that README.md's doc map and full rules summary do not contradict it, and update them together.
- New docs follow the `NN-topic.md` numbering scheme and are added to the README doc map.

## Verification

- Cross-check before completion: (1) every conventions doc has `## Core Rules`, (2) no contradiction between the README summary and individual docs, (3) no unsourced specific claims. Sizable changes are verified by fresh-context review lanes that start from the diff and criteria and never see the authoring session's reasoning — a rule this repo's 00-principles.md and 09-agentic-workflow.md set for itself.

## Commits

- Commit messages: Conventional Commits header (English type/scope) + Korean body (`## Why/What/How/Result`) — see `conventions/17-commit-protocol.md`. Doc changes use the `docs(conventions): ...` form.
- `.omc/` and `.claude/` are gitignored operational artifacts — never commit them.
