# 01. Project Structure + Naming

## Core Rules

- Separate development by module/feature as much as possible. Each module has a clear input/output contract.
- **Fit the structure to the design, not the design to the structure.** When integrating a new module, restructuring the surrounding project (moving/splitting/renaming existing modules) is allowed and preferred over force-fitting the new module into an ill-fitting layout.
- Use flat layout for app/research/pipeline code. Use `src/` layout only for distributed libraries.
- Keep files small and module boundaries clear — both humans and agents should be able to read only the part they need.
- Name variables/functions/classes/scripts/folders with semantic naming that directly reveals their role. Follow PEP 8.
- No `_v2`, `_new`, `_old`, `_final` suffixes on code identifiers, modules, or scripts. When improving, rename in place to change the name itself. The one exception is an artifact a past evaluation result is pinned to (prompt files, golden sets): those version append-only, because a result stops being reproducible the moment the input it ran against is overwritten (→ [10-llm-api-inference.md](10-llm-api-inference.md)).
- Never re-spell a module or symbol name as a string literal, least of all on an error path. A literal does not follow a rename, and the handler reporting the mismatch is the path the tests do not run — a guard marked `pragma: no cover` will name a module that no longer exists and read as if its check had succeeded. Derive the name from the object, or let the original error propagate.
- Delete dead code as soon as it's found. Don't leave it commented out. An unreachable function is not only clutter: its docstring is read as a statement about the system, so a correct claim sitting on a path nobody calls is how a reader concludes the live path holds a property it does not.
- Comments should state only constraints/intent that the code itself can't express. No internal context that other AIs/teammates wouldn't know, no unnecessary TMI, no explaining the obvious. Cap a comment block at three lines and an inline comment at one; past that the content belongs in a document, or the code needs a better shape. A comment claiming another component enforces something names the call site that enforces it — an unreferenced claim cannot be checked, and it outlives the day that component stopped being called.
- **Edit by rewrite, not by append.** Once a comment block or a document section has grown past about half again its original size through successive edits, rewrite the section instead of extending it. Prose that accumulates keeps every author's leftovers and loses the thread.
- Comments and documents describe the current state only. Change history — what it used to be, why it was changed, how many attempts it took — lives in git and in ADRs (→ [15-doc-tracking.md](15-doc-tracking.md)). A rule survives; the incident that produced it does not.
- Before adding a rule or an explanation, find where it already lives. Two copies drift; replace the second with a reference.
- Minimize emoji in docs and comments. Use one only when it carries information plain text cannot; never as decoration on headings, bullets, or section dividers, and never inside code comments. For status, write the word (`OK`, `FAILED`, `TODO`), not a symbol — words survive grep, diffs, and terminals that render emoji inconsistently.
- Write non-ASCII text (Korean included) as literal UTF-8 wherever it lands — tool-call JSON parameters, file content, serialized JSON — never as `\uXXXX` escapes. Escaped text fails the same greppability bar as emoji: a search for the Korean word cannot match its escaped form. In code this means `json.dumps(..., ensure_ascii=False)` — Python's default escapes every non-ASCII character. Exempt: the characters JSON itself requires escaping (quotation mark, backslash, control characters) and code or fixtures where the escape is the point.
- When refactoring/migrating, don't carry over anything unused in the existing project.
- Before finishing work, scan for and remove duplicate constants/functions/scripts.

## Details

### 1. Separation by module/feature

