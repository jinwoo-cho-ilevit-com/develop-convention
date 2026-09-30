# 05. Data Processing Performance and Profiling

## Core Rules

- For data-processing work, define expected input scale and a completion-time or throughput target, memory budget, and cost limit where relevant. If no target can be set during exploration, record a representative baseline and the missing limits.
- Start with a correct, measurable simple implementation. Measure end-to-end time on representative input; profile when it misses a target or repeated-run cost is material.
- Reduce data read and work performed, then improve the algorithm, joins, batching, file layout, and serialization before adding concurrency.
- Use concurrency when profiling shows a remaining bottleneck and the added coordination cost is justified. Choose multiprocessing for CPU-bound work or asyncio for non-blocking IO when appropriate.
- Compare correctness, end-to-end elapsed time, peak memory, and cost before/after a performance change on the same representative input in a comparable environment. Do not claim an improvement without measurement.
- Log only the stage and resource metrics needed to locate the bottleneck and verify the target; keep diagnostics bounded.
- Choose the implementation language from the measured bottleneck, never from expected speed: port a stage to a compiled language only under the conditions in §5.

## Details

### 1. Choosing Concurrency

The first pass is to read only needed rows and columns, push filtering/aggregation to the data source when appropriate, and check algorithmic complexity and join cardinality. Then inspect batch size, file size, intermediate writes, and serialization. Concurrency is a later option when these changes leave a measured bottleneck.

- **CPU-bound preprocessing** (tokenization, image decoding, feature computation): consider multiprocessing after measuring that CPU work dominates. In PyTorch, DataLoader's `num_workers>0` serves this role. Every sample crosses an inter-process queue, which can itself become a bottleneck.
- **IO-bound work** (API calls, file/network downloads, DB queries): consider asyncio when requests can use non-blocking I/O and concurrent waiting is material.
- **Python free-threading (3.14t)**: PEP 779 (Final, Python 3.14) moved the free-threaded build to phase II — officially supported, but still a separate optional build installed under the `t`-suffixed tag. The GIL can be re-enabled at runtime (`PYTHON_GIL`, `-X gil`) and is re-enabled automatically when a C extension not marked free-thread-safe is imported — that case prints a warning rather than being silent. Maintain a "watch and verify by benchmark before adopting" stance.

Sources: [PyTorch — data loading tutorial](https://docs.pytorch.org/tutorials/intermediate/intermediate_data_loading_tutorial.html), [PEP 779 — criteria for supported status of free-threaded Python](https://peps.python.org/pep-0779/), [Python 3.14 release notes](https://docs.python.org/3/whatsnew/3.14.html), [Python — free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html) (as of: 2026-08)

### 2. DataLoader Tuning Checklist

- Tune `num_workers`, `persistent_workers`, `pin_memory`, and `prefetch_factor` only when measured input throughput limits training. Compare total epoch time and memory as well as device utilization.
- Low GPU utilization with a busy CPU is a lead for profiling the data path, not proof that more workers will help.

### 3. Per-Stage Profiling

Use the smallest layer of instrumentation that answers the current bottleneck question:

| Layer | Tool | Purpose |
|---|---|---|
| Per op/layer | `torch.profiler` | Breaks down CPU+CUDA time/memory by operation, pinpoints bottlenecks |
| Real-time observation | `nvitop`, `nvidia-smi dmon` | Check GPU util/VRAM per process in real time |
| Automatic per-run logging | Trackio system metrics | Logs GPU metrics (utilization/VRAM/power/temperature) in the background across the whole run — requires the matching extra (`trackio[gpu]` / `trackio[apple-gpu]`) installed and compatible hardware detected |

- For GPU bottlenecks, inspect VRAM and GPU utilization; for data or CPU bottlenecks, inspect elapsed time, throughput, RAM, and CPU. Capture per-stage metrics where aggregate metrics cannot locate the problem.
- If repeated profiling needs in-code instrumentation, use one shared helper rather than duplicating probes at each stage.

Sources: [nvitop](https://github.com/XuehaiPan/nvitop), [Trackio — logging system metrics](https://huggingface.co/docs/trackio/en/track), [NVIDIA NVML — utilization metrics](https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceStructs.html) (GPU utilization = percent of time one or more kernels was executing; memory utilization = percent of time device memory was being read or written)

### 4. Structured Logging

- Use structured logs when a pipeline needs machine-readable progress or comparison. Library-style code should use stdlib `logging` + `NullHandler`.
- Useful fields are `stage`, `num_processed`, `elapsed_sec`, `samples_per_sec`, and peak memory for the constrained device. Emit them for stages being measured rather than forcing every stage to instrument every resource.
- For long-running work, use tqdm/rich for human progress and retain machine-readable summaries where needed.

Sources: [structlog](https://pypi.org/project/structlog/)

### 5. Language choice

Port a stage or hot loop to a compiled language (Rust via PyO3/maturin, or a standalone binary) only when all of these hold:

- profiling shows it CPU-bound in pure computation — not I/O, GPU, serialization or call overhead;
- its inputs and outputs are files only, so no Python object crosses the boundary;
- the Python-side options (data reduction, algorithm choice, vectorization, batching, and an existing compiled library) were measured and fail a throughput criterion set before the port decision (→ [18-work-contract.md](18-work-contract.md)).

The port must build and run on the project's supported hosts ([03-environment.md](03-environment.md)). A port is a rewrite: preserve behavior with the checks and before/after evidence selected under [00-principles.md](00-principles.md), [06-testing-verification.md](06-testing-verification.md) §1 and [19-evidence.md](19-evidence.md).

- A language port changes nothing when the bottleneck is elsewhere: a stage waiting on disk, the network, the GPU, or serialization runs at the same speed in any language, and a stage dominated by per-call overhead into a compiled library is fixed by batching the calls, not by rewriting the caller. The profile decides, which is why it is the first condition above.
- A PyO3/maturin extension or a standalone binary sits naturally at a stage boundary: the port replaces the inside of one stage, and that stage's existing debugging surface (→ [04-pipeline.md](04-pipeline.md)) becomes the characterization surface for the port.
- The throughput criterion lives in the module's work contract because one repository-wide number fits no module — a tokenizer and an image decoder do not share a floor — and because of when [18-work-contract.md](18-work-contract.md) fixes a contract, the criterion cannot be written after the measurement to justify a port already wanted.
