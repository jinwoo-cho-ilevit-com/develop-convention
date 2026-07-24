# 15. 문서-코드 동기화 추적

## 핵심 규칙

- 문서를 변화 속도가 다른 4계층으로 분리한다: 입출력 계약은 코드(type hints·스키마)가 단일 소스(손으로 쓴 입출력 문서 금지), 모듈 로직은 디렉토리별 AGENTS.md, 전체 플로우는 루트 ARCHITECTURE.md, 결정·이력은 구조화 커밋 + ADR.
- 함수 설명은 별도 문서가 아니라 docstring으로. 자명한 함수는 쓰지 않고, 비자명한 알고리즘 선택만 기록한다.
- 모듈 문서에서 에이전트는 `docsync:managed` 마커 내부만 재생성한다. 마커 밖 사람 섹션은 불가침. managed 블록에는 검증 커밋·날짜를 스탬프한다.
- managed 문서(L2 모듈·L3 플로우)의 사실 주장은 코드 위치(file:symbol)로 인용 가능해야 한다. 인용할 수 없는 주장은 쓰지 않는다 — 코드에서 유도되지 않는 결정 근거·실패 기록은 ADR·사람 섹션에 쓴다.
- 갱신은 변경 시점 sync가 주 메커니즘(`/docsync` — 마지막 문서화 커밋 ~ HEAD 증분, 첫 실행은 전체 = 부트스트랩). 주기 실행은 audit 전용 — 서사 문서의 주기적 통재생성 금지.
- audit은 sync 자체의 생존 확인부터(dead-man's switch: 마지막 sync 이후 N 커밋/M일 초과 시 그 사실부터 경고). 핵심 검사는 blind rebuild — 기존 문서를 차단하고 코드만으로 재작성해 주장 단위로 대조하고, 코드 인용이 안 붙는 주장은 환각 후보로 보고한다. 의미가 같은 표현 차이는 drift로 취급하지 않는다.
- 사람이 managed 섹션을 수정하면 조용히 되돌리지 말고 이유 코드를 corrections 로그에 기록해 이후 생성 프롬프트에 반영한다(RMA 루프). 같은 섹션에 모순된 이유가 쌓이면 그 섹션은 사람 소유로 강등한다.
- ADR은 append-only — 수정 대신 새 ADR로 supersede. 채택된 결정만이 아니라 뒤집힌 결정·롤백도 사유와 함께 남긴다. 에이전트는 ADR 참조 시 supersession 체인을 끝까지 해석해 유효한 결정만 따른다.
- 시각화는 Mermaid로 일원화한다(텍스트라 diff·리뷰 가능, GitHub 네이티브 렌더링, 에이전트가 읽고 씀). 모듈 의존 그래프는 결정적 도구(pydeps, madge 등)로 생성하고 손으로 유지하지 않는다.
- 리뷰 게이트에 "코드 변경 ↔ 문서 갱신 정합" 확인을 포함한다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)).

## 상세

### 1. 왜 계층 분리인가

"전체 플로우 · 모듈별 구현 로직 · 입출력 계약 · 변경 이력"은 변화 속도와 성격이 다른 정보다. 하나의 큰 문서로 만들면 갱신 비용이 가장 높은 부분의 속도로 전체가 썩는다. 계층별로 맞는 메커니즘과 갱신 주체를 두는 것이 원칙이다.

| 계층 | 추적 대상 | 메커니즘 | 갱신 주체 |
|---|---|---|---|
| L1 | 입출력 계약 | 코드 자체(type hints, pydantic 등 스키마). 문서가 필요하면 코드에서 생성 | 자동 |
| L2 | 모듈별 구현 로직 | 디렉토리별 AGENTS.md — 역할, 핵심 로직(입력→처리→출력 서사, invariant, 엣지 케이스), Mermaid, 함정 | 에이전트 + 사람 리뷰 |
| L3 | 전체 플로우 | 루트 ARCHITECTURE.md — 엔트리포인트별 sequence diagram + 의존 그래프 | 에이전트 + 사람 리뷰 |
| L4 | 결정·변경 이력 | 구조화 커밋 본문(Why/What/How/Result) + append-only ADR | 사람 (에이전트 초안) |

