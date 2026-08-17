# 08. LLM Training/Evaluation

LLM API call-based inference modules (using external provider APIs) follow [10-llm-api-inference.md](10-llm-api-inference.md) and [11-llm-api-providers.md](11-llm-api-providers.md). This document covers cases where you train/serve models directly.

## Core Rules

- Follow the use-case routing table for training frameworks. torchtune is no longer actively maintained — do not adopt it for new work.
- Default to FSDP2 for distributed training and bf16 for mixed precision.
- Use `tokenizer.apply_chat_template` as the single source for chat templates. Pin the formatted-string equality between training and inference with a golden test.
- Always specify sampling parameters (temperature/top_p/top_k/max_tokens) in config. Do not rely on engine defaults.
- Record everything for evaluation: harness version, task version, number of few-shot examples, and whether the chat template was applied.
- Default LLM-as-judge to bidirectional order evaluation + cross-family judge + a length-aware rubric.
- Standardize training data on the messages schema, and validate schema/template/tokenization with a small-sample dry-run before the actual training run.

## Details

### 1. Training Framework Routing

| Use case | Choice |
|---|---|
| Single-GPU SFT/LoRA | Unsloth (speed/memory) or TRL `SFTTrainer` |
| Multi-GPU, reproducible production training | Axolotl (config-driven, FSDP2) or TRL |
| DPO/GRPO/online RL | TRL (`GRPOTrainer` + vLLM rollout) or Axolotl GRPO |
| Pretraining/large-scale | torchtitan (PyTorch-native) or Megatron-Core |

- **torchtune is no longer actively maintained** — its README states "torchtune development wound down in 2025" — so do not adopt it for new projects (as of: 2026-08). This is a concrete instance of "research maintenance status before choosing a framework" (→ [00-principles.md](00-principles.md)).
- Axolotl/Unsloth/LLaMA-Factory overlap heavily on LoRA/QLoRA/full fine-tuning and vision, but their advertised coverage is not identical: Axolotl's docs and Unsloth's README both list DPO and GRPO, while GRPO is absent from LLaMA-Factory's main feature list (it announces the separate EasyR1 project for GRPO instead) (as of: 2026-08). Select on scale, reproducibility, and ergonomics — and confirm the specific method you need against the project's own docs rather than assuming parity.
- TRL's vLLM integration documents a supported version range, so pin the vLLM version within the range TRL states for your installed version (as of: 2026-08).

