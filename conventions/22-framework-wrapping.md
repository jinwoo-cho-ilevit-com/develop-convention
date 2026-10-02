# 22. Wrapping a Training Framework and the Remote GPU Loop

When your module's job is to drive someone else's training framework — any trainer you did not write, whether an open-source package or a vendored research repo — the code under test is mostly your reading of their source. This document is about proving that reading, before it costs a rented GPU. The rules name no particular framework, and only the fixture mechanics are training-specific: the rest carry unchanged to wrapping any heavy external dependency. It also governs the iteration loop when that code runs on a rented GPU host — edit, deliver, run, observe — and how failures are moved to the cheap side of the network. Choosing the framework is [08-llm-development.md](08-llm-development.md); testing your own code is [06-testing-verification.md](06-testing-verification.md); making the code run on both sides is [03-environment.md](03-environment.md); stage shape is [04-pipeline.md](04-pipeline.md).

## Core Rules

- Add a test layer that **imports the real package**. A double encodes your reading of the framework's source and is written by the person who did the reading, so it can never contradict you. This layer is the only one that can.
- Shrink the fixture's **expensive dimension and keep its structure**: build it from config alone — for a trainer, a tiny model with the pinned architecture and random weights. No weights download, no network, no GPU. Capacity is what you discard; structure and wiring are what you keep.
- Run it **inside the image that ships the framework**, and mount your own code over the installed copy. Reading your code out of the image tests whatever was built into it, which is never the change under test.
- **Judge with the production gate function**, not a copy of it. A second implementation of the pass/fail rule means the harness and the real run can disagree about what passes, and the disagreement appears only after you have paid.
- Give the fixture the **identifiers the real artifact carries**, not fresh ones, whenever the framework locates things by a fixed value rather than by asking the object it was handed — for a trainer, the real model's special-token ids.
- **Write every deviation the fixture forces into the code, at the deviation.** A local path with no hub id, a precision the framework refuses on CPU — each one is a place the layer stops matching production.
- **State what the layer cannot catch** and keep those on the expensive hardware. A layer trusted past its range is worse than none.
- Make each double **able to express the asymmetry it claims to catch**. A double that cannot represent the failure is coverage in name only, and it will read green through the entire investigation.

- Keep the iteration loop free of image rebuilds and git round trips. The image supplies dependencies; your working tree reaches the remote by direct sync (watch-and-rsync, SkyPilot workdir sync, or Mutagen).
- Give every training/evaluation entry point a `--smoke` mode — the target model's real tokenizer, a config-only tiny model, a handful of samples, one or two steps, through the real entry point on local CPU/MPS — with what the local device cannot run switched off via config and recorded as a fixture deviation. Passing smoke is the precondition for occupying a GPU; its range is this layer's range (§4).
- Open every entry point with a preflight that runs before the model or the full dataset loads: config validation, first-batch schema, one collated batch decoded to verify label masking, output-path writability. Preflight fails in seconds; loading takes minutes.
- Reproduce a remote failure locally: pull the failing stage's dumped input down and replay that stage standalone (→ [04-pipeline.md](04-pipeline.md) §1).

## Details

### 1. Why a double cannot contradict you

The failure mode is not that doubles are imprecise. It is that they are *yours*. You read the framework's source, form a belief, and encode that belief twice — once in the adapter and once in the double it is tested against. Where the belief is wrong, both copies are wrong in the same direction and the suite is green.

A double that can express only one kind of failure lets a fix for another kind pass the suite without its code path ever running. **When a test double is changed, ask what failure it can now represent that it could not before** — if the answer is none, the change is decorative.

### 2. What to shrink and what to keep

| Shrink | Keep |
| --- | --- |
| Capacity — billions of parameters to tens of millions | The real framework package |
| Scale — a full run's steps to two, many ranks to one | The image that ships it |
| Data — the dataset to a handful of records | Your own wrapper code, mounted from the working tree |
| Hardware — accelerators to CPU | The production pass/fail function |

A config-only model is enough because the defects this layer targets are wiring defects: which module the framework hands you, what its save writes, what its restore reads, which object your encode actually runs through. None of those depend on the weights being good.

### 3. Two rules on what the layer runs

**The image supplies the dependency; the working tree supplies your code.** A harness run against the copy of the repository installed in the image tests the build, not the change: it can reproduce a failure the working tree has already fixed. Mount the repository and put it ahead of the installed package on the interpreter's path.

**The gate lives in one place.** The harness produces the same result row the real run produces and hands it to the same judging function. Sabotaging that function must fail the layer with the same message the real run fails with; that identity is what makes the layer trustworthy, and a re-implemented gate would only prove the re-implementation.

### 4. What the layer cannot catch

Write this list down and keep it current — it is the layer's range, and everything outside it still needs the real hardware:

