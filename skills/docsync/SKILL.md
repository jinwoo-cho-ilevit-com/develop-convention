---
name: docsync
description: Incrementally syncs code changes into docs. Updates the managed sections of each directory's AGENTS.md and ARCHITECTURE.md/Mermaid diagrams, and audits drift/hallucination via --audit. Use after code changes to update docs, to check doc-code consistency, or to bootstrap docs initially.
---

# docsync — Incremental Doc-Code Synchronization

Execution procedure for convention [15-doc-tracking.md](../../conventions/15-doc-tracking.md). This file is a tool-neutral procedure — in Claude Code it runs as a skill; other agents (Codex/Cursor, etc.) read this file and follow the same procedure.

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
| `/docsync` | Syncs each module whose directory changed since that module's own last verified commit. With no state files at all (first run), every module = bootstrap |
| `/docsync <path>` | Scoped run for that module only |
| `/docsync --audit` | Audit mode: dead-man check + blind rebuild + global consistency |

## State Files

`.docsync/` is committed, not gitignored — the state is reviewable, and a teammate who cannot see it re-bootstraps from nothing every time.

One file per documented directory (why a shared file fails: → [15-doc-tracking.md](../../conventions/15-doc-tracking.md) §2).

```json
// .docsync/src__parser__AGENTS.md.json
{
  "doc": "src/parser/AGENTS.md",
  "verified_commit": "<sha>",
  "verified_at": "<YYYY-MM-DD>",
  "audited_at": "<YYYY-MM-DD>",
  "sections": {
    "overview": { "hash": "<sha256 of managed block content>" }
  }
}
```

**Flat, not under a subdirectory** (why: → [15-doc-tracking.md](../../conventions/15-doc-tracking.md) §2).

**The file name** is the doc path with `/` replaced by `__`. Two agents must derive the same name from the same path, so the rule is mechanical. It is not injective — `a/b__c/AGENTS.md` and `a/b/c/AGENTS.md` produce one name, and `__tests__` directories are real — so when the name is taken by a file whose `doc` is a different path, append `-` and the first 8 hex characters of the sha256 of the doc path. `doc` is the authority; the file name is an index into it.

**The verified commit is per document, not per section.** Scope, the dead-man check and staleness all judge a document as a whole, and a per-section commit leaves "the document's commit" undefined the moment one section is regenerated and another is not.

**There is no global commit pointer.** A module skipped this round keeps its own older commit and stays in scope, instead of being marked synced by a pointer that moved without it.

**Never hand-merge a state file.** Two people syncing the same document produce different hashes for the same section, and a merged result records hashes matching neither tree. Resolve by deleting the file and re-running sync for that module — the state is derived, so recomputing it is cheaper than reasoning about it.

```jsonl
// .docsync/corrections.jsonl — append-only
{"path": "...", "section": "...", "reason": "wrong|stale|unclear|granularity", "note": "...", "commit": "<sha>", "at": "<YYYY-MM-DD>"}
```

```
// .docsync/.gitattributes
corrections.jsonl merge=union
```

`union` is a built-in git driver, so an append from each side survives a merge with nothing to configure. It is right for an append-only log and wrong for the state files, which is why they are separate files.

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

### 0. Housekeeping (before anything reads state)

1. **Migrate** if `.docsync/state.json` is present. Its section keys are `"<doc-path>#<section-id>"`: split on the last `#`, group by the doc path, and write one file per group — `doc` set to that path, each section keyed by the id alone, `verified_commit`/`verified_at` taken from any section of that document since they were written together. Drop the two global pointers and delete `state.json` in the same run. Audit history is not recoverable from them, so every document sorts first in the audit rotation once.
2. **Write `.docsync/.gitattributes`** if it is missing — not only on a first run. A repo that migrates never passes through bootstrap, and those are exactly the repos whose corrections log is long enough to collide.
3. **Drop orphans**: any state file whose `doc` path no longer exists. If `git log --diff-filter=R --name-status` shows that document was renamed, move the state file to the new name instead of deleting it — its section hashes are the RMA baseline, and losing them makes the next run read every block as a human edit. An orphan left in place also pins the dead-man check at a commit that will never advance.

### 1. RMA Detection

Compare each managed block's current hash against the hash recorded in that document's own state file. **Hash mismatch + no corresponding code change for that doc = a human edited it.** Do not silently revert or overwrite — instead:

1. Show a summary of the before/after diff and ask the reason once, as multiple choice: `wrong` (content is incorrect) / `stale` (behind the code) / `unclear` (ambiguous) / `granularity` (wrong level of detail). The LLM proposes an estimated default and the user only confirms.
2. Append to `.docsync/corrections.jsonl`.
3. Adopt the human-edited version of that section as the new baseline (update the hash).

If contradictory reason codes accumulate on the same section (e.g. once "too long", once "too short"), propose excluding that section from managed and demoting it to human ownership.

### 2. Scope Calculation

