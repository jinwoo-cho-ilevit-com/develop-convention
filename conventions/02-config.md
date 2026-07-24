# 02. 중앙 Config + Ablation

## 핵심 규칙

- 하드코딩 절대 금지. 하이퍼파라미터, 경로, 상수, 매직 값은 전부 중앙 config에서 관리한다.
- config는 Hydra config group으로 조합 가능하게 구성한다. 실험 변형(ablation)은 코드 수정 없이 config 조합/오버라이드로만 만든다.
- config 값은 타입·범위를 검증한다(Pydantic 또는 typed dataclass). 잘못된 값은 실행 전에 fail-fast로 죽어야 한다.
- 모든 실행(run)은 그 시점의 resolved config 전체를 출력 디렉토리에 자동 저장한다.
- run 이름은 `{실험명}-{핵심조건}-{날짜}` 형식으로 식별 가능하게 짓는다.
- LLM 프롬프트는 인라인 문자열 리터럴이 아니라 전용 `.md` 파일로 외부화한다 — 코드 수정 없이 프롬프트를 편집·리뷰할 수 있어야 한다.

## 상세

### 1. 하드코딩 금지의 범위

코드에 직접 쓰면 안 되는 것: 파일 경로, 모델명/체크포인트 경로, 배치 크기, 학습률, 시드, 샘플 수 제한, API 엔드포인트, 디바이스 문자열, 임계값. 이들은 모두 config 필드다.

예외: 수학적 정의상 불변인 값(예: 초당 밀리초 1000)은 코드 내 명명된 상수로 허용된다. "지금은 안 바뀔 것 같은 값"은 예외가 아니다.

### 2. 도구 선택: Hydra + 검증 레이어

2025-2026 기준 계층적·조합형 config의 사실상 표준은 Hydra다.

- **config group**: `configs/model/`, `configs/data/`, `configs/train/` 처럼 축별로 나누고, 실험은 조합으로 정의한다.
- **ablation**: `python train.py --multirun model=base,large data=full,filtered` 처럼 조합 스윕이 한 줄로 된다. 각 run은 자동으로 격리된 출력 디렉토리에 config+로그가 저장된다.
- **검증 레이어**: Hydra(조합) + Pydantic(타입/범위 검증) 조합이 현재 권장 패턴이다. `train_size=1.5` 같은 값은 학습 시작 전에 죽어야 한다.
- 경량 대안: YAML 없이 코드-우선 typed config를 원하면 tyro(dataclass 기반, 정적 타입체크 우수) 또는 draccus. 프로젝트당 하나만 골라 일관되게 쓴다.

출처: [Hydra — configuring experiments](https://hydra.cc/docs/patterns/configuring_experiments/), [Hydra + Pydantic config 관리](https://towardsdatascience.com/configuration-management-for-model-training-experiments-using-pydantic-and-hydra-d14a6ae84c13/), [tyro](https://github.com/brentyi/tyro), [draccus](https://github.com/dlwh/draccus)

### 3. Ablation study 구조

- 실험 축(모델 크기, 데이터 필터링, 학습 기법 등)을 config group으로 정의하면 모든 조합이 선언적으로 표현된다.
- 각 조합 run의 결과는 실험 추적 도구에 config와 함께 기록되어, "어떤 조합이 어떤 성능"인지 코드를 열지 않고 비교 가능해야 한다 (→ [07-ml-development.md](07-ml-development.md)).
- ablation 조합 목록 자체도 config 파일로 관리한다 — 재실행 가능해야 실험이다.

### 4. 프롬프트 외부화

LLM 프롬프트도 config와 같은 취급이다: 코드에 인라인으로 박으면 프롬프트 한 줄 고치는 데 코드 리뷰·배포가 필요해지고, diff에서 프롬프트 변경과 로직 변경이 섞인다. 전용 `.md` 파일(예: `prompts/summarize.md`)로 분리하면 프롬프트 편집이 문서 편집이 되고, 버전 관리·리뷰·실험 추적이 로직과 독립적으로 돌아간다. 프롬프트 파일 경로 자체는 config 필드다.

### 5. Config 스냅샷과 재현성

- run 출력 디렉토리에는 최소한 다음이 남아야 한다: resolved config 전체(오버라이드 반영 후), git commit hash, 실행 명령.
- Hydra는 run별 출력 디렉토리에 config를 자동 저장한다. 이 기본 동작을 끄지 않는다.
- config 파일은 코드와 함께 버전 관리한다. "그때 그 설정"을 커밋 히스토리에서 복원할 수 있어야 한다.
