---
name: code-and-config
description: Routes to the conventions that govern file layout, naming, and configuration. Use when creating, moving, or renaming files, or when adding a config value.
---

# code-and-config — Layout and Config

Routing procedure for conventions [01-structure-naming.md](../../conventions/01-structure-naming.md) and [02-config.md](../../conventions/02-config.md).

## Which document decides what

| Question | Document |
|---|---|
| Where this file goes, and what it is called | 01 |
| Whether this is one module or two | 01 |
| How much comment or doc this deserves, and when to rewrite rather than extend | 01 |
| What to do with the code this change just made dead | 01 |
| This value is inline — where does it belong instead | 02 |
| Where prompts live, and how a run records the config it actually used | 02 |

## Order

1. **01 while writing.** Naming and placement are cheapest to get right before the file exists and most expensive after other code imports it.
2. **02 the moment a literal appears** that another run might want different.

## Boundaries with other skills

Committing the result is [commit](../commit/SKILL.md) — peeled out because it fires far more often than the rest of this bucket. Pipeline code has additional shape rules in [pipeline](../pipeline/SKILL.md); code that calls someone else's model API has its own in [external-sources](../external-sources/SKILL.md). Both compose with this skill rather than replacing it.
