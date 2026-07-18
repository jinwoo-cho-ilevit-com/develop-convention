# 10. LLM API 추론 모듈

LLM API(OpenAI/Anthropic/Gemini/DeepSeek 등, native 또는 OpenRouter 경유)를 호출하는 추론 모듈의 공통 컨벤션. provider별 세부와 구조화 출력 폴백은 [11-llm-api-providers.md](11-llm-api-providers.md).

## 핵심 규칙

- provider 추상화는 얇은 native SDK 어댑터로 한다. 무거운 게이트웨이/프록시 레이어는 필요가 실측될 때만 도입한다.
- 페이로드 조립은 네트워크 없는 순수 함수로 분리한다 — SDK/네트워크 없이 유닛 테스트 가능해야 한다.
- 호출은 async 기본. 모델별 동시성 상한(semaphore) + rate limit 응답 헤더 기반 적응 제어를 둔다.
- 에러 분류는 typed SDK exception 우선. 문자열 매칭은 최후 수단이다.
- 재시도 주인은 한 곳뿐이다: SDK 내장 재시도를 쓰면 러너는 재시도하지 않고, 러너가 재시도하면 SDK `max_retries=0`.
- 실패한 태스크는 에러 행으로 기록하고 배치는 계속 진행한다. 한 태스크가 전체 실행을 죽이면 안 된다.
- 앙상블 재시도는 태스크 단위가 아니라 멤버 단위로 한다.
- 응답 캐시(record/replay)는 개발/디버그 전용이다. 실험 본 실행과 평가에서는 금지.
- resume은 태스크 단위 멱등 + 입력 fingerprint(spec/seed/데이터셋/프롬프트 해시) 검증 의무. fingerprint가 다르면 이어쓰지 말고 에러.
- 가격/모델명 하드코딩 금지. 모든 결과 행에 토큰+비용 내역을 남기고, 실행 전 예산 상한을 둔다.
- 프로덕션/실험 config의 모델은 dated/pinned snapshot으로 고정한다.

## 상세

### 1. 아키텍처

- **얇은 어댑터**: provider마다 native SDK(openai/anthropic/google-genai)를 직접 쓰는 어댑터 하나. 공통 인터페이스는 단일 async 호출 메서드 수준으로 최소화한다. structured output·reasoning API가 provider별로 크게 갈라진 현재(→ 11 문서), 얇은 어댑터가 최신 기능 접근이 가장 빠르고 신뢰 표면이 가장 작다.
- **litellm 스탠스**: 라이브러리로 가볍게 쓰는 건 가능하나, proxy/게이트웨이는 프로덕션 페인 포인트(처리량 한계, 메모리 누수로 워커 재시작 운용, 콜드스타트 비용)가 다수 보고되어 있다 — 중앙 라우팅/과금 추적이 실제로 필요할 때만. 구조화 출력 검증-재시도가 필요하면 instructor를 선택적으로 얹는다(활발히 유지보수됨, provider별 네이티브 structured output에 위임하는 방식으로 전환됨).
- **순수 payload builder**: 요청 본문을 만드는 함수는 I/O 없이 dict를 반환한다. 어댑터의 네트워크 호출부는 이 builder의 출력을 전송만 한다. realtime과 batch가 같은 builder를 공유해 본문이 바이트 단위로 동일해야 한다.
- **lazy import**: SDK는 어댑터 메서드 내부에서 import해 provider extras를 선택 설치 가능하게 한다. registry import가 전체 SDK 설치를 요구하면 안 된다.
- **클라이언트 캐시**: SDK 클라이언트는 `(event loop, base_url, api_key)` 키로 캐시해 호출마다 커넥션 풀이 새로 생기는 것을 막는다.

