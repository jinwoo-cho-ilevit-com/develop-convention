# 08. LLM 학습/평가

## 핵심 규칙

- 학습 프레임워크는 용도별 라우팅 표를 따른다. torchtune은 deprecated — 신규 사용 금지.
- 분산 학습은 FSDP2 기본, mixed precision은 bf16 기본.
- chat template은 `tokenizer.apply_chat_template` 단일 소스만 쓴다. 학습/추론의 포맷된 문자열 동일성을 golden 테스트로 고정한다.
- 샘플링 파라미터(temperature/top_p/top_k/max_tokens)는 항상 config에 명시한다. 엔진 기본값에 의존 금지.
- 평가는 하네스 버전·task 버전·few-shot 수·chat template 적용 여부까지 전부 기록한다.
- LLM-as-judge는 양방향 순서 평가 + cross-family judge + 길이 인지 루브릭을 기본으로 한다.
- 학습 데이터는 messages 스키마로 표준화하고, 본 학습 전 소수 샘플 dry-run으로 스키마/템플릿/토크나이즈를 검증한다.

## 상세

### 1. 학습 프레임워크 라우팅

| 용도 | 선택 |
|---|---|
| 단일 GPU SFT/LoRA | Unsloth (속도/메모리) 또는 TRL `SFTTrainer` |
| 멀티 GPU, 재현성 있는 프로덕션 학습 | Axolotl (config-driven, FSDP2) 또는 TRL |
| DPO/GRPO/온라인 RL | TRL (`GRPOTrainer` + vLLM rollout) 또는 Axolotl GRPO |
| 프리트레이닝/대규모 | torchtitan (PyTorch-native) 또는 Megatron-Core |

- **torchtune은 공식적으로 개발 종료** ("no longer actively maintained", 2025) — 신규 채택 금지. 이것이 "프레임워크 선택 전 유지보수 상태를 리서치하라"( → [00-principles.md](00-principles.md))의 실례다.
- 2026 기준 Axolotl/Unsloth/LLaMA-Factory는 기능(LoRA/QLoRA/full/DPO/GRPO/vision)이 대부분 수렴했다. 선택 기준은 기능이 아니라 규모·재현성·인체공학이다.
- TRL의 vLLM 연동은 지원 버전 범위가 명시되므로 vLLM 버전을 그 범위 안에서 pin한다.

