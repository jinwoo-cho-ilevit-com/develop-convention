---
name: ml-pipeline
description: Routes to the conventions that govern pipeline stage shape, throughput, ML experiment discipline, and training or serving a model yourself. Use when building a preprocessing, training, or evaluation pipeline over weights you run yourself, when something is too slow, or when handling seeds, checkpoints, and experiment tracking. For a pipeline whose model is called over someone else's API, use external-sources instead.
---

# ml-pipeline — Stages, Throughput, Experiments, Self-Hosted Models

Routing procedure for conventions [04-pipeline.md](../../conventions/04-pipeline.md), [05-performance.md](../../conventions/05-performance.md), [07-ml-development.md](../../conventions/07-ml-development.md) and [08-llm-development.md](../../conventions/08-llm-development.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

Read the documents from `${CLAUDE_PLUGIN_ROOT}/conventions/` — the project you are working in does not carry a copy. This file routes to them and does not restate them; a rule written twice drifts.

## Which document decides what

| Question | Document |
|---|---|
| How a stage is shaped so it runs alone, on a sample, and resumes after a kill | 04 |
| How a stage hands its output to the next one | 04 |
| A write that must not leave a half-file behind | 04 |
| It is too slow — and is the bottleneck CPU or IO | 05 |
| What to measure, and what to log while it runs | 05 |
| Seeds, and why one helper rather than several | 07 |
| Which run produced this number, at which config and which commit | 07 |
| Checkpoints: what to keep, and surviving a pod that disappears | 07 |
| Training or serving an LLM yourself — framework, precision, sharding | 08 |
| The chat template, and proving train and inference agree on it | 08 |
| Evaluation that another run can reproduce, and where a judge is biased | 08 |
| Deduplicating and decontaminating training data | 08 |

## Order

1. **04 before writing a stage.** What it asks of a stage is structural, so retrofitting means rewriting rather than adding.
2. **07 as soon as a run produces a number** anyone might cite later — earlier than it feels, because by the time someone asks, the run that produced it is gone.
3. **08 only when the model is yours to train or serve.**
4. **05 last.** It comes last because each of the three above changes what there is to measure.

## Boundaries with other skills

Calling a model over someone else's API is [external-sources](../external-sources/SKILL.md), not 08 — the split is who runs the weights. File placement, config, and secret handling for this code still come from [code-and-config](../code-and-config/SKILL.md). Test tolerances, fixtures, and GPU paths exercised on CPU are in [verify-and-review](../verify-and-review/SKILL.md).

## When two documents disagree

[00-principles.md](../../conventions/00-principles.md) takes precedence over any of them.

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
When building a data or training pipeline, follow the routing at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/ml-pipeline/SKILL/
```
