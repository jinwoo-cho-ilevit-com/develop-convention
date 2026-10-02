# 15. Doc-Code Synchronization Tracking

## Core Rules

- Split documentation into 4 layers with different rates of change: for I/O contracts, the code itself (type hints, schemas) is the single source of truth (no hand-written I/O docs); module logic goes in per-directory AGENTS.md; overall flow goes in the root ARCHITECTURE.md; decisions and history go in structured commit bodies.
- Document functions via docstrings, not separate files. Skip self-evident functions; record only non-obvious algorithmic choices.
- In module docs, agents regenerate only the content inside `docsync:managed` markers. Human sections outside the markers are inviolable. Stamp managed blocks with the verification commit and date.
- Every factual claim in managed docs (L2 module, L3 flow) must be citable to a code location (file:symbol). Do not write claims that cannot be cited — decision rationale and failure records that aren't derivable from code go in human sections or the structured commit body.
- The primary update mechanism is change-time sync (`/docsync` — each module is resynced when its own directory changed since its own last verified commit, with no shared pointer across modules; the first run covers everything, i.e., bootstrap). Scheduled runs are audit-only — do not periodically regenerate narrative docs wholesale.
- Audit starts by confirming sync itself is alive (dead-man's switch: warn first if N commits/M days have passed since the *oldest* module's last sync — the newest keeps reading fresh while everything around it rots). The core check is a blind rebuild — block out the existing docs, rewrite from code alone, diff claim-by-claim, and report any claim that can't be backed by a code citation as a hallucination candidate. Wording differences with the same meaning are not treated as drift.
- If a human edits a managed section, don't silently revert it — log the reason code to the corrections log and feed it into future generation prompts (RMA loop). If contradictory reasons pile up for the same section, demote that section to human ownership.
- Standardize visualizations on Mermaid (it's text, so it's diffable/reviewable, GitHub renders it natively, and agents can read and write it). Generate module dependency graphs with deterministic tools (pydeps, madge, etc.) rather than maintaining them by hand.
- When something ships, update what distributes it in the same change: the installer or bootstrap script, the getting-started page, the excerpt loaded elsewhere, the navigation of the published site. Docs-follow-code covers the description; nothing covers the delivery path, and it is the one that leaves a working artifact unreachable.
- An excerpt is a copy, copies drift, and one that drifts is worse than the original being wrong — it is loaded everywhere and matches nothing. Prefer a **generated** excerpt: a consumer file declares marker blocks that `scripts/fill-excerpts.py` fills verbatim from a document's Core Rules, so the copy either regenerates or fails loudly when the source moves — it cannot drift silently. An excerpt a human authored instead carries a header naming its source document and the commit it was taken at, checked against the source automatically.

## Details

### 1. Why Split into Layers

"Overall flow, per-module implementation logic, I/O contracts, and change history" are information with different rates of change and different natures. Bundled into one large document, the whole thing rots at the pace of its most expensive-to-update part. The principle is to give each layer the mechanism and update owner that fits it.

- Why L1 isn't hand-written: a hand-written I/O doc becomes harmful the moment it diverges from the code. If the code is the single source, drift in this layer is structurally impossible.
- Why L2 lives in per-directory AGENTS.md: docs crammed into the root don't show up in the diff, so they rot. Placed next to the code, the doc appears in the same diff that fixes the module, and it reaches the agent working in that directory — the tracking system and the agent's context system become the same artifact. Codex and Cursor read AGENTS.md themselves. Claude Code reads CLAUDE.md, not AGENTS.md, and a subdirectory's CLAUDE.md is "included when Claude reads files in those subdirectories", so each AGENTS.md needs a sibling CLAUDE.md that imports it ([Claude Code — memory](https://code.claude.com/docs/en/memory), checked 2026-09-12).
- **The sibling CLAUDE.md.** Every AGENTS.md, at the root or in a directory, has a CLAUDE.md beside it whose only line is `@AGENTS.md` — bare in the file, since inside backticks it is text, not an import. The one exception is the root of a project that keeps its CLAUDE.md at `./.claude/CLAUDE.md`: that file imports the root AGENTS.md as `@../AGENTS.md`, and no second import is created beside it. Create it wherever an AGENTS.md has none, every AGENTS.md already in the tree included. Never overwrite an existing CLAUDE.md: leave one that is a symlink to AGENTS.md alone, and add the line as the first line of any other only after confirmation, moving into AGENTS.md rather than duplicating anything it already says that AGENTS.md would hold. Setup and docsync apply this rule by pointing here.
- At the function level, use docstrings: they need to live in the same file as the code so they follow along through refactors.

