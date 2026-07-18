# 09. AI 에이전트 병렬 개발 워크플로우

## 핵심 규칙

- CLAUDE.md/AGENTS.md는 간결하게 유지한다. 비대한 지시 파일은 규칙 무시를 유발한다. 각 줄에 "이걸 지우면 에이전트가 실수하는가?"를 물어 아니면 지운다.
- 모듈별 지시는 해당 디렉토리의 AGENTS.md에 계층화한다(closest wins). 가끔 필요한 지식은 Skills로 분리한다.
- 병렬 작업은 실행 전에 분해 표(Task | 담당 | 파일 | 의존성 | 통합 지점)를 만든다. 파일 소유권이 겹치는 작업은 병렬 금지 — 순차로 돌린다.
- 에이전트마다 하나의 worktree. 공유 인터페이스/스키마는 병렬 실행 중 동결한다. lock 파일과 마이그레이션은 단일 담당만 수정한다.
- worktree별 브랜치는 각자 테스트 통과 후 머지하고, 머지 후 통합 검증을 1회 수행한다.
- 리뷰·검증은 작성자와 다른 fresh-context 에이전트가 수행한다. 완료는 실행 증거로만 주장한다.
- 모델은 난이도에 맞게 라우팅한다: 기계적 작업→경량 모델, 표준 구현→중간, 아키텍처/딥 디버깅→상위 모델.
- 무거운 스펙 문서는 여러 PR/작업자가 공유하는 자산일 때만 작성한다. 소규모·탐색 작업은 경량 반복으로 진행한다.

## 상세

### 1. 에이전트 지시 파일 (CLAUDE.md / AGENTS.md)

AGENTS.md는 2025년 OpenAI·Google·Cursor 등이 공동 공식화한 오픈 표준("머신용 README")으로, 주요 코딩 에이전트가 네이티브로 읽는다. Claude Code는 CLAUDE.md를 쓰므로, 실무 패턴은 범용 AGENTS.md + 도구별 파일이다.

**넣을 것**: 에이전트가 추측 못 하는 빌드/테스트 명령, 기본값과 다른 코드 스타일, 브랜치/PR 규칙, 프로젝트 고유 아키텍처 결정, 환경 특이사항.
**빼야 할 것**: 코드에서 유추 가능한 내용, 표준 컨벤션, 상세 API 문서(링크로 대체), 자주 바뀌는 정보, 파일별 설명, 자명한 조언.

- **간결이 성능이다**: Anthropic 공식 경고 — "비대한 CLAUDE.md는 실제 지시를 무시하게 만든다." 시작은 20~30줄 수준.
- **계층화**: 루트가 기본값, 하위 디렉토리 파일이 오버라이드(closest wins). 각 파일은 자기 디렉토리 범위만 다룬다.
- **Skills 분리**: 항상 필요하지 않은 지식(특정 작업 절차 등)은 항시 로드되는 지시 파일이 아니라 온디맨드 Skill로 뺀다.