Sources: [torchtune (maintenance notice)](https://github.com/meta-pytorch/torchtune), [TRL — vLLM integration](https://huggingface.co/docs/trl/main/en/vllm_integration), [Axolotl](https://docs.axolotl.ai/), [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory), [Unsloth](https://github.com/unslothai/unsloth), [torchtitan](https://github.com/pytorch/torchtitan)

### 2. Distributed & Efficient Training

- **Default to FSDP2**. Axolotl's docs state "FSDP1 is deprecated and will be removed in an upcoming release of Axolotl" and that "FSDP2 is recommended for new users" (as of: 2026-08). Use DeepSpeed ZeRO only when CPU/NVMe offload is truly needed; ZeRO 1-2 is appropriate for LoRA, and avoid the LoRA + CPU offload combination.
- **Caution**: injecting a LoRA adapter after `fully_shard` is reported to leave the new parameters outside FSDP management so their gradients never sync — *(unverified — needs research)*. PyTorch's `fully_shard` reference documents only that it converts `model.parameters()` to DTensor in-place and that each group is all-gathered/reduce-scattered as a unit; it does not document post-hoc parameter injection either way. Treat injection order as load-bearing, verify against the official docs of the framework you adopt, and test that gradients actually sync before relying on it.
- Optimizations to apply by default: bf16 (no loss scaling needed), gradient checkpointing, Flash Attention, sequence packing. Start LoRA rank at 8 and adjust based on quality/memory.
- Use a single host framework per run — no framework chaining.

Sources: [Axolotl — multi-GPU (FSDP1 deprecation)](https://docs.axolotl.ai/docs/multi-gpu.html), [PyTorch — `fully_shard` reference](https://docs.pytorch.org/docs/stable/distributed.fsdp.fully_shard.html), [Anyscale — fine-tuning optimizations](https://docs.anyscale.com/llm/fine-tuning/speed-and-memory-optimizations)

### 3. Training/Inference Consistency (LLM-Specific)

**Chat template mismatch is the #1 silent bug in LLM development.** Incorrect role tokens/formatting corrupt the training signal without throwing any error.

- Single source for templates: use `tokenizer.apply_chat_template` for training, validation, and inference alike. No manual string assembly.
- **Golden equality test**: for a handful of sample conversations, assert string equality between the formatted string at training time and the formatted string at inference (serving) time.
- Special token verification: check that EOS/PAD/additional token IDs match between the training tokenizer and the serving engine.
- **Even with the same checkpoint, logits differ across engines**: the training engine (FSDP, etc.) and inference engine (vLLM/SGLang) differ in kernels, attention implementation, precision, and batch numerics, so the same weights produce different distributions. Be aware of this in evaluation/RL, and monitor train/infer logprob divergence during RL rollouts (correction technique: Truncated Importance Sampling).
- HF `generate` and vLLM have different sampling defaults, so pin every generation parameter explicitly in config.

Sources: [Diagnosing Training Inference Mismatch in LLM Reinforcement Learning (arXiv 2605.14220)](https://arxiv.org/abs/2605.14220), [vLLM — apply chat template through `LLM` class (issue 6416)](https://github.com/vllm-project/vllm/issues/6416)

### 4. Evaluation Reproducibility

Cautionary example: Llama-3.1-8B-Instruct GSM8K scored 84.5 officially versus 76.95 on community re-measurement — a gap of nearly 8 points from prompt/chat template/few-shot configuration differences alone.

- Use **lm-evaluation-harness** or **lighteval** as the harness, and pin the harness version (commit/PyPI version). lm-evaluation-harness versions tasks explicitly: its task guide describes marking each task with a `metadata: version` number "that can be bumped whenever a breaking change is made", so record the task version alongside the harness version.
- Include in every evaluation record: task name + task version, `num_fewshot`, whether `--apply_chat_template` was used, system instruction, backend (hf/vllm), dtype, and generation parameters.
- Evaluate instruct models as chat: `--apply_chat_template --fewshot_as_multiturn`.
- Version-control evaluation configs too — it has been empirically measured that a single-character difference in the prompt can change scores.

Sources: [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), [lm-evaluation-harness — task versioning guide](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md), [lm-evaluation-harness — interface flags](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/interface.md), [Llama-3.1 GSM8K reproduction gap](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/discussions/81), [A Single Character can Make or Break Your LLM Evals (arXiv 2510.05152)](https://arxiv.org/abs/2510.05152)

### 5. LLM-as-Judge

Always apply these three baseline requirements:

- **Position bias**: judges tend "to favor solutions based on their position within the prompt" (measured across 15 judges, 22 tasks, 150k+ instances), so for pairwise comparisons evaluate both orderings and average (swap-and-average), or randomize the slots.
- **Self-preference bias**: GPT-4 was measured to show "a significant degree of self-preference bias"; the same study attributes the mechanism to perplexity — judges rate low-perplexity (more familiar) text higher than humans do, "regardless of whether the outputs were self-generated". Use a judge from a different family (cross-family) than the model being evaluated. That family-level framing is the practical mitigation; whether leniency tracks *model family* specifically rather than familiarity is *(unverified — needs research)*.
- **Verbosity bias**: use a length-aware rubric (state explicitly that longer isn't better). The underlying claim that judges systematically prefer longer responses is *(unverified — needs research)*.

Additional rules:
- Pointwise and pairwise produce different results even for the same content — fix one protocol, document it, and don't mix them.
- Validate the judge as a measurement instrument: don't assume agreement with human evaluation — check it against samples.

Sources: [Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge (IJCNLP-AACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/), [Self-Preference Bias in LLM-as-a-Judge (arXiv 2410.21819)](https://arxiv.org/abs/2410.21819)

### 6. Data Engineering

- **Schema**: standardize chat/tool models on the messages schema (a list of `role`/`content` turns) — it maps directly to `apply_chat_template`. Alpaca format is also viable for simple Q&A-only cases, but standardize on one per project.
- **Dedup**: remove duplicate documents/lines using MinHashLSH-family n-gram hashing.
- **Decontamination**: remove eval-set leakage using n-gram overlap + semantic similarity (to catch paraphrased leakage). Exact match alone misses transformed leaks.
- **Dry-run**: before the actual training run, confirm on a small sample that schema parsing → template application → tokenization → 1 training step all pass (→ [04-pipeline.md](04-pipeline.md)).

Sources: [Anyscale — data preparation](https://docs.anyscale.com/llm/fine-tuning/data-preparation), [LSHBloom: Memory-efficient, Extreme-scale Document Deduplication (arXiv 2411.04257)](https://arxiv.org/abs/2411.04257), [NVIDIA — LLM data preprocessing](https://developer.nvidia.com/blog/mastering-llm-techniques-data-preprocessing/)
