# 04. 파이프라인 설계

## 핵심 규칙

- 모든 파이프라인 스테이지는 `--limit N` 옵션으로 소수 샘플만으로 단독 실행할 수 있어야 한다.
- 각 스테이지의 입력/출력은 파일로 덤프해 쉽게 열어볼 수 있어야 한다. 중간 결과를 눈으로 확인 못 하는 파이프라인은 만들지 않는다.
- 대용량 처리는 청크 단위로 중간 저장하고, 중단 후 resume 가능해야 한다. 완료된 청크는 재실행 시 스킵한다.
- 파일 저장은 원자적으로 한다: 임시 파일에 쓰고 `os.replace`로 교체.
- 대용량 데이터는 스트리밍으로 처리한다. 전체를 메모리에 올리거나 마지막에 한 번에 저장하는 방식 금지.
- 학습/평가/전처리 등 모든 장기 실행 작업은 진행률 표시(tqdm/rich)를 붙인다.

## 상세

### 1. 소수 샘플 기반 설계 (debuggability)

파이프라인의 각 스테이지는 "무슨 원리로 동작하고 무엇이 들어가 무엇이 나오는지"를 소수 샘플로 즉시 확인할 수 있어야 한다.

- 모든 스테이지 CLI에 `--limit N` (예: 10개 샘플만 처리)을 표준으로 둔다.
- 스테이지별 입출력 샘플을 사람이 읽을 수 있는 형식(JSON/JSONL/Parquet)으로 덤프하는 옵션을 둔다.
- 캡처된 입력으로 개별 스테이지를 단독 재실행(replay)할 수 있으면 디버깅 속도가 극적으로 빨라진다 — 전체 파이프라인을 다시 돌리지 않고 문제 스테이지만 격리 실행한다.
- 본 실행 전 소수 샘플 dry-run으로 스키마/포맷/토크나이즈를 검증하는 것을 기본 절차로 한다 (→ [08-llm-development.md](08-llm-development.md)).

출처: [AI agent observability — trace/replay](https://mastra.ai/articles/ai-agent-observability)

### 2. Resume 가능한 처리 (interruption-tolerant)

RunPod spot pod 등 언제든 중단될 수 있는 환경을 기본 전제로 설계한다.

- **청크 단위 처리 + 즉시 저장**: N건 처리할 때 전부 끝나고 저장하는 게 아니라, 청크(예: 1000건)마다 저장한다.
- **idempotent 스테이지**: 재실행 시 이미 완료된 출력이 있으면 스킵한다. 출력 존재 여부(또는 매니페스트)가 진행 상태다.
- **원자적 저장**: 쓰다가 죽으면 손상 파일이 남는다. 임시 파일에 쓴 뒤 `os.replace(tmp, final)`로 교체하면 최종 파일은 항상 완전하다.

```python
def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)  # 같은 파일시스템 내에서 원자적
```

- **대형 모델 체크포인트**: `torch.distributed.checkpoint`의 `async_save`(백그라운드 저장으로 학습 중단 최소화) + safetensors 직렬화를 쓴다 (→ [07-ml-development.md](07-ml-development.md)).

출처: [PyTorch — distributed checkpoint recipe](https://docs.pytorch.org/tutorials/recipes/distributed_checkpoint_recipe.html), [DCP safetensors 지원](https://pytorch.org/blog/huggingface-safetensors-support-in-pytorch-distributed-checkpointing/)

### 3. 대용량 데이터 스트리밍

- 텍스트/혼합 데이터: HuggingFace `datasets`의 streaming(`IterableDataset`). 셔플은 `shuffle(buffer_size=...)` 근사 셔플, 에포크 간에는 `set_epoch()` 호출로 재셔플을 보장한다.
- 대용량 멀티모달(이미지/오디오/비디오): WebDataset(~1GB TAR 샤드, 순차 I/O로 처리량 극대화).
- 어느 쪽이든 "전체 로드 후 처리" 패턴은 금지 — 메모리 한도와 중단 내성 양쪽을 깨뜨린다.

출처: [HF datasets — streaming](https://huggingface.co/docs/datasets/stream), [WebDataset](https://huggingface.co/docs/hub/en/datasets-webdataset)

### 4. 진행 모니터링

- 모든 루프성 장기 작업에 tqdm 또는 rich progress를 붙인다. "지금 어디쯤인지"를 로그 파일과 터미널 양쪽에서 알 수 있어야 한다.
- 진행 바와 로그 출력이 섞여 깨지지 않도록 `tqdm.contrib.logging`(또는 rich의 로그 통합)을 쓴다.
- 진행률과 함께 처리 속도(samples/sec)를 남긴다 — 속도 저하는 문제의 조기 신호다 (→ [05-performance.md](05-performance.md)).

출처: [tqdm.contrib.logging](https://tqdm.github.io/docs/contrib.logging/)
