---
description: Interview the user until the work is specific enough to split into parallel lanes, then write PLAN.md and the lane briefs
argument-hint: '<what you want to build>'
---

Specify: $ARGUMENTS

Interview first, plan mode second. Sections 1 and 2 run in the ordinary session; call `EnterPlanMode` only once the axes are settled, present the plan there, and write section 3's files after `ExitPlanMode` is approved. Plan mode refuses every write, `.plans/` included, so a plan drafted inside it cannot land — and the interview does not need that block, because sections 1 and 2 do nothing but read and ask.

Nothing mechanical stops a write during the interview: the hook meters reads rather than edits, and anything carrying an `agent_id` is exempt from even that. Interview with read-only agents only, and dispatch nothing that writes until the plan is approved. That is a norm rather than a boundary (→ `${CLAUDE_PLUGIN_ROOT}/conventions/21-development-loop.md` §3).

The user decides when the interview is over, not you.

The conventions this command refers to are in `${CLAUDE_PLUGIN_ROOT}/conventions/`. Read them from there — the project you are working in does not have a copy.

## 1. Derive the axes

What to ask about comes from this project, never from a fixed checklist. A checklist can only cover what someone already knew to list.

1. **Infer.** Read what the user gave you and, if the repository exists, what is actually in it — dependencies, directory layout, CI, data paths. From that, infer what decisions will shape this work. An axis is a hypothesis about where to look, not a factual claim, so prior knowledge is the right tool here (→ `${CLAUDE_PLUGIN_ROOT}/conventions/16-research-protocol.md`).
2. **Check for what you missed.** One narrow research pass, and its question is not "what is the answer" but "what has recently become standard that is absent from my list". Practices newer than your training data do not surface any other way.
3. **Filter by failure.** For each candidate ask whether this project could plausibly fail because of it. Keep what survives. A CLI tool produces no design-failure scenario, so no design axis appears; an ML pipeline produces an evaluation one, so it does.

Show the list and take additions and removals before the first question.

**The list is never locked.** When an answer reveals an axis you did not have, add it and say so.

**A greenfield project has no repository to ground step 1.** Derive the axes from the request alone — what is being built, how it runs, who uses it, what it stores — and open by proposing that list, each entry with the way it could sink the project. Propose rather than ask: a proposed list gives the user something to correct, where "what should we consider?" hands the blank page back. The interview then grows the list, which is what absorbs the weaker start.

## 2. Interview

One question at a time. For each:

- **Explore instead of asking** anything the codebase or the docs can answer.
- **Research the answer, do not recall it.** Every proposal must trace to a source fetched during this session; mark what you cannot find as unverified rather than filling it in (→ 16). Search in two hops — the first harvests current vocabulary from the ecosystem, the project's own lockfile, and official registries; the rest query with the harvested terms. Queries built from memory miss the current standard wholesale wherever names have changed.
- **Ask and recommend in plain language.** "Axis", "lane", "boundary", "freeze", "EARS" name the artifact section 3 writes, not words to say to the user. Translate before speaking — reach for the term only once it lands in `PLAN.md`.
- **When the options diverge, explain the difference before recommending — in terms of this project, not the framework's.** State what each choice costs in a scenario the user can picture, not in the vocabulary of the tradeoff itself.
- **Change the angle per axis.** Running every axis through the same "pick A or B, here's the cost" shape reads as one question asked twice. Frame each from what actually differs about it — a failure scenario for one, a user-visible difference for another, a cost-if-wrong for a third.
- If the user cannot answer, say what you would choose and why, and record it as an assumption with the cost of being wrong.

Settle the done level in the interview (→ 18 §3); it decides how deep the plan is challenged. The plan presented in plan mode carries the review points table 18 requires. Inside plan mode, before `ExitPlanMode`, run the plan lane with read-only agents at that depth (→ 20 §2) and fix what it finds in the plan text; every pre-approval row's exit is filled before the plan is shown. The plan and merged-whole points run a Claude reviewer lane alongside Codex in parallel rather than one tool (→ 20 §4). Ask for a cursor-agent tier only if Cursor has to substitute for Codex at the plan point, and record it in that row.

