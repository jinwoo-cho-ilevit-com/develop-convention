# 11. LLM API Provider Considerations + Structured Output Fallback

Rules for handling API differences across providers, and strategies for providers that don't support (or only weakly support) structured output. Core conventions are in [10-llm-api-inference.md](10-llm-api-inference.md). Provider facts in this document can go stale — when developing, follow the up-to-date documentation reference procedure in [12-upstream-docs.md](12-upstream-docs.md).

## Core Rules

- "OpenAI-compatible" only means wire format compatibility. Isolate capability detection, schema conversion, error parsing, and token aggregation per provider.
- Manage provider-specific constraints (supported features, required/forbidden parameters) via a declarative capability table rather than code branching, and drop impossible combinations before execution.
- Perform capability checks against the original provider, before router (OpenRouter) rewriting.
- Don't send sampling parameters like temperature/top_p on reasoning/thinking mode calls.
- Design structured output schemas to the provider lowest common denominator: root is object, `additionalProperties: false`, all keys required, unions use `anyOf`. Treat length/range/pattern constraints as not enforced by the server, and validate them client-side.
- When structured output isn't supported, follow the tiered fallback: native json_schema → json_object + schema/example prompt injection → robust parsing → validation + bounded retry.
- Classify `finish_reason` before parsing (truncated/refusal). For reasoning output, strip the thinking text before parsing.
- Even when OpenRouter responds with HTTP 200, check the body/stream for errors.

## Details

### 1. What "OpenAI-compatible" Actually Means

One third-party compatibility sweep reports that of 244 models × 23 providers (2026), only 43 models passed a full structured output test suite **(unverified — needs research: the only source is a vendor blog, which [16-research-protocol.md](16-research-protocol.md) §3 treats as a lead, not proof)**. Directionally, the same feature is implemented with different parameter placement, different schema constraints, and different error shapes across providers. The adapter shares only the request envelope (OpenAI wire format) and isolates the following four things per provider:

1. **Capability flags**: json_schema support / json_object only / none, reasoning parameter style, seed support
2. **Schema conversion**: normalize to provider-supported keywords
3. **Error parsing**: error body shapes differ, so generic parsing breaks when switching providers
4. **Token aggregation**: usage field composition differs (whether cache/thinking tokens are included), which throws off cost calculation

Keep the capability table default-permissive (unknown models are allowed; only explicit False blocks), drop impossible combinations at the config expansion stage, and expose the drop list. Checking against the original provider before rewriting to OpenRouter is what keeps rules like "Anthropic requires max_tokens" alive after routing.

