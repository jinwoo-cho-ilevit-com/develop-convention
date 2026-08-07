---
name: verify-and-review
description: Routes to the conventions that govern testing, evidence, and the review gate. Use before claiming a task complete, when deciding which tests to write or run, or when reviewing a diff.
---

# verify-and-review — Tests, Evidence, and the Review Gate

Routing procedure for conventions [06-testing-verification.md](../../conventions/06-testing-verification.md), [19-evidence.md](../../conventions/19-evidence.md) and [20-review-gate.md](../../conventions/20-review-gate.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the documents from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to them and does not restate them; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| Which tests this change needs, and which it does not | 06 |
| What a contract test pins, and what belongs in one fixture rather than two | 06 |
| Did I watch it fail before it passed, and what if it could not run at all | 06 |
| How I report what I ran — the table, the words, the real output | 19 |
| What to write when a check was skipped, bypassed, or waiting on a person | 19 |
| Who reviews this, and what input each reviewer gets | 20 |
| When the review loop stops, and which exits need a human | 20 |

## Order

1. **06 before writing tests.** It sets the budget and the layers. The common failure is not too few tests, it is a suite that grew per-function and now catches nothing.
2. **20 before reviewing.** Settling who reviews, and against what input, only once the diff exists means settling it inside the author's context — which is the thing the gate exists to prevent.
3. **19 when reporting either.** A criteria table with real output, not a narrative. This is also where the vocabulary lives for the case that is neither pass nor fail.

## Boundaries with other skills

The criteria this skill checks against are written earlier, under [plan-and-delegate](../plan-and-delegate/SKILL.md) — 18 states them, 20 judges against them, 19 records the judgment. Checking that docs still match the code is [docsync](../docsync/SKILL.md).

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
Before claiming completion or reviewing a diff, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/verify-and-review/SKILL/
```