## 3. Write the artifacts

After `ExitPlanMode` is approved — not before, because plan mode blocks these writes — write `.plans/<feature>/`:

**`PLAN.md`** — the done level, decisions and their reasoning, rejected alternatives with why, the axis table (`decided` / `not applicable` / `open` — this is the only coverage record, so it is where "what we never asked" stays visible), the boundary table, the lane table, the review points table carried from section 2, and the end-to-end condition as `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md` §1 defines it. A lane brief never lists the whole boundary contract as a criterion — the other side is not in its worktree — but the lane producing a schema'd payload lists the check of its own fresh output against that schema (→ `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md`).

**`lane-<name>.md`** per lane — scope, owned files, completion criteria, out of scope.

Split as far as file ownership allows. `owns` entries are directory prefixes or individually named files, never globs (why: `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md`). Lock files, migrations and generated files get a single owner. Files belonging to no directory (README, config at the root) go to an integration lane that runs last (→ `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md`).

List every boundary between lanes with the contract file and sample that will pin it, and — where the payload lands as JSON, YAML or TOML — the schema. The contract file and schema live under `.plans/<feature>/contracts/`, so they share the plan's lifetime; the sample lives under `tests/fixtures/`. Rows sharing a `sample` share a `schema` too, and a row with a `schema` names its `producer` — the lane whose output the schema checks, one of that row's `lanes`. Which boundaries get a schema is set by `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md` §7; for the rest, leave the `schema` and `producer` cells blank and omit both keys from the workflow args, since an empty string is not a path. None of these files is a test, all of them belong to no lane, and all are written before fan-out, which is what freezes the interface — `/dev-harness:build` dispatches a single agent to write them all, so an object reaching two boundaries gets one definition instead of two (→ `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md`).

Decide here, not at freeze time, which objects cross more than one boundary, and give those rows the same `sample` value — one sample per object (→ `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md`). The freeze cannot repair two paths for one object: `build.js` checks every row's path exists, so merging them there leaves a path it refuses the build over.

Write the boundary table with these exact keys, because `build.js` reads them and a boundary spelled another way silently drops that lane from three review lenses to one:

```markdown
| name | lanes | contract | schema | producer | sample |
|---|---|---|---|---|---|
| parser-validator | lane-a, lane-b | .plans/ingest/contracts/parser-validator.md | .plans/ingest/contracts/parser_out.schema.json | lane-a | tests/fixtures/parser_out.sample.json |
```

The lane table uses these keys — `name`, `owns` and `security` are required and `build.js` refuses a plan whose lane omits one; `tier` (`light`/`mid`/`top`) and `effort` record the routing choice per lane (→ `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md`):

```markdown
| name | owns | security | tier | effort |
|---|---|---|---|---|
| lane-a | src/parser/, tests/parser/ | false | mid | medium |
| lane-b | src/auth/ | true | top | high |
```

`security` is `true` or `false`, never inferred from the paths. Declare `true` when the lane touches auth, secrets, or input the project did not produce; that adds a security review lens, and nothing else does (→ `${CLAUDE_PLUGIN_ROOT}/conventions/20-review-gate.md`).

Write each completion criterion as a sentence paired with the command that checks it:

```markdown
## Completion criteria

- Rows with an empty required field SHALL be dropped with a warning
  → uv run pytest tests/parser/test_sample_run.py::test_c01_drops_empty_rows
- The parser's output at the parser-validator boundary matches its schema (lane-a is its producer; command form per 06 §7)
  → rm -rf runs/sample && uv run python -m parser --limit 100 --dump runs/sample && uvx check-jsonschema@0.38.0 --schemafile .plans/ingest/contracts/parser_out.schema.json runs/sample/parser_out.json
- [human] The warning text is actionable for an operator
  → verdict: ____  by: ____  at: ____

## Out of scope
- Normalisation rules (lane-b owns them)
```

The sentence is not decoration. Without it nothing can be judged against the criterion, and a test that checks the wrong thing still passes (→ 18, `${CLAUDE_PLUGIN_ROOT}/conventions/20-review-gate.md`).

Then tell the user that `/dev-harness:build` runs it.