출처: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices), [AGENTS.md 표준화 (InfoQ)](https://infoq.com/news/2025/08/agents-md/)

### 2. Worktree 병렬 개발

worktree는 하나의 저장소 히스토리를 공유하는 독립 작업 디렉토리로, 파일시스템 수준 격리를 제공한다. 병렬 에이전트 개발의 기반 단위다.

표준 패턴: **계획 → 공유 계약 정의 → 소유권 경계로 분할 → worktree별 격리 실행 → 작업별 테스트 → 머지 후 통합 검증 1회**

- **분해 표 먼저**: 실행 전에 Task | 담당 에이전트 | 주요 파일 | 의존성 | 통합 지점 표를 만든다. 두 작업의 파일 목록이 겹치면 병렬이 아니라 순차다 — 이것이 하드 제약이다.
- **공유 계약 동결**: API 시그니처, 데이터 스키마, 아키텍처 결정은 병렬 실행 시작 전에 문서로 고정하고 실행 중 변경 금지. 에이전트는 시작 시 읽기만 한다. 중간에 설계가 바뀌면 전체를 멈추고 계약을 갱신한 뒤 재시작한다 (context drift 방지).
- **단독 소유 자원**: lock 파일(uv.lock 등), DB 마이그레이션은 단일 담당만 수정. 마이그레이션은 항상 순차.
- **격리 위생**: worktree별 독립 `.env`, 독립 포트, 독립 의존성 디렉토리.
- **통합**: 각 브랜치는 lint+테스트 통과가 머지 전제조건. 머지 후 전체 통합 스모크 1회.
- **경계 인식**: 에이전트를 늘린다고 자동으로 빨라지지 않는다 — 격리·범위·검증이 안 되면 머지/리뷰 비용이 병렬 이득을 상쇄한다. 실측으로 확인한다 (→ [00-principles.md](00-principles.md)의 METR 사례).

출처: [Claude Code — worktrees](https://code.claude.com/docs/en/worktrees), [git worktree 병렬 에이전트 가이드](https://developersdigest.tech/blog/git-worktrees-claude-code-parallel-agents-guide)

### 3. 검증 게이트

- **작성자 ≠ 검증자**: 리뷰 에이전트는 diff와 기준만 본다(작성 과정의 추론을 보면 앵커링된다). 리뷰어에게는 "정확성/요구사항 격차만 지적"을 명시한다 — 격차를 찾으라고만 하면 멀쩡한 코드에도 지적을 만들어 과잉 설계를 유발한다.
- **실행 가능한 체크 제공**: 에이전트에게 스스로 돌릴 수 있는 검증(테스트, 빌드, 스모크)을 준다. 없으면 "돼 보인다"가 유일한 신호가 되고 사람이 검증 루프가 된다.
- **증거 기반 완료**: 완료 보고에는 실행한 명령과 출력이 포함되어야 한다. 프로듀스된 산문이 아니라 실제 툴 실행 결과가 증거다 (→ [06-testing-verification.md](06-testing-verification.md)).
- 무인 실행에는 결정적 게이트(Stop hook, 검증 스크립트 통과 전 종료 차단)를 건다.

출처: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices)

### 4. 리서치 도구 활용

- 라이브러리/SDK 사용 전 context7로 현재 문서를 확인한다. 훈련 데이터 기억으로 API를 쓰지 않는다.
- 모델/데이터셋 관련 작업은 HuggingFace 도구(hub 조회, hf-cli)로 실제 레지스트리를 조회한다.
- 방법론 선택 전 web search로 그 시점의 유지보수 상태·대안을 확인한다 (→ [00-principles.md](00-principles.md)).

### 5. 모델 라우팅

| 작업 난이도 | 모델 |
|---|---|
| 조회, 단순 읽기, 기계적 수정 | 경량 (haiku급) |
| 표준 구현, 단일 도메인 리팩토링, 일상 리뷰 | 중간 (sonnet급) |
| 아키텍처, 다중 시스템 추론, 딥 디버깅, 보안 | 상위 (opus급) |

기본은 중간 모델, 난이도의 증거가 있을 때만 상향한다.

### 6. Spec 게이팅 (선택적)

Spec-driven development(GitHub Spec Kit, Kiro 등)는 만능이 아니다. 실측 사례에서 소규모 기능에 대한 무거운 spec 파이프라인은 반복 프롬프팅 대비 ~10배의 시간 오버헤드를 냈다.

- **무겁게 갈 때**: 스펙이 여러 PR/서비스/작업자가 공유하는 자산일 때 — 그때 스펙 작성 비용이 회수된다. 병렬 worktree 분해(§2)의 공유 계약이 정확히 이 경우다.
- **가볍게 갈 때**: 소규모 수정, 탐색적 작업, 프로토타입 — 경량 반복(계획 → 실행 → 검증)으로 충분하다.
- 버그 발견 시 스펙을 고칠지 코드를 고칠지 기준을 프로젝트에서 미리 정한다 (스펙-코드 드리프트 방지).

출처: [GitHub — spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), [Spec Kit 실측 비판 (Scott Logic)](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