- L1을 손으로 쓰지 않는 이유: 손으로 쓴 입출력 문서는 코드와 어긋나는 순간부터 해악이다. 코드가 단일 소스면 이 계층의 drift는 구조적으로 불가능하다.
- L2를 디렉토리별 AGENTS.md에 두는 이유: 루트에 몰아둔 문서는 diff에 걸리지 않아 썩는다. 코드 옆에 두면 해당 모듈을 고치는 diff에 문서가 같이 보이고, 에이전트가 그 디렉토리에서 작업할 때 자동으로 컨텍스트로 로드된다 — 추적 시스템과 에이전트 컨텍스트 시스템이 같은 산출물이 된다.
- 함수 레벨은 docstring: 코드와 같은 파일에 있어야 리팩토링을 따라다닌다.

요약 원칙: **생성 가능한 것은 생성하고, 사람은 '왜'만 쓰고, 갱신은 게이트로 강제한다.**

### 2. docsync 스킬 — 증분 sync

갱신 절차는 [templates/skills/docsync/SKILL.md](../templates/skills/docsync/SKILL.md)로 스킬화한다. SKILL.md는 도구 중립 마크다운 절차서다 — Claude Code에서는 `.claude/skills/docsync/`로 복사해 스킬로 실행하고, Codex/Cursor 등에서는 같은 파일을 프롬프트로 참조해 동일한 절차를 수행한다.

- **상태 파일** (`.docsync/state.json`): 마지막 문서화 커밋 + managed 섹션별 content hash. 상태가 있으면 마지막 커밋 ~ HEAD의 변경 모듈만, 없으면(첫 실행) 전체 모듈 — 부트스트랩은 빈 상태의 sync 특수 케이스라 별도 부트스트랩 도구 의존이 없다(self-contained).
- **sync 파이프라인**: RMA 감지 → 범위 산출 → 모듈별 managed 섹션 갱신 → 전역 패스(의존 그래프 재생성, ARCHITECTURE.md 갱신, 모듈 간 모순 검수) → ADR 후보 질문 목록 보고 → fresh-context 검증 → 상태 갱신.
- **트리거 3종**:

| 트리거 | 방식 | 역할 |
|---|---|---|
| 수동 | 작업 마무리 시 `/docsync` | 주 메커니즘 |
| 리뷰 게이트 | 리뷰 항목에 "코드 변경 ↔ 문서 갱신 정합" 포함 | 누락 방지 |
| 주기 | `/docsync --audit` (예: 주 1회) | drift 감사 + 전역 정합성 |

시간 기반 통재생성을 주 메커니즘으로 쓰지 않는 이유: 문서화 시점에 변경의 맥락("왜")이 이미 사라져 diff 역추적·추측이 되고, 서사 문서를 주기적으로 LLM이 통재생성하면 문체가 흔들리고 diff가 비대해져 아무도 리뷰하지 않게 된다. 주기 실행이 맞는 영역은 결정적으로 유도되는 산출물(다이어그램)의 재생성과 저장소 전체 정합성 감사뿐이다.

### 3. 검증 계층 — 문서가 썩지 않게 하는 장치

생성만 하는 문서화 도구의 공통 한계가 설계 근거다. 가장 근접한 기존 스킬인 doc-it(생성·감사·갱신 지원)조차 저자가 "수동 트리거뿐이라 코드 변경 시 문서가 조용히 낡는다", "그럴듯하지만 존재하지 않는 내용을 생성하기도 한다"를 한계로 명시한다. 아래 장치들이 그 공백을 막는다.

