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
- **Python free-threading (3.14t)**: promoted to official support in 3.14, but it's a separate build, and depending on C extension compatibility the GIL can silently re-activate. Maintain a "watch and verify by benchmark before adopting" stance.

Sources: [PyTorch — data loading tutorial](https://docs.pytorch.org/tutorials/intermediate/intermediate_data_loading_tutorial.html), [Python — free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html)

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
| Automatic per-run logging | W&B system metrics (or Trackio) | Automatically logs CPU/GPU/memory/disk across the whole run |

- There are two headline metrics: **VRAM usage** and **GPU utilization (%)**. Record these two plus RAM/CPU at every pipeline stage.
- In-code instrumentation: have one shared helper that logs `torch.cuda.max_memory_allocated()` (when using CUDA) and `psutil`-based RAM/CPU at stage start/end, and have every stage share it.

Sources: [nvitop](https://github.com/XuehaiPan/nvitop), [W&B system metrics](https://docs.wandb.ai/models/ref/python/experiments/system-metrics), [GPU utilization guide](https://towardsdatascience.com/a-guide-to-gpu-utilization/)

### 4. Structured Logging

- Standardize on structlog-based JSON logging. Library-style code should use only stdlib `logging` + `NullHandler`.
- Required stage log fields: `stage`, `num_processed`, `elapsed_sec`, `samples_per_sec`, `peak_vram_mb` (when using GPU), `peak_ram_mb`.
- Progress display for humans is tqdm/rich; the machine-readable record is JSON logs — separate the roles, but keep both.

Sources: [structlog](https://pypi.org/project/structlog/)
