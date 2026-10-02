# 03. Toolchain + Environment Portability

## Core Rules

- Manage Python projects with uv: `pyproject.toml` + `uv.lock` (committed) + `.python-version`. Run via `uv run`.
- Unify lint and format on ruff alone (`ruff check` + `ruff format`).
- Put development tools in the dev group under `[dependency-groups]`. Do not mix them into runtime `dependencies`.
- Check lint/format twice: pre-commit (local) + CI (enforced).
- For ML projects that target both local macOS (CPU/MPS) and remote Linux (CUDA), keep source code portable across those targets; allow documented numerical differences.
- Where CPU fallback is a project requirement, select the device through one helper and avoid inline `.cuda()` calls.
- For multi-platform PyTorch projects, route installation per platform using uv platform markers or `--torch-backend=auto`.

## Details

### 1. 2026 Standard Toolchain

- **uv**: a single tool that replaces pip/pipenv/pyenv/virtualenv. `uv.lock` is a cross-platform lockfile — always commit it and never hand-edit it. `uv run` verifies lockfile↔pyproject↔env sync before every run. Core commands: `uv init`, `uv add`, `uv add --dev`, `uv sync`, `uv run`.
- **ruff**: replaces black/flake8/isort/pyupgrade entirely. A single `[tool.ruff]` config. Recommended lint set: `["E", "F", "I", "UP", "B"]`.
- **Type checker**: the default recommendation is mypy (safe, maximally compatible). If speed matters, explicitly pick exactly one of pyrefly (stable since its 1.0.0 release on 2026-05-12; 1.2.0 as of 2026-08) or ty (native to the uv/ruff ecosystem, still beta on `0.0.x` versioning with no stable API; 0.0.65 as of 2026-08) per project. Do not mix them.
- **pre-commit**: use the `astral-sh/ruff-pre-commit` hook. Local hooks can be skipped, so enforce them finally in CI with `uvx pre-commit run --all-files`.

Baseline pyproject.toml:

```toml
[project]
name = "my-project"
requires-python = ">=3.13"   # 3.13 is still in bugfix support (EOL scheduled 2029-10)
dependencies = []

[dependency-groups]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Sources: [uv — projects guide](https://docs.astral.sh/uv/guides/projects/), [ruff](https://docs.astral.sh/ruff/), [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), [pyrefly 1.0.0 release](https://github.com/facebook/pyrefly/releases/tag/1.0.0), [pyrefly releases](https://github.com/facebook/pyrefly/releases), [ty — version policy](https://github.com/astral-sh/ty#version-policy), [Python devguide — version status](https://devguide.python.org/versions/) (as of: 2026-08)

### 2. Local ↔ Remote GPU Portability

When both environments are supported, one pyproject.toml should cover them. PyTorch has no CUDA build for macOS, so platform-specific index routing is required for that setup.

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

Method B — `--torch-backend=auto` (or `UV_TORCH_BACKEND=auto`): detects the CUDA driver at install time to pick the index, falling back to CPU if none is found. Suited to ephemeral environments with changing GPU configurations.

Sources: [uv — PyTorch integration](https://docs.astral.sh/uv/guides/integration/pytorch/) (uses `whl/cu130` in its own example), [PyTorch wheel index listing](https://download.pytorch.org/whl/) (as of: 2026-08)