- A document with a state file: `git diff --name-only <its verified_commit>..HEAD -- <its directory>`. Non-empty puts that module in scope. Each document is judged against its own commit, so one that was skipped stays in scope until it is actually synced.
- A directory with no state file has never been synced, so it is in scope. No state files at all is the first run: every module.
- A document at the repository root, such as `ARCHITECTURE.md`, has the root as its directory, which changes on nearly every commit. Judge it by step 4's triggers instead — a changed dependency graph or entry-point flow — rather than by that diff being non-empty.
- A module unit is "a directory with cohesive responsibility" — don't over-split (roughly 2+ Python files per directory, or an entry point).
- Before editing docs, resolve symlinks to their canonical path (to prevent accidentally editing an alias).

### 3. Per-Module Update

For each module (independent, so can run in parallel; delegate to a subagent if context is tight):

1. Read the module's code + existing AGENTS.md + recent corrections for that module.
2. Regenerate only the managed block. **Never edit outside the block.**
3. Authoring rules:
   - Every factual claim must be citable to a code location (file:symbol). If it can't be cited, don't write it.
   - If the meaning is unchanged from the existing text, don't reword it (minimize diff).
   - Reflect corrections' reason codes as negative examples (e.g. avoid the same mistake if there's a `granularity` history).
   - Update the verification stamp (`> Verified: <sha> (<date>)`).

### 4. Global Pass

1. Regenerate the dependency graph with a deterministic tool: pydeps (Python) / madge (JS/TS) output → convert to Mermaid → insert into ARCHITECTURE.md. The LLM does not draw it.
2. If the change touched entry-point flow, update the corresponding sequence diagram.
3. Check for narrative contradictions among the module docs updated this round (both claiming the same responsibility, mismatched call direction, etc.).

### 5. Flag ADR Candidates

If the following are detected in this diff, report **only a list of questions** as ADR candidates (authoring happens after human approval): dependency added/removed, public interface changed, module structure changed, technology choice changed, rollback/revert. Attach a one-line question asking "why was this done this way" to each item.

### 6. Verification

Hand the diff and criteria — never the authoring session's reasoning — to a fresh-context review (a separate subagent or session), which may read the referenced code to confirm: (1) no edits outside the managed block, (2) updated narrative matches the code, (3) no uncitable claims. Do not self-approve in the authoring context.

### 7. Wrap-up

Write a state file for each document this run regenerated **and for each whose hash step 1 adopted**. An RMA-only document has no code diff, so it never enters scope; without persisting the adopted hash it re-prompts and appends a duplicate correction on every run, forever.

Recompute section hashes in both cases. Advance `verified_commit` to HEAD and `verified_at` to today only for documents regenerated against the code — adopting a human edit records what the text now says, not that anyone checked it against the code. Documents nobody touched keep the commit they were verified at; writing HEAD to them is the shared-pointer bug in a new shape.

Then report: list of updated files / ADR candidate questions / RMA handling record / unresolved flags.

## Audit Procedure (`--audit`)

### 1. Dead-Man Check

Run sync step 0's housekeeping first, so an orphaned state file cannot pin the answer. Then: if the oldest `verified_commit` across the state files is further behind HEAD than the threshold in commits, or the oldest `verified_at` is further back than the threshold in days (recommended defaults: 30 commits, 14 days), **warn about that fact before inspecting the docs.** A dead sync looks identical to a healthy one. The oldest rather than the newest, because one actively edited module keeps a newest-commit reading fresh while everything around it rots.

### 2. Target Selection

Staleness score = time elapsed since that document's `audited_at` × that module's churn (commit count). A document with no `audited_at` has never been audited and sorts first. Only inspect the top K (recommended default: 3-5, a cost cap) this round; rotate the rest to the next round.

### 3. Blind rebuild

For each selected module: a fresh-context agent, **with existing AGENTS.md/ADRs blocked from context**, reads only the code and rewrites the managed block from scratch.

### 4. Claim Comparison

Decompose the blind version and the retained version into atomic claim units and compare:

- **Claims only in the retained version** → attempt to attach a code citation (file:symbol). Citation failure = report as a hallucination candidate. Citable but background knowledge not derivable from the code = tacit knowledge → propose promoting it to the human section/ADR.
- **Claims only in the blind version** → candidate for a recent change the retained version missed.
- **Same meaning, different wording only** → not drift. Leave it alone.

Judgment results are submitted as a report, not auto-applied (hallucination deletion/tacit-knowledge promotion happen after human confirmation).

### 5. Freshness Banner

Insert a banner at the top of the managed block for any doc whose verification stamp exceeds the threshold (recommended default: 90 days or 100 commits): `> STALE: this section has not been verified since <date> — may differ from the code`.

Then set `audited_at` on every document inspected this round. Without it the rotation in step 2 keeps picking the same modules and the rest are never reached.

## Cost Cap

- Audit is capped at K modules per round (rotating). Sync covers only changed modules.
- For large modules, don't read cover-to-cover — focus on public symbols and entry points.
- The fitness test (perform the task from the docs alone → compare against execution results) is at the pilot stage — only attempt it for pure functions with an execution ground truth; mark everything else "unverified".

## Use From Other Tools

Claude Code gets this skill from the `dev-harness` plugin; nothing is copied into the project. Tools that do not read plugins need a pointer in AGENTS.md instead:

```
When doc sync is needed, follow the procedure at
https://jinwoo-cho-ilevit-com.github.io/develop-convention/skills/docsync/SKILL/
```

The procedure itself is tool-independent. Only the trigger (slash command, scheduled run) is tool-specific.
