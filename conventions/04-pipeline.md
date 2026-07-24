# 04. Pipeline Design

## Core Rules

- Every pipeline stage must be runnable standalone on a small sample via a `--limit N` option.
- Dump each stage's input/output to files so they can be easily inspected. Never build a pipeline whose intermediate results cannot be visually checked.
- Save large-scale processing incrementally in chunks and make it resumable after interruption. Skip already-completed chunks on rerun.
- Save files atomically: write to a temp file, then swap it in with `os.replace`.
- Process large data via streaming. Loading everything into memory or saving it all at once at the end is forbidden.
- Attach progress display (tqdm/rich) to every long-running task, including training/evaluation/preprocessing.

## Details

### 1. Small-Sample-Based Design (Debuggability)

Each pipeline stage must let you immediately verify "how it works, what goes in, and what comes out" using a small sample.

- Make `--limit N` (e.g., process only 10 samples) a standard option on every stage's CLI.
- Provide an option to dump per-stage input/output samples in a human-readable format (JSON/JSONL/Parquet).
- Being able to replay an individual stage standalone from captured input dramatically speeds up debugging — isolate and run just the problem stage instead of rerunning the whole pipeline.
- Make it standard procedure to validate schema/format/tokenization with a small-sample dry-run before the real run (→ [08-llm-development.md](08-llm-development.md)).

Sources: [AI agent observability — trace/replay](https://mastra.ai/articles/ai-agent-observability)

### 2. Resumable Processing (Interruption-Tolerant)

Design with the default assumption that the environment — like a RunPod spot pod — can be interrupted at any time.

- **Chunked processing + immediate save**: when processing N items, don't save only after everything finishes — save after each chunk (e.g., every 1000 items).
- **Idempotent stages**: skip an item on rerun if its output already exists. Output presence (or a manifest) is the progress state.
- **Atomic save**: dying mid-write leaves a corrupted file. Write to a temp file, then swap it in with `os.replace(tmp, final)`, so the final file is always complete.

```python
def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)  # atomic within the same filesystem
```

- **Large model checkpoints**: use `torch.distributed.checkpoint`'s `async_save` (background saving to minimize training interruption) plus safetensors serialization (→ [07-ml-development.md](07-ml-development.md)).

Sources: [PyTorch — distributed checkpoint recipe](https://docs.pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html), [DCP safetensors support](https://pytorch.org/blog/huggingface-safetensors-support-in-pytorch-distributed-checkpointing/)

### 3. Large-Scale Data Streaming

- Text/mixed data: HuggingFace `datasets` streaming (`IterableDataset`). Use `shuffle(buffer_size=...)` for approximate shuffling, and call `set_epoch()` between epochs to guarantee reshuffling.
- Large-scale multimodal (image/audio/video): WebDataset (~1GB TAR shards, maximizing throughput with sequential I/O).
- Either way, the "load everything then process" pattern is forbidden — it breaks both the memory budget and interruption tolerance.

Sources: [HF datasets — streaming](https://huggingface.co/docs/datasets/stream), [WebDataset](https://huggingface.co/docs/hub/en/datasets-webdataset)

### 4. Progress Monitoring

- Attach tqdm or rich progress to every loop-driven long-running task. "Where things currently stand" must be visible in both the log file and the terminal.
- Use `tqdm.contrib.logging` (or rich's log integration) so the progress bar and log output don't get garbled together.
- Record processing speed (samples/sec) alongside progress — a slowdown is an early signal of a problem (→ [05-performance.md](05-performance.md)).

Sources: [tqdm.contrib.logging](https://tqdm.github.io/docs/contrib.logging/)
