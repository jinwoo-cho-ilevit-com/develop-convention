# 07. Common AI/ML Development Practices

## Core Rules

- Set all seeds (random/numpy/torch/CUDA/DataLoader worker) at once with a single helper.
- Training and inference import the same preprocessing code (the same function). Don't duplicate preprocessing logic.
- Verify train/inference consistency with a sample replay comparison: feed the same input through both paths and compare element-wise.
- Prioritize performance optimization (speed/memory) over adding features. Apply proven optimizations like bf16 and optimized attention by default.
- Log every run to an experiment tracking tool along with its config + git commit.
- Checkpoints preserve last-N + best + milestones, and are stored on a network volume or HF Hub rather than temporary pod disk.
- Assume training can be interrupted at any time and make it resumable (spot pods are the default assumption).

## Details

### 1. Reproducibility

Unify around a single seed helper:

```python
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)          # CPU + all CUDA devices
    torch.use_deterministic_algorithms(True)  # error if no deterministic implementation exists
    torch.backends.cudnn.benchmark = False
```

- Seed DataLoader workers too, via `worker_init_fn` + `generator`.
- Document the limits: **bit-exact reproducibility is not guaranteed across different hardware (GPU generation), batch size, parallelism configuration, or framework version** (floating-point non-associativity, kernel selection differences). That's why tests use tolerance bands (→ [06-testing-verification.md](06-testing-verification.md)).
- Turn on deterministic mode by default. The performance cost is often not large but varies by workload, so only turn it off — and record that — once it's measured to be a bottleneck.

Sources: [PyTorch — reproducibility notes](https://glaringlee.github.io/notes/randomness.html), [Training reproducibility in PyTorch](https://learnopencv.com/ensuring-training-reproducibility-in-pytorch/)

### 2. Train/inference consistency (train-serve skew)

If preprocessing differs between training and inference, the model silently degrades — with no exception and no error.

- **Unify the code path**: define preprocessing/feature transforms in one place and have both training and inference import the same function. "Reimplementing similarly for inference" is the usual culprit behind skew.
- **Match dtypes**: mismatches like training float32 vs. serving float64 flip results near boundary values.
- **Replay verification**: keep a script that passes recent inference inputs through the training preprocessing path too, and compares them element-wise. This catches code-path branches that fixed unit tests miss.
- LLM chat template consistency has its own separate rule (→ [08-llm-development.md](08-llm-development.md)).

Sources: [Confluent — eliminate training-serving skew](https://www.confluent.io/blog/eliminate-training-serving-skew-mlops/), [Hopsworks — training-inference skew](https://www.hopsworks.ai/dictionary/training-inference-skew)

### 3. Experiment tracking

- Use **W&B** if you need team sharing and dashboards; use **Trackio** (HuggingFace, a W&B API-compatible drop-in — `wandb.init/log/finish` works as-is) if you want local-first, lightweight, and free. Use MLflow if self-hosting is a strong requirement.
- Regardless of tool, the invariant rule: every run is logged linked to (a) the resolved config, (b) the git commit hash, and (c) the data version/path. An untracked experiment is not an experiment.
- Run naming follows the convention in the config doc (→ [02-config.md](02-config.md)).

Sources: [Trackio](https://huggingface.co/blog/trackio), [W&B experiment tracking](https://wandb.ai/site/experiment-tracking/)

### 4. Checkpoints and interruption resilience

- **Saving**: save only from the main process, unwrap DDP/FSDP wrappers, include optimizer state. For large models, use DCP `async_save` (background save) + safetensors (→ [04-pipeline.md](04-pipeline.md)).
- **Retention policy**: `latest` (for resume) + step-based last-N + best-by-metric + major milestones. Set the specific N via the project config.
- **Storage location**: RunPod pod local disk disappears with the pod. Store on a network volume or HF Hub/bucket.
- **Cost optimization**: use spot/interruptible pods for interruption-tolerant work (sweeps, non-urgent experiments) — which is why all training must be resumable. Use reserved only for long-running training that needs guarantees.

Sources: [RunPod — reproducible training/checkpoint guide](https://www.runpod.io/articles/guides/reproducible-ai-made-easy-versioning-data-and-tracking-experiments)