출처: [dosu — A Claude Code Skill for Auto-Generating Project Docs](https://dosu.dev/blog/claude-code-skill-doc-it)

- **dead-man's switch**: 죽은 sync 파이프라인은 건강한 파이프라인과 똑같이 보인다. audit의 첫 검사는 문서가 아니라 "sync가 살아있는가"다.
- **신선도 스탬프**: 모든 managed 블록에 검증 커밋·날짜를 기록하고, 임계 초과 시 낡음 배너를 삽입한다. 낡은 문서가 최신 문서와 같은 권위로 읽히는 것이 실제 실패 모드다.
- **blind rebuild**: 증분 sync는 이전 문서를 발판으로 재생성하므로 초기 환각이 기정사실로 세탁된다. 기존 문서를 차단한 재작성본과 유지본을 주장 단위로 대조해 이 사슬을 끊는다. 유지본에만 있는 주장은 코드 인용을 시도하고, 인용 실패 = 환각 후보. 확정 환각은 삭제, 진짜 암묵지는 사람 섹션이나 ADR로 승격해 "코드에서 나온 척"을 중단시킨다.
- **관용(tolerance)**: 의미가 같은 표현 차이를 drift로 오판해 멀쩡한 문서를 반복 재작성하지 않는다.
- **RMA 루프**: 사람의 수정은 버리는 신호가 아니라 학습 신호다. managed 섹션의 hash 불일치 + 대응 코드 diff 없음 = 사람 개입으로 감지하고, 이유 코드(wrong/stale/unclear/granularity)를 `.docsync/corrections.jsonl`에 기록해 같은 섹션 유형의 이후 생성에 negative 예시로 주입한다.
- **fitness test (파일럿)**: 문서만 받은 에이전트에게 과제를 주고 실제 실행 결과와 대조 — "문서가 갱신됐는가"가 아니라 "이 문서로 일이 되는가"로 품질을 측정한다. 단 실행으로 ground truth를 확보할 수 있는 대상에 한정하고, 검증 불가 문서는 "미검증"으로 표기한다(채점 자체가 미검증 LLM 판단이 되면 측정으로 위장한 주장이 된다 — [00-principles.md](00-principles.md)의 evidence over claims).

### 4. 이력 계층 — 커밋과 ADR

- 커밋 단위 이력은 구조화 커밋 본문(Why/What/How/Result)이 담당한다 — `git log`만으로 개발 노트가 재구성되게 쓴다.
- 구조를 바꾼 결정은 ADR(`docs/adr/NNNN-제목.md`)로: 배경·결정·대안·결과를 짧게. 결정이 바뀌면 수정하지 않고 새 ADR로 supersede한다 — Nygard의 원문 그대로 "If a decision is reversed, we will keep the old one around, but mark it as superseded."
- 실패도 기록한다: 뒤집힌 결정·롤백을 사유와 함께 남긴다. 장애 대응 시 진짜 필요한 것은 "그 방법은 이미 시도됐고 실패했다"는 기록이다.
- 소비 규칙: 에이전트가 ADR을 검색·참조할 때는 supersession 체인을 끝까지 따라가 유효한 결정만 사용한다. 뒤집힌 옛 결정을 그대로 따르는 사고를 막는다.

출처: [Michael Nygard — Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), [adr.github.io](https://adr.github.io/)

### 5. 시각화

- Mermaid 일원화: 텍스트 기반이라 git diff·리뷰가 되고, GitHub가 markdown 코드 블록에서 네이티브 렌더링하며, 에이전트가 읽고 쓸 수 있어 갱신 파이프라인에 자연스럽게 들어간다.
- 결정적으로 생성 가능한 것은 LLM에 맡기지 않는다: 모듈 의존 그래프는 pydeps(Python)·madge(JS/TS) 같은 도구 출력에서 생성. LLM은 sequence/flow diagram처럼 판단이 필요한 것만 생성하고 사람이 리뷰한다.

출처: [GitHub — Include diagrams in your Markdown files with Mermaid](https://github.blog/developer-skills/github/include-diagrams-markdown-files-mermaid/)

### 6. 기존 도구와의 관계

- Claude Code 공식 플러그인에는 문서 생성·문서-코드 동기화 플러그인이 없다(2026-07 확인) — 이 컨벤션과 docsync 스킬이 그 공백을 메운다.
- doc-it은 생성 + 1회성 감사(낡은 참조·미문서화 탐지)에서 참고할 선례다. docsync의 symlink 해석, 스코프 실행(`/docsync <path>`), 최종 보고 형식은 doc-it의 워크플로우를 차용했다. 차이는 검증 계층(상태 기반 증분, dead-man's switch, blind rebuild, RMA)의 유무다.
- 호스팅형 자동 위키 서비스는 저장소 밖 외부 서비스에 의존하므로, 이 저장소의 도구 중립·self-contained 원칙과 맞지 않아 채택하지 않는다.

출처: [anthropics/claude-code plugins README](https://github.com/anthropics/claude-code/blob/main/plugins/README.md), [dosu — doc-it](https://dosu.dev/blog/claude-code-skill-doc-it)

### 7. 프로젝트 적용

1. [templates/skills/docsync/SKILL.md](../templates/skills/docsync/SKILL.md)를 프로젝트의 `.claude/skills/docsync/SKILL.md`로 복사한다 (Claude Code 외 도구는 AGENTS.md에서 이 파일 경로를 참조).
2. AGENTS.md에 docsync 선택 블록을 유지한다 (→ [templates/AGENTS.md](../templates/AGENTS.md)).
3. 첫 `/docsync` 실행이 부트스트랩이다 — 별도 초기화 절차 없음.
