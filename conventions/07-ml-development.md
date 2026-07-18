# 07. AI/ML 개발 공통

## 핵심 규칙

- 시드는 단일 헬퍼로 전체(random/numpy/torch/CUDA/DataLoader worker)를 한 번에 설정한다.
- 학습과 추론은 동일한 전처리 코드(같은 함수)를 임포트한다. 전처리 로직 복제 금지.
- 학습/추론 일관성은 샘플 replay 비교로 검증한다: 같은 입력을 양쪽 경로에 넣고 요소 단위로 비교.
- 성능 최적화(속도·메모리)를 기능 추가보다 우선한다. bf16, 최적화된 attention 등 검증된 최적화를 기본 적용한다.
- 모든 run은 실험 추적 도구에 config + git commit과 함께 기록한다.
- 체크포인트는 last-N + best + 마일스톤을 보존하고, 임시 pod 디스크가 아닌 network volume 또는 HF Hub에 저장한다.
- 학습은 언제든 중단될 수 있다고 전제하고 resume 가능하게 만든다 (spot pod 기본 전제).

## 상세

### 1. 재현성

시드 헬퍼 하나로 통일한다:

```python
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)          # CPU + 모든 CUDA 디바이스
    torch.use_deterministic_algorithms(True)  # 결정적 구현 없으면 에러
    torch.backends.cudnn.benchmark = False
```

- DataLoader 워커도 `worker_init_fn` + `generator`로 시드한다.
- 한계를 문서화한다: **bit-exact 재현은 하드웨어(GPU 세대), 배치 크기, 병렬 구성, 프레임워크 버전이 다르면 보장되지 않는다** (부동소수점 비결합성, 커널 선택 차이). 그래서 테스트는 허용 오차 밴드를 쓴다 (→ [06-testing-verification.md](06-testing-verification.md)).
- deterministic 모드는 기본 켠다. 성능 비용이 크지 않은 경우가 많지만 워크로드에 따라 다르므로, 병목으로 실측되면 그때 끄고 기록한다.

출처: [PyTorch — reproducibility notes](https://glaringlee.github.io/notes/randomness.html), [Training reproducibility in PyTorch](https://learnopencv.com/ensuring-training-reproducibility-in-pytorch/)

### 2. 학습/추론 일관성 (train-serve skew)

전처리가 학습과 추론에서 다르면 모델은 조용히 성능이 떨어진다. 예외도 에러도 없이.

- **코드 경로 단일화**: 전처리/피처 변환은 한 곳에 정의하고 학습·추론 양쪽이 같은 함수를 임포트한다. "추론용으로 비슷하게 다시 구현"이 skew의 주범이다.
- **dtype 일치**: 학습 float32 ↔ 서빙 float64 같은 불일치는 경계값에서 결과를 뒤집는다.
- **replay 검증**: 최근 추론 입력을 학습 전처리 경로에도 통과시켜 요소 단위 비교하는 스크립트를 둔다. 고정된 단위 테스트가 못 잡는 코드 경로 분기를 잡는다.
- LLM의 chat template 일관성은 별도 규칙이 있다 (→ [08-llm-development.md](08-llm-development.md)).

출처: [Confluent — eliminate training-serving skew](https://www.confluent.io/blog/eliminate-training-serving-skew-mlops/), [Hopsworks — training-inference skew](https://www.hopsworks.ai/dictionary/training-inference-skew)

### 3. 실험 추적

- 팀 공유·대시보드가 필요하면 **W&B**, 로컬 우선·경량·무료를 원하면 **Trackio**(HuggingFace, W&B API 호환 drop-in — `wandb.init/log/finish` 그대로). 자체 호스팅 요구가 강하면 MLflow.
- 어느 도구든 불변 규칙: 모든 run은 (a) resolved config, (b) git commit hash, (c) 데이터 버전/경로와 연결되어 기록된다. 추적 안 된 실험은 실험이 아니다.
- run 네이밍은 config 문서의 규칙을 따른다 (→ [02-config.md](02-config.md)).

출처: [Trackio](https://huggingface.co/blog/trackio), [W&B experiment tracking](https://wandb.ai/site/experiment-tracking/)

### 4. 체크포인트와 중단 내성

- **저장**: main process에서만 저장, DDP/FSDP 래퍼는 unwrap, optimizer state 포함. 대형 모델은 DCP `async_save`(백그라운드 저장) + safetensors (→ [04-pipeline.md](04-pipeline.md)).
- **보존 정책**: `latest`(resume용) + step 기반 last-N + best-by-metric + 주요 마일스톤. 구체적 N은 프로젝트 config로 정한다.
- **저장 위치**: RunPod pod 로컬 디스크는 pod와 함께 사라진다. network volume 또는 HF Hub/버킷에 저장한다.
- **비용 최적화**: 중단 허용 작업(스윕, 비긴급 실험)은 spot/interruptible pod를 쓴다 — 그래서 모든 학습이 resume 가능해야 한다. 보장이 필요한 장기 학습만 reserved를 쓴다.

출처: [RunPod — 재현 가능한 학습/체크포인트 가이드](https://www.runpod.io/articles/guides/reproducible-ai-made-easy-versioning-data-and-tracking-experiments)
