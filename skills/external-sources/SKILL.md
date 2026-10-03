---
name: external-sources
description: Routes to the conventions that govern verifying upstream documentation and researching factual specs. Use when writing code against someone else's SDK or model API, or when the deliverable itself is a claim about an external product, such as versions, pricing, lineups, or capabilities.
---

# external-sources — Upstream Docs, Factual Research

Routing procedure for conventions [04-upstream-docs.md](../../conventions/04-upstream-docs.md) and [05-research-protocol.md](../../conventions/05-research-protocol.md).

## Which document decides what

| Question | Document |
|---|---|
| Is what I remember about this SDK still true, and where do I check | 04 |
| Which source outranks which, and when a smoke test is the only answer | 04 |
| The deliverable is a factual claim about an external product | 05 |
| Enumerating variants, or asserting that something does not exist | 05 |

## Order

1. **04 before writing a line against an unfamiliar SDK.** Training data goes stale silently, and the failure mode is confident, plausible, wrong.
2. **05 instead of 04** when nobody is writing code and the facts are the product.

## 04 or 05 — they divide the same territory

Both are about not trusting what you remember. The split is what you are producing.

| You are | Read |
|---|---|
| Looking something up in order to write code | 04 |
| Producing the facts themselves as the deliverable | 05 |

05 is the stricter of the two, because a wrong fact in a document has nothing downstream that will fail and reveal it.

## Boundaries with other skills

Training or serving the model yourself is [pipeline](../pipeline/SKILL.md).
