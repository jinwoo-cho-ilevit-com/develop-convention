# 09. AI Agent Parallel Development Workflow

## Core Rules

- Keep CLAUDE.md/AGENTS.md concise. A bloated instruction file causes rules to be ignored. For each line, ask "would removing this cause the agent to make a mistake?" — if not, delete it.
- Layer module-specific instructions into that directory's AGENTS.md (closest wins). Split out occasionally-needed knowledge into Skills.
- The main session orchestrates and does not develop. It plans, splits, dispatches and judges; every edit goes to a subagent, and reading a large file there costs the same budget an edit would. The default shape is one worktree-isolated subagent per lane, fanning results back into the session that dispatched them (→ [21-development-loop.md](21-development-loop.md)). A hook can hold this mechanically: a subagent's tool call carries an `agent_id` and the main session's does not, which is the whole test.
- Before running parallel work, build a decomposition table (Task | Owner | Files | Dependencies | Integration point). Tasks with overlapping file ownership run sequentially, never in parallel.
- For parallelization, prioritize workflows/subagent orchestration first. git worktree is a file isolation mechanism, not a coordination mechanism — it isolates live writes and does not resolve merge conflicts, so it does not make overlapping tasks parallelizable. Agents that write concurrently need one each; agents that only read do not.
- Name the **channel** a subagent must report on, not only the shape of the report, and confirm it delivered. Where agents address each other by name, a turn's ordinary text output is not a delivery mechanism — reaching another agent takes an explicit send, so an agent that writes its findings and ends its turn has answered from its own side and said nothing from yours. A fan-in that counts agents as finished rather than as *answered with content* drops those silently.
- Freeze shared interfaces/schemas during parallel execution. Only a single owner modifies lock files and migrations.
- Merge each work branch only after its tests pass, and run one integration verification pass after merging. Every change then goes through a review its author did not perform (→ [20-review-gate.md](20-review-gate.md)).
- Route models to match task difficulty: mechanical work → lightweight model, standard implementation → mid-tier, architecture/deep debugging → top-tier model.
- Write heavyweight spec documents only when they are an asset shared across multiple PRs/workers. For small-scale or exploratory work, proceed with lightweight iteration.

## Details

### 1. Agent Instruction Files (CLAUDE.md / AGENTS.md)

AGENTS.md is an open standard (a "README for machines") jointly formalized in 2025 by OpenAI, Google, Cursor, and others, and is read natively by the major coding agents. Since Claude Code uses CLAUDE.md, the practical pattern is a generic AGENTS.md plus tool-specific files.

**Include**: build/test commands the agent cannot guess, code style that deviates from defaults, branch/PR rules, project-specific architecture decisions, environment quirks.
**Exclude**: content inferable from the code, standard conventions, detailed API documentation (replace with links), frequently-changing information, per-file descriptions, and obvious advice.

- **Conciseness is performance**: Anthropic's official warning — "a bloated CLAUDE.md causes real instructions to be ignored." Start at around 20-30 lines.
- **Layering**: the root file is the default, and subdirectory files override it (closest wins). Each file covers only the scope of its own directory.
- **Split into Skills**: knowledge that isn't always needed (e.g., procedures for specific tasks) belongs in an on-demand Skill, not in an always-loaded instruction file.

**Skill extraction criteria.** Move a passage out of an instruction file and into a skill when all three hold, and leave it in place otherwise:

1. It is needed for a minority of sessions. Something every session uses costs more to load on demand than to carry.
2. It is a *procedure* — steps with an order and a stopping point — rather than a standing rule. A rule has to be in force while work happens; a procedure is looked up when it starts.
3. It is longer than the instruction file can afford. A three-line rule stays; a page does not.

