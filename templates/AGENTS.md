# AGENTS.md

Instructions for coding agents working in this repository.

## Project

[One line: what this project is]

## Commands

- Run: `uv run python -m [ENTRY]`
- Test: `uv run pytest`
- Lint: `uv run ruff check && uv run ruff format --check`
- Smoke: `[small-sample run — e.g. uv run python -m ENTRY --limit 10 device=cpu]`

<!--
Nothing else belongs here. The conventions ship as the dev-harness plugin, which reads them
directly; a copy pasted into this file drifts from its source while being loaded in every
session. Tools that read neither plugins nor a local clone get one pointer instead:
https://jinwoo-cho-ilevit-com.github.io/develop-convention/
-->
