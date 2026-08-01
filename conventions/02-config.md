# 02. Central Config + Ablation

## Core Rules

- No hardcoding, ever. Manage hyperparameters, paths, constants, and magic values entirely in central config.
- Compose config as Hydra config groups so they can be combined. Build experiment variants (ablation) purely from config composition/overrides, without code changes.
- Validate config values' types and ranges (Pydantic or a typed dataclass). Invalid values must fail fast before the run starts.
- Every run automatically saves its full resolved config, as of that point, to the output directory.
- Externalize LLM prompts into dedicated `.md` files instead of inline string literals — prompts should be editable and reviewable without code changes.

## Details

Name runs identifiably (`{experiment-name}-{key-condition}-{date}`) so a directory listing is readable months later.


### 1. Scope of the no-hardcoding rule

Things that must not be written directly in code: file paths, model names/checkpoint paths, batch size, learning rate, seed, sample count limits, API endpoints, device strings, thresholds. These are all config fields.

Exception: values that are invariant by mathematical definition (e.g., 1000 milliseconds per second) are allowed as named constants in code. "A value that probably won't change for now" is not an exception.

### 2. Tool choice: Hydra + a validation layer

As of 2025-2026, Hydra is the de facto standard for hierarchical, composable config.

- **config group**: split by axis, like `configs/model/`, `configs/data/`, `configs/train/`, and define experiments as compositions.
- **ablation**: a combinatorial sweep becomes a single line, e.g. `python train.py --multirun model=base,large data=full,filtered`. Each run automatically saves config+logs to an isolated output directory.
- **validation layer**: the combination of Hydra (composition) and Pydantic (type/range validation) is the currently recommended pattern. A value like `train_size=1.5` must fail before training starts.
- Lightweight alternative: if you want code-first typed config without YAML, use tyro (dataclass-based, strong static type checking) or draccus. Pick one per project and use it consistently.

Sources: [Hydra — configuring experiments](https://hydra.cc/docs/patterns/configuring_experiments/), [Configuration management for model training experiments using Pydantic and Hydra](https://towardsdatascience.com/configuration-management-for-model-training-experiments-using-pydantic-and-hydra-d14a6ae84c13/), [tyro](https://github.com/brentyi/tyro), [draccus](https://github.com/dlwh/draccus)

### 3. Ablation study structure

- Defining experiment axes (model size, data filtering, training technique, etc.) as config groups expresses every combination declaratively.
- Each combination run's results must be logged to an experiment tracking tool alongside its config, so "which combination gave which performance" can be compared without opening the code (→ [07-ml-development.md](07-ml-development.md)).
- Manage the list of ablation combinations itself as a config file — it's only an experiment if it's re-runnable.

### 4. Prompt externalization

LLM prompts get the same treatment as config: inlining them in code means a one-line prompt fix requires a code review and deployment, and diffs mix prompt changes with logic changes. Separating them into dedicated `.md` files (e.g., `prompts/summarize.md`) turns prompt editing into doc editing, so version control, review, and experiment tracking run independently of the logic. The prompt file path itself is a config field.

### 5. Config snapshots and reproducibility

- A run's output directory must retain, at minimum: the full resolved config (after overrides applied), the git commit hash, and the run command.
- Hydra automatically saves config to each run's output directory. Don't turn off this default behavior.
- Version-control config files alongside code. "That run's settings at that time" must be recoverable from commit history.
