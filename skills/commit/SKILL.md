---
name: commit
description: Routes to the commit protocol — header form, which types require a body, the body sections, and the trailers. Use immediately before running git commit, or when splitting a working tree into commits.
---

# commit — The Commit Protocol

Routing procedure for convention [17-commit-protocol.md](../../conventions/17-commit-protocol.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the document from `${CLAUDE_PLUGIN_ROOT}/conventions/17-commit-protocol.md` — the project you are working in does not carry a copy. This file routes to it and does not restate it; the template and the worked examples live there.

## What 17 decides

| Question | Where in 17 |
|---|---|
| The header form, and the length it is counted in | Core Rules |
| Which change types require a body, and which sections that body has | Core Rules, and the template under Details |
| What goes in the section that reports a result, when nothing was measured | Core Rules |
| Which trailers apply, and which identifier is reused across a research thread | Core Rules |
| What language each part is written in | Core Rules |

## Order

17 gives the sequence — survey, group, split, then write — in its Core Rules and again as a worked procedure under Details. Follow it from there rather than from memory: the survey step names more commands than the two that are obvious, and the split step names which interactive form is unavailable inside an agent harness.

The step that gets skipped is the first one, and skipping it is what produces the commit that bundles an unrelated fix. Nothing later in the sequence recovers from it.

## Boundaries with other skills

What the code should have looked like before it was committed is [code-and-config](../code-and-config/SKILL.md). Whether it is finished at all is [verify-and-review](../verify-and-review/SKILL.md) — a commit is not a completion claim, and 19 governs the latter.

## When documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
Before committing, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/commit/SKILL/
```
