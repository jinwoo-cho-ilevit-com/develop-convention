# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A development-conventions documentation repository. The deliverable is documents, not code — there are no build/test commands.
`README.md` is the doc map + full rules summary; the actual rules live in `conventions/NN-*.md`, split by topic. Other projects consume these docs by excerpting the "Core Rules" sections into their CLAUDE.md/AGENTS.md, and `templates/` (AGENTS.md, CLAUDE.md, pyproject.toml, contract.md) is the starting point for new projects. When changing a convention rule, also check consistency with templates/.

## Document format (must follow when editing/adding docs)

- Every `conventions/*.md` must have `## Core Rules` as its first body heading: a list of imperative rules excerptable verbatim into agent instruction files. It is followed by `## Details` (human-oriented explanation + source links).
- Body in English; code/identifiers/tool names in English. Exception: the commit body template and examples in `conventions/17-commit-protocol.md` are intentionally Korean (commit-message policy: English header, Korean body).
- Specific factual claims (a tool's deprecated status, research numbers, comparison results) must carry a source URL in that section. Numbers/claims not verified by research are omitted or marked "unverified". General engineering advice needs no source.
- When editing a doc, check that README.md's doc map and full rules summary do not contradict it, and update them together.
- New docs follow the `NN-topic.md` numbering scheme and are added to the README doc map.

## Verification

- Cross-check before completion: (1) every conventions doc has `## Core Rules` as its first body heading, (2) the body is in English (17 is the only exception), (3) no contradiction between the README summary and individual docs, (4) no unsourced specific claims, (5) no tool-call residue and every doc-map link resolves.
- **A claim that two rules conflict, or that a rule lives somewhere, must quote the actual file.** Three times during this repo's own review a claim about the repository turned out to be an inference rather than an observation: twice a "conflict" did not exist and the proposed fix would have weakened a rule that was already correct, and once a reviewer refuted a commit body after testing a different tool version than the one this repo pins. Reading beats inferring in both directions — quote the file, and pin the version you tested.
- **A gate that passes is not evidence the gate works.** Verify the gate itself fails when it should, at least once. This repo shipped a red-check gate whose own evidence pack contained no red results, and the completion report treated the resulting exit 0 as proof.
- Sizable changes are verified by fresh-context review lanes that start from the diff and criteria and never see the authoring session's reasoning — a rule this repo's 00-principles.md and 09-agentic-workflow.md set for itself.

## Commits

- Commit messages: Conventional Commits header (English type/scope) + Korean body (`## Why/What/How/Result`) — see `conventions/17-commit-protocol.md`. Doc changes use the `docs(conventions): ...` form.
- `.omc/` and `.claude/` are gitignored operational artifacts — never commit them.
