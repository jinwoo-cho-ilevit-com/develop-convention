---
name: code-and-config
description: Routes to the conventions that govern file layout and naming, configuration, the local toolchain, secrets, and agent sandboxing. Use when creating, moving, or renaming files, when adding a dependency or a config value, when any credential is involved, or when an agent runs unattended, in CI, or on untrusted input.
---

# code-and-config — Layout, Config, Toolchain, Secrets, Sandboxing

Routing procedure for conventions [01-structure-naming.md](../../conventions/01-structure-naming.md), [02-config.md](../../conventions/02-config.md), [03-environment.md](../../conventions/03-environment.md), [13-secret-management.md](../../conventions/13-secret-management.md) and [25-agent-sandboxing.md](../../conventions/25-agent-sandboxing.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

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
| An agent is about to run with prompts skipped, unattended, or as a CI step | 25 |
| An agent will read issue or pull-request text, comments, or fetched pages | 25 |

## Order

1. **13 first when a credential is anywhere in scope.** It and 25 are the two whose violation a later commit cannot undo.
2. **25 before the agent starts**, when it will run without a person approving each step or on input a stranger wrote. The boundary is set before the session; nothing after it takes back what the session sent out.
3. **01 while writing.** Naming and placement are cheapest to get right before the file exists and most expensive after other code imports it.
4. **02 the moment a literal appears** that another run might want different.
5. **03 when the change touches the toolchain** rather than the source — dependencies, pins, hooks, containers.

## Boundaries with other skills

Committing the result is [commit](../commit/SKILL.md) — peeled out because it fires far more often than the rest of this bucket. Pipeline and training code has additional shape rules in [ml-pipeline](../ml-pipeline/SKILL.md); code that calls someone else's model API has its own in [external-sources](../external-sources/SKILL.md). Both compose with this skill rather than replacing it. An unattended agent session also meets the review gate's rule on blocking hooks, which [verify-and-review](../verify-and-review/SKILL.md) routes to.

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
When adding or moving files, config, dependencies, or credentials, or running an agent
unattended, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/code-and-config/SKILL/
```
