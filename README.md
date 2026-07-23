# Development Conventions

개발 컨벤션 문서 모음. 범용 개발 규칙 + AI/ML·LLM 전용 규칙으로 구성되며, 사람과 AI 에이전트가 함께 소비한다.

각 문서는 최상단 `## 핵심 규칙`(에이전트 지시 파일에 발췌 가능한 명령형 규칙)과 사람용 상세 설명 + 출처로 구성된다. 모든 사실 주장은 2025-2026 시점 리서치로 검증된 출처를 인용한다.

## 문서 맵

| 문서 | 내용 |
|---|---|
| [00-principles.md](conventions/00-principles.md) | 핵심 원칙: fresh start, fresh-context, evidence over claims, 사실 기반 판단, 실측 우선 |
| [01-structure-naming.md](conventions/01-structure-naming.md) | 모듈 분리, flat layout, PEP 8 시맨틱 네이밍, dead code/중복 제거 |
| [02-config.md](conventions/02-config.md) | 하드코딩 금지, Hydra config group + 검증, ablation 조합, run 스냅샷 |
| [03-environment.md](conventions/03-environment.md) | uv/ruff 툴체인, 로컬↔RunPod 이식성, device 추상화(CPU fallback) |
| [04-pipeline.md](conventions/04-pipeline.md) | 소수 샘플 디버깅, 원자적 저장 + resume, 스트리밍, 진행 모니터링 |
| [05-performance.md](conventions/05-performance.md) | 비동기/병렬 선택, DataLoader 튜닝, GPU/RAM 프로파일링, 구조화 로깅 |
| [06-testing-verification.md](conventions/06-testing-verification.md) | 최소-의미 테스트, golden file, 허용 오차 밴드, CPU 스모크, 완료 검증 |
| [07-ml-development.md](conventions/07-ml-development.md) | 시드/재현성, train-serve skew 방지, 실험 추적, 체크포인트/spot pod |
| [08-llm-development.md](conventions/08-llm-development.md) | 학습 프레임워크 라우팅, FSDP2/bf16, chat template 일관성, 평가 재현성, LLM-as-judge, 데이터 |
| [09-agentic-workflow.md](conventions/09-agentic-workflow.md) | CLAUDE.md/AGENTS.md 작성법, workflows 우선 병렬 개발(worktree는 파일 격리용), 개발 후 리뷰 게이트(Codex 플러그인/cursor CLI), 모델 라우팅 |
| [10-llm-api-inference.md](conventions/10-llm-api-inference.md) | LLM API 추론 모듈: 어댑터 구조, 호출/rate limit, 에러/재시도, 앙상블, 캐싱/resume, 비용/평가 |
| [11-llm-api-providers.md](conventions/11-llm-api-providers.md) | Provider별 고려사항(OpenAI/Anthropic/Gemini/DeepSeek/OpenRouter) + 구조화 출력 계층 폴백 |
| [12-docs-reference.md](conventions/12-docs-reference.md) | 최신 문서 참조 절차(4계층) + provider별 canonical URL 레지스트리 + 스모크 확정 |
| [13-secret-management.md](conventions/13-secret-management.md) | 시크릿 하드코딩·커밋 금지, 중앙 매니저(Infisical) 주입, 코드에서 env 읽기, 컨테이너·CI 머신 신원, 스캐닝·회전 |
| [14-context-management.md](conventions/14-context-management.md) | 메인 컨텍스트 최소화(방화벽·위임), compaction/clear 동작 이해, 외부 파일·CLAUDE.md·auto memory로 맥락 손실 방지 |

## 새 프로젝트에 적용하는 법

1. [templates/AGENTS.md](templates/AGENTS.md)·[templates/CLAUDE.md](templates/CLAUDE.md)·[templates/pyproject.toml](templates/pyproject.toml)을 새 프로젝트로 복사하고, placeholder(`[...]`, `PROJECT_NAME`)를 채운 뒤 해당 없는 선택 블록(ML/LLM API)을 삭제하거나 주석 해제한다. 공통 지침의 단일 소스는 AGENTS.md(오픈 표준 — Codex/Cursor 등도 읽음)이고, CLAUDE.md는 `@AGENTS.md`로 이를 임포트한다.
2. 지시 파일은 간결하게 유지한다 — 전체 문서를 붙여넣지 말고, 그 프로젝트에서 실수를 막는 데 필요한 규칙만 넣는다 (→ [09-agentic-workflow.md](conventions/09-agentic-workflow.md)). 전체 컨벤션은 이 저장소를 clone한 로컬 경로로 참조한다 (템플릿의 `[CONVENTION_PATH]`에 기입).

