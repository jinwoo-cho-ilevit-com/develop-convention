# 01. 프로젝트 구조 + 네이밍

## 핵심 규칙

- 모듈/기능별로 최대한 분리해 개발한다. 각 모듈은 명확한 입출력 계약을 가진다.
- 앱/리서치/파이프라인 코드는 flat layout을 쓴다. `src/` 레이아웃은 배포용 라이브러리에만 쓴다.
- 파일은 작게, 모듈 경계는 명확하게 유지한다 — 사람도 에이전트도 필요한 부분만 읽을 수 있어야 한다.
- 변수/함수/클래스/스크립트/폴더명은 역할이 그대로 드러나는 시맨틱 네이밍으로 짓는다. PEP 8을 따른다.
- `_v2`, `_new`, `_old`, `_final` 같은 접미사 금지. 개선 시 rename-in-place로 이름 자체를 바꾼다.
- dead code는 발견 즉시 삭제한다. 주석 처리로 남기지 않는다.
- 주석은 코드가 표현할 수 없는 제약·의도만 쓴다. 다른 AI/팀원이 봐도 모를 내부 맥락, 불필요한 TMI, 자명한 내용 설명 금지.
- 리팩토링/이관 시 기존 프로젝트에서 사용하지 않는 것은 옮기지 않는다.
- 작업 완료 전 중복된 상수/함수/스크립트를 스캔해 제거한다.

## 상세

### 1. 모듈/기능별 분리

- 파이프라인은 스테이지 단위(전처리/학습/평가/추론 등)로 독립 모듈화한다. 각 스테이지는 단독 실행 가능해야 한다 (→ [04-pipeline.md](04-pipeline.md)).
- 모듈 간 의존은 명시적 인터페이스(함수 시그니처, 데이터 스키마)로만 연결한다. 에이전트는 아키텍처 경계를 침묵 속에 위반하는 경향이 있으므로, 경계가 코드와 문서에 명시되어야 병렬 개발이 가능하다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

### 2. 레이아웃: flat 기본

PyPA는 src-layout과 flat-layout 중 어느 쪽도 강제하지 않는다. src-layout의 이점(개발 중 사본의 우발적 import 방지, editable install 검증)은 **배포·재사용되는 라이브러리**에서 의미가 있고, NumPy·SciPy·Matplotlib도 flat을 유지하고 있다.

- 파이프라인/리서치/앱 코드: flat layout (예: 저장소 루트에 `preprocess/`, `train/`, `eval/`, `configs/`)
- PyPI 배포 또는 여러 프로젝트에서 재사용하는 패키지: src-layout
- 한 저장소에 여러 패키지가 필요해지면 uv workspaces를 쓴다: 루트 `[tool.uv.workspace]`에 members 등록, 전체가 단일 `uv.lock`과 단일 venv를 공유해 패키지 간 버전 충돌이 원천 차단된다.

출처: [PyPA — src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/), [uv workspaces로 Python 모노레포 구성](https://pydevtools.com/handbook/how-to/how-to-set-up-a-python-monorepo-with-uv-workspaces/)

### 3. 네이밍

- PEP 8: 함수/변수/모듈 `snake_case`, 클래스 `PascalCase`, 상수 `UPPER_SNAKE_CASE`. 모듈명은 짧은 소문자.
- 이름은 역할을 서술해야 한다: `data`보다 `raw_train_samples`, `process()`보다 `normalize_audio()`.
- 버전 접미사 금지. `parse_header_v2()`를 만들지 말고 `parse_header()`를 LSP rename으로 안전하게 교체한다. 리네임은 테스트를 낀 작은 단위로 수행한다.
- 리팩토링 시 기존 네이밍에 얽매이지 않는다. 이름이 현재 역할과 어긋나면 그 자리에서 개선한다.

출처: [PEP 8](https://peps.python.org/pep-0008/)

### 4. 주석 규칙

주석의 기준은 "처음 보는 사람(사람이든 모델이든)이 읽고 행동할 수 있는가"다.

- 쓸 것: 코드만으로 드러나지 않는 제약(예: "이 순서는 외부 API의 호출 제한 때문"), 알려진 한계와 업그레이드 경로, 비자명한 선택의 이유.
- 쓰지 않을 것: 다음 줄이 무엇을 하는지 설명(코드 중복), 작성 경위·히스토리(git이 담당), 내부자만 아는 맥락("지난번 회의에서 결정된 대로"), 개인 메모나 TMI.
- 문서(README/docstring)도 같은 기준: 처음 읽는 사람에게 필요한 것만, 간결하게.

### 5. 이관·정리 규칙

- 새 프로젝트로 옮길 때는 "실제로 호출되는 것"만 옮긴다. 사용 여부가 불분명하면 옮기지 않고, 필요해졌을 때 추가한다.
- dead code(미사용 함수, 주석 처리된 블록, 도달 불가 분기)는 발견 즉시 삭제한다. git 히스토리가 백업이다.
- 작업 마무리 단계에서 중복 스캔: 같은 상수가 두 곳에 정의되어 있지 않은지, 같은 일을 하는 함수/스크립트가 두 개 생기지 않았는지 확인 후 완료를 선언한다.

### 6. 에이전트 친화 구조 (context engineering)

컨텍스트 윈도우는 에이전트의 근본 제약이다. 거대한 단일 파일은 사람에게도 에이전트에게도 나쁘다.

- 하나의 파일은 하나의 관심사만 담는다. 파일이 길어지면 분리를 검토한다.
- 모듈별 문서(해당 디렉토리의 README 또는 AGENTS.md)는 그 디렉토리 범위의 내용만 담는다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

출처: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)
