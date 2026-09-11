# 09. AI Agent Parallel Development Workflow

## Core Rules

- Keep CLAUDE.md/AGENTS.md concise. A bloated instruction file causes rules to be ignored. For each line, ask "would removing this cause the agent to make a mistake?" — if not, delete it.
- Layer module-specific instructions into that directory's AGENTS.md (closest wins), with a sibling CLAUDE.md importing it for Claude Code (§1). Split out occasionally-needed knowledge into Skills.
- **Instruction anti-patterns**: keep verification rituals ("double-check your work"), thoroughness boosters ("be maximally thorough"), mandatory procedures or scratchpad scaffolds that duplicate native reasoning, stale examples showing long reasoning chains, contradictory rules, and dated configuration such as manual thinking budgets out of instruction files and prompts — these were written for older models and cost tokens on current ones without adding capability.
- The main session orchestrates and does not develop. It plans, splits, dispatches and judges; every edit goes to a subagent, and reading a large file there costs the same budget an edit would. The default shape is one worktree-isolated subagent per lane, fanning results back into the session that dispatched them (→ [21-development-loop.md](21-development-loop.md)). A hook can tell the two apart mechanically — a subagent's tool call carries an `agent_id` and the main session's does not — which is enough to meter what the main session reads. Where it writes is convention: gating that costs a prompt on every edit and still cannot be judged exactly (→ [21-development-loop.md](21-development-loop.md) §3).
- Before running parallel work, build a decomposition table (Task | Owner | Files | Dependencies | Integration point). Tasks with overlapping file ownership run sequentially, never in parallel.
- For parallelization, prioritize workflows/subagent orchestration first. git worktree is a file isolation mechanism, not a coordination mechanism — it isolates live writes and does not resolve merge conflicts, so it does not make overlapping tasks parallelizable. Agents that write concurrently need one each; agents that only read do not.
- Name the **channel** a subagent must report on, not only the shape of the report, and confirm it delivered. Where agents address each other by name, a turn's ordinary text output is not a delivery mechanism — reaching another agent takes an explicit send, so an agent that writes its findings and ends its turn has answered from its own side and said nothing from yours. A fan-in that counts agents as finished rather than as *answered with content* drops those silently.
- Freeze shared interfaces/schemas during parallel execution. Only a single owner modifies lock files and migrations.
- Merge each work branch only after its completion criteria ([18-work-contract.md](18-work-contract.md), checked as [06-testing-verification.md](06-testing-verification.md) sets out) and the checks CI enforces (lint, run locally by pre-commit on a branch CI does not see; → [03-environment.md](03-environment.md)) pass, and after a review its author did not perform has ended with no open blocker (→ [20-review-gate.md](20-review-gate.md)). Run the integration runs — one to three per project — on the merged head after the last merge (→ [18-work-contract.md](18-work-contract.md) §1).
- A merged lane is a closed lane: once the integration runs are green, remove its worktree and delete its branch — `git worktree remove` without `--force` and `git branch -d`, never `-D`, because both refusals are safety signals, not obstacles. A halted lane keeps both; its worktree is where the fix round resumes. A branch that survives its merge reads as unfinished work to the next session.
- Route on two axes, model tier and effort, not tier alone: a stronger model at lower effort can be both cheaper and better than a weaker model pushed to high effort, so the tier ladder (mechanical → lightweight, standard → mid-tier, architecture/deep debugging → top-tier) does not by itself settle the choice. Choose effort per task alongside tier, and re-choose effort whenever the model changes rather than carrying the old setting over.
- Write heavyweight spec documents only when they are an asset shared across multiple PRs/workers. For small-scale or exploratory work, proceed with lightweight iteration.

## Details

### 1. Agent Instruction Files (CLAUDE.md / AGENTS.md)

