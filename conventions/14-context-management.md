# 14. 컨텍스트 예산 관리

## 핵심 규칙

- 메인 컨텍스트는 오케스트레이터다. 결론만 보관하고, 탐색·검색·대용량 읽기는 subagent에 위임해 요약만 받는다 — subagent는 별도 컨텍스트 창에서 돌아 메인을 오염시키지 않는다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)).
- 디렉토리 스윕·큰 파일 통독을 메인에서 하지 않는다. 직접 읽기 전에 "subagent가 답만 돌려줄 수 있나?"를 묻고, 예면 위임한다.
- 독립 작업은 한 번에 병렬 디스패치하고 빌드·테스트는 백그라운드로 돌려 병목을 줄인다. 단 과병렬(머지·리뷰 비용)은 실측으로 경계한다.
- 진실의 원본은 대화가 아니라 파일에 둔다. 계획·결정·진행 상황을 외부 파일에 지속화하고, 대화 컨텍스트는 언제든 요약·소실될 수 있는 휘발성 자원으로 취급한다.
- 지속되어야 할 규칙·사실은 CLAUDE.md와 auto memory에 둔다(둘 다 compaction·`/clear` 후에도 유지). 대화 히스토리에 의존해 규칙을 기억하게 하지 않는다.
- 마일스톤마다 "완료 / 다음 / 핵심 결정 / 관련 파일 경로"를 핸드오프 문서에 체크포인트한다. 작업은 외부화된 태스크로 재개 가능하게 설계한다.
- 무관한 작업 사이에는 `/clear`로 컨텍스트를 비운다. 두 번 교정해도 안 되면 오염된 컨텍스트를 `/clear`하고 더 나은 프롬프트로 다시 시작한다.
- compaction이 임박하면 자동 실행을 기다리지 말고 `/compact <focus>`로 남길 것을 지시하거나 먼저 파일로 요약한다. 보존 항목은 CLAUDE.md의 "Compact Instructions"에 명시한다.
- resume·compaction 직후 `git status`·cwd·상태 아티팩트를 재확인한 뒤 작업을 재개한다 (stale 맥락·엉뚱한 브랜치 방지).

## 상세

두 목표 — **메인 컨텍스트 최소화**와 **compaction/clear 시 맥락 보존** — 은 동전의 양면이다. 메인을 아끼면 compaction이 늦게 오고, 원본을 외부화하면 메인이 가벼워진다. 근본 제약은 하나다: "컨텍스트 창은 빠르게 차고, 찰수록 성능이 떨어진다."

