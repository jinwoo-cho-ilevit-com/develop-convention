# 12. Upstream Documentation: Reference Procedure + Canonical URL Registry

How to check someone else's official documentation before writing against their SDK or API.

Provider API knowledge goes stale on a timescale of months (the silent `output_format`→`output_config.format` migration, DeepSeek model name deprecations, torchtune's development sunset). This document defines not a "structure that trusts memory" but a **"structure that forces verification."**

## Core Rules

- Before writing or modifying provider API code, actually fetch and verify the corresponding provider's official documentation from the registry below. Do not write API code from training knowledge or memory.
- If a provider offers an official skill, install and use it, and prioritize it over ctx7 when checking SDK usage (it's a primary source the provider maintains directly).
- Check SDK usage and code examples with context7 (`ctx7`). For exception classes, parameter signatures, and default retry counts, the installed (locked) SDK source is the local source of truth.
- For behavior the official docs are silent on (e.g., feature combinations), don't guess — confirm it empirically with a provider-specific 1-call smoke test.
- Leave a verification date stamp on provider facts in conventions/code comments. When writing code that depends on a fact whose stamp is more than 3 months old, re-verify against the official docs.
- If the official docs and the conventions/code comments diverge during development, don't just move on. Fix your own code comments to match the official docs. Update the convention at its source repository; a project consuming it through the plugin opens an issue there rather than editing the installed copy, which the next update overwrites.
- An SDK upgrade is an explicit action accompanied by a changelog review. Pin versions with uv.lock.

## Details

### 1. Five-Tier Reference System

| Tier | Source | Purpose |
|---|---|---|
| Tier 1 | Canonical URL registry below (official docs) | API specs, parameters, constraints, pricing, deprecations — the source of facts |
| Tier 1.5 | Provider official skill (§2) | On-demand knowledge bundle maintained directly by the provider — takes priority over Tier 2 when available |
| Tier 2 | context7 (`ctx7` CLI/MCP) | SDK usage, code examples, version migration |
| Tier 3 | Installed SDK source/type definitions | Exception hierarchy, signatures, defaults — the locked version is authoritative |
| Tier 4 | Provider-specific smoke tests | Empirical confirmation of undocumented behavior (feature combinations, actual error shapes) |

Web search is for lead-finding only. Facts are confirmed only through Tiers 1–4 (→ [00-principles.md](00-principles.md), fact-based judgment).

### 2. Canonical URL Registry (as of: 2026-08)

When starting work related to a provider, fetch the page you need under its docs root. Check whether the provider offers an `llms.txt` (a documentation index for agents), and if so, add it here.

| Provider | Docs root |
|---|---|
| OpenAI | https://developers.openai.com/api/docs/ |
| Anthropic | https://platform.claude.com/docs/en/ |
| Google Gemini | https://ai.google.dev/gemini-api/docs/ |
| DeepSeek | https://api-docs.deepseek.com/ |
| OpenRouter | https://openrouter.ai/docs/ |

When a new library is adopted, leaving its official docs URL as a source in the corresponding convention document is itself the registry entry.

Provider official skills follow the [Agent Skills](https://agentskills.io) open standard (a folder holding a `SKILL.md`); check the provider's docs for one before falling back to ctx7. A skill does not replace the Tier 1 fetch: a parameter's existence, a limit, or a model name is still confirmed on the registry page.

### 3. Provider Smoke Tests (Tier 4)

Each provider adapter has a minimum smoke set: one basic call, one structured output call, one thinking/reasoning combination, and error classification verification (confirm a typed exception with an invalid parameter). Run it: when writing a new adapter, upgrading the SDK, or changing the target model. Cost runs about 1–2 calls per task.