### 도구별 동작 방식

선행 조건: 각 기기에서 이 저장소를 clone하고, 그 경로를 프로젝트 AGENTS.md의 `[CONVENTION_PATH]`에 기입.

| 도구 | 동작 |
|---|---|
| Claude Code | `CLAUDE.md` → `@AGENTS.md` 임포트로 공통 지침 로드. 작업 중 필요한 컨벤션 문서를 경로로 직접 Read. Claude 전용 지침은 CLAUDE.md에만 추가 |
| Codex CLI | `AGENTS.md`를 네이티브로 읽음(루트→현재 디렉토리 체인, 용량 상한 있음 — 발췌+경로 참조 구조가 이에 맞음). 추가 설정 불필요 |
| Cursor | AGENTS.md 표준 공동 제정사 — 네이티브로 읽음. 항상 강제할 소수 규칙만 필요 시 `.cursor/rules/`로 승격 |
| 기타 (Gemini CLI, Windsurf, Aider 등) | AGENTS.md 표준을 읽는 도구는 동일하게 동작. 미지원 도구만 해당 도구의 지시 파일에서 AGENTS.md를 가리키는 한 줄 추가 |

**클라우드 실행 에이전트 주의**: 로컬 경로 참조는 로컬 실행에만 유효하다. 격리 샌드박스(Codex 클라우드, Cursor 백그라운드 에이전트, Claude Code 웹)에서는 해당 프로젝트에 이 저장소를 git submodule로 포함하거나, AGENTS.md에 규칙 요약을 복사해 self-contained로 만든다. 클라우드 사용이 실제로 시작될 때 submodule 방식 전환을 권장.

### AI에게 시키는 법

템플릿이 프로젝트에 있으면 **평소에는 명령이 필요 없다** — AGENTS.md가 자동 로드되어 규칙이 적용된다. 명령이 필요한 경우는 아래뿐이며, 특정 문서를 확실히 적용시키고 싶을 때는 문서 번호로 지칭하면 된다.

새 프로젝트 부트스트랩 (1회):
```
<컨벤션 저장소 경로>/templates/의 AGENTS.md, CLAUDE.md, pyproject.toml을
이 프로젝트에 복사하고 placeholder를 채워줘. [한 줄 설명], [일반/ML/LLM API] 프로젝트야.
```

특정 규칙 강제:
```
전처리 파이프라인 만들어줘. conventions/04의 핵심 규칙(소수 샘플 실행, resume) 지켜서.
DeepSeek 어댑터 추가해줘. 12 절차대로 공식 문서 먼저 fetch해서 확인하고 구현해.
```

리뷰:
```
이 diff를 <컨벤션 저장소 경로> 컨벤션 기준으로 리뷰해줘.
위반 사항은 문서 번호와 함께, 작성 세션이 아닌 별도 리뷰 에이전트로.
```

재작성/리팩토링:
```
이 모듈을 재작성해줘. 00 원칙대로: 기존 구조에 얽매이지 말고 스펙에서 출발하되,
재작성 전에 characterization test로 기존 동작 먼저 고정해.
```

컨벤션 갱신 (낡은 사실 발견 시):
```
공식 문서 확인해보니 11 문서의 [X] 내용이 바뀌었어. 컨벤션 갱신하고 커밋해줘.
```

## 전체 규칙 요약 (에이전트 주입용)

