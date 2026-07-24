# 01. Project Structure + Naming

## Core Rules

- Separate development by module/feature as much as possible. Each module has a clear input/output contract.
- Use flat layout for app/research/pipeline code. Use `src/` layout only for distributed libraries.
- Keep files small and module boundaries clear — both humans and agents should be able to read only the part they need.
- Name variables/functions/classes/scripts/folders with semantic naming that directly reveals their role. Follow PEP 8.
- No `_v2`, `_new`, `_old`, `_final` suffixes. When improving, rename in place to change the name itself.
- Delete dead code as soon as it's found. Don't leave it commented out.
- Comments should state only constraints/intent that the code itself can't express. No internal context that other AIs/teammates wouldn't know, no unnecessary TMI, no explaining the obvious.
- When refactoring/migrating, don't carry over anything unused in the existing project.
- Before finishing work, scan for and remove duplicate constants/functions/scripts.

## Details

### 1. Separation by module/feature

- Modularize the pipeline independently by stage (preprocessing/training/evaluation/inference, etc.). Each stage must be runnable standalone (→ [04-pipeline.md](04-pipeline.md)).
- Connect dependencies between modules only through explicit interfaces (function signatures, data schemas). Agents tend to silently violate architectural boundaries, so boundaries must be explicit in both code and docs for parallel development to work (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

### 2. Layout: flat by default

PyPA does not mandate either src-layout or flat-layout. The benefits of src-layout (preventing accidental imports of the in-development copy, verifying editable installs) are meaningful for **distributed, reused libraries**, and NumPy, SciPy, and Matplotlib all keep flat layout.

- Pipeline/research/app code: flat layout (e.g., `preprocess/`, `train/`, `eval/`, `configs/` at the repo root)
- Packages distributed on PyPI or reused across multiple projects: src-layout
- Once a single repo needs multiple packages, use uv workspaces: register members under the root `[tool.uv.workspace]`; the whole set shares a single `uv.lock` and a single venv, which eliminates version conflicts between packages at the source.

Sources: [PyPA — src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), [Setting up a Python monorepo with uv workspaces](https://pydevtools.com/handbook/how-to/how-to-set-up-a-python-monorepo-with-uv-workspaces/)

### 3. Naming

- PEP 8: `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants. Module names should be short and lowercase.
- Names must describe the role: `raw_train_samples` over `data`, `normalize_audio()` over `process()`.
- No version suffixes. Don't create `parse_header_v2()` — safely replace `parse_header()` via LSP rename. Do renames in small units backed by tests.
- When refactoring, don't be bound by existing naming. If a name has drifted from its current role, improve it on the spot.

Sources: [PEP 8](https://peps.python.org/pep-0008/)

### 4. Comment rules

The bar for a comment is: "can a first-time reader (human or model) read it and act on it?"

- Write: constraints not visible from the code alone (e.g., "this order exists because of the external API's rate limit"), known limitations and upgrade paths, reasons for non-obvious choices.
- Don't write: explaining what the next line does (duplicates the code), history of how it was written (git already covers this), context only insiders know ("as decided in last time's meeting"), personal notes or TMI.
- Documentation (README/docstrings) follows the same bar: only what a first-time reader needs, kept concise.

### 5. Migration/cleanup rules

- When moving to a new project, move only what's "actually called." If usage is unclear, don't move it — add it later when it's needed.
- Delete dead code (unused functions, commented-out blocks, unreachable branches) as soon as it's found. Git history is the backup.
- At the wrap-up stage of a task, scan for duplication: confirm the same constant isn't defined in two places and that two functions/scripts doing the same thing haven't been created, before declaring completion.

### 6. Agent-friendly structure (context engineering)

The context window is an agent's fundamental constraint. A giant single file is bad for both humans and agents.

- One file holds one concern only. When a file grows long, consider splitting it.
- Per-module docs (a README or AGENTS.md in that directory) should contain only content scoped to that directory (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)
