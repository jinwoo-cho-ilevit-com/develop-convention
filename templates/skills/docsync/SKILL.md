---
name: docsync
description: 코드 변경을 문서에 증분 동기화한다. 디렉토리별 AGENTS.md의 managed 섹션과 ARCHITECTURE.md·Mermaid 다이어그램을 갱신하고, --audit로 drift·환각을 감사한다. 코드 변경 후 문서 갱신, 문서-코드 정합 검사, 문서 초기 부트스트랩 시 사용.
---

# docsync — 문서-코드 증분 동기화

컨벤션 [15-doc-tracking.md](../../../conventions/15-doc-tracking.md)의 실행 절차. 이 파일은 도구 중립 절차서다 — Claude Code에서는 스킬로 실행하고, 다른 에이전트(Codex/Cursor 등)에서는 이 파일을 읽고 같은 절차를 수행한다.

## 담당 범위

| 계층 | 이 스킬의 역할 |
|---|---|
| L1 입출력 계약 | 관리하지 않음 — 코드(type hints·스키마)가 단일 소스. 문서에는 요약 + 코드 참조만 |
| L2 모듈 문서 | 디렉토리별 AGENTS.md의 managed 블록 생성·갱신 |
| L3 전체 플로우 | ARCHITECTURE.md + 의존 그래프·sequence diagram 갱신 |
| L4 결정 이력 | ADR **후보 감지·질문만** — ADR 작성은 사람이 승인 |

## 실행 모드

| 명령 | 동작 |
|---|---|
| `/docsync` | 마지막 sync 커밋 ~ HEAD의 변경 모듈만 증분 동기화. 상태 파일이 없으면(첫 실행) 전체 모듈 = 부트스트랩 |
| `/docsync <path>` | 해당 모듈만 스코프 실행 |
| `/docsync --audit` | 감사 모드: dead-man 체크 + blind rebuild + 전역 정합성 |

## 상태 파일

`.docsync/` (gitignore하지 않는다 — 상태도 리뷰 대상):

```json
// .docsync/state.json
{
  "last_sync_commit": "<sha>",
  "last_audit_commit": "<sha>",
  "sections": {
    "<doc-path>#<section-id>": {
      "hash": "<managed 블록 내용의 sha256>",
      "verified_commit": "<sha>",
      "verified_at": "<YYYY-MM-DD>"
    }
  }
}
```

```jsonl
// .docsync/corrections.jsonl — append-only
{"path": "...", "section": "...", "reason": "wrong|stale|unclear|granularity", "note": "...", "commit": "<sha>", "at": "<YYYY-MM-DD>"}
```

## 모듈 문서 형식

각 주요 디렉토리의 `AGENTS.md`:

```markdown
# <모듈명>

<!-- docsync:managed:start id=overview -->
> 검증: <commit-sha> (<YYYY-MM-DD>)

## 역할
한두 문장.

## 핵심 로직
입력 → 처리 단계 → 출력의 서사. invariant(항상 성립해야 하는 조건), 엣지 케이스 처리.

## 입출력 계약
코드 참조로 요약: "입력 스키마는 `models.py:RequestSchema`, 출력은 `models.py:ResultSchema`". 시그니처를 문서에 복제하지 않는다.

## 다이어그램
```mermaid
(모듈 내부 흐름 또는 인접 모듈과의 관계)
```

## 함정
비자명한 제약, 실수하기 쉬운 지점.
<!-- docsync:managed:end -->

## 설계 노트
<!-- human — 에이전트 수정 금지. '왜'는 여기에 사람이 쓴다 -->
```

## Sync 절차

### 0. RMA 감지 (매 실행 첫 단계)

각 managed 블록의 현재 hash를 state.json과 대조한다. **hash 불일치 + 그 문서에 대응하는 코드 변경 없음 = 사람이 수정한 것.** 조용히 되돌리거나 덮어쓰지 말고:

1. before/after diff를 요약해 보여주고 이유를 객관식으로 1회 질문: `wrong`(내용 틀림) / `stale`(코드보다 늦음) / `unclear`(불명확) / `granularity`(상세 수준 부적절). LLM이 추정 기본값을 제안하고 사용자는 확정만 한다.
2. `.docsync/corrections.jsonl`에 append.
3. 그 섹션의 사람 수정본을 새 기준으로 채택(hash 갱신).

같은 섹션에 모순된 이유 코드가 누적되면(예: 한 번은 "너무 김", 한 번은 "너무 짧음") 그 섹션을 managed에서 제외하고 사람 소유로 강등할 것을 제안한다.

### 1. 범위 산출

- `state.json` 있음: `git diff --name-only <last_sync_commit>..HEAD`로 변경 파일 → 소속 모듈(디렉토리) 목록.
- 없음(부트스트랩): 전체 모듈. 모듈 단위는 "응집된 책임을 가진 디렉토리" — 과분할하지 않는다(대략 디렉토리당 파이썬 파일 2개 이상 또는 진입점).
- 문서 편집 전 symlink는 canonical 경로로 해석한다(alias를 고치는 사고 방지).

