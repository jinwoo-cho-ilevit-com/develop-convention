---
name: code-and-config
description: Routes to the conventions that govern file layout and naming, configuration, the local toolchain, and secrets. Use when creating, moving, or renaming files, when adding a dependency or a config value, or when any credential is involved.
---

# code-and-config — Layout, Config, Toolchain, Secrets

Routing procedure for conventions [01-structure-naming.md](../../conventions/01-structure-naming.md), [02-config.md](../../conventions/02-config.md), [03-environment.md](../../conventions/03-environment.md) and [13-secret-management.md](../../conventions/13-secret-management.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the documents from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to them and does not restate them; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| Where this file goes, and what it is called | 01 |
| Whether this is one module or two | 01 |
| How much comment or doc this deserves, and when to rewrite rather than extend | 01 |
| What to do with the code this change just made dead | 01 |
| This value is inline — where does it belong instead | 02 |
| Where prompts live, and how a run records the config it actually used | 02 |
| Adding a dependency, pinning a tool, wiring a check | 03 |
| Will this run on the other OS, or without a GPU | 03 |
| This is a credential — how does it reach the process | 13 |
| A sample or a log might carry real data | 13 |

## Order

1. **13 first when a credential is anywhere in scope.** It is the only one of the four whose violation cannot be undone by a later commit.
2. **01 while writing.** Naming and placement are cheapest to get right before the file exists and most expensive after other code imports it.
3. **02 the moment a literal appears** that another run might want different.
4. **03 when the change touches the toolchain** rather than the source — dependencies, pins, hooks, containers.

## Boundaries with other skills

Committing the result is [commit](../commit/SKILL.md) — peeled out because it fires far more often than the rest of this bucket. Pipeline and training code has additional shape rules in [ml-pipeline](../ml-pipeline/SKILL.md); code that calls someone else's model API has its own in [external-sources](../external-sources/SKILL.md). Both compose with this skill rather than replacing it.

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
When adding or moving files, config, dependencies, or credentials, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/code-and-config/SKILL/
```
