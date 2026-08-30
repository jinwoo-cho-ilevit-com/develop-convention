# 05. Async/Parallel Optimization + Profiling

## Core Rules

- Use the concurrency model that matches the bottleneck type: CPU-bound → multiprocessing, IO-bound → asyncio. Don't guess — identify the bottleneck with profiling first.
- Tune DataLoader's `num_workers`, `persistent_workers=True`, `pin_memory=True`, and `prefetch_factor`.
- Log GPU utilization, VRAM, RAM, CPU usage, and throughput at every pipeline stage.
- Structure logs as JSON. Include stage name / items processed / elapsed time / samples-per-sec / peak memory as required fields.
- Always compare before/after optimization with empirical measurement. Optimization claims without measurement are forbidden.

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
| Automatic per-run logging | Trackio system metrics | Logs GPU metrics (utilization/VRAM/power/temperature) in the background across the whole run when compatible hardware is detected |

- There are two headline metrics: **VRAM usage** and **GPU utilization (%)**. Record these two plus RAM/CPU at every pipeline stage.
- In-code instrumentation: have one shared helper that logs `torch.cuda.max_memory_allocated()` (when using CUDA) and `psutil`-based RAM/CPU at stage start/end, and have every stage share it.

Sources: [nvitop](https://github.com/XuehaiPan/nvitop), [Trackio — logging system metrics](https://huggingface.co/docs/trackio/en/track), [NVIDIA NVML — utilization metrics](https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceStructs.html) (GPU utilization = percent of time one or more kernels was executing; memory utilization = percent of time device memory was being read or written)

### 4. Structured Logging

- Standardize on structlog-based JSON logging. Library-style code should use only stdlib `logging` + `NullHandler`.
- Required stage log fields: `stage`, `num_processed`, `elapsed_sec`, `samples_per_sec`, `peak_vram_mb` (when using GPU), `peak_ram_mb`.
- Progress display for humans is tqdm/rich; the machine-readable record is JSON logs — separate the roles, but keep both.

Sources: [structlog](https://pypi.org/project/structlog/)