### 원칙
- 새 개발/리팩토링은 기존 구조·주석·기억이 아니라 요구사항과 동작(스펙)에서 출발한다.
- 사전 지식으로 판단하지 않는다. 라이브러리/API/모델 사실은 context7·web search·HuggingFace로 현재 시점 확인 후 반영한다.
- 리뷰·재작성은 fresh context(별도 subagent/세션)에서 수행하고, 완료는 실행 증거로만 주장한다. 작성자와 검증자를 분리한다.
- 재작성 전 characterization test로 기존 동작을 고정한다. 성능·생산성 개선은 실측으로만 주장한다.

### 구조·네이밍
- 모듈/기능별 분리, 명확한 입출력 계약. 파일은 작게, 경계는 명확하게.
- 앱/리서치/파이프라인 코드는 flat layout (src/는 배포 라이브러리만). 다중 패키지는 uv workspaces.
- 시맨틱 네이밍 + PEP 8. `_v2`/`_new` 금지, rename-in-place. dead code 즉시 삭제, 미사용 코드 이관 금지, 완료 전 중복 스캔.
- 주석은 코드가 표현 못 하는 제약·의도만. 내부자만 아는 맥락, TMI, 자명한 설명 금지.

### Config
- 하드코딩 절대 금지 — 경로/하이퍼파라미터/상수는 전부 중앙 config. Hydra config group으로 조합하고 타입 검증으로 fail-fast.
- ablation은 코드 수정 없이 config 조합으로만. 모든 run은 resolved config + git hash를 출력 디렉토리에 저장.

### 환경
- uv(uv.lock 커밋) + ruff + pre-commit/CI. 개발 도구는 `[dependency-groups]`.
- 로컬(macOS/CPU/MPS)과 RunPod(Linux/CUDA)에서 수정 없이 동일 실행 — uv platform marker 또는 `--torch-backend=auto`.
- device는 단일 헬퍼로만 선택(`torch.accelerator` 기반), `.cuda()` 인라인 금지. GPU 없으면 CPU로 실행·테스트 가능해야 한다.

### 파이프라인
- 모든 스테이지에 `--limit N` 소수 샘플 실행 + 입출력 덤프. 본 실행 전 소수 샘플 dry-run.
- 청크 단위 중간 저장 + resume(완료분 스킵). 저장은 temp→`os.replace` 원자적으로. 대용량은 스트리밍, 전체 메모리 적재 금지.
- 장기 작업은 tqdm/rich 진행 표시 + 처리 속도 로그.

### 성능
- CPU-bound→multiprocessing, IO-bound→asyncio. 병목은 프로파일링으로 먼저 확인.
- 스테이지별 GPU util/VRAM/RAM/CPU + throughput을 구조화(JSON) 로그로 기록.

### 테스트·검증
- 불필요한 pytest 최소화: 핵심 로직 단위 테스트 + E2E 스모크 1~3개. 메트릭은 허용 오차 밴드로 단언, golden file은 명시 플래그로만 갱신.
- CI는 CPU + 소수 샘플로 GPU 코드 경로 스모크. TODO/스텁/skip은 완료가 아니라 블로커.

### AI/ML
- 시드는 단일 헬퍼로 통합 설정. 학습/추론은 동일 전처리 함수를 임포트(복제 금지), 샘플 replay로 skew 검증.
- 모든 run은 실험 추적 도구에 config+commit과 함께 기록. 체크포인트는 last-N+best+마일스톤을 network volume/HF Hub에 저장. 학습은 중단 전제(resume 가능)로 설계.

### LLM
- 프레임워크는 용도별 라우팅(단일 GPU→Unsloth/TRL, 멀티 GPU 재현성→Axolotl, RL→TRL+vLLM, 프리트레이닝→torchtitan). torchtune 금지(deprecated). FSDP2 + bf16 기본.
- chat template은 `apply_chat_template` 단일 소스, 학습/추론 문자열 동일성 golden 테스트, 샘플링 파라미터 config 명시.
- 평가는 하네스/task 버전·fewshot·template 적용 여부까지 기록. judge는 양방향 순서 + cross-family + 길이 인지 루브릭.

