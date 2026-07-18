# 11. LLM API Provider별 고려사항 + 구조화 출력 폴백

provider별 API 차이를 다루는 규칙과, 구조화 출력을 지원하지 않는(또는 약하게 지원하는) provider 대응 전략. 코어 컨벤션은 [10-llm-api-inference.md](10-llm-api-inference.md). 이 문서의 provider 사실은 낡을 수 있다 — 개발 시 최신 문서 참조 절차는 [12-docs-reference.md](12-docs-reference.md)를 따른다.

## 핵심 규칙

- "OpenAI 호환"은 wire 포맷 호환일 뿐이다. capability 판별, 스키마 변환, 에러 파싱, 토큰 집계는 provider별로 격리한다.
- provider별 제약(지원 기능, 필수/금지 파라미터)은 코드 분기가 아니라 선언적 capability 테이블로 관리하고, 불가능 조합은 실행 전에 드롭한다.
- capability 검사는 라우터(OpenRouter) rewrite 전에 원 provider 기준으로 수행한다.
- reasoning/thinking 모드 호출에는 temperature/top_p 등 샘플링 파라미터를 보내지 않는다.
- 구조화 출력 스키마는 provider 최소공통분모로 설계한다: 루트는 object, `additionalProperties: false`, 모든 키 required, union은 `anyOf`. 길이/범위/패턴 제약은 서버가 강제하지 않는 것으로 간주하고 클라이언트에서 검증한다.
- 구조화 출력 미지원 시 계층 폴백을 따른다: native json_schema → json_object + 스키마·예시 프롬프트 주입 → 견고한 파싱 → 검증 + 제한된 재요청.
- 파싱 전에 `finish_reason`을 먼저 분류한다(truncated/refusal). reasoning 출력은 thinking 텍스트를 제거한 뒤 파싱한다.
- OpenRouter 응답은 HTTP 200이어도 본문/스트림의 에러를 검사한다.

## 상세

### 1. "OpenAI 호환"의 실체

244개 모델 × 23개 provider 실측(2026)에서 structured output 전체 테스트를 통과한 모델은 43개뿐이었다. 같은 기능이 provider마다 다른 파라미터 위치·다른 스키마 제약·다른 에러 형태로 구현된다. 어댑터는 요청 envelope(OpenAI wire 포맷)만 공유하고 다음 네 가지를 provider별로 격리한다:

1. **capability 플래그**: json_schema 지원 / json_object만 / 없음, reasoning 파라미터 방식, seed 지원 여부
2. **스키마 변환**: provider별 지원 키워드로 정규화
3. **에러 파싱**: 에러 본문 형태가 달라 generic 파싱은 provider 전환 시 깨진다
4. **토큰 집계**: usage 필드 구성이 달라(캐시/thinking 토큰 포함 여부) 비용 계산이 틀어진다

capability 테이블은 default-permissive(모르는 모델은 허용, 명시적 False만 차단)로 두고, 불가능 조합은 config 확장 단계에서 드롭하되 드롭 목록을 노출한다. OpenRouter로 rewrite하기 전에 원 provider 기준으로 검사해야 "Anthropic은 max_tokens 필수" 같은 규칙이 라우팅 후에도 살아있다.

