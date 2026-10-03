---
name: ml-pipeline
description: Routes to the convention that governs pipeline stage shape. Use when building a preprocessing, training, or evaluation pipeline, or when a stage must run on a sample, resume, or publish output safely.
---

# ml-pipeline — Stages

Routing procedure for convention [03-pipeline.md](../../conventions/03-pipeline.md).

## Which document decides what

| Question | Document |
|---|---|
| How a stage is shaped so it runs alone, on a sample, and resumes after a kill | 03 |
| How a stage hands its output to the next one | 03 |
| A write that must not leave a half-file behind | 03 |

## Order

1. **03 before writing a stage.** Choose the simplest stage shape that runs on a sample and resumes.

## Boundaries with other skills

Looking up a third-party SDK or API is [external-sources](../external-sources/SKILL.md). File placement and config for this code still come from [code-and-config](../code-and-config/SKILL.md).
