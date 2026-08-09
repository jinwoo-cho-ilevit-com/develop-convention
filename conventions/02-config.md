# 02. Central Config + Ablation

## Core Rules

- No hardcoding, ever. Manage hyperparameters, paths, constants, and magic values entirely in central config.
- Split config into groups along one axis each, so they compose. Build experiment variants (ablation) purely from composition and overrides, without code changes.
- Validate config values' types and ranges (Pydantic or a typed dataclass). Invalid values must fail fast before the run starts.
- Every run automatically saves its full resolved config, as of that point, to the output directory.
- Externalize LLM prompts into dedicated `.md` files instead of inline string literals — prompts should be editable and reviewable without code changes.

## Details

Name runs identifiably (`{experiment-name}-{key-condition}-{date}`) so a directory listing is readable months later.


### 1. Scope of the no-hardcoding rule

Things that must not be written directly in code: file paths, model names/checkpoint paths, batch size, learning rate, seed, sample count limits, API endpoints, device strings, thresholds. These are all config fields.

Exception: values that are invariant by mathematical definition (e.g., 1000 milliseconds per second) are allowed as named constants in code. "A value that probably won't change for now" is not an exception.

### 2. What the config layer has to provide

No tool is prescribed here. Pick one per project and use it consistently; what the choice may not trade away is this:

- **composition by axis**: groups like `configs/model/`, `configs/data/`, `configs/train/`, with an experiment being a named combination of them rather than a file per variant.
- **sweeps from that same composition**: a combinatorial run is one command over the group values. A loop written per variant is the thing composition exists to avoid, and it drifts from the single-run path the moment either is edited.
- **validation at load**: types and ranges checked while the config is assembled, so `train_size=1.5` fails before the run starts rather than mid-training. Typed dataclasses cover shape; pair them with a constraint validator (Pydantic) for what a type cannot express.
- **a run snapshot nobody has to remember**: §5 states the requirement. A tool that writes it by default satisfies it; a tool that does not leaves the runner to, which is a step that gets skipped exactly when a run turns out to matter.

Code-first without YAML: tyro (dataclass-based, strong static type checking) or draccus.

Sources: [tyro](https://github.com/brentyi/tyro), [draccus](https://github.com/dlwh/draccus) (as of: 2026-08)

### 3. Ablation study structure

- Defining experiment axes (model size, data filtering, training technique, etc.) as config groups expresses every combination declaratively.
- Each combination run's results must be logged to an experiment tracking tool alongside its config, so "which combination gave which performance" can be compared without opening the code (→ [07-ml-development.md](07-ml-development.md)).
- Manage the list of ablation combinations itself as a config file — it's only an experiment if it's re-runnable.

### 4. Prompt externalization

LLM prompts get the same treatment as config: inlining them in code means a one-line prompt fix requires a code review and deployment, and diffs mix prompt changes with logic changes. Separating them into dedicated `.md` files (e.g., `prompts/summarize.md`) turns prompt editing into doc editing, so version control, review, and experiment tracking run independently of the logic. The prompt file path itself is a config field.

### 5. Config snapshots and reproducibility

- A run's output directory must retain, at minimum: the full resolved config (after overrides applied), the git commit hash, and the run command.
- Where the config tool writes that snapshot by default, leave the default on; where it does not, the runner writes it. Either way it is not the caller's job to remember.
- Version-control config files alongside code. "That run's settings at that time" must be recoverable from commit history.