AGENTS.md is an open standard (a "README for machines") jointly formalized in 2025 by OpenAI, Google, Cursor, and others, and is read natively by the major coding agents. Claude Code reads CLAUDE.md, not AGENTS.md, so a project keeps its instructions in AGENTS.md and gives Claude Code a CLAUDE.md whose first line is the import `@AGENTS.md`, loaded at session start; Claude-specific lines go below it. A symlink `CLAUDE.md → AGENTS.md` also works where nothing Claude-specific is needed, but not on Windows without Administrator rights or Developer Mode ([Claude Code — memory](https://code.claude.com/docs/en/memory), checked 2026-09-12).

**Include**: build/test commands the agent cannot guess, code style that deviates from defaults, branch/PR rules, project-specific architecture decisions, environment quirks.
**Exclude**: content inferable from the code, standard conventions, detailed API documentation (replace with links), frequently-changing information, per-file descriptions, and obvious advice.

- **Conciseness is performance**: Anthropic's official warning — "a bloated CLAUDE.md causes real instructions to be ignored." Start at around 20-30 lines.
- **Layering**: the root file is the default, and subdirectory files override it (closest wins). Each file covers only the scope of its own directory. Claude Code loads a subdirectory's CLAUDE.md only when it reads files there, and reads AGENTS.md only through a sibling CLAUDE.md that imports it ([15-doc-tracking.md](15-doc-tracking.md) §1).
- **Split into Skills**: knowledge that isn't always needed (e.g., procedures for specific tasks) belongs in an on-demand Skill, not in an always-loaded instruction file.
- **Instruction anti-patterns to strip out**, each written for a weaker or older model and now spending tokens on capability current models already have natively: verification rituals ("double-check your work") make the model re-narrate work it already checks internally; thoroughness boosters ("be maximally thorough") push toward over-exploration rather than a calibrated stop; mandatory procedures or scratchpad scaffolds duplicate reasoning the model performs natively without being told; stale examples that show long reasoning chains steer imitation of outdated verbosity rather than the current model's own reasoning; contradictory rules force the model to silently pick a winner instead of following the instruction; and dated configuration such as manual thinking budgets is superseded machinery (→ [11-llm-api-providers.md](11-llm-api-providers.md) for the `budget_tokens` deprecation). This is distinct from the fresh-context review lanes of [20-review-gate.md](20-review-gate.md): those are a separate review by a different agent, the opposite mechanism from an in-prompt "check your own work" instruction, and this rule does not remove them.

**Skill extraction criteria.** Move a passage out of an instruction file and into a skill when all three hold, and leave it in place otherwise:

1. It is needed for a minority of sessions. Something every session uses costs more to load on demand than to carry.
2. It is a *procedure* — steps with an order and a stopping point — rather than a standing rule. A rule has to be in force while work happens; a procedure is looked up when it starts.
3. It is longer than the instruction file can afford. A three-line rule stays; a page does not.

What remains behind is a pointer of one line, naming the skill and when to reach for it. A skill nothing points at is one nobody invokes.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices), [AGENTS.md standardization (InfoQ)](https://infoq.com/news/2025/08/agents-md/), [Anthropic — Reducing cost and improving performance with Claude Platform](https://claude.com/blog/reducing-cost-and-improving-performance-with-claude-platform)

### 2. Parallel Development: Workflows First, Worktree for File Isolation

Parallelization has two layers — a **coordination layer** that splits and coordinates the work, and an **isolation layer** that prevents file-editing conflicts. Decide coordination first, and layer on isolation only when needed.

**Coordination: prioritize workflows/subagent orchestration.** Use Claude Code's coordination primitives as the default:

- **subagents**: one session spawns a worker and receives back only the result. The default for isolated task delegation — no worktree needed.
- **workflows**: scripts pipeline/fan out multiple subagents and cross-verify them. Suited to large-scale, repeated decomposition.
- **agent teams** (experimental): for when workers need to coordinate or debate via messages. There is no automatic isolation, so split files logically.
- **agent view**: for manually dispatching independent background sessions — each session is automatically assigned a worktree.

**Isolation: use worktree when independent branches are needed.** git worktree is a filesystem isolation mechanism, not a coordination mechanism. Use it when **assigning different files** to multiple agents to run on independent branches/environments; otherwise, a subagent sharing the same working tree is lighter weight. Tasks with overlapping file ownership still leave merge conflicts even with worktree (worktree only isolates live writes), so run them sequentially. worktree carries the cost of a fresh checkout and environment setup, and `.git`, plugins, and permission rules are shared. subagents can turn on isolation via the frontmatter `isolation: worktree`.

Standard pattern: **plan → define shared contracts → split along non-overlapping ownership boundaries → (for independent execution) worktree isolation → per-task checks → the integration run after merge**

- **Decomposition table first**: before execution, build a table of Task | Owner (subagent/team) | Main files | Dependencies | Integration point. The ownership constraint is stated once in the Core Rules above and is a hard one; what the table adds is who and in what order.
- **Freeze shared contracts**: fix API signatures, data schemas, and architecture decisions in a document before parallel execution starts, and do not change them during execution. Agents only read them at the start. When the design changes mid-way, how much stops depends on what changed — [18-work-contract.md](18-work-contract.md) §4 gives the three cases, and only the breaking one restarts everything. A rule that restarts every lane over one added criterion is the rule that gets quietly ignored.
- **Sole-owned resources**: only a single owner modifies lock files (uv.lock, etc.) and DB migrations. Migrations always run sequentially.
- **Isolation hygiene**: when using worktree, supply secrets to each worktree via runtime injection (do not copy plaintext `.env` files → [13-secret-management.md](13-secret-management.md)). Keep ports and dependency directories independent.
- **Integration**: the merge precondition for each branch is its lane's completion criteria and the CI-enforced checks such as lint passing (→ [18-work-contract.md](18-work-contract.md), [03-environment.md](03-environment.md)), with its review closed on no blocker. Run one integration run — the assembled project's sample run — after merge.
- **Cleanup closes the lane**: after the integration run, remove each merged lane's worktree and delete its branch. `git worktree remove` refusing a dirty tree and `git branch -d` refusing an unmerged branch are the safety checks working — investigate, do not escalate to `--force`/`-D`. Halted lanes keep their worktrees: fix rounds continue in them.
- **Know the boundaries**: adding more agents/worktrees doesn't automatically make things faster — without isolation, scoping, and verification, merge/review cost offsets the gains from parallelism. Confirm this empirically (→ the METR case in [00-principles.md](00-principles.md)).
- **Say which channel the report travels on.** Between named agents, ordinary turn output does not reach the dispatcher; only an explicit send does, and Claude Code states this outright — "Your plain text output is NOT visible to other agents — to communicate, you MUST call this tool" ([SendMessage](https://code.claude.com/docs/en/agent-teams), as of 2026-08). An agent that writes its findings as text and ends its turn has delivered nothing until the orchestrator asks for it by name. Specifying the report's shape is not specifying its delivery, and the gap between the two looks exactly like a lane with nothing to say.

Sources: [Claude Code — run agents in parallel](https://code.claude.com/docs/en/agents), [subagents](https://code.claude.com/docs/en/sub-agents), [agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees)

### 3. Model Routing

| Task difficulty | Model | Default effort |
|---|---|---|
| Lookups, simple reads, mechanical edits | Lightweight (haiku-class) | Low |
| Standard implementation, single-domain refactoring, routine review | Mid-tier (sonnet-class) | Medium |
| Architecture, multi-system reasoning, deep debugging, security | Top-tier (opus-class) | High (or above) |

These are starting points, not a fixed mapping — effort moves independently of tier on evidence, not in lockstep with it.

Default to the mid-tier model at the effort level the table above recommends, and escalate — tier, effort, or both — only when there's evidence of difficulty. Step effort back down for routine or latency-sensitive work once evals show quality holds at the lower setting; effort chosen for one model does not transfer to another, so a model change is a reason to re-sweep effort rather than carry the old setting over. Anthropic's effort page describes the `low` level, in its description column, as "Most efficient. Significant token savings with some capability reduction."; its typical-use-case column names "Simpler tasks that need the best speed and lowest costs, such as subagents." For Claude Fable 5, "lower effort settings … still perform well and often exceed `xhigh` performance on prior models"; for Claude Opus 5, "if you carried effort settings over from an earlier model, run a fresh effort sweep on your evals rather than reusing them"; and setting `effort` to `"high"` is equivalent to omitting the parameter entirely.

Sources: [Anthropic — effort](https://platform.claude.com/docs/en/build-with-claude/effort)

### 4. Spec Gating (Optional)

Spec-driven development (GitHub Spec Kit, Kiro, etc.) is not a cure-all. One practitioner write-up reports a heavyweight spec pipeline for a small feature taking roughly ten times as long as iterative prompting — a single blog case, a lead rather than a measurement (unverified).

- **When to go heavy**: when the spec is an asset shared across multiple PRs/services/workers — that's when the cost of writing the spec pays off. The shared contract in parallel worktree decomposition (§2) is exactly this case.
- **When to go light**: small fixes, exploratory work, prototypes — lightweight iteration (plan → execute → verify) is enough.
- Decide in advance, at the project level, the criteria for whether to fix the spec or the code when a bug is found (to prevent spec-code drift).

Sources: [GitHub — spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), [Spec Kit critique (Scott Logic blog — lead, not a primary source)](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
