---
name: docsync
description: Incrementally syncs code changes into docs. Updates the managed sections of each directory's AGENTS.md and ARCHITECTURE.md/Mermaid diagrams, and audits drift/hallucination via --audit. Use after code changes to update docs, to check doc-code consistency, or to bootstrap docs initially.
---

# docsync — Incremental Doc-Code Synchronization

Execution procedure for convention [15-doc-tracking.md](../../../conventions/15-doc-tracking.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

## Scope of Responsibility

| Layer | This Skill's Role |
|---|---|
| L1 I/O contract | Not managed — code (type hints/schema) is the single source. Docs contain only a summary + code reference |
| L2 Module docs | Create/update the managed block in each directory's AGENTS.md |
| L3 Overall flow | Update ARCHITECTURE.md + dependency graph/sequence diagram |
| L4 Decision history | ADR **candidate detection/questions only** — ADR authoring requires human approval |

## Execution Modes

| Command | Behavior |
|---|---|
| `/docsync` | Incrementally syncs only the modules changed between the last sync commit and HEAD. If no state file exists (first run), all modules = bootstrap |
| `/docsync <path>` | Scoped run for that module only |
| `/docsync --audit` | Audit mode: dead-man check + blind rebuild + global consistency |

## State Files

`.docsync/` (do not gitignore — state is also subject to review):

```json
// .docsync/state.json
{
  "last_sync_commit": "<sha>",
  "last_audit_commit": "<sha>",
  "sections": {
    "<doc-path>#<section-id>": {
      "hash": "<sha256 of managed block content>",
      "verified_commit": "<sha>",
      "verified_at": "<YYYY-MM-DD>"
    }
  }
}
```

```jsonl
// .docsync/corrections.jsonl — append-only
{"path": "...", "section": "...", "reason": "wrong|stale|unclear|granularity", "note": "...", "commit": "<sha>", "at": "<YYYY-MM-DD>"}
```

## Module Doc Format

Each major directory's `AGENTS.md`:

```markdown
# <module-name>

<!-- docsync:managed:start id=overview -->
> Verified: <commit-sha> (<YYYY-MM-DD>)

## Role
One or two sentences.

## Core Logic
Narrative of input → processing steps → output. Invariants (conditions that must always hold), edge-case handling.

## I/O Contract
Summarize via code reference: "Input schema is `models.py:RequestSchema`, output is `models.py:ResultSchema`". Do not duplicate signatures in the doc.

## Diagram
```mermaid
(Internal module flow or relationship with adjacent modules)
```

## Pitfalls
Non-obvious constraints, easy-to-make mistakes.
<!-- docsync:managed:end -->

## Design Notes
<!-- human — do not edit as agent. The 'why' is written here by humans -->
```

## Sync Procedure

### 0. RMA Detection (first step every run)

Compare each managed block's current hash against state.json. **Hash mismatch + no corresponding code change for that doc = a human edited it.** Do not silently revert or overwrite — instead:

1. Show a summary of the before/after diff and ask the reason once, as multiple choice: `wrong` (content is incorrect) / `stale` (behind the code) / `unclear` (ambiguous) / `granularity` (wrong level of detail). The LLM proposes an estimated default and the user only confirms.
2. Append to `.docsync/corrections.jsonl`.
3. Adopt the human-edited version of that section as the new baseline (update the hash).

If contradictory reason codes accumulate on the same section (e.g. once "too long", once "too short"), propose excluding that section from managed and demoting it to human ownership.

### 1. Scope Calculation

- `state.json` exists: use `git diff --name-only <last_sync_commit>..HEAD` for changed files → list of owning modules (directories).
- Does not exist (bootstrap): all modules. A module unit is "a directory with cohesive responsibility" — don't over-split (roughly 2+ Python files per directory, or an entry point).
- Before editing docs, resolve symlinks to their canonical path (to prevent accidentally editing an alias).

### 2. Per-Module Update

For each module (independent, so can run in parallel; delegate to a subagent if context is tight):

1. Read the module's code + existing AGENTS.md + recent corrections for that module.
2. Regenerate only the managed block. **Never edit outside the block.**
3. Authoring rules:
   - Every factual claim must be citable to a code location (file:symbol). If it can't be cited, don't write it.
   - If the meaning is unchanged from the existing text, don't reword it (minimize diff).
   - Reflect corrections' reason codes as negative examples (e.g. avoid the same mistake if there's a `granularity` history).
   - Update the verification stamp (`> Verified: <sha> (<date>)`).

### 3. Global Pass

1. Regenerate the dependency graph with a deterministic tool: pydeps (Python) / madge (JS/TS) output → convert to Mermaid → insert into ARCHITECTURE.md. The LLM does not draw it.
2. If the change touched entry-point flow, update the corresponding sequence diagram.
3. Check for narrative contradictions among the module docs updated this round (both claiming the same responsibility, mismatched call direction, etc.).

### 4. Flag ADR Candidates

If the following are detected in this diff, report **only a list of questions** as ADR candidates (authoring happens after human approval): dependency added/removed, public interface changed, module structure changed, technology choice changed, rollback/revert. Attach a one-line question asking "why was this done this way" to each item.

### 5. Verification

Give only the diff and criteria to a fresh-context review (a separate subagent or session) and confirm: (1) no edits outside the managed block, (2) updated narrative matches the code, (3) no uncitable claims. Do not self-approve in the authoring context.

### 6. Wrap-up

Update `state.json` (last_sync_commit = HEAD, recompute section hashes), then report: list of updated files / ADR candidate questions / RMA handling record / unresolved flags.

## Audit Procedure (`--audit`)

### 1. Dead-Man Check

If the elapsed time since `last_sync_commit` exceeds the threshold (recommended default: 30 commits or 14 days), **warn about that fact before inspecting the docs.** A dead sync looks identical to a healthy one.

### 2. Target Selection

Staleness score = time elapsed since last audit × that module's churn (commit count). Only inspect the top K (recommended default: 3-5, a cost cap) this round; rotate the rest to the next round.

### 3. Blind rebuild

For each selected module: a fresh-context agent, **with existing AGENTS.md/ADRs blocked from context**, reads only the code and rewrites the managed block from scratch.

### 4. Claim Comparison

Decompose the blind version and the retained version into atomic claim units and compare:

- **Claims only in the retained version** → attempt to attach a code citation (file:symbol). Citation failure = report as a hallucination candidate. Citable but background knowledge not derivable from the code = tacit knowledge → propose promoting it to the human section/ADR.
- **Claims only in the blind version** → candidate for a recent change the retained version missed.
- **Same meaning, different wording only** → not drift. Leave it alone.

Judgment results are submitted as a report, not auto-applied (hallucination deletion/tacit-knowledge promotion happen after human confirmation).

### 5. Freshness Banner

Insert a banner at the top of the managed block for any doc whose verification stamp exceeds the threshold (recommended default: 90 days or 100 commits): `> ⚠ This section has not been verified since <date> — may differ from the code`.

## Cost Cap

- Audit is capped at K modules per round (rotating). Sync covers only changed modules.
- For large modules, don't read cover-to-cover — focus on public symbols and entry points.
- The fitness test (perform the task from the docs alone → compare against execution results) is at the pilot stage — only attempt it for pure functions with an execution ground truth; mark everything else "unverified".

## Use From Other Tools

For Codex/Cursor etc., put the following line in AGENTS.md to point to this file:

```
When doc sync is needed, follow the procedure in .claude/skills/docsync/SKILL.md.
```

The procedure itself is tool-independent. Only the trigger (slash command, scheduled run) is tool-specific.
