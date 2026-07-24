# 10. LLM API Inference Module

Common conventions for inference modules that call LLM APIs (OpenAI/Anthropic/Gemini/DeepSeek, etc., either native or via OpenRouter). For provider-specific details and structured output fallback, see [11-llm-api-providers.md](11-llm-api-providers.md).

## Core Rules

- Provider abstraction should be a thin native SDK adapter. Introduce a heavy gateway/proxy layer only once the need is measured (empirically).
- Separate payload assembly into pure, network-free functions — they must be unit-testable without the SDK or network.
- Calls are async by default. Use a per-model concurrency cap (semaphore) plus adaptive control based on rate-limit response headers.
- Classify errors using typed SDK exceptions first. String matching is a last resort.
- Retries have exactly one owner: if you use the SDK's built-in retry, the runner must not retry; if the runner retries, set the SDK's `max_retries=0`.
- Record failed tasks as error rows and let the batch continue. One task must never kill the entire run.
- Retry ensembles at the member level, not the task level.
- Response caching (record/replay) is for development/debugging only. It is prohibited in actual experiment runs and evaluations.
- Resume requires per-task idempotency plus mandatory input fingerprint verification (spec/seed/dataset/prompt hash). If the fingerprint differs, error out instead of continuing.
- No hardcoding prices/model names. Record token + cost breakdown on every result row, and set a budget cap before running.
- Pin models in production/experiment configs to a dated/pinned snapshot.

## Details

### 1. Architecture