- **One process** — nothing about gradient synchronisation, sharding, rank-dependent placement, or collective ordering.
- **Small capacity** — nothing about memory ceilings, allocator behaviour, or numerical effects that appear only at scale.
- **Few steps** — nothing about schedules, long-horizon drift, or anything that degrades over a run.
- **Small inputs** — nothing about the resize path at real resolutions or throughput.

A defect that survives the layer is not disproved; it is only not yet reproduced cheaply.

### 5. Code sync

- **Default: one-way watch-and-sync, local → remote.** The working tree stays the single source of truth and the remote copy is disposable. watchexec — "a simple, standalone tool that watches a path and runs a command whenever it detects modifications" — driving rsync over SSH is enough.
- **SkyPilot bakes the sync into the launcher**: it uploads the local working directory to `~/sky_workdir` on the cluster on every `sky launch` and `sky exec`, so each re-run delivers the current tree with no separate sync process. RunPod is a supported backend (`pip install "skypilot-nightly[runpod]"`).
- **Mutagen only when two-way sync is genuinely needed** (files written on the remote that must flow back). Its default `two-way-safe` mode auto-resolves conflicts only when no data is lost. On Linux/BSD endpoints — the GPU host — it falls back to poll-based watching with a default 10-second interval, so remote-side changes propagate on a delay. Check its maintenance status before adopting (→ [00-principles.md](00-principles.md)).
- **One-off transfers** — a checkpoint, a failing stage's dumped input — use `runpodctl send` / `runpodctl receive`, a peer-to-peer relay that needs no open port on either side.
- The alternative that removes delivery entirely is editing on the remote host itself over VS Code Remote-SSH.
- `docker build` never enters the loop. The image carries the Linux/CUDA runtime and dependencies (→ [03-environment.md](03-environment.md)); §3 records why code read out of an image is never the change under test, and the same holds outside the test layer.

Sources: [watchexec](https://github.com/watchexec/watchexec), [SkyPilot — syncing code and artifacts](https://docs.skypilot.ai/en/latest/examples/syncing-code-artifacts.html), [RunPod — SkyPilot integration](https://docs.runpod.io/integrations/skypilot), [Mutagen — synchronization modes](https://mutagen.io/documentation/synchronization/), [Mutagen — filesystem watching](https://mutagen.io/documentation/synchronization/watching), [runpodctl send](https://docs.runpod.io/runpodctl/reference/runpodctl-send), [VS Code Remote-SSH](https://code.visualstudio.com/docs/remote/ssh)

### 6. The smoke tier

`--smoke` makes the small-sample run of [04-pipeline.md](04-pipeline.md) §1 a standing mode of the real entry point — not a separate script, which would drift from the run it stands in for. It selects a config group ([02-config.md](02-config.md)) that swaps in:

- **The target model's real tokenizer.** A tokenizer needs no GPU and carries the largest silent-bug class in fine-tuning: chat template application, prompt-span label masking, padding/truncation, EOS handling (→ [08-llm-development.md](08-llm-development.md) §3). Match the tiny config's `vocab_size` to it.
- **A config-only tiny model of the pinned architecture.** What to shrink and what to keep is §2. Staying in the target's architecture family means the module names a LoRA/PEFT config targets still exist in the tiny model, so the adapter wiring runs for real.
- **A handful of samples, one or two steps**, on the local CPU/MPS device (→ [03-environment.md](03-environment.md)).

Swap the random tiny model for a small pretrained one and the tier also answers a question randomness cannot: training loss on a handful of samples must fall, and a model that cannot overfit a trivial set points at the labels or the optimizer wiring, not at the data volume.

The `--smoke` mode is also what the CPU sample runs of [06-testing-verification.md](06-testing-verification.md) §4 invoke in CI — one mechanism serves the development loop and CI, so neither drifts from the other. Write the project's own out-of-range list (§4) down and keep those checks on the rented hardware.

### 7. Preflight

Order the checks by cost and run them all before the first expensive load, at the top of the entry point in the same process — a separate validation script drifts from the run it guards:

1. **Config validation** — resolve the full config and fail on type or range errors (→ [02-config.md](02-config.md)).
2. **First-batch schema** — pull one batch through the real dataset and collator path.
3. **Label-mask decode** — decode that collated batch and check the supervised positions cover exactly the response span. Template and masking corruption is silent everywhere else (→ [08-llm-development.md](08-llm-development.md) §3); this is the one place it is loud.
4. **Output-path writability** — create the run directory and write the resolved-config snapshot [02-config.md](02-config.md) already requires; the snapshot doubles as the writability check.

The same preflight runs on the GPU host at full-run start. The point is not where it runs but what it runs before: a config typo that dies at second five costs one sync; the same typo dying after twenty minutes of loading costs twenty minutes, on every attempt until it is found.