### 2. 모듈별 갱신

모듈마다 (독립적이므로 병렬 가능, 컨텍스트 여유가 없으면 subagent에 위임):

1. 모듈 코드 + 기존 AGENTS.md + 해당 모듈의 최근 corrections를 읽는다.
2. managed 블록만 재생성한다. **블록 밖은 절대 수정 금지.**
3. 작성 규칙:
   - 모든 사실 주장은 코드 위치(file:symbol)로 인용 가능해야 한다. 인용할 수 없으면 쓰지 않는다.
   - 기존 서술과 의미가 같으면 표현을 바꾸지 않는다(diff 최소화).
   - corrections의 이유 코드를 negative 예시로 반영한다 (예: `granularity` 이력이 있으면 같은 실수 회피).
   - 검증 스탬프(`> 검증: <sha> (<date>)`)를 갱신한다.

### 3. 전역 패스

1. 의존 그래프를 결정적 도구로 재생성: pydeps(Python) / madge(JS·TS) 출력 → Mermaid 변환 → ARCHITECTURE.md에 삽입. LLM이 그리지 않는다.
2. 변경이 엔트리포인트 흐름에 닿았으면 해당 sequence diagram 갱신.
3. 이번에 갱신된 모듈 문서들 사이의 서술 모순(같은 책임을 서로 자기 것이라 주장, 호출 방향 불일치 등)을 검사한다.

### 4. ADR 후보 플래그

이번 diff에서 다음이 감지되면 ADR 후보로 **질문 목록만** 보고한다(작성은 사람 승인 후): 의존성 추가/제거, 공개 인터페이스 변경, 모듈 구조 변경, 기술 선택 변경, 롤백/revert. 각 항목에 "왜 이렇게 했는지"를 묻는 한 줄 질문을 붙인다.

### 5. 검증

fresh-context 리뷰(별도 subagent 또는 별도 세션)에 diff와 기준만 주고 확인: (1) managed 블록 밖 수정 없음, (2) 갱신된 서술이 코드와 일치, (3) 인용 불가능한 주장 없음. 작성 컨텍스트에서 자기 승인하지 않는다.

### 6. 마무리

`state.json` 갱신(last_sync_commit = HEAD, 섹션 hash 재계산) 후 보고: 갱신 파일 목록 / ADR 후보 질문 / RMA 처리 내역 / 미해결 플래그.

## Audit 절차 (`--audit`)

### 1. dead-man 체크

`last_sync_commit` 이후 경과가 임계(권장 기본: 30커밋 또는 14일) 초과면 **문서 검사 전에 그 사실부터 경고한다.** 죽은 sync는 건강한 sync와 똑같이 보인다.

### 2. 대상 선정

staleness 점수 = 마지막 audit 이후 경과 × 그 모듈의 churn(커밋 수). 상위 K개(권장 기본: 3~5, 비용 상한)만 이번 회차에 검사하고, 나머지는 다음 회차로 순환한다.

### 3. Blind rebuild

선정된 모듈마다: **기존 AGENTS.md·ADR을 컨텍스트에서 차단한** fresh-context 에이전트가 코드만 읽고 managed 블록을 처음부터 재작성한다.

### 4. 주장 대조

blind본과 유지본을 원자적 주장 단위로 분해해 대조한다:

- **유지본에만 있는 주장** → 코드 인용(file:symbol) 부착 시도. 인용 실패 = 환각 후보로 보고. 인용은 되지만 코드에서 유도 불가한 배경 지식 = 암묵지 → 사람 섹션/ADR로 승격 제안.
- **blind본에만 있는 주장** → 유지본이 놓친 최신 변경 후보.
- **의미가 같고 표현만 다른 것** → drift 아님. 건드리지 않는다.

판정 결과는 자동 반영하지 않고 보고서로 제출한다(환각 삭제·암묵지 승격은 사람 확인 후).

### 5. 신선도 배너

검증 스탬프가 임계(권장 기본: 90일 또는 100커밋) 초과인 문서의 managed 블록 상단에 배너를 삽입한다: `> ⚠ 이 섹션은 <date> 이후 검증되지 않음 — 코드와 다를 수 있다`.

## 비용 상한

- audit은 회당 K개 모듈 상한(순환). sync는 변경 모듈만.
- 모듈이 크면 통독하지 말고 public 심볼·진입점 중심으로 읽는다.
- fitness test(문서만으로 과제 수행 → 실행 결과 대조)는 파일럿 단계 — 실행 ground truth가 있는 순수 함수에 한해 시도하고, 그 외는 "미검증"으로 표기한다.

## 다른 도구에서 사용

Codex/Cursor 등에서는 AGENTS.md에 다음 한 줄을 두고 이 파일을 참조시킨다:

```
문서 동기화가 필요하면 .claude/skills/docsync/SKILL.md의 절차를 따른다.
```

절차 자체는 도구 독립적이다. 도구에 종속되는 것은 트리거(슬래시 명령, 스케줄 실행)뿐이다.
