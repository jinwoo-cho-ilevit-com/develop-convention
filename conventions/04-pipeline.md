# 04. Pipeline Design

## Core Rules

- Give data-processing stages a bounded sample mode and an optional bounded input/output diagnostic sample where inspection helps.
- For workloads that exceed the memory budget or are costly to restart, process incrementally and support safe resume. Reuse output only after validating completion and input identity.
- Publish durable output atomically or with an equivalent completion protocol.
- Stream or chunk data when full materialization would exceed the memory budget or add avoidable I/O.
- Attach progress display (tqdm/rich) to every long-running task, including training/evaluation/preprocessing.
- A stage measured as the bottleneck may be ported to a compiled language under the conditions [05-performance.md](05-performance.md) sets; the rules above apply to it unchanged, so the stage boundary stays the language boundary.

## Details

### 1. Small-Sample-Based Design (Debuggability)

Each pipeline stage must let you immediately verify "how it works, what goes in, and what comes out" using a small sample.

- Provide a bounded sample mode such as `--limit N` (e.g., 10 records) for a stage that processes a dataset.
- When intermediate inspection is useful, provide an opt-in, size-limited input/output sample in a readable format (JSON/JSONL/Parquet). Avoid dumping whole intermediate datasets as a default.
- Being able to replay an individual stage standalone from captured input dramatically speeds up debugging — isolate and run just the problem stage instead of rerunning the whole pipeline. When the failure happened on a remote GPU host, pull the dumped input down and replay locally (→ [22-framework-wrapping.md](22-framework-wrapping.md)).
- Make it standard procedure to validate schema/format/tokenization with a small-sample dry-run before the real run (→ [08-llm-development.md](08-llm-development.md)).

Sources: [AI agent observability — trace/replay](https://mastra.ai/articles/ai-agent-observability)

### 2. Resumable Processing (Interruption-Tolerant)

For long-running or expensive-to-restart jobs, account for interruption, especially on ephemeral compute.

- **Chunked processing + save**: choose chunk size from memory and restart cost; persist completed chunks when rerunning the whole job would be costly.
- **Validated resume**: skip a chunk only when its completion state confirms success and its recorded input/config identity matches the current run. A file's presence alone does not prove either condition.
- **Atomic publication**: for a single local file, write to a temp file on the same filesystem and swap it in with `os.replace(tmp, final)`. For multiple files or remote storage, publish a completion marker or manifest only after all required outputs are complete.

- **Large model checkpoints**: consider `torch.distributed.checkpoint`'s `async_save` and safetensors when checkpoint time or format is a measured constraint (→ [07-ml-development.md](07-ml-development.md)).

Sources: [PyTorch — distributed checkpoint recipe](https://docs.pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html), [DCP safetensors support](https://pytorch.org/blog/huggingface-safetensors-support-in-pytorch-distributed-checkpointing/)

### 3. Large-Scale Data Streaming

- When input exceeds the memory budget, consider HuggingFace `datasets` streaming (`IterableDataset`) for text/mixed data. Use `shuffle(buffer_size=...)` for approximate shuffling, and call `set_epoch()` between epochs when reshuffling is required.
- For large multimodal data, consider sharded sequential I/O such as WebDataset; choose shard size from measured I/O and restart costs.

Sources: [HF datasets — streaming](https://huggingface.co/docs/datasets/stream), [WebDataset](https://huggingface.co/docs/hub/en/datasets-webdataset)

### 4. Progress Monitoring

- Use `tqdm.contrib.logging` (or rich's log integration) so the progress bar and log output don't get garbled together.
- Record processing speed (samples/sec) alongside progress — a slowdown is an early signal of a problem (→ [05-performance.md](05-performance.md)).

Sources: [tqdm.contrib.logging](https://tqdm.github.io/docs/contrib.logging/)