출처: [Requesty — structured output 호환성 실측](https://requesty.ai/blog/structured-outputs-across-llm-providers-the-compatibility-mess)

### 2. Capability 요약 (2026-07 기준 — 변화가 빠르므로 채택 전 공식 문서 재확인)

| | Structured output | Reasoning 제어 | Seed | 주의사항 |
|---|---|---|---|---|
| OpenAI | `json_schema` strict (Responses: `text.format` / Chat: `response_format`) | `reasoning.effort` (모델별 레벨 상이) | 있음 (best-effort) + `system_fingerprint` | Responses/Chat 파라미터 이름이 다름. reasoning 시 temperature/top_p 거부 |
| Anthropic | `output_config.format` json_schema GA (constrained decoding) | adaptive thinking + `effort` (`budget_tokens` deprecated) | **없음** | `max_tokens` 필수. 최신 모델은 비기본 temperature/top_p/top_k에 400 |
| Gemini | `responseSchema` (+`response_json_schema`) | `thinking_level` (구세대는 `thinking_budget`) | 있음 (best-effort) | 스키마를 프롬프트에 중복 기재하면 품질 저하 — responseSchema에만 |
| DeepSeek | **`json_object`만, 스키마 강제 없음** | thinking 토글 (모델 축) | — | 프롬프트에 "json" 단어 필수 + 예시 권장. 빈 content 반환 가능성 공식 명시 |
| OpenRouter | `response_format` pass-through — **일부 provider만 지원** | provider별 pass-through | provider별 | `require_parameters: true` 없으면 스키마 미지원 provider로 조용히 라우팅됨 |

출처: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Anthropic effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking), [DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

### 3. Provider별 세부

**OpenAI**
- native는 Responses API, base_url 지정(호환 API)은 Chat Completions — 페이로드 형태가 다르므로 builder를 분리한다.
- reasoning 모델은 `reasoning_effort != none`일 때 temperature/top_p를 거부한다. effort 레벨은 모델 세대별로 다르고 기본값도 다르므로(일부 모델은 기본 `none`) config에 명시한다.
- `seed` + 응답 `system_fingerprint` 기록 — fingerprint 변경은 백엔드 변경(재현 무효) 신호.

**Anthropic**
- structured output은 constrained decoding 기반 `output_config.format`(GA). 스키마는 grammar로 컴파일되어 24시간 캐시 — 스키마 변경은 첫 요청에 컴파일 지연을 만든다.
- strict tool use(`strict: true`)와 JSON output은 독립 기능으로 병용 가능.
- `stop_reason: "refusal"`(안전이 스키마보다 우선)과 `"max_tokens"`(잘린 JSON)를 반드시 처리한다.
- seed 없음, `max_tokens` 필수, 최신 모델은 thinking이 기본이며 `effort`로 제어 — 수동 `budget_tokens`는 deprecated.
- 529(overloaded)는 글로벌 용량 신호로 failover 대상 (→ [10](10-llm-api-inference.md) §3).

**Gemini**
- 스키마는 `responseSchema`에만 — 프롬프트에 중복하면 품질이 떨어진다고 공식 문서가 명시.
- thinking과 structured output 병용은 래퍼 레이어에서 취약 사례가 보고되어 있으므로 raw SDK 수준에서 통합 테스트로 확인 후 사용.
- 출력 토큰에 thinking 토큰이 포함될 수 있어 토큰 집계 매핑에 반영한다.

**DeepSeek**
- OpenAI 호환 endpoint. 단 `json_object` 모드만 있고 json_schema 강제가 없다 — 아래 §4 폴백 체인이 기본 경로다.
- JSON 모드 요건: 프롬프트에 "json" 단어 포함(없으면 오류/무시), 예시 JSON 제공 권장, 충분한 `max_tokens`. **빈 content가 반환될 수 있음이 공식 문서에 명시** — 파싱 레이어가 빈 문자열을 처리해야 한다.
- thinking 모드 제약: temperature/top_p 등은 조용히 무시되고(에러 없음), `logprobs`는 400 에러 — "무시되는 것"과 "죽는 것"을 capability 테이블에 구분해 기록한다.
- 모델명 앨리어스(`deepseek-chat`/`deepseek-reasoner`)는 deprecation 일정이 있으므로 하드코딩하지 말고 config 축(모델 + thinking 토글)으로 관리한다.
- rate limit은 RPM이 아니라 동시성 상한 + 동적 스로틀링 방식이고, 피크 시간 할증 요금이 있다(구체 수치는 시점별로 공식 가격 페이지 확인).

**OpenRouter**
- **HTTP 200 + error body**: 업스트림 실패가 200 응답의 본문(또는 SSE 이벤트)에 에러로 담겨 온다. 상태 코드만 보면 실패를 성공으로 처리하게 되므로 본문/스트림 에러 검사가 의무다.
- `provider: { require_parameters: true }`를 설정하지 않으면 structured output 등 요청 파라미터를 지원하지 않는 provider로 조용히 라우팅되어 제약이 사라진다.
- 모델 내 provider failover + `models` 배열 기반 모델 fallback의 이중 구조를 활용할 수 있다. failover 소진 후 실패하면 과금되지 않는다(zero-completion insurance).
- native 대비 트레이드오프: 멀티 모델 실험·단일 키·fallback에 유리, 최저 지연·신기능 즉시 접근·대규모 지출에는 native 직행이 유리. BYOK로 자체 키를 라우팅에 쓸 수 있다.

출처: 위 §2 출처 + [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing), [OpenRouter BYOK](https://openrouter.ai/docs/guides/overview/auth/byok), [OpenRouter reliability/failover](https://openrouter.ai/blog/insights/reliability-failover)

### 4. 구조화 출력 계층 폴백

provider capability에 따라 다음 체인을 내려간다. 각 단계는 실패 시에만 다음으로 넘어가고, 어느 단계에서 성공했는지를 결과 행에 기록한다(품질 모니터링 지표).

1. **native json_schema** (OpenAI/Anthropic/Gemini/지원 provider): 스키마는 최소공통분모로 — 루트 object, `additionalProperties: false`, 전 키 required, union은 `anyOf`. `minLength`/`pattern`/`minimum` 등은 provider 지원이 제각각이므로 서버 강제를 기대하지 말고 클라이언트(Pydantic)에서 검증.
2. **json_object 모드 + 프롬프트 주입** (DeepSeek 등): 스키마와 구체적 예시를 프롬프트에 넣는다. "json" 단어 포함은 DeepSeek/Qwen에서 하드 요건이고 다른 provider에도 무해하므로 항상 포함. 코드 펜스 금지를 지시하되 어차피 펜스가 나온다고 가정하고 방어적으로 제거한다.
3. **견고한 파싱** (스키마 모드 없음/실패 시): `json.loads` 직접 → 마크다운 펜스 제거 → 첫 balanced `{...}`/`[...]` 블록 추출 순의 계단식 파서. reasoning 모델 출력은 thinking 텍스트(`reasoning_content` 등)를 먼저 제거한 대상에서 추출한다.
4. **json-repair** (선택): 구조적 수리(따옴표/괄호/잘림 보정)는 가능하지만 **의미를 조용히 오염시킬 수 있다** — 잘린 값이 null/""로 채워져 "구조는 유효한데 값은 무의미"가 된다. repair를 쓰면 타입 검증만이 아니라 값 범위/분포 수준의 시맨틱 검증을 반드시 동반한다.
5. **검증 + 제한된 재요청**: Pydantic 검증 실패 시 오류 메시지를 피드백해 재요청(instructor 방식). 재시도는 2~3회로 상한(재시도마다 전체 호출 비용 발생) 하고, **재시도율을 메트릭으로 추적**한다 — 재시도율 상승은 프롬프트/모델 문제의 조기 신호다. 단일 모델 벤치마크 실측(n=1000)에서 검증-재시도 3회 ≈ 99.6%, repair 병행 하이브리드 ≈ 99.9% 유효율이 보고된 바 있다(모델/태스크에 따라 다르므로 자체 측정 권장).

파싱 이전에 항상 `finish_reason`을 먼저 분류한다: length → TRUNCATED, content filter/safety → REFUSAL — 이들은 파싱 실패가 아니라 별도 outcome bucket이다 (→ [10](10-llm-api-inference.md) §7).

**constrained decoding과의 구분**: XGrammar/llguidance 같은 문법 강제 디코딩은 서빙을 직접 제어할 때(vLLM/SGLang self-host)만 쓸 수 있다. 호스티드 API에서는 provider의 `response_format` 지원이 상한이다 — 자체 서빙 모델의 구조화 출력은 [08-llm-development.md](08-llm-development.md) 영역과 겹치므로 그쪽 스택에서는 constrained decoding을 우선한다.

출처: [json-repair](https://github.com/mangiucugna/json_repair), [instructor](https://python.useinstructor.com/), [JSONSchemaBench (arXiv 2501.10868)](https://arxiv.org/abs/2501.10868), [DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode)
