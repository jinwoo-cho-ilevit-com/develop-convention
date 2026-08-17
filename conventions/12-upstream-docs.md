# 12. Upstream Documentation: Reference Procedure + Canonical URL Registry

How to check someone else's official documentation before writing against their SDK or API. Keeping *this* project's own docs in step with its code is [15-doc-tracking.md](15-doc-tracking.md).

Provider API knowledge goes stale on a timescale of months (the silent `output_format`→`output_config.format` migration, DeepSeek model name deprecations, torchtune's development sunset). This document defines not a "structure that trusts memory" but a **"structure that forces verification."** To follow the numbering scheme, the registry and the procedure are consolidated into one document.

## Core Rules

- Before writing or modifying provider API code, actually fetch and verify the corresponding provider's official documentation from the registry below. Do not write API code from training knowledge or memory.
- If a provider offers an official skill, install and use it, and prioritize it over ctx7 when checking SDK usage (it's a primary source the provider maintains directly).
- Check SDK usage and code examples with context7 (`ctx7`). For exception classes, parameter signatures, and default retry counts, the installed (locked) SDK source is the local source of truth.
- For behavior the official docs are silent on (e.g., feature combinations), don't guess — confirm it empirically with a provider-specific 1-call smoke test.
- Leave a verification date stamp on provider facts in conventions/code comments. When writing code that depends on a fact whose stamp is more than 3 months old, re-verify against the official docs.
- If the official docs and the conventions/code comments diverge during development, don't just move on — update the convention to match the official docs and commit it.
- An SDK upgrade is an explicit action accompanied by a changelog review. Pin versions with uv.lock.

## Details

### 1. Four-Tier Reference System

| Tier | Source | Purpose |
|---|---|---|
| Tier 1 | Canonical URL registry below (official docs) | API specs, parameters, constraints, pricing, deprecations — the source of facts |
| Tier 1.5 | Provider official skill (§2.1 below) | On-demand knowledge bundle maintained directly by the provider — takes priority over Tier 2 when available |
| Tier 2 | context7 (`ctx7` CLI/MCP) | SDK usage, code examples, version migration |
| Tier 3 | Installed SDK source/type definitions | Exception hierarchy, signatures, defaults — the locked version is authoritative |
| Tier 4 | Provider-specific smoke tests | Empirical confirmation of undocumented behavior (feature combinations, actual error shapes) |

Web search is for lead-finding only. Facts are confirmed only through Tiers 1–4 (→ [00-principles.md](00-principles.md), fact-based judgment).

### 2. Canonical URL Registry (as of: 2026-08)

When starting work related to a provider, fetch the URL in the corresponding row. Check whether the provider offers an `llms.txt` (a documentation index for agents), and if so, add it to this table.

**OpenAI** — https://developers.openai.com/api/docs/
- guides/structured-outputs · guides/reasoning · guides/rate-limits · guides/batch · guides/prompt-caching · deprecations (top level, not under guides/)
- Reference parallel-processing implementation: https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py

**Anthropic** — https://platform.claude.com/docs/en/
- build-with-claude/structured-outputs · build-with-claude/effort · build-with-claude/thinking · build-with-claude/prompt-caching · build-with-claude/batch-processing · build-with-claude/streaming
- api/rate-limits · about-claude/models/model-ids-and-versions

**Google Gemini** — https://ai.google.dev/gemini-api/docs/
- structured-output · thinking · models · troubleshooting

**DeepSeek** — https://api-docs.deepseek.com/
- guides/json_mode · guides/thinking_mode · guides/tool_calls · quick_start/pricing

**OpenRouter** — https://openrouter.ai/docs/
- guides/features/structured-outputs · guides/overview/auth/byok · api_reference/limits

For the ML/training stack (torch, TRL, vLLM, etc.), the source links in [08-llm-development.md](08-llm-development.md) are the seed. When a new library is adopted, leaving its official docs URL as a source in the corresponding convention document is itself the registry entry.

### 2.1 Provider Official Skills (as of: 2026-08)

Agent Skills is an open standard — a folder holding a `SKILL.md` (with `name` and `description`) plus optional scripts and references — originally developed by Anthropic and then released as an open standard. Claude Code, Codex, Cursor, and Gemini CLI all read it, as do a long tail of other agents. If a provider offers an official skill, install and use it instead of fetching docs every time, and prioritize it over ctx7 when checking SDK usage.

| Provider | Official skill | Install |
|---|---|---|
| Google | `gemini-api-dev` (general development), `gemini-live-api-dev` (real-time), `gemini-interactions-api`, `gemini-omni-flash-api` | `npx skills add google-gemini/gemini-skills --skill <name> --global` or ctx7 |
| Anthropic | anthropics/skills marketplace (`document-skills`, `example-skills`). A dedicated Claude API development skill is **not** among them; for the API itself use the Tier 1 docs | Claude Code: `/plugin marketplace add anthropics/skills` then `/plugin install` |
| OpenAI | Dedicated API-development skill **(unverified — needs research)**. Codex itself reads the standard from `.agents/skills`, but the `openai/skills` catalog repo is deprecated in favor of `openai/plugins` (author new ones as skill-only plugins) | — Use the Tier 1/2 path, re-check periodically |
| DeepSeek / OpenRouter | **(unverified — needs research)** | — Use the Tier 1/2 path, re-check periodically |

Sources: [Agent Skills — open standard](https://agentskills.io), [Claude Code — skills](https://code.claude.com/docs/en/skills), [Codex — build skills](https://learn.chatgpt.com/docs/build-skills), [Gemini — coding agents](https://ai.google.dev/gemini-api/docs/coding-agents), [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills), [anthropics/skills](https://github.com/anthropics/skills), [openai/skills (deprecation notice)](https://github.com/openai/skills)

### 3. Provider Smoke Tests (Tier 4)

Each provider adapter has a minimum smoke set: one basic call, one structured output call, one thinking/reasoning combination, and error classification verification (confirm a typed exception with an invalid parameter). Run it: when writing a new adapter, upgrading the SDK, or changing the target model. Cost runs about 1–2 calls per task.

Combinations the docs are silent on (e.g., a given provider's thinking × structured output combined) are confirmed with this smoke test, and the result is recorded in the capability table ([11-llm-api-providers.md](11-llm-api-providers.md)) along with a date stamp.

### 4. How This Reaches a Project

In Claude Code, the dev-harness plugin's `external-sources` skill routes to this document the moment provider-API work starts, rather than having any of it pasted into a project's CLAUDE.md/AGENTS.md — an excerpt is a copy, and README's "How to Apply" forbids that path. Tools and cloud sandboxes without the plugin installed read this document directly from the published site, https://jinwoo-cho-ilevit-com.github.io/develop-convention/. The criterion for what belongs in an on-demand skill rather than an always-loaded instruction file is in [09-agentic-workflow.md](09-agentic-workflow.md) §1.
