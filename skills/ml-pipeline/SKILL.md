---
name: ml-pipeline
description: Routes to the conventions that govern pipeline stage shape and throughput. Use when building a preprocessing, training, or evaluation pipeline, or when something is too slow.
---

# ml-pipeline — Stages and Throughput

Routing procedure for conventions [04-pipeline.md](../../conventions/04-pipeline.md) and [05-performance.md](../../conventions/05-performance.md).

## Which document decides what

| Question | Document |
|---|---|
| How a stage is shaped so it runs alone, on a sample, and resumes after a kill | 04 |
| How a stage hands its output to the next one | 04 |
| A write that must not leave a half-file behind | 04 |
| What scale, time, memory, and cost targets does this run need to meet | 05 |
| It misses a target — where is the measured bottleneck | 05 |
| What to measure, and what to log while it runs | 05 |
| Whether a slow stage should move to a compiled language | 05 |

## Order

1. **05 to set the run's scale and resource targets, then 04 before writing a stage.** Use the targets to choose the simplest stage shape that meets them.
2. **05 again when a target is missed or repeated runs become costly.** Profile the whole flow and improve the largest bottleneck before changing concurrency or language.

## Boundaries with other skills

Looking up a third-party SDK or API is [external-sources](../external-sources/SKILL.md). File placement and config for this code still come from [code-and-config](../code-and-config/SKILL.md). Test tolerances, fixtures, and the sample runs CI runs on CPU are in [verify-and-review](../verify-and-review/SKILL.md).
