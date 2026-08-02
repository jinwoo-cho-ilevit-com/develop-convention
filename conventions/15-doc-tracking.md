# 15. Doc-Code Synchronization Tracking

## Core Rules

- Split documentation into 4 layers with different rates of change: for I/O contracts, the code itself (type hints, schemas) is the single source of truth (no hand-written I/O docs); module logic goes in per-directory AGENTS.md; overall flow goes in the root ARCHITECTURE.md; decisions and history go in structured commits + ADRs.
- Document functions via docstrings, not separate files. Skip self-evident functions; record only non-obvious algorithmic choices.
- In module docs, agents regenerate only the content inside `docsync:managed` markers. Human sections outside the markers are inviolable. Stamp managed blocks with the verification commit and date.
- Every factual claim in managed docs (L2 module, L3 flow) must be citable to a code location (file:symbol). Do not write claims that cannot be cited — decision rationale and failure records that aren't derivable from code go in ADRs or human sections.
- The primary update mechanism is change-time sync (`/docsync` — incremental from the last documented commit to HEAD; the first run covers everything, i.e., bootstrap). Scheduled runs are audit-only — do not periodically regenerate narrative docs wholesale.
- Audit starts by confirming sync itself is alive (dead-man's switch: warn first if N commits/M days have passed since the last sync). The core check is a blind rebuild — block out the existing docs, rewrite from code alone, diff claim-by-claim, and report any claim that can't be backed by a code citation as a hallucination candidate. Wording differences with the same meaning are not treated as drift.
- If a human edits a managed section, don't silently revert it — log the reason code to the corrections log and feed it into future generation prompts (RMA loop). If contradictory reasons pile up for the same section, demote that section to human ownership.
- ADRs are append-only — supersede with a new ADR instead of editing. Record not only adopted decisions but also reversed decisions and rollbacks, with reasons. When agents reference ADRs, they must resolve the supersession chain to the end and follow only the currently valid decision.
- Standardize visualizations on Mermaid (it's text, so it's diffable/reviewable, GitHub renders it natively, and agents can read and write it). Generate module dependency graphs with deterministic tools (pydeps, madge, etc.) rather than maintaining them by hand.
- Include a "code change ↔ doc update consistency" check in the review gate (→ [20-review-gate.md](20-review-gate.md)).
- When something ships, update what distributes it in the same change: the installer or bootstrap script, the getting-started page, the excerpt loaded elsewhere, the navigation of the published site. Docs-follow-code covers the description; nothing covers the delivery path, and it is the one that leaves a working artifact unreachable.
- Give an excerpt a header naming the document it was taken from and the commit it was taken at, and check the two against each other automatically. An excerpt is a copy, copies drift, and one that drifts is worse than the original being wrong — it is loaded everywhere and matches nothing.

## Details

### 1. Why Split into Layers

"Overall flow, per-module implementation logic, I/O contracts, and change history" are information with different rates of change and different natures. Bundled into one large document, the whole thing rots at the pace of its most expensive-to-update part. The principle is to give each layer the mechanism and update owner that fits it.

| Layer | Tracks | Mechanism | Update owner |
|---|---|---|---|
| L1 | I/O contracts | The code itself (type hints, pydantic and other schemas). If docs are needed, generate them from code | Automatic |
| L2 | Per-module implementation logic | Per-directory AGENTS.md — role, core logic (input→processing→output narrative, invariants, edge cases), Mermaid, pitfalls | Agent + human review |
| L3 | Overall flow | Root ARCHITECTURE.md — per-entry-point sequence diagram + dependency graph | Agent + human review |
| L4 | Decisions/change history | Structured commit body (Why/What/How/Result) + append-only ADR | Human (agent drafts) |

- Why L1 isn't hand-written: a hand-written I/O doc becomes harmful the moment it diverges from the code. If the code is the single source, drift in this layer is structurally impossible.
- Why L2 lives in per-directory AGENTS.md: docs crammed into the root don't show up in the diff, so they rot. Placed next to the code, the doc appears in the same diff that fixes the module, and it's automatically loaded as context when an agent works in that directory — the tracking system and the agent's context system become the same artifact.
- At the function level, use docstrings: they need to live in the same file as the code so they follow along through refactors.

Summary principle: **Generate whatever can be generated, have humans write only the "why," and enforce updates with a gate.**

### 2. The docsync Skill — Incremental Sync

The update procedure is packaged as a skill in [skills/docsync/SKILL.md](../skills/docsync/SKILL.md). SKILL.md is a tool-neutral markdown procedure — Claude Code gets it from the `dev-harness` plugin, and Codex/Cursor and similar tools reference the same file as a prompt to carry out the identical procedure.

- **State file** (`.docsync/state.json`): the last documented commit + a content hash per managed section. If state exists, process only the modules changed between the last commit and HEAD; if not (first run), process all modules — bootstrap is just the special case of sync with empty state, so there's no dependency on a separate bootstrap tool (self-contained).
- **sync pipeline**: detect RMA → compute scope → update per-module managed sections → global pass (regenerate dependency graph, update ARCHITECTURE.md, check for cross-module contradictions) → report a list of ADR-candidate questions → fresh-context verification → update state.
- **3 trigger types**:

| Trigger | Method | Role |
|---|---|---|
| Manual | `/docsync` at the end of a task | Primary mechanism |
| Review gate | Include "code change ↔ doc update consistency" as a review item | Prevents omissions |
| Scheduled | `/docsync --audit` (e.g., weekly) | Drift audit + global consistency |

Why time-based wholesale regeneration isn't the primary mechanism: by the time documentation happens, the context of the change (the "why") has already evaporated, turning it into diff archaeology and guesswork; and if an LLM periodically regenerates narrative docs wholesale, the prose style drifts and the diffs balloon until nobody reviews them anymore. The only areas where scheduled runs fit are regenerating deterministically derived artifacts (diagrams) and auditing repository-wide consistency.

### 3. The Verification Layer — Mechanisms That Keep Docs From Rotting

The design rationale is the common limitation of documentation tools that only generate. Even doc-it — the closest existing skill (generation, audit, and update support) — has its author state as limitations that "it's manual-trigger-only, so docs go stale silently as code changes" and that "it can generate content that sounds plausible but doesn't exist." The mechanisms below close that gap.

Sources: [dosu — A Claude Code Skill for Auto-Generating Project Docs](https://dosu.dev/blog/claude-code-skill-doc-it)

- **dead-man's switch**: a dead sync pipeline looks identical to a healthy one. The first check in an audit isn't the docs — it's "is sync still alive?"
- **Freshness stamp**: record the verification commit and date on every managed block, and insert a staleness banner once a threshold is exceeded. The real failure mode is a stale doc being read with the same authority as a current one.
- **blind rebuild**: because incremental sync regenerates using the previous doc as scaffolding, early hallucinations get laundered into established fact. Break this chain by comparing a version rewritten with the existing doc blocked out against the maintained version, claim by claim. For claims that exist only in the maintained version, attempt a code citation — citation failure = hallucination candidate. Confirmed hallucinations are deleted; genuine tacit knowledge is promoted to a human section or an ADR, ending the pretense of "derived from code."
- **Tolerance**: don't misjudge same-meaning wording differences as drift and repeatedly rewrite a perfectly fine doc.
- **RMA loop**: a human edit is a learning signal, not something to discard. A managed section's hash mismatch with no corresponding code diff is detected as human intervention; log the reason code (wrong/stale/unclear/granularity) to `.docsync/corrections.jsonl` and feed it as a negative example into future generation of the same section type.

### 4. The History Layer — Commits and ADRs

- Per-commit history is carried by the structured commit body (Why/What/How/Result) — write it so a dev note can be reconstructed from `git log` alone (→ [17-commit-protocol.md](17-commit-protocol.md)).
- Decisions that change the structure go into an ADR (`adr/NNNN-title.md`): context, decision, alternatives, consequences, kept brief. Keep the directory in the source tree — a docs site assembled at build time is not one, and an ADR written into the assembled output is not tracked at all. When a decision changes, don't edit it — supersede it with a new ADR, per Nygard's original wording: "If a decision is reversed, we will keep the old one around, but mark it as superseded."
- Record failures too: keep reversed decisions and rollbacks with their reasons. What's actually needed during incident response is the record that "that approach was already tried and it failed."
- Consumption rule: when an agent searches or references ADRs, it must follow the supersession chain to the end and use only the currently valid decision. This prevents the mistake of following an old, reversed decision as-is.

Sources: [Michael Nygard — Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), [adr.github.io](https://adr.github.io/)

### 5. Visualization

- Standardize on Mermaid: because it's text-based, it works with git diff and review, GitHub renders it natively in markdown code blocks, and agents can read and write it, so it fits naturally into the update pipeline.
- Don't hand off to the LLM anything that can be generated deterministically: generate module dependency graphs from the output of tools like pydeps (Python) or madge (JS/TS). The LLM generates only things that require judgment, like sequence/flow diagrams, and a human reviews them.

Sources: [GitHub — Include diagrams in your Markdown files with Mermaid](https://github.blog/developer-skills/github/include-diagrams-markdown-files-mermaid/)

### 6. Applying This to a Project

1. Install the `dev-harness` plugin; [skills/docsync/SKILL.md](../skills/docsync/SKILL.md) comes with it. Tools that do not read plugins get a one-line pointer to the published copy from AGENTS.md instead.
2. The first `/docsync` run is the bootstrap — there is no separate initialization procedure.
