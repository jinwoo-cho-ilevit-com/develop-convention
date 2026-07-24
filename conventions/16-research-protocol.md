# 16. Research Protocol (Factual Specs)

## Core Rules

- This protocol applies whenever researching factual specs — model/library/API/product **versions, sizes, release dates, pricing, licenses, capabilities, lineups** — especially for fast-moving AI models.
- Use prior/training knowledge ONLY to **form search queries and hypotheses** — NEVER to (a) fix the research scope or candidate set, or (b) populate facts in the deliverable.
- **Discover the candidate set from actual searches/registry queries**, not from "the models/APIs I already know." Recall ≠ research; a remembered list is a starting query, not an answer.
- **Every factual claim in the output must trace to a source fetched in THIS research.** If it wasn't found, it does not go in — leave a gap marked **"unverified — needs research"**. Never backfill, guess, or "complete" from memory, even when confident.
- Confidence from training is not evidence. When memory and a fetched source disagree, the source wins; when memory has no source, it is not a fact yet.
- **Enumeration facts** (variants, sizes, dates, license, modality) are confirmed ONLY from the **authoritative registry**: official org page / model card / collection / changelog / API docs.
- Search snippets, leaderboards, news, and third-party blogs are **leads, not proof** — fetch the canonical page before asserting.
- Never trust search ranking for **completeness**: new/small items rank low. Query the registry directly (e.g. HF Hub `pipeline_tag` + `sort=created` + param filter), don't keyword-search only.
- Negative and universal claims ("X doesn't exist / smallest is N / all are Y / none support Z") require **primary-source enumeration**, never absence-in-search. If not verified against the registry, mark **"unverified"** — do not assert.
- For each named vendor/library in scope, fetch its **official latest collection/release page once** — don't rely on emergent discovery alone. Seed research with already-known canonical URLs (from repo docs/citations) as **must-fetch**.
- If a finding conflicts with an existing repo doc/citation, **surface the conflict and resolve via primary source** before writing. Verify the in-repo claim before overriding it.

## Details

### 1. Scope and relationship to neighboring docs

- [00-principles.md](00-principles.md) states the general principle: never judge from prior knowledge; verify against current sources.
- [12-docs-reference.md](12-docs-reference.md) covers **how to look up SDK/API usage** for implementation (tier: official skill > ctx7 > installed SDK source > smoke test).
- This document governs **factual-spec research as a deliverable** — building comparisons, lineups, recommendations, or any document whose claims are facts about external products. The failure mode it prevents is different from 12's: not "wrong API call" but "confidently wrong facts assembled from memory."

### 2. Prior knowledge: queries only, never results (governing rule)

Training data always lags reality, and for fast-moving domains (AI model lineups, pricing, capabilities) it lags badly. The trap is subtle: prior knowledge feels like knowledge, so a model (or person) "completes" a table from memory and the result looks thoroughly researched while being stale or invented.

The rule that prevents this: prior knowledge may propose **where to look** (query terms, candidate names, hypotheses to test), but every cell of the final deliverable must be backed by a source actually fetched during this research session. A gap marked "unverified — needs research" is a correct result; a plausible number from memory is not.

### 3. Source tier (hard rule)

| Tier | Source | Role |
|---|---|---|
| Authoritative | Official org page, model card, collection, changelog, API docs | The ONLY basis for enumeration facts (variants, sizes, dates, license, modality) |
| Leads | Search snippets, leaderboards, news, third-party blogs | Pointers to fetch the canonical page — never citable as proof |

Search ranking is optimized for popularity, not completeness — a newly released or small variant ranks low or not at all. For completeness questions, query the registry directly with structured filters (e.g. Hugging Face Hub: `pipeline_tag` + `sort=created` + parameter-count filter) instead of keyword search alone.

### 4. Negative and universal claims

"Absence of evidence ≠ evidence of absence." A claim of the form "no model under 1B supports X" or "the smallest variant is N" asserts something about the **entire registry**, so it can only be verified by enumerating the registry — not by observing that a search didn't surface a counterexample. If enumeration wasn't done, write "unverified" instead of asserting.

### 5. Coverage

Emergent discovery (following links from search results) is biased toward what is popular. Two mechanical guards:

- For every vendor/library named in the research scope, fetch its official latest collection/release page at least once.
- Before searching, collect canonical URLs already known to the repo (existing doc citations) and treat them as a must-fetch list.

### 6. Contradictions

When fresh research contradicts an existing claim in this repo's docs, neither silently overrides the other. Surface the conflict, fetch the primary source, and update whichever side is wrong — the repo claim may be stale, or the new finding may be misread.
