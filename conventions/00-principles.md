# 00. Core Principles

The foundation for all convention documents. When it conflicts with another document, this document takes precedence.

## Core Rules

- Start from requirements and observed behavior. Inspect existing code, docs, and interfaces for behavior and compatibility constraints; do not treat their structure as the required design.
- Add implementation, configuration, abstraction, or process only when a current requirement, observed failure risk, or measured constraint justifies its cost. Prefer the simplest design that meets the acceptance criteria and preserves required behavior.
- Don't decide from prior knowledge. Verify library/API/model facts against current-point-in-time primary sources before applying them — what counts as one is [05-research-protocol.md](05-research-protocol.md) §2 for factual specs and [04-upstream-docs.md](04-upstream-docs.md) §1 for provider APIs.
- Use a fresh context for independent review and substantial refactoring or rewrites; scale review depth to the work's risk.
- Match completion claims to evidence: use execution results for behavior, measurements for performance, and direct source inspection for static claims. Keep verification independent where the work's risk calls for it.
- When rewriting, preserve required behavior. Capture it with the smallest suitable existing check, sample run, or characterization test before the rewrite, then compare after it.
- Measure performance/productivity improvements — don't estimate them. If you didn't measure, write "not measured."

## Details

### 1. Independent fresh start

For a new project or a refactor, use the existing codebase to discover required behavior and compatibility boundaries. Choose the new structure from the requirements.

- Take from the existing code: **what it must do** (input/output contracts, behavior, edge cases, compatibility constraints)
- Don't take from the existing code: file structure, class hierarchy, naming, explanations embedded in comments, memory of "how it used to be done"
- Never carry over code, config, or scripts that the existing project doesn't use (→ [01-structure-naming.md](01-structure-naming.md))

### 2. Fresh-context principle

AI agents anchor to conclusions already present in context, and the anchoring has been measured. On meta-review generation, GPT-4o showed an anchoring coefficient toward the first reviewer of 0.255 against a 0.193 human-committee baseline, and the authors report the bias persists even when later reviews supply contradictory evidence. Separating the review session changes the outcome and not just the wording: in a controlled comparison, cross-context review reached F1 28.6% versus 24.6% for same-session review (p=0.008), while reviewing twice in the same session did not beat reviewing once (p=0.11) — so the gain comes from the context separation itself, not from the extra review.

Both are single studies (the second an unrefereed preprint). Treat the direction as evidence and the magnitudes as provisional.

Application:
- Code review is done by a fresh reviewer who starts from the diff and the requirements, never the session that wrote the code.
- When rewriting legacy code, inspect the relevant behavior and interfaces before choosing a structure; avoid reading unrelated areas. Compare the result with the behavior evidence selected for the work.

Sources: [Conflict-Aware Meta-Review Generation via Cognitive Alignment (arXiv 2503.13879)](https://arxiv.org/abs/2503.13879), [Cross-Context Review: Separating Production and Review Sessions (arXiv 2603.12123)](https://arxiv.org/abs/2603.12123), [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 3. Evidence over claims

"Done" means the acceptance criteria are met, not merely that the program terminated.

- Verify behavior with an appropriate execution or sample and inspect its output. Static claims can be checked from source; label them as static findings.
- Use independent verification or review when the change's risk requires it.
- Attach decisive evidence to claims: the relevant command and result, source location, or measurement.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 4. Measure first

Even the effect of using AI tools can run opposite to felt experience versus measurement. In METR's 2025 RCT, experienced developers estimated they were 20% faster with AI, but the measured result was 19% slower.
Apply the same principle to speed optimization, parallelization, and parallel agent development: to claim an improvement, measure before/after.

Sources: [METR — Early 2025 AI experienced OS dev study](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
