# AGENTS.md

Instructions for coding agents working in this repository.

## Project

[One line: what this project is]

## Commands

- Run: `uv run python -m [ENTRY]`
- Test: `uv run pytest`
- lint/format: `uv run ruff check && uv run ruff format --check`
- Small-sample smoke: `[smoke command — e.g. uv run python -m ENTRY --limit 10 device=cpu]`

## Conventions

Full conventions: `[CONVENTION_PATH]` (local path where the develop-convention repo is cloned) — follow the "Core Rules" of the doc matching the type of work (doc map is that repo's README.md). If no local clone is available (e.g. cloud sandbox), reference the published docs instead: https://jinwoo-cho-ilevit-com.github.io/develop-convention/

Especially keep in this project:
- No hardcoding, all values in central config (02)
- Every pipeline stage supports `--limit N` small-sample runs + intermediate save/resume (04)
- Scan for duplicates/dead code before completion, no `_v2`/`_new` naming (01)

[Keep for ML projects, else delete]
- Unified seeding helper + single source for train/inference preprocessing code, device via a single helper only (03/07)

[Keep for LLM API projects, else delete]
- Before writing/modifying provider API code: fetch and confirm the relevant provider's official docs from `[CONVENTION_PATH]/conventions/12-docs-reference.md`
- If an official provider skill exists, install and use it (e.g. Gemini `gemini-api-dev`) — for SDK usage, official skill > ctx7 in priority; for exceptions/signatures, the installed SDK source is authoritative
- Don't guess behavior not covered in the docs — confirm with a provider smoke test (10/11/12)

[Keep if using docsync doc tracking, else delete]
- Module docs are managed via the `docsync:managed` block in each directory's AGENTS.md — after code changes, sync via the `.claude/skills/docsync/SKILL.md` procedure; do not edit the human section outside the block (15)
- Factual claims in the managed block must be citable to a code location (file:symbol) (rationale/failure history go in the ADR/human section); ADRs are superseded rather than edited — when referencing, follow only the valid decision at the end of the chain (15)

## Verification

Before completion: run `uv run pytest` + the smoke command above, check full output. No completion claims without execution evidence. TODOs/stubs/`test.skip` are blockers, not completion.

[Keep if using work contracts, else delete]
- Work starts from a `contract.md` stating completion criteria, ownership, and `done_level` before any code is written; it is frozen during execution. Three to five lines is a complete contract for small work (18)
- Every criterion carries an executable `verify:` or an explicit `verify: human`, and every new test is observed failing at the base commit before it passes (06/18)
- Report completion as artifact paths plus the criteria table, never as a narrative summary (19)