Summary principle: **Generate whatever can be generated, and have humans write only the "why."**

### 2. The docsync Skill — Incremental Sync

The update procedure is packaged as a skill in [skills/docsync/SKILL.md](../skills/docsync/SKILL.md). SKILL.md is a tool-neutral markdown procedure — Claude Code gets it from the `dev-harness` plugin, and Codex/Cursor and similar tools reference the same file as a prompt to carry out the identical procedure.

- **State files** (`.docsync/<doc-path-with-__>.json`, flat — a `docs/` subdirectory is swallowed by the site-build ignore most projects carry): one per documented directory, each holding a content hash per managed section plus the commit that document was verified at. A module is in scope when its directory changed since its own verified commit; a directory with no state file has never been synced, and no state files at all is the first run — bootstrap is the special case of sync with empty state, so there's no dependency on a separate bootstrap tool (self-contained). One file per document rather than one shared file, because a shared one is rewritten whole on every sync and collides between people working on unrelated modules, and a hand-merged result records hashes that match neither tree — which silently disables the RMA check those hashes exist for.
- **sync pipeline**: detect RMA → compute scope → update per-module managed sections → global pass (regenerate dependency graph, update ARCHITECTURE.md, check for cross-module contradictions) → fresh-context verification → update state.
- **3 trigger types**:

| Trigger | Method | Role |
|---|---|---|
| Manual | `/docsync` at the end of a task | Primary mechanism |
| Scheduled | `/docsync --audit` (e.g., weekly) | Drift audit + global consistency |

Why time-based wholesale regeneration isn't the primary mechanism: by the time documentation happens, the context of the change (the "why") has already evaporated, turning it into diff archaeology and guesswork; and if an LLM periodically regenerates narrative docs wholesale, the prose style drifts and the diffs balloon until nobody reviews them anymore. The only areas where scheduled runs fit are regenerating deterministically derived artifacts (diagrams) and auditing repository-wide consistency.

### 3. The Verification Layer

- **blind rebuild**: because incremental sync regenerates using the previous doc as scaffolding, early hallucinations get laundered into established fact. Comparing a version rewritten with the existing doc blocked out against the maintained version, claim by claim, breaks this chain. Confirmed hallucinations are deleted; genuine tacit knowledge is promoted to a human section.
- **RMA loop**: a managed section's hash mismatch with no corresponding code diff is detected as human intervention; log the reason code (wrong/stale/unclear/granularity) to `.docsync/corrections.jsonl` and feed it as a negative example into future generation of the same section type.

### 4. The History Layer — Commits

- History is carried by the structured commit body (Why/What/How/Result) — write it so a dev note can be reconstructed from `git log` alone (→ [17-commit-protocol.md](17-commit-protocol.md)).
- Record failures too: a reverting or rolling-back commit states in its body what was tried and why it did not work. What's actually needed during incident response is the record that "that approach was already tried and it failed", and `git log` is where it is searched for.

### 5. Generated Excerpts

A consumer that needs a subset of this repository's rules (an agent's always-on rules file, a tool-specific instruction file) declares what it excerpts with marker blocks; `scripts/fill-excerpts.py` fills each block verbatim from the named document's Core Rules bullets, selected by anchors that must match exactly one bullet. The marker syntax and CLI live in the script's docstring. The failure contract is the point: a reworded source bullet makes the fill fail loudly instead of leaving a stale copy behind, which replaces stamp-and-audit maintenance for these consumers.