출처: [litellm 프로덕션 이슈 정리](https://app.daily.dev/posts/litellm-has-some-serious-issues-in-production-pus0vbakk), [instructor](https://python.useinstructor.com/)

### 2. 호출과 동시성

- **async + 전역 워커 풀**: 전체 작업을 하나의 큐로 흘리고 워커 수를 config로 제어한다. 진행 바는 stderr(stdout의 JSON 출력 오염 방지).
- **모델별 상한 + 적응 제어**: 큐 순서 조정(모델별 인터리빙)만으로는 부족하다 — 사내 참조 구현(`llm-api-research`)에는 spec 순서대로 큐를 채웠다가 한 모델의 429로 900개 중 154개를 잃은 사고가 코드 주석으로 기록되어 있다. 컨벤션은 두 층을 요구한다: (a) 모델별 동시성 semaphore, (b) rate limit 응답 헤더(`x-ratelimit-*`, `anthropic-ratelimit-*`, `retry-after`) 기반 token bucket. OpenAI 공식 cookbook의 병렬 처리기가 기준형이다(요청/토큰 이중 용량 추적, 시간 기반 리필). Anthropic은 급격한 사용량 증가 자체가 429를 유발하므로(acceleration limit) 점진적으로 램프업한다.
- **스트리밍 기준**: 배치 평가·비대화형 처리는 단일 요청/응답으로 충분하다. 대화형 UX 또는 장문 출력은 스트리밍 — Anthropic은 장시간 요청(대략 `max_tokens` 2만 토큰대 이상)에 스트리밍을 요구한다(정확한 임계값은 [스트리밍 공식 문서](https://platform.claude.com/docs/en/build-with-claude/streaming)에서 SDK 버전 기준으로 확인). 스트림 중단은 재시도 대상이다(이어받기 없음, 재발행).
- **Batch API**: 결과를 당장 볼 필요 없는 대량 처리는 provider Batch API를 기본 검토한다 — OpenAI/Anthropic 공식 50% 할인 + 24시간 윈도우, Gemini도 동급 배치 할인을 제공한다(채택 시점에 공식 가격 문서 확인). prompt caching과 중첩 가능. OpenAI는 결과 파일이 30일 후 자동 삭제되므로 수거를 워크플로우에 포함한다.

출처: [OpenAI cookbook — api_request_parallel_processor](https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py), [OpenAI rate limits](https://developers.openai.com/api/docs/guides/rate-limits), [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits), [OpenAI Batch](https://developers.openai.com/api/docs/guides/batch), [Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)

### 3. 에러 처리와 재시도

- **typed exception 분류**: transient(429, 5xx, 408/409, 타임아웃, 커넥션) vs terminal(400/401/403/404/422)을 SDK의 예외 클래스로 구분한다(OpenAI: `RateLimitError`/`InternalServerError`/`APIConnectionError` 등). 에러 메시지 문자열 매칭은 provider가 문구만 바꿔도 분류가 뒤집히는 취약한 방식 — 타입 정보가 없는 경우의 최후 수단으로만.
- **재시도 단일 소유**: SDK 내장 재시도(지수 백오프+지터 자동)를 쓰거나, SDK `max_retries=0`으로 끄고 러너가 재큐잉하거나 — 하나만 선택한다. 이중 재시도는 요청량을 증폭시킨다.
- **backoff 예산**: 재시도 총예산이 rate limit 윈도우(통상 60초)보다 짧으면 429가 재시도를 전부 소진하고 죽는다. `retry-after` 헤더가 있으면 그것을 따르고, 없으면 max_delay를 윈도우 이상으로 잡는다.
- **529/503은 failover 신호**: Anthropic 529(overloaded)는 계정 한도가 아니라 글로벌 용량 문제 — 짧은 백오프 재시도가 아니라 다른 모델/경로로의 failover 또는 긴 대기 대상으로 다룬다.
- **파싱도 분류기 안에서**: 응답 매핑/파싱 함수의 예외가 transient 분류를 우회하면, 재시도 가능한 상황이 파서 `TypeError`로 둔갑해 0회 재시도로 죽는다(사내 `llm-api-research` 코드베이스가 자가 문서화한 구조적 결함). 응답 매핑은 분류 래퍼 안에서 실행한다.
- **부분 실패 격리**: 최종 실패 태스크는 synthetic error row(에러 종류 포함)로 기록해 (a) 전체 실행이 계속되고, (b) resume 시 무한 재시도되지 않고, (c) 채점 분모가 유지되게 한다.
- **멤버 단위 재시도**: 앙상블에서 멤버 하나의 transient 실패로 태스크 전체(멤버 n개)를 재호출하면 이미 과금된 호출이 낭비되고, 부하가 높을 때 요청량이 정확히 그 시점에 증폭된다. 실패한 멤버만 재시도한다.

출처: [openai-python 예외/재시도](https://github.com/openai/openai-python), [google-genai 에러 처리](https://ai.google.dev/gemini-api/docs/troubleshooting)

### 4. 앙상블

- **단일 spec**: self-consistency(동일 모델 n회)와 panel(이종 모델 목록)을 하나의 ensemble spec으로 표현한다. 미구현 투표 방식 문자열은 config 검증 단계에서 거부한다 — `weighted`라고 썼는데 조용히 majority로 도는 사고 방지.
- **투표**: majority 기본. 기권(파싱 실패)은 표로 세지 않고, 명시적 "해당 없음" 응답은 표로 센다. 동률 규칙은 결정적으로 고정한다.
- **분석 의무**: 앙상블 run은 member 평균 정확도, oracle 정확도(멤버 중 하나라도 정답), vote 정확도, member 대비 lift를 항상 산출한다 — "앙상블이 실제로 이득인가"를 수치 없이 주장하지 않는다.
- **적용 기준**: self-consistency의 이득은 제약된 답(선택형/수치)에서 입증되어 있고, 개방형 생성에는 투표 대상이 없다. 연구상 단일 에이전트 정확도가 충분히 높으면 다중 조정의 수익이 체감하므로, **더 강한 단일 모델을 먼저 검토**하고 앙상블은 고가치·제약형 태스크에 선별 적용한다.

출처: [self-consistency 관련 정리](https://www.emergentmind.com/topics/self-consistency-sampling), [test-time ensemble (arXiv 2510.13855)](https://arxiv.org/pdf/2510.13855)

### 5. 캐싱과 재개

- **prompt caching**: 프롬프트는 정적 콘텐츠 먼저(tools → system → 문서/예시), 가변 콘텐츠(사용자 입력, 타임스탬프) 나중 순서로 배치한다. Anthropic은 명시적 `cache_control`(breakpoint 최대 4개, 모델별 최소 캐시 토큰 존재, 읽기 0.1×/쓰기 1.25~2×), OpenAI는 1024토큰 이상 자동(~50% 할인), Gemini는 implicit 기본. Anthropic은 캐시 읽기 토큰이 대부분 모델에서 ITPM에 미산입 — 캐시 적중률이 곧 실효 rate limit이다.
- **응답 캐시는 개발/디버그 전용**: VCR 방식 record/replay(pytest-recording + vcrpy)로 실 API를 한 번 치고 카세트로 재생한다 — 프롬프트 회귀 감지와 비 LLM 버그 격리에 유효하고 반복 개발 비용을 없앤다. **의무 사항**: (a) `Authorization` 등 인증 헤더는 카세트에서 필터링, (b) 실험 본 실행·평가에서는 금지(캐시된 응답은 샘플링 분포를 왜곡해 측정을 무효화), (c) 카세트는 안정성 검증이지 정답 검증이 아니므로 주기적 라이브 평가와 병행.
- **resume**: 태스크 단위 멱등(완료 태스크는 결과 파일 기준으로 스킵) + 손상된 마지막 행 허용(중단 시 크래시 없이 스킵). **fingerprint 의무**: `spec 시그니처 + seed + 데이터셋(경로/mtime 또는 해시) + 프롬프트 내용 해시`를 저장하고, resume 시 다르면 이어쓰지 않고 에러를 낸다 — 프롬프트를 고친 뒤 이어 돌려 신구 예측이 한 결과에 섞이는 것과 batch 이중 제출(이중 과금)을 모두 막는다. realtime과 batch 양쪽 모두에 적용한다.

출처: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), [pytest-recording/VCR](https://til.simonwillison.net/pytest/pytest-recording-vcr)

### 6. 비용과 관측성

- **가격은 config**: 모델별 단가 테이블(입력/캐시 읽기/캐시 생성/출력 per-1M)을 config로 관리한다. 코드에 가격 하드코딩 금지. 미등록 모델은 0원이 아니라 "unknown"으로 드러나야 한다.
- **행 단위 비용**: 모든 결과 행에 토큰 내역(fresh input/cached/output)과 계산된 비용을 기록한다. run 요약에 cost-per-correct 같은 효율 지표를 포함한다.
- **예산 상한**: run 시작 전 예상 비용을 추정하고, 실행 중 상한 초과 시 남은 태스크를 스킵하되 done으로 표시하지 않는다 — 상한을 올려 재실행하면 이어서 처리된다.
- **관측성**: 호출 로그는 OpenTelemetry GenAI semantic convention의 속성 체계(`gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `gen_ai.response.finish_reasons`)를 기준으로 남긴다 — 단 이 스펙은 아직 Development 상태이므로 필드 변경 가능성을 인지한다. 수집기는 Langfuse(OSS, self-host 강점)/Phoenix 등.
- **모델 고정**: 프로덕션/실험 config의 모델명은 dated/pinned snapshot으로 고정한다(OpenAI `-YYYY-MM-DD` 스냅샷, Anthropic은 모든 ID가 pinned, Gemini는 stable 채널 고정). 앨리어스는 개발 중에만. OpenAI는 `seed` + 응답의 `system_fingerprint`를 기록해 백엔드 변경(재현 무효)을 감지한다.

출처: [OTel GenAI observability](https://opentelemetry.io/blog/2026/genai-observability), [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations), [Anthropic model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions), [reproducible outputs with seed](https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter)

### 7. 평가

- **outcome bucket 분리**: CORRECT/WRONG/NONE/PARSE_FAIL/REFUSAL/TRUNCATED/API_ERROR를 별도 버킷으로 집계한다. 파싱 실패·거부·잘림을 오답으로 뭉개면 모델 문제와 파이프라인 문제를 구분할 수 없다. `finish_reason` 분류가 파싱보다 먼저다.
- **통계적 엄밀성**: 지표에는 bootstrap CI를 붙이고, 두 run 비교는 동일 샘플 인덱스로 재추출하는 **paired** bootstrap으로 한다 — "이 차이가 유의한가"에 답할 수 없는 비교는 결론이 아니다. 품질 지표에는 cost-per-quality를 병기한다.
- **프롬프트 관리**: 프롬프트는 저장소 내 버전드 파일(front-matter + role 블록), 수정 시 덮어쓰지 않고 v2 파일 추가. 프롬프트/모델 변경은 골든셋 평가 게이트를 통과해야 반영한다(promptfoo/DeepEval 등 하네스 활용 가능).
- **API 재현성의 한계 명시**: [07-ml-development.md](07-ml-development.md)의 시드 규칙은 직접 제어하는 학습/서빙에 적용되는 것으로, API 추론에는 적용 한계가 있다 — Anthropic은 seed 파라미터가 없고, OpenAI/Gemini seed는 best-effort다. API 추론의 재현성은 "보장"이 아니라 snapshot 고정 + 전체 파라미터 로깅 + 통계적 비교로 관리한다. 정확 일치 기반 회귀 테스트를 만들지 않는다.
- LLM-as-judge를 쓰는 평가는 [08-llm-development.md](08-llm-development.md)의 judge 규칙(양방향 순서, cross-family, 길이 인지 루브릭)을 그대로 적용한다.

출처: [DeepEval — LLM-as-judge](https://deepeval.com/guides/guides-llm-as-a-judge), [promptfoo vs DeepEval](https://qaskills.sh/blog/promptfoo-vs-deepeval-2026), [LLM 결정성의 한계](https://unstract.com/blog/understanding-why-deterministic-output-from-llms-is-nearly-impossible/)