- **Thin adapter**: one adapter per provider that uses its native SDK (openai/anthropic/google-genai) directly. Keep the common interface minimal — a single async call method. With structured output and reasoning APIs currently diverging significantly across providers (→ doc 11), a thin adapter gives the fastest access to new features and the smallest trust surface.
- **Stance on litellm**: using it lightly as a library is fine, but the proxy/gateway has multiple reported production pain points (throughput limits, memory leaks requiring worker restarts, cold-start cost) — adopt it only when centralized routing/billing tracking is actually needed. If structured-output validation-and-retry is needed, add instructor optionally on top (actively maintained, and has shifted toward delegating to each provider's native structured output).
- **Pure payload builder**: functions that build the request body return a dict with no I/O. The adapter's network-calling code only transmits this builder's output. Realtime and batch should share the same builder so the body is byte-identical.
- **Lazy import**: import the SDK inside the adapter method so provider extras can be installed selectively. Importing the registry must not require installing every SDK.
- **Client caching**: cache the SDK client keyed by `(event loop, base_url, api_key)` to prevent a new connection pool from being created on every call.

Sources: [litellm production issues summary](https://app.daily.dev/posts/litellm-has-some-serious-issues-in-production-pus0vbakk), [instructor](https://python.useinstructor.com/)

### 2. Calls and Concurrency

- **async + global worker pool**: feed all work through a single queue and control worker count via config. Progress bars go to stderr (to avoid polluting stdout's JSON output).
- **Per-model caps + adaptive control**: reordering the queue alone (per-model interleaving) is not enough — an in-house reference implementation (`llm-api-research`) has a code comment documenting an incident where filling the queue in spec order and hitting a 429 from one model lost 154 out of 900 items. The convention requires two layers: (a) a per-model concurrency semaphore, (b) a token bucket driven by rate-limit response headers (`x-ratelimit-*`, `anthropic-ratelimit-*`, `retry-after`). OpenAI's official cookbook parallel processor is the reference implementation (dual request/token capacity tracking, time-based refill). Anthropic's 429s can be triggered by a sharp increase in usage itself (acceleration limit), so ramp up gradually.
- **Streaming criteria**: batch evaluation and non-interactive processing are fine with a single request/response. Use streaming for interactive UX or long-form output — Anthropic requires streaming for long-running requests (roughly `max_tokens` in the tens-of-thousands range), so check the exact threshold against the SDK version in the [official streaming docs](https://platform.claude.com/docs/en/build-with-claude/streaming). A stream interruption should be retried (no resuming mid-stream — reissue the request).
- **Batch API**: for bulk processing where results aren't needed immediately, default to considering the provider's Batch API — OpenAI/Anthropic officially offer a 50% discount with a 24-hour window, and Gemini offers a comparable batch discount (check the official pricing docs at adoption time). It stacks with prompt caching. OpenAI auto-deletes result files after 30 days, so include retrieval in the workflow.

Sources: [OpenAI cookbook — api_request_parallel_processor](https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py), [OpenAI rate limits](https://developers.openai.com/api/docs/guides/rate-limits), [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits), [OpenAI Batch](https://developers.openai.com/api/docs/guides/batch), [Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)

### 3. Error Handling and Retries

- **Typed exception classification**: distinguish transient errors (429, 5xx, 408/409, timeouts, connection errors) from terminal errors (400/401/403/404/422) using the SDK's exception classes (OpenAI: `RateLimitError`/`InternalServerError`/`APIConnectionError`, etc.). Matching error message strings is fragile — classification breaks if the provider merely changes the wording — use it only as a last resort when no type information is available.
- **Single retry ownership**: either use the SDK's built-in retry (automatic exponential backoff + jitter), or turn it off with SDK `max_retries=0` and have the runner requeue — pick exactly one. Double retrying amplifies request volume.
- **Backoff budget**: if the total retry budget is shorter than the rate-limit window (typically 60 seconds), a 429 will exhaust all retries and fail. Follow the `retry-after` header when present; otherwise set `max_delay` to at least the window length.
- **529/503 are failover signals**: Anthropic's 529 (overloaded) is a global capacity issue, not an account limit — treat it as a candidate for failover to another model/path or a long wait, not a short-backoff retry.
- **Parsing must also run inside the classifier**: if an exception from the response mapping/parsing function bypasses transient classification, a retryable situation turns into a parser `TypeError` and fails with zero retries (a structural flaw the in-house `llm-api-research` codebase self-documents). Run response mapping inside the classification wrapper.
- **Partial failure isolation**: record a finally-failed task as a synthetic error row (including the error type) so that (a) the overall run continues, (b) resume doesn't retry it infinitely, and (c) the scoring denominator is preserved.
- **Retry at the member level**: in an ensemble, if a transient failure of a single member causes the entire task (all n members) to be recalled, the calls already billed are wasted, and request volume is amplified exactly when load is already high. Retry only the failed member.

Sources: [openai-python exceptions/retries](https://github.com/openai/openai-python), [google-genai error handling](https://ai.google.dev/gemini-api/docs/troubleshooting)

### 4. Ensembles

- **Single spec**: represent both self-consistency (n calls to the same model) and a panel (a list of heterogeneous models) with a single ensemble spec. Reject unimplemented voting-method strings at the config validation stage — to prevent the accident of writing `weighted` and silently falling back to majority.
- **Voting**: majority by default. Abstentions (parse failures) are not counted as votes, while an explicit "not applicable" response is counted as a vote. Fix the tie-breaking rule to be deterministic.
- **Mandatory analysis**: an ensemble run must always produce member-average accuracy, oracle accuracy (correct if any member is correct), vote accuracy, and lift over the member average — never claim "the ensemble actually helps" without numbers.
- **Applicability criteria**: self-consistency's benefit is proven for constrained answers (multiple-choice/numeric), and open-ended generation has nothing to vote on. Research shows that once a single agent's accuracy is high enough, the returns from multi-agent coordination diminish, so **consider a stronger single model first** and apply ensembles selectively to high-value, constrained tasks.

Sources: [self-consistency overview](https://www.emergentmind.com/topics/self-consistency-sampling), [test-time ensemble (arXiv 2510.13855)](https://arxiv.org/pdf/2510.13855)

### 5. Caching and Resume

- **Prompt caching**: order prompts with static content first (tools → system → docs/examples) and variable content (user input, timestamps) last. Anthropic uses explicit `cache_control` (up to 4 breakpoints, a per-model minimum cache token count, reads at 0.1x / writes at 1.25-2x), OpenAI caches automatically above 1024 tokens (~50% discount), and Gemini defaults to implicit caching. For Anthropic, cached-read tokens don't count toward ITPM on most models — the cache hit rate effectively is the rate limit.
- **Response caching is for development/debugging only**: use VCR-style record/replay (pytest-recording + vcrpy) to hit the real API once and replay from a cassette — this is effective for detecting prompt regressions and isolating non-LLM bugs, and it removes the cost of repeated development runs. **Mandatory**: (a) filter authentication headers such as `Authorization` out of the cassette, (b) prohibit this in actual experiment runs and evaluations (cached responses distort the sampling distribution and invalidate measurement), (c) a cassette verifies stability, not correctness, so pair it with periodic live evaluation.
- **Resume**: per-task idempotency (skip completed tasks based on the result file) plus tolerance for a corrupted last line (skip without crashing on interruption). **Fingerprint is mandatory**: store `spec signature + seed + dataset (path/mtime or hash) + prompt content hash`, and if it differs at resume time, error out instead of continuing — this prevents both old and new predictions from mixing into one result after editing a prompt and resuming, and prevents double submission (double billing) in batch. Apply this to both realtime and batch.

Sources: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), [pytest-recording/VCR](https://til.simonwillison.net/pytest/pytest-recording-vcr)

### 6. Cost and Observability

- **Prices belong in config**: manage the per-model unit-price table (input/cache read/cache write/output per 1M) as config. No hardcoding prices in code. An unregistered model must surface as "unknown," not as zero cost.
- **Per-row cost**: record token breakdown (fresh input/cached/output) and computed cost on every result row. Include efficiency metrics such as cost-per-correct in the run summary.
- **Budget cap**: estimate the expected cost before starting a run, and if the cap is exceeded during execution, skip remaining tasks without marking them done — raising the cap and rerunning will pick up where it left off.
- **Observability**: log calls according to the OpenTelemetry GenAI semantic convention attribute set (`gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `gen_ai.response.finish_reasons`) — note that this spec is still in Development status, so field names may change. Collectors include Langfuse (OSS, strong for self-hosting)/Phoenix, etc.
- **Pin models**: pin the model name in production/experiment configs to a dated/pinned snapshot (OpenAI's `-YYYY-MM-DD` snapshots, Anthropic where every ID is pinned, Gemini's stable channel). Use aliases only during development. For OpenAI, record `seed` plus the response's `system_fingerprint` to detect backend changes (which invalidate reproducibility).

Sources: [OTel GenAI observability](https://opentelemetry.io/blog/2026/genai-observability), [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations), [Anthropic model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions), [reproducible outputs with seed](https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter)

### 7. Evaluation

- **Separate outcome buckets**: tally CORRECT/WRONG/NONE/PARSE_FAIL/REFUSAL/TRUNCATED/API_ERROR as separate buckets. Lumping parse failures, refusals, and truncations in with wrong answers makes it impossible to distinguish a model problem from a pipeline problem. Classify `finish_reason` before parsing.
- **Statistical rigor**: attach a bootstrap CI to metrics, and compare two runs using **paired** bootstrap that resamples the same sample indices — a comparison that cannot answer "is this difference significant" is not a conclusion. Report cost-per-quality alongside quality metrics.
- **Prompt management**: keep prompts as versioned files in the repo (front-matter + role blocks); when revising, add a v2 file rather than overwriting. Prompt/model changes must pass a golden-set evaluation gate before being adopted (harnesses such as promptfoo/DeepEval can be used).
- **State the limits of API reproducibility explicitly**: the seed rule in [07-ml-development.md](07-ml-development.md) applies to training/serving that you directly control, and has limited applicability to API inference — Anthropic has no seed parameter, and OpenAI/Gemini's seed is best-effort. Manage API inference reproducibility not as a "guarantee" but through pinned snapshots, full parameter logging, and statistical comparison. Do not build exact-match-based regression tests.
- Evaluations using LLM-as-judge apply the judge rules from [08-llm-development.md](08-llm-development.md) as-is (bidirectional order, cross-family, length-aware rubric).

Sources: [DeepEval — LLM-as-judge](https://deepeval.com/guides/guides-llm-as-a-judge), [promptfoo vs DeepEval](https://qaskills.sh/blog/promptfoo-vs-deepeval-2026), [limits of LLM determinism](https://unstract.com/blog/understanding-why-deterministic-output-from-llms-is-nearly-impossible/)