- Modularize the pipeline independently by stage (preprocessing/training/evaluation/inference, etc.). Each stage must be runnable standalone (→ [04-pipeline.md](04-pipeline.md)).
- Connect dependencies between modules only through explicit interfaces (function signatures, data schemas). Agents tend to silently violate architectural boundaries, so boundaries must be explicit in both code and docs for parallel development to work (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

### 2. Integrating new modules: structure follows design

Left unstated, agents (and cautious humans) default to "don't touch existing files" and bolt a new module awkwardly onto whatever layout exists. That conservatism is explicitly overridden here: when the clean design of a new module doesn't fit the current layout, adjust the layout.

- Allowed and preferred: moving, splitting, renaming existing modules so the new module lands with clean boundaries and an efficient shape — instead of duplicated helpers, awkward import paths, or a "misc" dumping ground.
- Scope guard: restructure only what the integration actually touches. A repo-wide reorganization is not "integration" — that's a rewrite, which goes through the procedure in [00-principles.md](00-principles.md) (characterization tests first).
- Behavior guard: existing tests must pass after the move; if the touched area has no tests, pin behavior first (→ [06-testing-verification.md](06-testing-verification.md)).
- Commit guard: structural moves and the new module's logic are separate commits, so the diff stays reviewable (→ [17-commit-protocol.md](17-commit-protocol.md)).

### 3. Layout: flat by default

PyPA does not mandate either src-layout or flat-layout. The benefits of src-layout (preventing accidental imports of the in-development copy, verifying editable installs) are meaningful for **distributed, reused libraries**, and NumPy, SciPy, and Matplotlib all keep flat layout.

- Pipeline/research/app code: flat layout (e.g., `preprocess/`, `train/`, `eval/`, `configs/` at the repo root)
- Packages distributed on PyPI or reused across multiple projects: src-layout
- Once a single repo needs multiple packages, use uv workspaces: register members under the root `[tool.uv.workspace]`; the whole set shares a single `uv.lock` and a single venv, which eliminates version conflicts between packages at the source.

Sources: [PyPA — src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), [Setting up a Python monorepo with uv workspaces](https://pydevtools.com/handbook/how-to/how-to-set-up-a-python-monorepo-with-uv-workspaces/)

### 4. Naming

- Names must describe the role: `raw_train_samples` over `data`, `normalize_audio()` over `process()`.
- No version suffixes on code. Don't create `parse_header_v2()` — safely replace `parse_header()` via LSP rename. Do renames in small units backed by tests.
- The rule is about code, not about evaluation inputs. A prompt file or golden set that a recorded result points at is versioned, never overwritten: renaming it in place silently invalidates every result already filed against it. Keep the two apart — code gets renamed, evaluation-pinned artifacts get appended.
- When refactoring, don't be bound by existing naming. If a name has drifted from its current role, improve it on the spot.

Sources: [PEP 8](https://peps.python.org/pep-0008/)

### 5. Comment rules

The bar for a comment is: "can a first-time reader (human or model) read it and act on it?"

- Write: constraints not visible from the code alone (e.g., "this order exists because of the external API's rate limit"), known limitations and upgrade paths, reasons for non-obvious choices.
- Don't write: explaining what the next line does (duplicates the code), history of how it was written (git already covers this), context only insiders know ("as decided in last time's meeting"), personal notes or TMI.
- Documentation (README/docstrings) follows the same bar: only what a first-time reader needs, kept concise.

**Emoji.** The same "does it inform?" bar applies to emoji, and decorative emoji fail it. Concretely, prefer plain text because:

- Status markers as words (`OK` / `FAILED` / `TODO` / `unverified`) are greppable; symbols are not, and they collapse into unreadable boxes in terminals, log aggregators, and diffs with narrow fonts.
- Emoji on every heading or bullet costs tokens and adds no signal an agent can act on — the same bloat problem that makes over-long instruction files get skipped (see [09-agentic-workflow.md](09-agentic-workflow.md)).
- A rare informative case survives the rule: a legend where the symbol *is* the data (e.g. a status column in a compatibility matrix). Use one there, consistently, and define it.

Code comments take no emoji at all — a comment exists to state a constraint, and a symbol cannot state one.

**Unicode escapes.** `\uXXXX` escapes fail the same greppability bar: a file holding `\uc548\ub155` never matches a search for `안녕`, and a diff over escaped text is unreadable. So non-ASCII text is written as literal UTF-8 everywhere it lands — tool-call JSON parameters, file content, serialized output. JSON itself requires escaping only the quotation mark, the backslash, and control characters (RFC 8259 §7); everything else may be literal. Python's `json.dumps` escapes every non-ASCII character unless told otherwise (`ensure_ascii` defaults to true), so serialization whose output humans or agents read passes `ensure_ascii=False`. Deliberate escapes in code or test fixtures are the remaining exception.

Sources: [RFC 8259 §7 — Strings](https://www.rfc-editor.org/rfc/rfc8259#section-7), [Python `json` — `ensure_ascii`](https://docs.python.org/3/library/json.html#json.dump)

### 6. Migration/cleanup rules

- When moving to a new project, move only what's "actually called." If usage is unclear, don't move it — add it later when it's needed.
- Delete dead code (unused functions, commented-out blocks, unreachable branches) as soon as it's found. Git history is the backup.
- At the wrap-up stage of a task, scan for duplication: confirm the same constant isn't defined in two places and that two functions/scripts doing the same thing haven't been created, before declaring completion.

### 7. Agent-friendly structure (context engineering)

The context window is an agent's fundamental constraint. A giant single file is bad for both humans and agents.

- One file holds one concern only. When a file grows long, consider splitting it.
- Per-module docs (a README or AGENTS.md in that directory) should contain only content scoped to that directory (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)