### LLM API 추론
- provider 추상화는 얇은 native SDK 어댑터 + 순수 payload builder(네트워크 없이 테스트 가능). "OpenAI 호환"은 wire 포맷만 — capability/스키마/에러/토큰 매핑은 provider별 격리.
- 모델별 동시성 상한 + rate limit 헤더 기반 적응 제어. 에러는 typed exception으로 분류, 재시도 주인은 한 곳, 앙상블 재시도는 멤버 단위. 실패 태스크는 에러 행으로 기록하고 배치는 계속.
- 구조화 출력은 최소공통분모 스키마 + 계층 폴백(native schema → json_object+프롬프트 → 파싱 → 검증-재요청 2~3회 상한). 파싱 전 finish_reason 분류 먼저. reasoning 호출에 샘플링 파라미터 금지.
- 응답 캐시는 개발/디버그 전용. resume은 fingerprint(spec+seed+데이터+프롬프트) 검증 의무. 가격/모델명 하드코딩 금지, dated snapshot 고정, 행 단위 토큰+비용 기록, 예산 상한.
- provider API 코드 작성 전 canonical URL 레지스트리의 공식 문서를 fetch해 확인. SDK 사용법은 provider 공식 skill > ctx7 순, 예외/시그니처는 설치된 SDK 소스, 문서에 없는 동작은 스모크 테스트로 실측 확정.

### 에이전트 워크플로우
- CLAUDE.md/AGENTS.md는 간결하게(비대하면 규칙 무시 유발), 모듈별 계층화, 가끔 쓰는 지식은 Skills로.
- 병렬화는 workflows/subagent 오케스트레이션 우선. git worktree는 파일 격리 수단이라 겹치는 파일을 수정해 충돌할 때만 도입. 분해 표(담당·파일·의존성·통합·리뷰 도구) 작성 후 시작, 공유 계약은 실행 중 동결, lock/마이그레이션은 단일 담당.
- 각 에이전트는 개발 완료 후 작성자와 분리된 리뷰를 필수로 거친다. 리뷰 도구는 개발 전에 선택 — 경로 A: Codex 플러그인(Stop 게이트 `ALLOW`/`BLOCK` + `/codex:review`, 구성된 기본 모델, 오케스트레이터가 종합·반영) / 경로 B: cursor CLI(`gpt-5.3-codex-xhigh` 깊게 또는 `composer-2.5` 빠르게, 읽기 전용).
- 브랜치별 테스트 통과 후 머지 + 통합 검증 1회. 모델은 난이도별 라우팅(기계적→경량, 표준→중간, 아키텍처→상위).

### 시크릿 관리
- 시크릿을 코드·config·로그·이미지에 하드코딩 금지, 평문 `.env` 커밋 금지(`.gitignore`+`.env.example` 키 목록만). 단일 원본은 중앙 시크릿 매니저(Infisical 권장).
- 로컬·CI·컨테이너 모두 실행 시점 주입(`infisical run -- <cmd>`)으로 공급하고 디스크에 평문 잔존 금지. 코드는 그대로 env로 읽는다(`os.environ[...]`). 코딩 에이전트도 동일 규칙.
- 컨테이너·CI는 머신 신원(Universal Auth)으로 최소권한·단기 토큰 인증. 환경(dev/staging/prod) 분리 + 회전 + gitleaks 스캐닝(pre-commit/CI). 이미 커밋된 시크릿은 즉시 회전·재발급.

### 컨텍스트 관리
- 메인 컨텍스트는 오케스트레이터 — 결론만 보관하고 탐색·검색·대용량 읽기는 subagent(별도 컨텍스트 창)에 위임해 요약만 받는다. 디렉토리 스윕·큰 파일 통독을 메인에서 하지 않는다. 독립 작업은 병렬 디스패치 + 장기 실행은 백그라운드.
- 진실의 원본은 대화가 아니라 파일에 둔다 — 계획·결정·진행상황을 외부 파일에 지속화하고 마일스톤마다 체크포인트. 지속 규칙·사실은 CLAUDE.md(세션마다 로드·compaction 후 재주입)와 auto memory(`/clear`도 견딤)에 둔다.
- auto-compaction은 비활성화 불가(오래된 tool output 제거 → 요약). 임박 시 `/compact <focus>`로 남길 것 지시, 무관한 작업 사이·오염 시 `/clear`. resume·compaction 직후 git status·cwd·상태 아티팩트 재확인 후 재개.
