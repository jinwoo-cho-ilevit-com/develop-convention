---
description: Interview the user until the work is specific enough to split into parallel lanes, then write PLAN.md and the lane briefs
argument-hint: '<what you want to build>'
---

Specify: $ARGUMENTS

Interview first, plan mode second. Sections 1 and 2 run in the ordinary session; call `EnterPlanMode` only once the axes are settled, present the plan there, and write section 3's files after `ExitPlanMode` is approved. Plan mode refuses every write, `.plans/` included, so a plan drafted inside it cannot land — and the interview does not need that block, because this plugin's own hook already holds the main session to reading and asking.

The hook does not hold subagents: anything carrying an `agent_id` goes through. Interview with read-only agents only, and dispatch nothing that writes until the plan is approved. That is a norm rather than a boundary (→ `${CLAUDE_PLUGIN_ROOT}/conventions/21-development-loop.md` §3).

The user decides when the interview is over, not you.

The conventions this command refers to are in `${CLAUDE_PLUGIN_ROOT}/conventions/`. Read them from there — the project you are working in does not have a copy.

## 1. Derive the axes

What to ask about comes from this project, never from a fixed checklist. A checklist can only cover what someone already knew to list.

1. **Infer.** Read what the user gave you and, if the repository exists, what is actually in it — dependencies, directory layout, CI, data paths. From that, infer what decisions will shape this work. An axis is a hypothesis about where to look, not a factual claim, so prior knowledge is the right tool here (→ `${CLAUDE_PLUGIN_ROOT}/conventions/16-research-protocol.md`).
2. **Check for what you missed.** One narrow research pass, and its question is not "what is the answer" but "what has recently become standard that is absent from my list". Practices newer than your training data do not surface any other way.
3. **Filter by failure.** For each candidate ask whether this project could plausibly fail because of it. Keep what survives. A CLI tool produces no design-failure scenario, so no design axis appears; an ML pipeline produces an evaluation one, so it does.

Show the list and take additions and removals before the first question.

**The list is never locked.** When an answer reveals an axis you did not have, add it and say so. A greenfield project has no repository to ground step 1, and the growing list is what absorbs that.

## 2. Interview

One question at a time. For each:

- **Explore instead of asking** anything the codebase or the docs can answer.
- **Research the answer, do not recall it.** Every proposal must trace to a source fetched during this session; mark what you cannot find as unverified rather than filling it in (→ 16). Search in two hops — the first harvests current vocabulary from the ecosystem, the project's own lockfile, and official registries; the rest query with the harvested terms. Queries built from memory miss the current standard wholesale wherever names have changed.
- **When the options diverge, explain the difference before recommending.** State what each choice costs, not just what it does.
- If the user cannot answer, say what you would choose and why, and record it as an assumption with the cost of being wrong.

## 3. Write the artifacts

After `ExitPlanMode` is approved — not before, because plan mode blocks these writes — write `.plans/<feature>/`:

**`PLAN.md`** — decisions and their reasoning, rejected alternatives with why, the axis table (`decided` / `not applicable` / `open` — this is the only coverage record, so it is where "what we never asked" stays visible), the boundary table, the lane table, and the whole-project completion condition (every lane plus end-to-end).

**`lane-<name>.md`** per lane — scope, owned files, completion criteria, out of scope.

Split as far as file ownership allows. `owns` entries are directory prefixes or individually named files, never globs — a glob is expanded against the files that exist now and misses the ones the work is about to create. Lock files, migrations and generated files get a single owner. Files belonging to no directory (README, config at the root) go to an integration lane that runs last (→ `${CLAUDE_PLUGIN_ROOT}/conventions/18-work-contract.md`).

List every boundary between lanes with the contract test that will pin it. Those test files belong to no lane and are written before fan-out, which is what freezes the interface — `/dev-harness:build` dispatches a single agent to write them all, so an object reaching two boundaries gets one definition instead of two (→ `${CLAUDE_PLUGIN_ROOT}/conventions/06-testing-verification.md`).

Decide here, not at freeze time, which objects cross more than one boundary: give those rows the same `sample` value. One file listed twice is what the two contracts both load, and `build.js` checks each row's path and finds it. Two paths for one object is the shape that cannot be fixed later — the freeze cannot merge them without leaving a path the existence check refuses the build over, and if it does not merge them the object has two definitions that no test compares.

Write the boundary table with these exact keys, because `build.js` reads them and a boundary spelled another way silently drops that lane from three review lenses to one:

```markdown
| name | lanes | test | sample |
|---|---|---|---|
| parser-validator | lane-a, lane-b | tests/contract/test_parser_validator.py | tests/fixtures/parser_out.sample.json |
```

Mark a lane `security: true` in the lane table when it touches auth, secrets, or input the project did not produce; that adds a security review lens (→ `${CLAUDE_PLUGIN_ROOT}/conventions/20-review-gate.md`).

Write each completion criterion as a sentence paired with the command that checks it:

```markdown
## Completion criteria

- Rows with an empty required field SHALL be dropped with a warning
  → uv run pytest tests/unit/parser/test_empty.py
- The parser→validator boundary holds
  → uv run pytest tests/contract/test_parser_validator.py
- [human] The warning text is actionable for an operator
  → verdict: ____  by: ____  at: ____

## Out of scope
- Normalisation rules (lane-b owns them)
```

The sentence is not decoration. Without it nothing can be judged against the criterion, and a test that checks the wrong thing still passes (→ 18, `${CLAUDE_PLUGIN_ROOT}/conventions/20-review-gate.md`).

Then tell the user that `/dev-harness:build` runs it.
