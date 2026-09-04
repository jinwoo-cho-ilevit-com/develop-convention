---
name: plan-and-delegate
description: Routes to the conventions that govern the development loop, work contracts, delegation, and context. Use when starting a piece of work larger than one edit — interviewing toward a plan, splitting work into lanes, deciding what "done" means, or handing a task to a subagent.
---

# plan-and-delegate — Loop, Contract, Delegation, Context

Routing procedure for conventions [21-development-loop.md](../../conventions/21-development-loop.md), [18-work-contract.md](../../conventions/18-work-contract.md), [09-agentic-workflow.md](../../conventions/09-agentic-workflow.md) and [14-context-management.md](../../conventions/14-context-management.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the documents from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to them and does not restate them; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| Where am I in the loop, and what does this step owe the next one | 21 |
| What do I have to ask before a plan exists, and when is the interview over | 21 |
| How do I split this so two lanes cannot collide | 18 |
| What does "done" mean here, what command decides it, what needs a person | 18 |
| What the plan must carry before it is shown | 18 |
| Subagent, workflow, or inline — and how much isolation | 09 |
| Which model, and what belongs in the instruction file rather than a skill | 09 |
| What stays in my context and what goes out to a subagent | 14 |
| What survives a compaction, and where the durable copy lives | 14 |

## Order

1. **21 first.** It holds the order of the loop and the seams between steps, and it points at the rest. Its interview rules are the only ones native to it — everything else there is a pointer, so follow the pointer rather than reading around it.
2. **18 when the work splits.** Ownership and completion criteria are cheap to settle before anyone writes code and expensive after, because by then the tree already encodes a different answer.
3. **09 when the work is dispatched.** Decomposition, isolation, and model routing. Also the test for whether something should become a skill at all.
4. **14 throughout.** This one is a posture, not a step: it governs what you read yourself versus what you send a subagent to read, for the whole session.

## Boundaries with other skills

Writing the code once the lanes exist is [code-and-config](../code-and-config/SKILL.md). Deciding whether the result is acceptable is [verify-and-review](../verify-and-review/SKILL.md); 18 sets the criteria, 20 runs the gate against them — the pre-approval plan challenge included.

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
Before starting work larger than one edit, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/plan-and-delegate/SKILL/
```
