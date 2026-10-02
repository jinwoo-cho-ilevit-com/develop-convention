---
name: verify-and-review
description: Routes to the conventions that govern testing and evidence. Use before claiming a task complete, when deciding which tests to write or run, or when reporting what a check showed.
---

# verify-and-review — Tests and Evidence

Routing procedure for conventions [06-testing-verification.md](../../conventions/06-testing-verification.md) and [19-evidence.md](../../conventions/19-evidence.md).

## Which document decides what

| Question | Document |
|---|---|
| What the sample run checks, and when a test beyond it is warranted | 06 |
| When does a new test need a failing baseline, and what if it could not run at all | 06 |
| How I report what I ran — the command, verdict, and decisive output | 19 |
| What to write when a check was skipped, bypassed, or waiting on a person | 19 |

## Order

1. **06 before writing tests.** It selects the smallest relevant existing check first and sets the reason for adding a durable test.
2. **19 when reporting.** Record the exact command, verdict, and decisive output, including checks that could not run.

## Boundaries with other skills

Checking that docs still match the code is [docsync](../docsync/SKILL.md). Testing code whose job is to drive another project's training framework needs a layer 06 does not describe — that is [ml-pipeline](../ml-pipeline/SKILL.md), routing to 22.
