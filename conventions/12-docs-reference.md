# 12. 최신 문서 참조 절차 + Canonical URL 레지스트리

provider API 지식은 몇 달 단위로 낡는다(`output_format`→`output_config.format` 무경고 마이그레이션, DeepSeek 모델명 deprecation, torchtune 개발 종료). 이 문서는 "기억을 믿는 구조"가 아니라 **"확인을 강제하는 구조"**를 정의한다. 번호 체계를 따르기 위해 레지스트리와 절차를 한 문서로 통합했다.

## 핵심 규칙

- provider API 코드를 작성/수정하기 전, 아래 레지스트리의 해당 provider 공식 문서를 실제로 fetch해 확인한다. 훈련 지식·기억으로 API를 쓰지 않는다.
- SDK 사용법·코드 예시는 context7(`ctx7`)로 확인한다. 예외 클래스·파라미터 시그니처·기본 재시도 횟수는 설치된(lock된) SDK 소스가 로컬 진실이다.
- 공식 문서가 침묵하는 동작(기능 조합 등)은 추측하지 말고 provider별 1-call 스모크 테스트로 실측 확정한다.
- 컨벤션/코드 주석의 provider 사실에는 검증 날짜 스탬프를 남긴다. 스탬프가 3개월 이상 지난 사실에 의존하는 코드를 만들 때는 공식 문서를 재확인한다.
- 개발 중 공식 문서와 컨벤션/코드 주석이 다르면 그냥 넘어가지 않는다 — 공식 문서 기준으로 컨벤션을 갱신하고 커밋한다.
- SDK 업그레이드는 changelog 확인을 동반한 명시적 작업이다. uv.lock으로 버전을 고정한다.

## 상세

### 1. 4계층 참조 체계

| 계층 | 원천 | 용도 |
|---|---|---|
| Tier 1 | 아래 canonical URL 레지스트리 (공식 문서) | API 스펙, 파라미터, 제약, 가격, deprecation — 사실의 원천 |
| Tier 2 | context7 (`ctx7` CLI/MCP) | SDK 사용법, 코드 예시, 버전 마이그레이션 |
| Tier 3 | 설치된 SDK 소스/타입 정의 | 예외 계층, 시그니처, 기본값 — lock된 버전이 정답 |
| Tier 4 | provider별 스모크 테스트 | 문서에 없는 동작(기능 조합, 실제 에러 형태)의 실측 확정 |

web search는 리드 발굴용이다. 사실 확정은 Tier 1~4로만 한다 (→ [00-principles.md](00-principles.md) 사실 기반 판단).

### 2. Canonical URL 레지스트리 (등록 기준: 2026-07)

provider 관련 작업 시작 시 해당 행의 URL을 fetch한다. provider가 `llms.txt`(에이전트용 문서 인덱스)를 제공하는지 확인해 있으면 이 표에 추가한다.

**OpenAI** — https://developers.openai.com/api/docs/
- guides/structured-outputs · guides/reasoning · guides/rate-limits · guides/batch · guides/prompt-caching · guides/deprecations
- 병렬 처리 기준형: https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py

**Anthropic** — https://platform.claude.com/docs/en/
- build-with-claude/structured-outputs · build-with-claude/effort · build-with-claude/adaptive-thinking · build-with-claude/prompt-caching · build-with-claude/batch-processing · build-with-claude/streaming
- api/rate-limits · about-claude/models/model-ids-and-versions

**Google Gemini** — https://ai.google.dev/gemini-api/docs/
- structured-output · thinking · models · troubleshooting

**DeepSeek** — https://api-docs.deepseek.com/
- guides/json_mode · guides/thinking_mode · guides/tool_calls · quick_start/pricing

**OpenRouter** — https://openrouter.ai/docs/
- guides/features/structured-outputs · guides/overview/auth/byok · api_reference/limits

ML/학습 스택(torch, TRL, vLLM 등)의 공식 문서는 [08-llm-development.md](08-llm-development.md)의 출처 링크가 시드다. 새 라이브러리를 채택하면 그 공식 문서 URL을 해당 컨벤션 문서에 출처로 남기는 것이 곧 레지스트리 등록이다.

### 3. Provider 스모크 테스트 (Tier 4)

각 provider 어댑터는 최소 스모크 세트를 갖는다: 기본 호출 1건, structured output 1건, thinking/reasoning 조합 1건, 에러 분류 확인(잘못된 파라미터로 typed exception 확인). 실행 시점: 어댑터 신규 작성, SDK 업그레이드, 대상 모델 변경 시. 비용은 태스크당 1~2 호출 수준이다.

문서가 침묵하는 조합(예: 특정 provider의 thinking × structured output 병용)은 이 스모크로 확정하고, 결과를 capability 테이블([11-llm-api-providers.md](11-llm-api-providers.md))에 날짜 스탬프와 함께 기록한다.

### 4. 프로젝트에 주입하는 법

각 프로젝트 CLAUDE.md/AGENTS.md에 다음 세 줄이면 충분하다:

```
- provider API 코드 작성/수정 전: develop-convention conventions/12-docs-reference.md의 해당 provider 공식 문서를 fetch해 확인
- SDK 사용법은 ctx7, 예외/시그니처는 설치된 SDK 소스가 기준
- 문서에 없는 동작은 추측하지 말고 provider 스모크 테스트로 확정
```

이 절차가 실제로 반복 사용되는 것이 확인되면 skill로 승격을 검토한다 — 그 전에는 레지스트리 + 세 줄 규칙이 유지비 대비 효과가 크다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)의 Skills 분리 기준).
