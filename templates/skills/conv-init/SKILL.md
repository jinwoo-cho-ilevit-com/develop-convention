---
name: conv-init
description: Bootstrap a project with the develop-convention templates — copy AGENTS.md/CLAUDE.md/pyproject.toml, fill placeholders, prune non-applicable optional blocks (ML / LLM API / docsync), optionally install the docsync skill. Use when starting a new project or retrofitting conventions onto an existing one.
---

# conv-init — project bootstrap

One-command application of the convention templates to the current project. Tool-neutral: run as a Claude Code skill, or follow this file as a prompt in any agent.

## Inputs (ask if not provided)

1. **One-line project description** (fills `[One line: what this project is]`).
2. **Project type**: `general` / `ML` / `LLM API` (multiple allowed) — decides which optional blocks survive.
3. **Adopt docsync doc tracking?** yes/no.

## Procedure

### 1. Locate the convention repo

- Default path: `~/Codes/develop-convention` (the fixed clone path used by claude-config bootstrap). Respect an explicit user-given path.
- If missing: `git clone https://github.com/jinwoo-cho-ilevit-com/develop-convention.git ~/Codes/develop-convention`. If cloning is impossible (sandbox), use the published docs as read-only reference: https://jinwoo-cho-ilevit-com.github.io/develop-convention/ — but state that path references in AGENTS.md will need a local clone to work.

### 2. Copy templates

Copy from `<CONVENTION_PATH>/templates/` into the project root:

- `AGENTS.md`, `CLAUDE.md` — if the project already has either, do NOT overwrite: show a diff and merge only the missing convention sections after confirmation.
- `pyproject.toml` — only for new Python projects; for existing projects, merge the relevant tool sections (`[tool.ruff]`, `[dependency-groups]`) instead.

### 3. Fill placeholders

| Placeholder | Fill with |
|---|---|
| `[One line: what this project is]` | user's description |
| `PROJECT_NAME` | directory name or existing pyproject name |
| `[CONVENTION_PATH]` | the path from step 1 |
| `[ENTRY]` / smoke command | actual entrypoint if known, else leave a TODO comment for the user |

### 4. Prune optional blocks

In the copied AGENTS.md, keep only the blocks matching the project type (`ML`, `LLM API`, `docsync`); delete the others including their marker lines. No empty leftover markers.

### 5. docsync (if adopted)

Copy `<CONVENTION_PATH>/templates/skills/docsync/` → `.claude/skills/docsync/`. Mention that the first `/docsync` run bootstraps module docs (no separate init).

### 6. Report

List: files created/merged, placeholders filled (and any left as TODO), blocks kept/removed, and next steps — e.g. "run `/docsync` to bootstrap module docs", "fill the smoke command in AGENTS.md".

## Rules

- Never silently overwrite existing project files; diff + confirm.
- Do not paste whole convention docs into AGENTS.md — the template's excerpt + path-reference structure is intentional (see conventions/09: bloated instruction files cause rule-skipping).
- Keep the placeholders you cannot fill as visible TODOs rather than guessing.
