# 03. Toolchain + Environment Portability

## Core Rules

- Manage Python projects with uv: `pyproject.toml` + `uv.lock` (committed) + `.python-version`. Run via `uv run`.
- Unify lint and format on ruff alone (`ruff check` + `ruff format`).
- Put development tools in the dev group under `[dependency-groups]`. Do not mix them into runtime `dependencies`.
- Check lint/format twice: pre-commit (local) + CI (enforced).
- Code must run identically, without modification, on local (macOS, CPU/MPS) and RunPod (Linux, CUDA).
- Without a GPU, the code must still be runnable and testable on CPU. Select the device only through a single helper function; inline `.cuda()` calls are forbidden.
- Route PyTorch installation automatically per platform using uv platform markers or `--torch-backend=auto`.

## Details

### 1. 2026 Standard Toolchain

- **uv**: a single tool that replaces pip/pipenv/pyenv/virtualenv. `uv.lock` is a cross-platform lockfile — always commit it and never hand-edit it. `uv run` verifies lockfile↔pyproject↔env sync before every run. Core commands: `uv init`, `uv add`, `uv add --dev`, `uv sync`, `uv run`.
- **ruff**: replaces black/flake8/isort/pyupgrade entirely. A single `[tool.ruff]` config. Recommended lint set: `["E", "F", "I", "UP", "B"]`.
- **Type checker**: the default recommendation is mypy (safe, maximally compatible). If speed matters, explicitly pick exactly one of pyrefly (stable at 1.0) or ty (native to the uv/ruff ecosystem, still beta) per project. Do not mix them.
- **pre-commit**: use the `astral-sh/ruff-pre-commit` hook. Local hooks can be skipped, so enforce them finally in CI with `uvx pre-commit run --all-files`.

Baseline pyproject.toml:

```toml
[project]
name = "my-project"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Sources: [uv — projects guide](https://docs.astral.sh/uv/guides/projects/), [ruff](https://docs.astral.sh/ruff/), [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), [type checker comparison](https://pydevtools.com/handbook/explanation/how-do-mypy-pyright-and-ty-compare/)

### 2. Local ↔ RunPod Portability

A single pyproject.toml must cover both environments. PyTorch has no CUDA build for macOS, so platform-specific index routing is required.

Method A — automatic routing via platform marker (recommended):

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cpu",  marker = "sys_platform != 'linux'" },
  { index = "pytorch-cuda", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cuda"
url = "https://download.pytorch.org/whl/cu130"  # Match the CUDA version to the target pod
explicit = true
```

Method B — `--torch-backend=auto` (or `UV_TORCH_BACKEND=auto`): detects the CUDA driver at install time to pick the index, falling back to CPU if none is found. Suited to ephemeral environments with changing GPU configurations, like RunPod.

Sources: [uv — PyTorch integration](https://docs.astral.sh/uv/guides/integration/pytorch/)

### 3. Device Abstraction (CPU Fallback)

Select the device through exactly one helper function per project. Base it on the `torch.accelerator` API (a unified CUDA/MPS/XPU abstraction), but guard it since older torch versions lack this API.

```python
def get_device() -> torch.device:
    if hasattr(torch, "accelerator") and torch.accelerator.is_available():
        return torch.accelerator.current_accelerator()
    return torch.device("cpu")
```

- It must be overridable via config (force CPU testing with `device: cpu`).
- Inline `.cuda()` or `"cuda:0"` strings are forbidden — they are the main culprit that breaks CPU fallback.
- CI verifies GPU code paths with small-sample smoke tests on CPU (→ [06-testing-verification.md](06-testing-verification.md)).

Sources: [PyTorch — accelerator device API](https://docs.pytorch.org/docs/main/accelerator/device.html)

### 4. Docker

When using Docker, combine it with uv and keep it thin: copy only the lockfile and pyproject.toml first → run `uv sync` as a cache layer → then copy the source. uv.lock handles reproducibility; the image handles the Linux/CUDA runtime.
