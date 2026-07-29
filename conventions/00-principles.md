# 00. Core Principles

The foundation for all convention documents. When it conflicts with another document, this document takes precedence.

## Core Rules

- When starting new development, don't rely on the existing project's structure, comments, docs, or memory — start from requirements and behavior (the spec).
- Don't decide from prior knowledge. Verify library/API/model facts against current-point-in-time sources (context7, web search, HuggingFace, etc.) before applying them.
- Perform refactoring, review, and rewrites in a new context (a separate subagent/session) detached from the context that produced the existing code.
- Only claim completion with executable evidence (test output, run logs, measured values). Separate the author from the verifier.
- When rewriting, discard the existing structure but preserve existing behavior: pin down existing behavior with characterization tests before the rewrite, then confirm the same tests pass after the rewrite.
- Measure performance/productivity improvements — don't estimate them. If you didn't measure, write "not measured."
- Research current methodology before starting development, and adopt a better method when one is confirmed, instead of defaulting to habit.

## Details

### 1. Independent fresh start

For a new project or a refactor, treat the existing codebase's structure not as a "reference" but only as the origin of the behavioral spec.

- Take from the existing code: **what it must do** (input/output contracts, behavior, edge cases)
- Don't take from the existing code: file structure, class hierarchy, naming, explanations embedded in comments, memory of "how it used to be done"
- Never carry over code, config, or scripts that the existing project doesn't use (→ [01-structure-naming.md](01-structure-naming.md))

### 2. Fresh-context principle

AI agents anchor to conclusions already present in context. It's a measured problem that once a first conclusion is in context, a second review is biased toward validating it. Review dispatched in a separate context actually changes review behavior.

Application:
- Code review is done by a fresh reviewer who starts from the diff and the criteria, never the session that wrote the code.
- When rewriting legacy code, don't start by reading through the entire existing codebase. Write the spec first, implement from the spec alone, and check against existing behavior via tests.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 3. Evidence over claims

"Done" means the program terminated, not that the task succeeded.

- Verify by running: execute with real inputs and check real outputs. Reading code and saying "looks right" isn't verification.
- The judge must not be the author: whoever decides whether something is complete (tests, review agent, verification script) must be independent from whoever wrote the code.
- Attach evidence to claims: the command you ran + output/test results/screenshots.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 4. Research-first, fact-based judgment

- Library usage, model specs, versions, APIs — verify against current documentation, not trained memory. Prioritize context7, official docs, web search, and HuggingFace Hub lookups.
- Before choosing a framework/methodology, research its maintenance status and alternatives at that point in time (e.g., a tool that was once standard can become deprecated — torchtune, see [08-llm-development.md](08-llm-development.md)).
- Don't put facts unverified by research into docs, code, or commits — mark them "unverified" instead.

### 5. Measure first

Even the effect of using AI tools can run opposite to felt experience versus measurement. In METR's 2025 RCT, experienced developers estimated they were 20% faster with AI, but the measured result was 19% slower.
Apply the same principle to speed optimization, parallelization, and parallel agent development: to claim an improvement, measure before/after.

Sources: [METR — Early 2025 AI experienced OS dev study](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
