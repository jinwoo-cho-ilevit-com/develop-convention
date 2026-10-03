---
name: verify-and-review
description: Routes to the convention that governs testing and verification. Use before claiming a task complete, or when deciding which tests to write or run.
---

# verify-and-review — Tests and Verification

Routing procedure for convention [06-testing-verification.md](../../conventions/06-testing-verification.md).

## Which document decides what

| Question | Document |
|---|---|
| What the sample run checks, and when a test beyond it is warranted | 06 |
| When does a new test need a failing baseline, and what if it could not run at all | 06 |
| What a bug fix must show before and after, and what blocks completion | 06 |

## Order

1. **06 before writing tests.** It selects the smallest relevant existing check first and sets the reason for adding a durable test.
2. **06 again before claiming completion.** Run the narrowest relevant verification and inspect its decisive output.

## Boundaries with other skills

Pipeline stages and their sample modes are [ml-pipeline](../ml-pipeline/SKILL.md).