출처: [torchtune (deprecated 고지)](https://github.com/meta-pytorch/torchtune), [TRL](https://github.com/huggingface/trl), [Axolotl](https://docs.axolotl.ai/docs/lora_optims.html), [torchtitan](https://github.com/pytorch/torchtitan)

### 2. 분산·효율 학습

- **FSDP2 기본** (FSDP1은 deprecated, Axolotl에서 제거 진행). DeepSpeed ZeRO는 CPU/NVMe offload가 꼭 필요할 때만; LoRA에는 ZeRO 1-2가 적정, LoRA + CPU offload 조합은 피한다.
- **주의**: LoRA 어댑터를 `fully_shard` 이후에 주입하면 새 파라미터가 FSDP 관리 밖이라 gradient가 동기화되지 않는다 — 주입 순서를 지키거나 명시적 all-reduce 훅을 등록한다 ([출처: FSDP vs Megatron vs DeepSpeed 서베이](https://megacpp.com/blog/framework-survey-fsdp-vs-megatron-vs-deepspeed/)). 채택 전 사용하는 프레임워크의 공식 문서로 재확인할 것.
- 기본 적용 최적화: bf16 (loss scaling 불필요), gradient checkpointing, Flash Attention, sequence packing. LoRA rank는 8에서 시작해 품질/메모리로 조정.
- 한 run에는 하나의 호스트 프레임워크만 — 프레임워크 체이닝 금지.

출처: [FSDP vs Megatron vs DeepSpeed 서베이](https://megacpp.com/blog/framework-survey-fsdp-vs-megatron-vs-deepspeed/), [Anyscale — fine-tuning 최적화](https://docs.anyscale.com/llm/fine-tuning/speed-and-memory-optimizations)

### 3. 학습/추론 일관성 (LLM 특화)

**chat template 불일치는 LLM 개발의 1순위 침묵 버그다.** 잘못된 role 토큰/포맷은 에러 없이 학습 신호를 오염시킨다.

- template 단일 소스: 학습·검증·추론 모두 `tokenizer.apply_chat_template`을 쓴다. 수동 문자열 조립 금지.
- **golden 동일성 테스트**: 샘플 대화 몇 건에 대해 학습 시 포맷 문자열 == 추론(서빙) 시 포맷 문자열을 string equality로 단언한다.
- special token 검증: EOS/PAD/추가 토큰의 ID가 학습 토크나이저와 서빙 엔진에서 일치하는지 확인한다.
- **같은 체크포인트라도 엔진마다 logits이 다르다**: 학습 엔진(FSDP 등)과 추론 엔진(vLLM/SGLang)은 커널·attention 구현·정밀도·배치 numerics가 달라 동일 가중치에서 다른 분포를 낸다. 평가·RL에서 이 차이를 인지하고, RL rollout에서는 train/infer logprob 발산을 모니터링한다 (보정 기법: Truncated Importance Sampling).
- HF `generate`와 vLLM의 샘플링 기본값이 다르므로 모든 생성 파라미터를 config에 명시 고정한다.

출처: [Training-Inference Mismatch in LLM RL (arXiv 2605.14220)](https://arxiv.org/pdf/2605.14220), [vLLM chat template issue](https://github.com/vllm-project/vllm/issues/6416)

### 4. 평가 재현성

경고 사례: Llama-3.1-8B-Instruct GSM8K는 공식 84.5, 커뮤니티 재측정 76.95 — 프롬프트/chat template/few-shot 구성 차이만으로 8점 가까이 벌어졌다.

- 하네스는 **lm-evaluation-harness**(task가 버전 관리되는 재현성 표준) 또는 **lighteval**을 쓰고, 하네스 버전(커밋/PyPI 버전)을 pin한다.
- 모든 평가 기록에 포함할 것: task 이름 + task 버전, `num_fewshot`, `--apply_chat_template` 사용 여부, system instruction, 백엔드(hf/vllm), dtype, 생성 파라미터.
- instruct 모델은 chat으로 평가한다: `--apply_chat_template --fewshot_as_multiturn`.
- 평가 config도 버전 관리한다 — 프롬프트 한 글자 차이가 점수를 바꾼다는 것이 실측되어 있다.

출처: [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness), [Llama-3.1 GSM8K 재현 격차](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/discussions/81), [프롬프트 민감도 (arXiv 2510.05152)](https://arxiv.org/pdf/2510.05152)

### 5. LLM-as-judge

기본 요건 세 가지를 항상 적용한다:

- **Position bias**: pairwise 비교는 양쪽 순서로 두 번 평가해 평균(swap-and-average)하거나 슬롯을 랜덤화한다.
- **Self-preference bias**: judge는 자기 모델 계열에 후하다 — 평가 대상과 다른 계열(cross-family)의 judge를 쓴다.
- **Verbosity bias**: 길이를 인지하는 루브릭을 쓴다 (길다고 좋은 답이 아님을 명시).

추가 규칙:
- pointwise와 pairwise는 같은 내용에도 다른 결과를 낸다 — 프로토콜을 하나로 정해 문서화하고 섞지 않는다.
- judge를 측정 도구로 검증한다: 사람 평가와의 일치도를 가정하지 말고 샘플로 확인한다.

출처: [judge 편향 연구 (IJCNLP 2025)](https://aclanthology.org/2025.ijcnlp-long.18/), [self-preference bias (arXiv 2505.19176)](https://arxiv.org/pdf/2505.19176)

### 6. 데이터 엔지니어링

- **스키마**: chat/tool 모델은 messages 스키마(`role`/`content` 턴 목록)로 표준화한다 — `apply_chat_template`에 직접 매핑된다. 단순 Q&A만 있으면 Alpaca 형식도 가능하나 프로젝트당 하나로 통일한다.
- **dedup**: MinHashLSH 계열 n-gram 해싱으로 문서/라인 중복 제거.
- **decontamination**: 평가셋 누출을 n-gram overlap + 의미 유사도(패러프레이즈 누출 대비)로 제거한다. exact match만으로는 변형된 누출을 놓친다.
- **dry-run**: 본 학습 전 소수 샘플로 스키마 파싱 → template 적용 → 토크나이즈 → 1 step 학습까지 통과를 확인한다 (→ [04-pipeline.md](04-pipeline.md)).

출처: [Anyscale — data preparation](https://docs.anyscale.com/llm/fine-tuning/data-preparation), [dedup 연구 (arXiv 2411.04257)](https://arxiv.org/html/2411.04257v3), [NVIDIA — LLM data preprocessing](https://developer.nvidia.com/blog/mastering-llm-techniques-data-preprocessing/)