What remains behind is a pointer of one line, naming the skill and when to reach for it. A skill nothing points at is one nobody invokes.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices), [AGENTS.md standardization (InfoQ)](https://infoq.com/news/2025/08/agents-md/)

### 2. Parallel Development: Workflows First, Worktree for File Isolation

Parallelization has two layers — a **coordination layer** that splits and coordinates the work, and an **isolation layer** that prevents file-editing conflicts. Decide coordination first, and layer on isolation only when needed.

**Coordination: prioritize workflows/subagent orchestration.** Use Claude Code's coordination primitives as the default:

- **subagents**: one session spawns a worker and receives back only the result. The default for isolated task delegation — no worktree needed.
- **workflows**: scripts pipeline/fan out multiple subagents and cross-verify them. Suited to large-scale, repeated decomposition.
- **agent teams** (experimental): for when workers need to coordinate or debate via messages. There is no automatic isolation, so split files logically.
- **agent view**: for manually dispatching independent background sessions — each session is automatically assigned a worktree.

**Isolation: use worktree when independent branches are needed.** git worktree is a filesystem isolation mechanism, not a coordination mechanism. Use it when **assigning different files** to multiple agents to run on independent branches/environments; otherwise, a subagent sharing the same working tree is lighter weight. Tasks with overlapping file ownership still leave merge conflicts even with worktree (worktree only isolates live writes), so run them sequentially. worktree carries the cost of a fresh checkout and environment setup, and `.git`, plugins, and permission rules are shared. subagents can turn on isolation via the frontmatter `isolation: worktree`.

Standard pattern: **plan → define shared contracts → split along non-overlapping ownership boundaries → (for independent execution) worktree isolation → per-task tests → one integration verification pass after merge**

- **Decomposition table first**: before execution, build a table of Task | Owner (subagent/team) | Main files | Dependencies | Integration point. The ownership constraint is stated once in the Core Rules above and is a hard one; what the table adds is who and in what order.
- **Freeze shared contracts**: fix API signatures, data schemas, and architecture decisions in a document before parallel execution starts, and do not change them during execution. Agents only read them at the start. When the design changes mid-way, how much stops depends on what changed — [18-work-contract.md](18-work-contract.md) §4 gives the three cases, and only the breaking one restarts everything. A rule that restarts every lane over one added criterion is the rule that gets quietly ignored.
- **Sole-owned resources**: only a single owner modifies lock files (uv.lock, etc.) and DB migrations. Migrations always run sequentially.
- **Isolation hygiene**: when using worktree, supply secrets to each worktree via runtime injection (do not copy plaintext `.env` files → [13-secret-management.md](13-secret-management.md)). Keep ports and dependency directories independent.
- **Integration**: each branch requires passing lint + tests as a merge precondition. Run one full integration smoke (test) after merge.
- **Know the boundaries**: adding more agents/worktrees doesn't automatically make things faster — without isolation, scoping, and verification, merge/review cost offsets the gains from parallelism. Confirm this empirically (→ the METR case in [00-principles.md](00-principles.md)).
- **Say which channel the report travels on.** Between named agents, ordinary turn output does not reach the dispatcher; only an explicit send does, and Claude Code states this outright — "Your plain text output is NOT visible to other agents — to communicate, you MUST call this tool" ([SendMessage](https://code.claude.com/docs/en/agent-teams), as of 2026-08). Measured over one review of this repository: five dispatched lanes, every one of them ended its turn having written its findings as text, and every report arrived only after the orchestrator asked for it by name — five out of five, no exceptions. Specifying the report's shape is not specifying its delivery, and the gap between the two looks exactly like a lane with nothing to say.

Sources: [Claude Code — run agents in parallel](https://code.claude.com/docs/en/agents), [subagents](https://code.claude.com/docs/en/sub-agents), [agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees)

### 3. Model Routing

| Task difficulty | Model |
|---|---|
| Lookups, simple reads, mechanical edits | Lightweight (haiku-class) |
| Standard implementation, single-domain refactoring, routine review | Mid-tier (sonnet-class) |
| Architecture, multi-system reasoning, deep debugging, security | Top-tier (opus-class) |

Default to the mid-tier model, and escalate only when there's evidence of difficulty.

### 4. Spec Gating (Optional)

Spec-driven development (GitHub Spec Kit, Kiro, etc.) is not a cure-all. In an empirically measured case, a heavyweight spec pipeline for a small feature produced roughly a 10x time overhead compared to iterative prompting.

- **When to go heavy**: when the spec is an asset shared across multiple PRs/services/workers — that's when the cost of writing the spec pays off. The shared contract in parallel worktree decomposition (§2) is exactly this case.
- **When to go light**: small fixes, exploratory work, prototypes — lightweight iteration (plan → execute → verify) is enough.
- Decide in advance, at the project level, the criteria for whether to fix the spec or the code when a bug is found (to prevent spec-code drift).

Sources: [GitHub — spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), [Spec Kit empirical critique (Scott Logic)](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
