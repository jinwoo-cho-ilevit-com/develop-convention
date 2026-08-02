# 0003. What is deliberately not specified

Status: accepted (2026-08-02)

## Context

A convention repository accumulates two kinds of gap: the ones nobody got to, and the ones somebody decided against. They look identical from the outside, and the second kind keeps getting reopened by whoever finds it next. This session reopened three, spent effort re-deriving the reasoning, and in one case rediscovered a constraint an earlier plan had already written down and lost.

## Decisions

### 1. The evidence visualization format stays unspecified

Visualization tiers, `figure ↔ criterion ↔ code anchor` linking and a self-contained `index.html` are named in `19 §7` and left without a format.

*Reason:* a required field is a promise that something validates it. Until the format exists nothing can, so every contract fills it differently and the accumulated files all need rewriting once the real format lands.

*What changed here:* the section used to say the intent goes in an `evidence_todo` front-matter field, and the runner refuses every field it does not read — so an author following `19` wrote a contract the tool then rejected. The intent now goes in the contract body, which is where something unvalidated belongs.

*What would settle it:* enough evidence packs to see which figures a reviewer actually opens. Not a design session.

### 2. The runner reads the lane fields but does not execute a lane

**Superseded in part.** This entry originally recorded that the runner refused `lanes`, `sequential_owner`, `integration` and `checkpoints` outright. It now reads them and checks that the decomposition holds together — disjoint `owns`, no globs, nothing claimed by both a lane and `sequential_owner`, a tier rather than a model id — while `integration` and `checkpoints` are read and left alone, `18 §3` calling a checkpoint a marker rather than a trigger.

*What is still not done, and why:* running a lane, or enforcing ownership while lanes write. That is a separate mechanism and it gets its own contract. The check added here answers a different question — whether the decomposition contradicts itself — and answers it before the lanes start rather than when they collide.

*What changed the decision:* the session that wrote this entry then nearly broke the ownership rule itself, slicing five lanes by kind of change so that all five landed in the same three documents. Re-slicing per file avoided it. A rule that is easy to break while writing the document that states it is a rule worth making mechanical.

### 3. `review_rounds` is not in the manifest

`19 §4` names it alongside `created_at` and `verify_runs[].at`, both of which the runner now records.

*Reason:* the count belongs to a review subcommand this runner does not have. A field the tool cannot derive would be filled by hand, and a hand-filled provenance field is the thing `19` exists to replace.

### 4. `created_at` was the render timestamp — resolved

**Closed.** Recorded here as a defect rather than a decision, and fixed on that basis: the value is written once into the state directory by whichever phase runs first and read back from there, so it is the time the evidence began. The mechanism is the one `verify_runs` introduced, which is why the entry said it was cheap.

Kept in this list because the distinction it drew is the useful part — a gap recorded as "not decided, just undone" is one the next reader may close without reopening an argument.

### 5. The review-tool selection rules are complete

The original follow-up list carried "review tool probe + attribute rules" as unfinished. It is not: `20` refuses to pin a model id and resolves one at use time by role, and gives the two paths separate jobs on separate quotas so exhausting one does not make the other absorb both.

*Reason it looked unfinished:* the fail-open contradiction that item recorded belonged to a tool-probe design — `cheapest`, `highest-effort`, `family` as computed attributes — that was rejected during planning and never built. The complaint outlived the thing it was about.

## Consequence

Anything in this list that gets reopened should be reopened with new evidence, not with the observation that it is missing. That it is missing is the record.
