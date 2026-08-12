# 23. The Remote GPU Iteration Loop

When code is written on one machine and runs on a rented GPU host, the iteration loop — edit, deliver, run, observe — crosses a network on every pass, and its speed is set by the slowest crossing. This document governs that loop: how code reaches the remote, and how failures are moved to the cheap side of it. Making the code itself run on both sides is [03-environment.md](03-environment.md); the tiny-model fixture mechanics are [22-framework-wrapping.md](22-framework-wrapping.md); stage shape is [04-pipeline.md](04-pipeline.md); the tests CI runs on CPU are [06-testing-verification.md](06-testing-verification.md).

## Core Rules

- Keep the iteration loop free of image rebuilds and git round trips. The image supplies dependencies; your working tree reaches the remote by direct sync (watch-and-rsync, SkyPilot workdir sync, or Mutagen).
- Give every training/evaluation entry point a `--smoke` mode: the target model's real tokenizer, a config-only tiny model, a handful of samples, one or two steps — through the real entry point, runnable on local CPU/MPS. Passing smoke is the precondition for occupying a GPU.
- In smoke mode, switch off what the local device cannot run (CUDA-only kernels, quantization backends) via config, and record each switch-off as [22-framework-wrapping.md](22-framework-wrapping.md) requires of fixture deviations.
- The smoke tier shares the test layer's range (→ [22-framework-wrapping.md](22-framework-wrapping.md) §4); what falls outside it is verified on the GPU.
- Open every entry point with a preflight that runs before the model or the full dataset loads: config validation, first-batch schema, one collated batch decoded to verify label masking, output-path writability. Preflight fails in seconds; loading takes minutes.
- Reproduce a remote failure locally: pull the failing stage's dumped input down and replay that stage standalone (→ [04-pipeline.md](04-pipeline.md) §1).

## Details

### 1. Where the time goes

Only one of the loop's four segments needs the GPU. The other three are where slow loops actually spend their time, in two patterns:

- **Delivery measured in minutes.** A loop that contains commit → push → pull, or a `docker build` and re-pull, pays a multi-minute round trip per attempt for a step that direct sync removes entirely (§2).
- **Discovery after loading.** An error raised after minutes of weight and dataset loading costs that loading again on every attempt. Preflight (§4) moves cheap failures ahead of expensive loads; the smoke tier (§3) moves whole-code-path failures off the GPU altogether — most of what a remote run discovers (schema, template, masking, wiring, path errors) never needed a GPU to discover.

### 2. Code sync

- **Default: one-way watch-and-sync, local → remote.** The working tree stays the single source of truth and the remote copy is disposable. watchexec — "a simple, standalone tool that watches a path and runs a command whenever it detects modifications" — driving rsync over SSH is enough.
- **SkyPilot bakes the sync into the launcher**: it uploads the local working directory to `~/sky_workdir` on the cluster on every `sky launch` and `sky exec`, so each re-run delivers the current tree with no separate sync process. RunPod is a supported backend (`pip install "skypilot-nightly[runpod]"`).
- **Mutagen only when two-way sync is genuinely needed** (files written on the remote that must flow back). Its default `two-way-safe` mode auto-resolves conflicts only when no data is lost. Two caveats: on Linux/BSD endpoints — the GPU host — it falls back to poll-based watching with a default 10-second interval, so remote-side changes propagate on a delay; and its release cadence has stalled (latest v0.18.1, 2025-02-24, as of: 2026-08), so re-check maintenance status before adopting (→ [00-principles.md](00-principles.md)).
- **One-off transfers** — a checkpoint, a failing stage's dumped input — use `runpodctl send` / `runpodctl receive`, a peer-to-peer relay that needs no open port on either side.
- The alternative that removes delivery entirely is editing on the remote host itself over VS Code Remote-SSH.
- `docker build` never enters the loop. The image carries the Linux/CUDA runtime and dependencies (→ [03-environment.md](03-environment.md) §4); [22-framework-wrapping.md](22-framework-wrapping.md) §3 records why code read out of an image is never the change under test, and the same holds outside the test layer.

Sources: [watchexec](https://github.com/watchexec/watchexec), [SkyPilot — syncing code and artifacts](https://docs.skypilot.ai/en/latest/examples/syncing-code-artifacts.html), [RunPod — SkyPilot integration](https://docs.runpod.io/integrations/skypilot), [Mutagen — synchronization modes](https://mutagen.io/documentation/synchronization/), [Mutagen — filesystem watching](https://mutagen.io/documentation/synchronization/watching), [Mutagen — releases](https://github.com/mutagen-io/mutagen/releases), [runpodctl send](https://docs.runpod.io/runpodctl/reference/runpodctl-send), [VS Code Remote-SSH](https://code.visualstudio.com/docs/remote/ssh) (as of: 2026-08)

### 3. The smoke tier

`--smoke` composes the small-sample run of [04-pipeline.md](04-pipeline.md) §1 and the dry-run of [08-llm-development.md](08-llm-development.md) §6 into a standing mode of the real entry point — not a separate script, which would drift from the run it stands in for. It selects a config group ([02-config.md](02-config.md)) that swaps in:

- **The target model's real tokenizer.** A tokenizer needs no GPU and carries the largest silent-bug class in fine-tuning: chat template application, prompt-span label masking, padding/truncation, EOS handling (→ [08-llm-development.md](08-llm-development.md) §3). Match the tiny config's `vocab_size` to it.
- **A config-only tiny model of the pinned architecture.** What to shrink and what to keep is [22-framework-wrapping.md](22-framework-wrapping.md) §2; that this is how the frameworks test themselves is §5. Staying in the target's architecture family means the module names a LoRA/PEFT config targets still exist in the tiny model, so the adapter wiring runs for real.
- **A handful of samples, one or two steps**, on the local CPU/MPS device (→ [03-environment.md](03-environment.md) §3).

Swap the random tiny model for a small pretrained one and the tier also answers a question randomness cannot: training loss on a handful of samples must fall, and a model that cannot overfit a trivial set points at the labels or the optimizer wiring, not at the data volume.

The `--smoke` mode is also what the CPU smoke runs of [06-testing-verification.md](06-testing-verification.md) §5 invoke in CI — one mechanism serves the development loop and the verification gate, so neither drifts from the other. The tier's range is the test layer's range (→ [22-framework-wrapping.md](22-framework-wrapping.md) §4); write the project's own out-of-range list down and keep those checks on the rented hardware.

### 4. Preflight

Order the checks by cost and run them all before the first expensive load, at the top of the entry point in the same process — a separate validation script drifts from the run it guards:

1. **Config validation** — resolve the full config and fail on type or range errors (→ [02-config.md](02-config.md)).
2. **First-batch schema** — pull one batch through the real dataset and collator path.
3. **Label-mask decode** — decode that collated batch and check the supervised positions cover exactly the response span. Template and masking corruption is silent everywhere else (→ [08-llm-development.md](08-llm-development.md) §3); this is the one place it is loud.
4. **Output-path writability** — create the run directory and write the resolved-config snapshot [02-config.md](02-config.md) already requires; the snapshot doubles as the writability check.

The same preflight runs on the GPU host at full-run start. The point is not where it runs but what it runs before: a config typo that dies at second five costs one sync; the same typo dying after twenty minutes of loading costs twenty minutes, on every attempt until it is found.
