---
description: Write the short AGENTS.md this project needs — what it is and the commands the harness cannot guess — and the CLAUDE.md line that loads it
---

Write or update `AGENTS.md` at the project root.

The harness carries the conventions, the hooks and the skills. The only thing it cannot know is this project: what it is, and how to run, test, lint and smoke it. That is all this file holds.

Read the project first — `pyproject.toml`, `package.json`, `Makefile`, the CI workflow, the test directory — and propose the commands rather than asking for them. Ask only for what you could not find.

Start from `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS.md` and fill its placeholders; the shape is the template's, not this command's.

Claude Code reads `CLAUDE.md`, not `AGENTS.md`, so give `AGENTS.md` its sibling `CLAUDE.md` under the rule in `${CLAUDE_PLUGIN_ROOT}/conventions/15-doc-tracking.md` §1. Two cases exist only at the root:

- The project `CLAUDE.md` may live at `./.claude/CLAUDE.md` instead. There the line is `@../AGENTS.md`, since an import resolves relative to the file that holds it.
- Where both `./CLAUDE.md` and `./.claude/CLAUDE.md` exist, put the line in `./CLAUDE.md`. The memory documentation names both locations without saying how they combine, so confirm with `/context` that `AGENTS.md` appears under Memory files.

Then list every other `AGENTS.md` in the tree that has no sibling `CLAUDE.md`, and offer to add those under the same rule.

Rules:

- **Never overwrite an existing `AGENTS.md` or `CLAUDE.md`.** Show a diff and merge only the missing sections or line after confirmation.
- **Do not paste convention rules into it.** The harness reads `conventions/` directly, and a copied excerpt drifts from its source while being loaded everywhere (→ `${CLAUDE_PLUGIN_ROOT}/conventions/15-doc-tracking.md`). Every line here must be something no one could infer from the repository.
- Leave a command you genuinely cannot determine as a visible `TODO` rather than guessing.

Nothing triggers this automatically: you run it once per project, again after a plugin update, and again after the commands change.
