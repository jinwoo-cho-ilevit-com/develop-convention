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

### 2. The runner does not implement `lanes`, `sequential_owner`, `integration` or `checkpoints`

`18` defines all four. The runner refuses a contract carrying any of them, and names the field.

*Reason:* refusing is louder than ignoring. An author who writes `sequential_owner` believes it is enforced; a runner that accepts and ignores it leaves that belief intact and unfounded. The parallel-lane machinery is real work with its own contract, and until it exists the honest answer to a lane field is no.

*Alternative rejected:* accepting them inertly, which is what the withdrawn first runner did and is the shape of six of its seven blockers.

### 3. `review_rounds` is not in the manifest

`19 §4` names it alongside `created_at` and `verify_runs[].at`, both of which the runner now records.

*Reason:* the count belongs to a review subcommand this runner does not have. A field the tool cannot derive would be filled by hand, and a hand-filled provenance field is the thing `19` exists to replace.

### 4. `created_at` is the render timestamp, not the creation timestamp

Disclosed in `19 §6` rather than fixed.

*Reason:* every render rewrites `manifest.json` whole. Making it a creation time needs the value to survive a render, which is the same run-log mechanism `verify_runs` now uses — so this is cheap to fix and simply was not in scope. It is a defect, not a decision, and is recorded here so the next reader knows which.

### 5. The review-tool selection rules are complete

The original follow-up list carried "review tool probe + attribute rules" as unfinished. It is not: `20` refuses to pin a model id and resolves one at use time by role, and gives the two paths separate jobs on separate quotas so exhausting one does not make the other absorb both.

*Reason it looked unfinished:* the fail-open contradiction that item recorded belonged to a tool-probe design — `cheapest`, `highest-effort`, `family` as computed attributes — that was rejected during planning and never built. The complaint outlived the thing it was about.

## Consequence

Anything in this list that gets reopened should be reopened with new evidence, not with the observation that it is missing. That it is missing is the record.
