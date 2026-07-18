# 05. 비동기/병렬 최적화 + 프로파일링

## 핵심 규칙

- 병목 유형에 맞는 동시성을 쓴다: CPU-bound → multiprocessing, IO-bound → asyncio. 추측하지 말고 프로파일링으로 병목을 먼저 확인한다.
- DataLoader는 `num_workers`, `persistent_workers=True`, `pin_memory=True`, `prefetch_factor`를 튜닝한다.
- 모든 파이프라인 스테이지에서 GPU utilization, VRAM, RAM, CPU 사용량과 처리 속도(throughput)를 로그로 남긴다.
- 로그는 구조화(JSON)한다. 스테이지명/처리 건수/소요 시간/samples-per-sec/peak 메모리를 필수 필드로 포함한다.
- 최적화 전후는 반드시 실측 비교한다. 측정 없는 최적화 주장 금지.

## 상세

### 1. 동시성 선택

- **CPU-bound 전처리** (토크나이즈, 이미지 디코딩, 피처 연산): multiprocessing. PyTorch에서는 DataLoader `num_workers>0`가 그 역할이다. 단, 모든 샘플이 프로세스 간 큐를 통과하므로 큐 전송 자체가 병목이 될 수 있음을 인지한다.
- **IO-bound 작업** (API 호출, 파일/네트워크 다운로드, DB 조회): asyncio. 단일 스레드 동시성으로 오버헤드가 낮지만, 실제 non-blocking I/O를 쓸 때만 효과가 있다.
- **Python free-threading (3.14t)**: 3.14에서 공식 지원으로 승격됐지만 별도 빌드이고 C 확장 호환에 따라 GIL이 조용히 재활성화될 수 있다. "관찰 대상 — 벤치마크로 확인 후 도입" 스탠스를 유지한다.

출처: [PyTorch — data loading tutorial](https://docs.pytorch.org/tutorials/intermediate/intermediate_data_loading_tutorial.html), [Python — free-threading HOWTO](https://docs.python.org/3/howto/free-threading-python.html)

### 2. DataLoader 튜닝 체크리스트

- `num_workers`: 코어 수 기준으로 시작해 실측으로 조정
- `persistent_workers=True`: 에포크마다 워커 재생성 방지
- `pin_memory=True`: GPU 전송 가속
- `prefetch_factor`: GPU가 데이터를 기다리지 않도록 선적재
- 판단 기준은 GPU utilization이다: GPU util이 낮고 CPU가 바쁘면 데이터 로딩 병목이다.

### 3. 스테이지별 프로파일링

세 층위로 계측한다:

| 층위 | 도구 | 용도 |
|---|---|---|
| op/레이어 단위 | `torch.profiler` | CPU+CUDA 시간·메모리를 연산 단위로 분해, 병목 특정 |
| 실시간 관찰 | `nvitop`, `nvidia-smi dmon` | GPU util/VRAM을 프로세스 단위로 실시간 확인 |
| run 단위 자동 기록 | W&B system metrics (또는 Trackio) | CPU/GPU/메모리/디스크를 run 전체에 걸쳐 자동 로깅 |

- 헤드라인 지표는 두 개다: **VRAM 사용량**과 **GPU utilization(%)**. 파이프라인 각 스테이지에서 이 둘 + RAM/CPU를 기록한다.
- 코드 내 계측: 스테이지 시작/종료에 `torch.cuda.max_memory_allocated()`(CUDA일 때), `psutil` 기반 RAM/CPU를 로그로 남기는 공용 헬퍼를 하나 두고 전 스테이지가 공유한다.

출처: [nvitop](https://github.com/XuehaiPan/nvitop), [W&B system metrics](https://docs.wandb.ai/models/ref/python/experiments/system-metrics), [GPU utilization guide](https://towardsdatascience.com/a-guide-to-gpu-utilization/)

### 4. 구조화 로깅

- structlog 기반 JSON 로그를 표준으로 한다. 라이브러리성 코드는 stdlib `logging` + `NullHandler`만 쓴다.
- 스테이지 로그 필수 필드: `stage`, `num_processed`, `elapsed_sec`, `samples_per_sec`, `peak_vram_mb`(GPU 시), `peak_ram_mb`.
- 사람용 진행 표시는 tqdm/rich, 기계용 기록은 JSON 로그 — 역할을 분리하되 둘 다 남긴다.

출처: [structlog](https://pypi.org/project/structlog/)
