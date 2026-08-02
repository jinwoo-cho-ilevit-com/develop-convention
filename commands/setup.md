---
description: Write the short AGENTS.md this project needs — what it is and the commands the harness cannot guess
---

Write or update `AGENTS.md` at the project root.

The harness carries the conventions, the hooks and the skills. The only thing it cannot know is this project: what it is, and how to run, test, lint and smoke it. That is all this file holds.

Read the project first — `pyproject.toml`, `package.json`, `Makefile`, the CI workflow, the test directory — and propose the commands rather than asking for them. Ask only for what you could not find.

```markdown
# AGENTS.md

## Project

Catalogue product-name matching pipeline.

## Commands

- Run: `uv run python -m app`
- Test: `uv run pytest`
- Lint: `uv run ruff check && uv run ruff format --check`
- Smoke: `uv run python -m app --limit 10 device=cpu`
```

Rules:

- **Never overwrite an existing `AGENTS.md`.** Show a diff and merge only the missing sections after confirmation.
- **Do not paste convention rules into it.** The harness reads `conventions/` directly, and a copied excerpt drifts from its source while being loaded everywhere (→ `conventions/15-doc-tracking.md`). Every line here must be something no one could infer from the repository.
- Leave a command you genuinely cannot determine as a visible `TODO` rather than guessing.

This normally runs on its own, the first time the harness needs a command and finds no file. Invoking it by hand is the way to redo it after the commands change.
