# 02. Central Config + Ablation

## Core Rules

- Put values that vary by run, experiment, deployment, or environment in one resolved configuration. Keep fixed local invariants as named code constants.
- For experiments with independent axes, compose config groups and overrides so variants need no code changes.
- Validate config values' types and ranges (Pydantic or a typed dataclass). Invalid values must fail fast before the run starts.
- Persist the resolved config, git commit, and invocation with experiment or data-processing outputs that must be reproduced; make this automatic for those runs.
- Externalize LLM prompts into dedicated `.md` files instead of inline string literals — prompts should be editable and reviewable without code changes.

## Details

### 1. Scope of configuration

Values that vary between runs or environments belong in config: input/output paths, model and checkpoint choices, batch size, learning rate, seed, sample limits, API endpoints, device choice, and adjustable thresholds. A constant intrinsic to the algorithm or file format stays in code as a named constant. Do not expose a setting merely because a literal appears in code.

When uncertain, ask whether changing the value without a code review is a supported use case. If not, keep it close to its use until a real variant exists.

### 2. What the config layer has to provide

No tool is prescribed here. Pick one per project and use it consistently; what it may not trade away is validation at load: types and ranges checked while the config is assembled, so `train_size=1.5` fails before the run starts rather than mid-training. Typed dataclasses cover shape; pair them with a constraint validator (Pydantic) for what a type cannot express.

Code-first without YAML: tyro (dataclass-based, strong static type checking) or draccus.

Sources: [tyro](https://github.com/brentyi/tyro), [draccus](https://github.com/dlwh/draccus) (as of: 2026-08)

### 3. Ablation study structure

- Defining experiment axes (model size, data filtering, training technique, etc.) as config groups expresses every combination declaratively.
- Each combination run's results must be logged to an experiment tracking tool alongside its config, so "which combination gave which performance" can be compared without opening the code (→ [07-ml-development.md](07-ml-development.md)).
- Manage the list of ablation combinations itself as a config file — it's only an experiment if it's re-runnable.

### 4. Config snapshots and reproducibility

- Name runs identifiably (`{experiment-name}-{key-condition}-{date}`) so a directory listing is readable months later.
- Version-control config files alongside code. "That run's settings at that time" must be recoverable from commit history.
