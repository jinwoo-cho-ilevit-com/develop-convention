# 22. Wrapping a Third-Party Training Framework

When your module's job is to drive someone else's training framework — any trainer you did not write, whether an open-source package or a vendored research repo — the code under test is mostly your reading of their source. This document is about proving that reading, before it costs a rented GPU. The rules name no particular framework, and only the fixture mechanics are training-specific: the rest carry unchanged to wrapping any heavy external dependency. Choosing the framework is [08-llm-development.md](08-llm-development.md); testing your own code is [06-testing-verification.md](06-testing-verification.md).

## Core Rules

- Add a test layer that **imports the real package**. A double encodes your reading of the framework's source and is written by the person who did the reading, so it can never contradict you. This layer is the only one that can.
- Shrink the fixture's **expensive dimension and keep its structure**: build it from config alone — for a trainer, a tiny model with the pinned architecture and random weights. No weights download, no network, no GPU. Capacity is what you discard; structure and wiring are what you keep.
- Run it **inside the image that ships the framework**, and mount your own code over the installed copy. Reading your code out of the image tests whatever was built into it, which is never the change under test.
- **Judge with the production gate function**, not a copy of it. A second implementation of the pass/fail rule means the harness and the real run can disagree about what passes, and the disagreement appears only after you have paid.
- Give the fixture the **identifiers the real artifact carries**, not fresh ones, whenever the framework locates things by a fixed value rather than by asking the object it was handed — for a trainer, the real model's special-token ids.
- **Write every deviation the fixture forces into the code, at the deviation.** A local path with no hub id, a precision the framework refuses on CPU — each one is a place the layer stops matching production.
- **State what the layer cannot catch** and keep those on the expensive hardware. A layer trusted past its range is worse than none.
- Make each double **able to express the asymmetry it claims to catch**. A double that cannot represent the failure is coverage in name only, and it will read green through the entire investigation.

## Details

### 1. Why a double cannot contradict you

The failure mode is not that doubles are imprecise. It is that they are *yours*. You read the framework's source, form a belief, and encode that belief twice — once in the adapter and once in the double it is tested against. Where the belief is wrong, both copies are wrong in the same direction and the suite is green.

Four instances from one benchmark harness, all found on rented GPUs after a full test suite passed:

| What broke | Why the double could not hold it |
| --- | --- |
| Encoding ran with dropout live | The fake model had no `training` flag at all |
| Two modules built the same integrity record and drifted | The test built both sides with the same function |
| A fix silently fell through a `TypeError` fallback | The fake `unwrap_model` did not take the real argument |
| A single flaky upload sank a finished run | The fake uploader could only express permanent failure |

The last one is the sharpest: the fix was applied, the suite stayed green, and nothing indicated the new code path was never reached. **When a test double is changed, ask what failure it can now represent that it could not before** — if the answer is none, the change is decorative.

### 2. What to shrink and what to keep

| Shrink | Keep |
| --- | --- |
| Capacity — billions of parameters to tens of millions | The real framework package |
| Scale — a full run's steps to two, many ranks to one | The image that ships it |
| Data — the dataset to a handful of records | Your own wrapper code, mounted from the working tree |
| Hardware — accelerators to CPU | The production pass/fail function |

A config-only model is enough because the defects this layer targets are wiring defects: which module the framework hands you, what its save writes, what its restore reads, which object your encode actually runs through. None of those depend on the weights being good.

### 3. Two rules learned by getting them wrong

**The image supplies the dependency; the working tree supplies your code.** A first attempt ran the harness against the copy of the repository installed in the image. It reproduced a failure that had already been fixed — the layer was testing the build, not the change. Mount the repository and put it ahead of the installed package on the interpreter's path.

**The gate lives in one place.** The harness produces the same result row the real run produces and hands it to the same judging function. When that function was reverted to the shipped code, the layer failed with the identical message the paid run had failed with, in fourteen seconds. That identity is what makes the layer trustworthy; a re-implemented gate would only have proved the re-implementation.

### 4. What the layer cannot catch

Write this list down and keep it current — it is the layer's range, and everything outside it still needs the real hardware:

- **One process** — nothing about gradient synchronisation, sharding, rank-dependent placement, or collective ordering.
- **Small capacity** — nothing about memory ceilings, allocator behaviour, or numerical effects that appear only at scale.
- **Few steps** — nothing about schedules, long-horizon drift, or anything that degrades over a run.
- **Small inputs** — nothing about the resize path at real resolutions or throughput.

A defect that survives the layer is not disproved; it is only not yet reproduced cheaply.

### 5. This is how the frameworks test themselves

Tiny random models are established practice in this ecosystem, not an invention. The organisations that maintain the frameworks you are wrapping publish and consume them: [trl-internal-testing/tiny-random-LlamaForCausalLM](https://hf.co/trl-internal-testing/tiny-random-LlamaForCausalLM) (created 2023-03-29, 507.6K downloads), [peft-internal-testing/tiny-random-OPTForCausalLM](https://hf.co/peft-internal-testing/tiny-random-OPTForCausalLM) (574.5K), [optimum-intel-internal-testing/tiny-random-LlamaForCausalLM](https://hf.co/optimum-intel-internal-testing/tiny-random-LlamaForCausalLM) (513.9K), [llamafactory/tiny-random-Llama-3](https://hf.co/llamafactory/tiny-random-Llama-3) (327.9K), [hmellor/tiny-random-LlamaForCausalLM](https://hf.co/hmellor/tiny-random-LlamaForCausalLM) (4.7M).

Build your own rather than pulling one when the architecture is pinned and the fixture must carry specific token ids — but the practice, and the expectation that a framework is testable this way, is theirs.

Sources: [Hugging Face Hub model search, `tiny-random`, sorted by downloads](https://hf.co/models?search=tiny-random)

### 6. A worked example of what this catches

A reload gate compared embeddings before and after a checkpoint round trip and reported the checkpoint broken for three paid runs. On CPU, through the real framework, the two models' parameters and buffers were bit-identical and the same batch still produced different embeddings. The cause was `Accelerator.unwrap_model`, whose signature is `(self, model, keep_fp32_wrapper: bool = True, keep_torch_compile: bool = True)` in accelerate 1.14.0: a module that has been through training keeps accelerate's autocast `forward`, and a freshly loaded one does not. The gate was measuring the wrapper, not the checkpoint.

No amount of reading would have settled it, because the reading was the thing in doubt. Running it did, for nothing.

Sources: `accelerate.Accelerator.unwrap_model` signature, read from the installed package inside the pinned framework image (accelerate 1.14.0)
