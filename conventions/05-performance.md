# 05. Async/Parallel Optimization + Profiling

## Core Rules

- Use the concurrency model that matches the bottleneck type: CPU-bound → multiprocessing, IO-bound → asyncio. Don't guess — identify the bottleneck with profiling first.
- Tune DataLoader's `num_workers`, `persistent_workers=True`, `pin_memory=True`, and `prefetch_factor`.
- Log GPU utilization, VRAM, RAM, CPU usage, and throughput at every pipeline stage.
- Structure logs as JSON. Include stage name / items processed / elapsed time / samples-per-sec / peak memory as required fields.
- Always compare before/after optimization with empirical measurement. Optimization claims without measurement are forbidden.
- Choose the implementation language from the measured bottleneck, never from expected speed: port a stage to a compiled language only under the conditions in §5.

## Details

### 1. Choosing Concurrency

- **CPU-bound preprocessing** (tokenization, image decoding, feature computation): multiprocessing. In PyTorch, DataLoader's `num_workers>0` serves this role. Note, though, that every sample passes through an inter-process queue, so the queue transfer itself can become a bottleneck.
- **IO-bound work** (API calls, file/network downloads, DB queries): asyncio. Single-thread concurrency keeps overhead low, but it only helps when actual non-blocking I/O is used.
- **Python free-threading (3.14t)**: PEP 779 (Final, Python 3.14) moved the free-threaded build to phase II — officially supported, but still a separate optional build installed under the `t`-suffixed tag. The GIL can be re-enabled at runtime (`PYTHON_GIL`, `-X gil`) and is re-enabled automatically when a C extension not marked free-thread-safe is imported — that case prints a warning rather than being silent. Maintain a "watch and verify by benchmark before adopting" stance.

Sources: [PyTorch — data loading tutorial](https://docs.pytorch.org/tutorials/intermediate/intermediate_data_loading_tutorial.html), [PEP 779 — criteria for supported status of free-threaded Python](https://peps.python.org/pep-0779/), [Python 3.14 release notes](https://docs.python.org/3/whatsnew/3.14.html), [Python — free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html) (as of: 2026-08)

### 2. DataLoader Tuning Checklist

- `num_workers`: start from core count, then adjust based on measurement
- `persistent_workers=True`: prevents worker recreation every epoch
- `pin_memory=True`: speeds up GPU transfer
- `prefetch_factor`: preloads data so the GPU doesn't wait
- The judgment criterion is GPU utilization: if GPU util is low while CPU is busy, it's a data-loading bottleneck.

### 3. Per-Stage Profiling

Instrument at three layers:

| Layer | Tool | Purpose |
|---|---|---|
| Per op/layer | `torch.profiler` | Breaks down CPU+CUDA time/memory by operation, pinpoints bottlenecks |
| Real-time observation | `nvitop`, `nvidia-smi dmon` | Check GPU util/VRAM per process in real time |
| Automatic per-run logging | Trackio system metrics | Logs GPU metrics (utilization/VRAM/power/temperature) in the background across the whole run — requires the matching extra (`trackio[gpu]` / `trackio[apple-gpu]`) installed and compatible hardware detected |

- There are two headline metrics: **VRAM usage** and **GPU utilization (%)**. Record these two plus RAM/CPU at every pipeline stage.
- In-code instrumentation: have one shared helper that logs `torch.cuda.max_memory_allocated()` (when using CUDA) and `psutil`-based RAM/CPU at stage start/end, and have every stage share it.

Sources: [nvitop](https://github.com/XuehaiPan/nvitop), [Trackio — logging system metrics](https://huggingface.co/docs/trackio/en/track), [NVIDIA NVML — utilization metrics](https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceStructs.html) (GPU utilization = percent of time one or more kernels was executing; memory utilization = percent of time device memory was being read or written)

### 4. Structured Logging

- Standardize on structlog-based JSON logging. Library-style code should use only stdlib `logging` + `NullHandler`.
- Required stage log fields: `stage`, `num_processed`, `elapsed_sec`, `samples_per_sec`, `peak_vram_mb` (when using GPU), `peak_ram_mb`.
- Progress display for humans is tqdm/rich; the machine-readable record is JSON logs — separate the roles, but keep both.

Sources: [structlog](https://pypi.org/project/structlog/)

### 5. Language choice

Port a stage or hot loop to a compiled language (Rust via PyO3/maturin, or a standalone binary) only when all of these hold:

- profiling shows it CPU-bound in pure computation — not I/O, GPU, serialization or call overhead;
- its inputs and outputs are files only, so no Python object crosses the boundary;
- the Python-side options (vectorization, multiprocessing, an existing compiled library) were measured and fail the throughput criterion the module's contract carries (→ [18-work-contract.md](18-work-contract.md)). A module whose contract carries no such criterion is not a candidate.

The port must build and run unmodified on both hosts [03-environment.md](03-environment.md) names. A port is a rewrite: the characterization test, the sample run over the stage's boundary files and the before/after evidence it needs are set by [00-principles.md](00-principles.md), [06-testing-verification.md](06-testing-verification.md) §1 and [19-evidence.md](19-evidence.md).

- A language port changes nothing when the bottleneck is elsewhere: a stage waiting on disk, the network, the GPU, or serialization runs at the same speed in any language, and a stage dominated by per-call overhead into a compiled library is fixed by batching the calls, not by rewriting the caller. The profile decides, which is why it is the first condition above.
- A PyO3/maturin extension or a standalone binary sits naturally at a stage boundary: the port replaces the inside of one stage, and that stage's existing debugging surface (→ [04-pipeline.md](04-pipeline.md)) becomes the characterization surface for the port.
- The throughput criterion lives in the module's work contract because one repository-wide number fits no module — a tokenizer and an image decoder do not share a floor — and because of when [18-work-contract.md](18-work-contract.md) fixes a contract, the criterion cannot be written after the measurement to justify a port already wanted.