Sources: [Requesty — empirical test of structured output compatibility](https://requesty.ai/blog/structured-outputs-across-llm-providers-the-compatibility-mess) (third-party blog — lead only, not citable as proof)

### 2. Capability Summary (as of 2026-08 — this changes fast, re-check official docs before adopting)

| | Structured output | Reasoning control | Seed | Caveats |
|---|---|---|---|---|
| OpenAI | `json_schema` strict (Responses: `text.format` / Chat: `response_format`) | `reasoning.effort`, values model-dependent (`none`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max`) | (unverified — needs research) | Responses/Chat parameter names differ. All fields `required` + `additionalProperties: false`. Temperature/top_p rejection during reasoning (unverified — needs research) |
| Anthropic | `output_config.format` json_schema GA (constrained decoding) | adaptive thinking + `effort`; `thinking.type: "enabled"` + `budget_tokens` deprecated on 4.6, 400 on 4.7+ | **None** | `max_tokens` required (unverified — needs research). Latest models return 400 for non-default temperature/top_p/top_k |
| Gemini | `response_format` (`type`/`mime_type: "application/json"`/`schema`) | `thinking_level` | (unverified — needs research) | Schema goes in `response_format.schema`; use `description` fields to steer |
| DeepSeek | **`json_object` only, no schema enforcement** | `thinking: {"type": "enabled"/"disabled"}` parameter, enabled by default | — | The word "json" is required in the prompt + examples recommended. Docs explicitly note empty content may be returned |
| OpenRouter | `response_format` — support is per **endpoint**, not per model; **only some providers support it** | pass-through, varies by provider | varies by provider | Without `require_parameters: true`, requests get silently routed to an endpoint that doesn't support the schema |

Sources: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning), [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Anthropic effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Anthropic thinking](https://platform.claude.com/docs/en/build-with-claude/thinking), [Anthropic extended thinking (deprecation notice)](https://platform.claude.com/docs/en/build-with-claude/extended-thinking), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking), [DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode), [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

### 3. Provider Details

**OpenAI**
- Native uses the Responses API; specifying a base_url (compatible API) uses Chat Completions — payload shapes differ, so separate the builders.
- `reasoning.effort` values are model-dependent and can include `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`; defaults differ by model (e.g. `gpt-5.5` defaults to `medium`), so specify it explicitly in config. Whether reasoning models reject temperature/top_p is **(unverified — needs research: not stated on the current structured-outputs or reasoning guides)**.
- Record `seed` + the response `system_fingerprint` — a fingerprint change signals a backend change (reproducibility invalidated). **(unverified — needs research: neither parameter appears on the current structured-outputs or reasoning guides.)**

**Anthropic**
- Structured output is `output_config.format` (GA), based on constrained decoding. The schema is compiled into a grammar and cached for 24 hours — schema changes incur a compilation delay on the first request.
- Strict tool use (`strict: true`) and JSON output are independent features that can be combined.
- Always handle `stop_reason: "refusal"` (safety takes priority over the schema) and `"max_tokens"` (truncated JSON).
- No seed. Latest models default to thinking and are controlled via `output_config.effort`; manual extended thinking (`thinking.type: "enabled"` with `budget_tokens`) is deprecated on the 4.6 models (requests still succeed) and rejected with a 400 error on 4.7 and later. Migration: drop `budget_tokens`, set `thinking: {type: "adaptive"}`, control depth with `effort`. `max_tokens` required **(unverified — needs research: it no longer carries a required label in the Messages API reference)**.
- 529 (overloaded) is a global capacity signal and a failover target (→ [10](10-llm-api-inference.md) §3).

**Gemini**
- Structured output is configured with `response_format` (`type: "text"`, `mime_type: "application/json"`, `schema`) — the older `responseSchema`/`response_json_schema` field names no longer appear in the docs. Steer the model with `description` fields inside the schema. The claim that duplicating the schema in the prompt degrades quality is **(unverified — needs research: no such statement on the current structured-output page)**.
- Combining thinking with structured output has reported fragility at the wrapper layer **(unverified — needs research: no vendor statement, no identified source)**, so verify with integration tests at the raw SDK level before use.
- Thinking tokens are billed **in addition to** output tokens ("response pricing is the sum of output tokens and thinking tokens") and are reported separately as `total_thought_tokens` — map both fields in token aggregation.

**DeepSeek**
- OpenAI-compatible endpoint. However, only `json_object` mode exists with no json_schema enforcement — the §4 fallback chain below is the default path.
- JSON mode requirements: include the word "json" in the prompt (otherwise error/ignored), providing an example JSON is recommended, sufficient `max_tokens`. **Official docs state empty content may be returned** — the parsing layer must handle empty strings.
- Thinking mode constraints: thinking mode "does not support the `temperature`, `top_p`, `presence_penalty`, or `frequency_penalty` parameters" and "setting these parameters will not trigger an error but will also have no effect". `logprobs` returning a 400 error is **(unverified — needs research: not stated on the current thinking-mode guide)**. Record the distinction between "ignored" and "fails" in the capability table.
- Model names churn: the currently documented models are `deepseek-v4-flash` and `deepseek-v4-pro`, and the older `deepseek-chat`/`deepseek-reasoner` aliases no longer appear in the docs (no deprecation schedule is published — they are simply gone). Thinking is now a request parameter (`thinking: {"type": "enabled"/"disabled"}`, enabled by default at `effort: high`), not a separate model. Don't hardcode model names — manage via a config axis (model + thinking toggle).
- Rate limiting isn't RPM-based; it's a per-model concurrency cap (documented as 2500 for `deepseek-v4-flash`, 500 for `deepseek-v4-pro`) that returns HTTP 429 when exceeded — "dynamic throttling" is **(unverified — needs research: the rate-limit page describes fixed caps + 429)**. Peak/off-peak pricing applies: peak hours (09:00–12:00 and 14:00–18:00 Beijing time, UTC+8) are 2x regular prices on all billing items (check the official pricing page for current figures).

**OpenRouter**
- **HTTP 200 + error body**: once a request passes validation, "the returned HTTP response status will be 200 OK and any error occurred while the LLM is producing the output will be emitted in the response body or as an SSE data event." Mid-stream failures cannot fail over (partial content is already delivered) and arrive in-band with `finish_reason: "error"`. Checking only the status code would treat a failure as success, so checking the body/stream for errors is mandatory.
- Structured output support is determined **per endpoint, not per model** — the same model served by several providers may support it on only some of them. Without setting `provider: { require_parameters: true }`, requests get routed to an endpoint that doesn't support the parameter and the constraint disappears.
- You can leverage the dual structure of within-model provider failover + `models`-array-based model fallback. Zero-completion insurance is automatic on all accounts, models, and providers: you aren't charged when the response has zero completion tokens with a blank/null finish reason, or an `error` finish reason.
- Trade-off vs. native: favorable for multi-model experimentation, a single key, and fallback; going native directly is favorable for lowest latency, immediate access to new features, and large-scale spend. BYOK lets you use your own keys in routing.

Sources: same as §2 above + [Anthropic Messages API reference](https://platform.claude.com/docs/en/api/messages), [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing), [DeepSeek rate limit](https://api-docs.deepseek.com/quick_start/rate_limit), [OpenRouter errors](https://openrouter.ai/docs/api-reference/errors), [OpenRouter zero completion insurance](https://openrouter.ai/docs/guides/features/zero-completion-insurance), [OpenRouter BYOK](https://openrouter.ai/docs/guides/overview/auth/byok)

### 4. Structured Output Tiered Fallback

Descend through the following chain based on provider capability. Each stage only proceeds to the next on failure, and which stage succeeded is recorded in the result row (a quality-monitoring metric).

1. **native json_schema** (OpenAI/Anthropic/Gemini/supporting providers): schema at the lowest common denominator — root object, `additionalProperties: false`, all keys required, unions use `anyOf`. Support for `minLength`/`pattern`/`minimum` etc. varies by provider, so don't expect server enforcement — validate client-side (Pydantic).
2. **json_object mode + prompt injection** (DeepSeek, etc.): put the schema and a concrete example into the prompt. Including the word "json" is a hard requirement for DeepSeek/Qwen and harmless for other providers, so always include it. Instruct against code fences, but assume fences will show up anyway and strip them defensively.
3. **Robust parsing** (when no schema mode / on failure): a cascading parser in the order of direct `json.loads` → strip markdown fences → extract the first balanced `{...}`/`[...]` block. For reasoning model output, first strip the thinking text (`reasoning_content`, etc.) before extracting.
4. **json-repair** (optional): structural repair (fixing quotes/brackets/truncation) is possible, but **it can silently corrupt meaning** — a truncated value gets filled in as null/"", producing "structurally valid but semantically meaningless" output. If you use repair, it must be paired with semantic validation at the value range/distribution level, not just type validation.
5. **Validation + bounded retry**: on Pydantic validation failure, feed the error message back and retry (the instructor approach). Cap retries at 2-3 (each retry incurs the full call cost), and **track the retry rate as a metric** — a rising retry rate is an early signal of a prompt/model problem. Retry rounds and repair are often quoted with high single-digit-nines validity rates **(unverified — needs research: the "n=1000, ≈99.6% at 3 retries, ≈99.9% hybrid with repair" figures previously cited here trace to no identified source)** — measure the rate on your own model/task rather than assuming a published number.

Always classify `finish_reason` before parsing: length → TRUNCATED, content filter/safety → REFUSAL — these are a separate outcome bucket, not a parsing failure (→ [10](10-llm-api-inference.md) §7).

**Distinction from constrained decoding**: grammar-enforced decoding like XGrammar/llguidance can only be used when you directly control serving (vLLM/SGLang self-host). On hosted APIs, the provider's `response_format` support is the ceiling — structured output for self-served models overlaps with the [08-llm-development.md](08-llm-development.md) domain, so prefer constrained decoding on that stack.

Sources: [json-repair](https://github.com/mangiucugna/json_repair), [instructor](https://python.useinstructor.com/), [JSONSchemaBench (arXiv 2501.10868)](https://arxiv.org/abs/2501.10868), [DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode)
