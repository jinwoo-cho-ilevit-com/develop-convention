---
name: explainer-docs
description: Routes to the convention that governs human-facing explanatory documents. Use when writing a report, guide, tutorial, or HTML artifact whose reader is a person — before drafting, and again before shipping it.
---

# explainer-docs — Writing to Be Understood

Routing procedure for convention [24-explainer-docs.md](../../conventions/24-explainer-docs.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the document from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to it and does not restate it; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| When a term needs a plain-language gloss | 24 |
| What naming a methodology obliges the author to explain | 24 |
| When a concept needs an example, and of which kind | 24 |
| Which visual form fits what is being shown, in which medium | 24 |
| How long is long enough, and what gets cut | 24 |
| What an HTML deliverable must carry to stand alone | 24 |

## Order

1. **24 before drafting.** The layer structure is a decision made before the first paragraph, not a repair after it.
2. **24 again when a visual is considered.** The trigger decides whether it exists; the medium decides its form.
3. **20 before shipping.** An explainer's review is the fresh-reader lane — [verify-and-review](../verify-and-review/SKILL.md) routes it.

## Starting point

An HTML explainer is copied from `${CLAUDE_PLUGIN_ROOT}/skills/explainer-docs/explainer-skeleton.html`; the recipe gallery beside it is `explainer-gallery.html`. What the files carry, and when the gallery is opened, is documented inside them and in 24 — this file only points.

## Boundaries with other skills

Code-adjacent reference docs — AGENTS.md, ARCHITECTURE.md, managed module docs — are the other genre, synced by [docsync](../docsync/SKILL.md) under 15. Reviewing a finished explainer is [verify-and-review](../verify-and-review/SKILL.md), routing to 20. Facts an explainer asserts about external products follow [external-sources](../external-sources/SKILL.md).

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
Before writing a report, guide, or HTML page for a human reader, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/explainer-docs/SKILL/
The skeleton an HTML explainer starts from, and the recipe gallery beside it:
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/explainer-docs/explainer-skeleton.html
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/explainer-docs/explainer-gallery.html
```