출처: [Claude Code — best practices](https://code.claude.com/docs/en/best-practices)

### 1. 메인 컨텍스트 최소화 (컨텍스트 방화벽)

- **subagent 위임**: 코드베이스 조사는 파일을 대량으로 읽어 컨텍스트를 소모한다. subagent는 별도 컨텍스트 창에서 조사하고 요약만 반환하므로 메인이 깨끗하게 유지된다. "인증 토큰 갱신이 어떻게 처리되는지 조사해줘" 같은 탐색은 메인이 아니라 subagent가 한다.
- **구조화 반환**: 위임 결과는 schema로 검증된 압축 데이터로 받는다 — 파일 덤프가 메인에 쌓이지 않는다.
- **사용량 점검**: `/context`로 무엇이 컨텍스트를 차지하는지(메모리 파일·MCP 도구·스킬·대화) 확인한다. MCP 도구 정의는 기본 지연 로드(deferred)이며, 자주 안 쓰는 스킬은 `skillOverrides`로 숨긴다.
- **병목 최소화**: 의존성 없는 작업은 단일 메시지로 병렬 디스패치하고, 장기 실행(빌드·테스트)은 백그라운드로 돌린다. barrier(전부 대기)보다 pipeline(스트리밍)을 우선한다.
- **재파생 금지**: 이미 확정된 사실을 다시 읽거나 재도출하지 않는다.

출처: [Claude Code — best practices](https://code.claude.com/docs/en/best-practices), [subagents](https://code.claude.com/docs/en/sub-agents)

### 2. compaction / clear 동작 이해

무엇이 남고 무엇이 사라지는지를 알아야 무엇을 외부화할지 정할 수 있다.

- **auto-compaction**: 컨텍스트가 한계에 가까우면 자동 실행 — 오래된 tool output을 먼저 비우고, 그다음 대화를 요약으로 대체한 뒤 세션을 계속한다. **비활성화할 수 없다.** 단일 출력이 너무 커서 매 요약 직후 다시 가득 차면 몇 번 시도 후 thrashing 에러로 멈춘다.
- **`/compact [focus]`**: 세션을 유지한 채 수동 요약. `focus` 인자로 무엇을 강조할지 지시할 수 있다 (예: `/compact focus on the API changes`).
- **`/clear [name]`**: 대화 히스토리를 완전히 비우고 새 컨텍스트로 시작(세션 재시작). alias `/reset`·`/new`. 이름을 붙이면 나중에 `/resume`으로 되찾을 수 있다.

| 구분 | `/compact` | `/clear` |
|---|---|---|
| 대화 | 유지(요약) | 초기화 |
| 프로젝트 메모리 | 유지 | 유지 |
| 용도 | 작업 중 공간 확보 | 새 작업 시작 |

- **compaction 후 유지되는 것**: 프로젝트 루트 CLAUDE.md는 디스크에서 재주입된다. auto memory(MEMORY.md 앞 200줄/25KB)도 재로드된다. 하위 디렉토리의 CLAUDE.md는 자동 재주입되지 않고, 그 디렉토리 파일을 읽을 때 로드된다.

출처: [Claude Code — how it works](https://code.claude.com/docs/en/how-claude-code-works), [commands](https://code.claude.com/docs/en/commands), [memory](https://code.claude.com/docs/en/memory)

### 3. 맥락 손실 방지 (외부화 + 지속 메모리)

- **원본을 파일로**: 계획·결정·진행 상황을 `PLAN.md`/`PROGRESS.md`/`DECISIONS.md` 또는 핸드오프 아티팩트(예: `.omc/handoffs/`)에 남긴다. 이 파일들은 자동으로 컨텍스트에 로드되지 않지만, compaction이 와도 원본이 남아 언제든 다시 읽을 수 있다.
- **CLAUDE.md**: 세션마다 시작 시 로드되고 compaction 후 재주입된다. git에 커밋해 팀이 공유한다. 파일당 200줄 이하로 유지하고, 파일 유형별 규칙은 path-scoped `.claude/rules/`로 분리해 매칭될 때만 로드한다.
- **auto memory**: Claude가 스스로 남기는 학습·빌드 명령·디버깅 통찰. compaction과 `/clear`를 모두 견딘다. 상세 노트는 토픽 파일로 분리해 `MEMORY.md`를 간결하게 유지한다.
- **체크포인트**: 마일스톤마다 상태를 핸드오프 문서에 갱신한다. `/rewind`(또는 Esc 2회)로 대화·코드 상태를 스냅샷에서 되돌릴 수 있으나, 이는 git과 별개이며 Claude 도구를 통한 변경만 추적하고 Bash 변경은 추적하지 않는다.
- **재오리엔테이션**: 지속 규칙은 대화 히스토리가 아니라 CLAUDE.md에 둔다. resume·compaction 직후에는 `git status`·cwd·상태 아티팩트를 먼저 확인한 뒤 이어서 작업한다.

개인은 auto memory + 핸드오프 파일로 충분하고, 팀은 지속 규칙을 프로젝트 CLAUDE.md(git 커밋)로 공유하되 개인 로컬 auto memory와 구분한다.

출처: [Claude Code — memory](https://code.claude.com/docs/en/memory), [best practices](https://code.claude.com/docs/en/best-practices)
