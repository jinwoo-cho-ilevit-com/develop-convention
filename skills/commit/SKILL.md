---
name: commit
description: Routes to the commit protocol — header form, which types require a body, the body sections, and the trailers. Use immediately before running git commit, or when splitting a working tree into commits.
---

# commit — The Commit Protocol

Routing procedure for convention [06-commit-protocol.md](../../conventions/06-commit-protocol.md).

## What 06 decides

| Question | Where in 06 |
|---|---|
| The header form, and the length it is counted in | Core Rules |
| Which change types require a body, and which sections that body has | Core Rules, and the template under Details |
| What goes in the section that reports a result, when nothing was measured | Core Rules |
| Which trailers apply, and which identifier is reused across a research thread | Core Rules |
| What language each part is written in | Core Rules |

## Order

06 gives the sequence — survey, group, split, then write — in its Core Rules and again as a worked procedure under Details. Follow it from there rather than from memory: the survey step names more commands than the two that are obvious, and the split step names which interactive form is unavailable inside an agent harness.

The step that gets skipped is the first one, and skipping it is what produces the commit that bundles an unrelated fix. Nothing later in the sequence recovers from it.

## Boundaries with other skills

What the code should have looked like before it was committed is [code-and-config](../code-and-config/SKILL.md).
