---
name: external-sources
description: Routes to the conventions that govern calling third-party LLM APIs, provider capability differences, verifying upstream documentation, and researching factual specs. Use when writing code against someone else's SDK or model API — including an evaluation or judging pipeline whose model runs on someone else's hardware — or when the deliverable itself is a claim about an external product, such as versions, pricing, lineups, or capabilities.
---

# external-sources — Provider APIs, Upstream Docs, Factual Research

Routing procedure for conventions [10-llm-api-inference.md](../../conventions/10-llm-api-inference.md), [11-llm-api-providers.md](../../conventions/11-llm-api-providers.md), [12-upstream-docs.md](../../conventions/12-upstream-docs.md) and [16-research-protocol.md](../../conventions/16-research-protocol.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the documents from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to them and does not restate them; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| The shape of code that calls someone else's model | 10 |
| Concurrency, retries, and which layer owns them | 10 |
| Caching, resuming, and knowing what a run cost | 10 |
| Which provider supports what | 11 |
| Structured output when the provider does not offer it natively | 11 |
| Is what I remember about this SDK still true, and where do I check | 12 |
| Which source outranks which, and when a smoke test is the only answer | 12 |
| The deliverable is a factual claim about an external product | 16 |
| Enumerating variants, or asserting that something does not exist | 16 |

## Order

1. **12 before writing a line against an unfamiliar SDK.** Training data goes stale silently, and the failure mode is confident, plausible, wrong.
2. **11 when more than one provider is in play,** or when a capability you assumed turns out to be provider-specific.
3. **10 while writing the calling code** — adapter shape, concurrency, retries, cost.
4. **16 instead of all three** when nobody is writing code and the facts are the product.

## 12 or 16 — they divide the same territory

Both are about not trusting what you remember. The split is what you are producing.

| You are | Read |
|---|---|
| Looking something up in order to write code | 12 |
| Producing the facts themselves as the deliverable | 16 |

16 is the stricter of the two, because a wrong fact in a document has nothing downstream that will fail and reveal it.

## Boundaries with other skills

Training or serving the model yourself is [ml-pipeline](../ml-pipeline/SKILL.md) — the split is who runs the weights. API keys reach the process under [code-and-config](../code-and-config/SKILL.md).

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
When calling a third-party model API or researching external facts, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/external-sources/SKILL/
```
