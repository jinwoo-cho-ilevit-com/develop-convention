# 08. LLM Training/Evaluation

LLM API call-based inference modules (using external provider APIs) follow [10-llm-api-inference.md](10-llm-api-inference.md) and [11-llm-api-providers.md](11-llm-api-providers.md). This document covers cases where you train/serve models directly.

## Core Rules

- Follow the use-case routing table for training frameworks. torchtune is deprecated — do not adopt it for new work.
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

- **torchtune has been officially discontinued** ("no longer actively maintained", 2025) — do not adopt it for new projects. This is a concrete instance of "research maintenance status before choosing a framework" (→ [00-principles.md](00-principles.md)).
- As of 2026, Axolotl/Unsloth/LLaMA-Factory have mostly converged on features (LoRA/QLoRA/full/DPO/GRPO/vision). The selection criteria are scale, reproducibility, and ergonomics — not features.
- TRL's vLLM integration specifies a supported version range, so pin the vLLM version within that range.

Sources: [torchtune (deprecation notice)](https://github.com/meta-pytorch/torchtune), [TRL](https://github.com/huggingface/trl), [Axolotl](https://docs.axolotl.ai/docs/lora_optims.html), [torchtitan](https://github.com/pytorch/torchtitan)

### 2. Distributed & Efficient Training

- **Default to FSDP2** (FSDP1 is deprecated and being removed from Axolotl). Use DeepSpeed ZeRO only when CPU/NVMe offload is truly needed; ZeRO 1-2 is appropriate for LoRA, and avoid the LoRA + CPU offload combination.
- **Caution**: If you inject a LoRA adapter after `fully_shard`, the new parameters fall outside FSDP management and gradients won't sync — respect the injection order or register an explicit all-reduce hook ([source: FSDP vs Megatron vs DeepSpeed survey](https://megacpp.com/blog/framework-survey-fsdp-vs-megatron-vs-deepspeed/)). Re-verify against the official docs of whichever framework you adopt before relying on this.
- Optimizations to apply by default: bf16 (no loss scaling needed), gradient checkpointing, Flash Attention, sequence packing. Start LoRA rank at 8 and adjust based on quality/memory.
- Use a single host framework per run — no framework chaining.

Sources: [FSDP vs Megatron vs DeepSpeed survey](https://megacpp.com/blog/framework-survey-fsdp-vs-megatron-vs-deepspeed/), [Anyscale — fine-tuning optimizations](https://docs.anyscale.com/llm/fine-tuning/speed-and-memory-optimizations)

### 3. Training/Inference Consistency (LLM-Specific)

**Chat template mismatch is the #1 silent bug in LLM development.** Incorrect role tokens/formatting corrupt the training signal without throwing any error.

- Single source for templates: use `tokenizer.apply_chat_template` for training, validation, and inference alike. No manual string assembly.
- **Golden equality test**: for a handful of sample conversations, assert string equality between the formatted string at training time and the formatted string at inference (serving) time.
- Special token verification: check that EOS/PAD/additional token IDs match between the training tokenizer and the serving engine.
- **Even with the same checkpoint, logits differ across engines**: the training engine (FSDP, etc.) and inference engine (vLLM/SGLang) differ in kernels, attention implementation, precision, and batch numerics, so the same weights produce different distributions. Be aware of this in evaluation/RL, and monitor train/infer logprob divergence during RL rollouts (correction technique: Truncated Importance Sampling).
- HF `generate` and vLLM have different sampling defaults, so pin every generation parameter explicitly in config.

Sources: [Training-Inference Mismatch in LLM RL (arXiv 2605.14220)](https://arxiv.org/pdf/2605.14220), [vLLM chat template issue](https://github.com/vllm-project/vllm/issues/6416)

### 4. Evaluation Reproducibility

Cautionary example: Llama-3.1-8B-Instruct GSM8K scored 84.5 officially versus 76.95 on community re-measurement — a gap of nearly 8 points from prompt/chat template/few-shot configuration differences alone.

- Use **lm-evaluation-harness** (the reproducibility standard where tasks are version-controlled) or **lighteval** as the harness, and pin the harness version (commit/PyPI version).
- Include in every evaluation record: task name + task version, `num_fewshot`, whether `--apply_chat_template` was used, system instruction, backend (hf/vllm), dtype, and generation parameters.
- Evaluate instruct models as chat: `--apply_chat_template --fewshot_as_multiturn`.
- Version-control evaluation configs too — it has been empirically measured that a single-character difference in the prompt can change scores.

Sources: [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), [Llama-3.1 GSM8K reproduction gap](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/discussions/81), [Prompt sensitivity (arXiv 2510.05152)](https://arxiv.org/pdf/2510.05152)

### 5. LLM-as-Judge

Always apply these three baseline requirements:

- **Position bias**: for pairwise comparisons, evaluate both orderings and average (swap-and-average), or randomize the slots.
- **Self-preference bias**: judges are lenient toward their own model family — use a judge from a different family (cross-family) than the model being evaluated.
- **Verbosity bias**: use a length-aware rubric (state explicitly that longer isn't better).

Additional rules:
- Pointwise and pairwise produce different results even for the same content — fix one protocol, document it, and don't mix them.
- Validate the judge as a measurement instrument: don't assume agreement with human evaluation — check it against samples.

Sources: [Judge bias research (IJCNLP 2025)](https://aclanthology.org/2025.ijcnlp-long.18/), [Self-preference bias (arXiv 2505.19176)](https://arxiv.org/pdf/2505.19176)

### 6. Data Engineering

- **Schema**: standardize chat/tool models on the messages schema (a list of `role`/`content` turns) — it maps directly to `apply_chat_template`. Alpaca format is also viable for simple Q&A-only cases, but standardize on one per project.
- **Dedup**: remove duplicate documents/lines using MinHashLSH-family n-gram hashing.
- **Decontamination**: remove eval-set leakage using n-gram overlap + semantic similarity (to catch paraphrased leakage). Exact match alone misses transformed leaks.
- **Dry-run**: before the actual training run, confirm on a small sample that schema parsing → template application → tokenization → 1 training step all pass (→ [04-pipeline.md](04-pipeline.md)).

Sources: [Anyscale — data preparation](https://docs.anyscale.com/llm/fine-tuning/data-preparation), [Dedup research (arXiv 2411.04257)](https://arxiv.org/html/2411.04257v3), [NVIDIA — LLM data preprocessing](https://developer.nvidia.com/blog/mastering-llm-techniques-data-preprocessing/)
