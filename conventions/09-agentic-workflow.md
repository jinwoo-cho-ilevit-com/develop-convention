# 09. AI Agent Parallel Development Workflow

## Core Rules

- Keep CLAUDE.md/AGENTS.md concise. A bloated instruction file causes rules to be ignored. For each line, ask "would removing this cause the agent to make a mistake?" — if not, delete it.
- Layer module-specific instructions into that directory's AGENTS.md (closest wins). Split out occasionally-needed knowledge into Skills.
- Before running parallel work, build a decomposition table (Task | Owner | Files | Dependencies | Integration point). Tasks with overlapping file ownership are not allowed to run in parallel — run them sequentially.
- For parallelization, prioritize workflows/subagent orchestration first. git worktree is a file isolation mechanism, not a coordination mechanism — use it to isolate multiple agents into independent branches/environments. Tasks with overlapping file ownership still leave merge conflicts even with worktree, so run them sequentially.
- Freeze shared interfaces/schemas during parallel execution. Only a single owner modifies lock files and migrations.
- Merge each work branch only after its tests pass, and run one integration verification pass after merging.
- Every agent must go through a review separated from the author after development is complete. Choose the review tool (Codex plugin vs. cursor CLI) before development starts and record it in the decomposition table. Claim completion only with execution evidence.
- Scale review lanes to change risk: a change spanning 2+ modules or touching an interface/schema gets three parallel lanes, each defined by its input — module (diff + changed files), project (diff + callers/callees + convention docs), critic (requirement/plan + diff, hunting for what the diff omits); anything smaller gets one lane. Add a security lane (diff + trust boundaries + input-validation points) only when auth, secrets, or external input is touched.
- Parallel lanes are independent — no lane sees another's output — and the dispatching orchestrator must fan them back in: confirm every lane answered, dedupe by `file:line`, resolve conflicting advice, verify each finding against the code, and rank by severity. Unsynthesized parallel output is noise, not a review.
- A review terminates on evidence, not on output: confirmed blocker-severity findings are fixed and re-reviewed by the lane that raised them, and the remainder is reported with the completion evidence. Producing a findings list is not completing a review.
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

- **Decomposition table first**: before execution, build a table of Task | Owner (subagent/team) | Main files | Dependencies | Integration point | Review lanes | Review tool. If two tasks' file lists overlap, they run sequentially, not in parallel — worktree does not resolve merge conflicts either (it only isolates live writes). This is a hard constraint.
- **Freeze shared contracts**: fix API signatures, data schemas, and architecture decisions in a document before parallel execution starts, and do not change them during execution. Agents only read them at the start. If the design changes mid-way, stop everything, update the contract, and restart (to prevent context drift).
- **Sole-owned resources**: only a single owner modifies lock files (uv.lock, etc.) and DB migrations. Migrations always run sequentially.
- **Isolation hygiene**: when using worktree, supply secrets to each worktree via runtime injection (do not copy plaintext `.env` files → [13-secret-management.md](13-secret-management.md)). Keep ports and dependency directories independent.
- **Integration**: each branch requires passing lint + tests as a merge precondition. Run one full integration smoke (test) after merge.
- **Know the boundaries**: adding more agents/worktrees doesn't automatically make things faster — without isolation, scoping, and verification, merge/review cost offsets the gains from parallelism. Confirm this empirically (→ the METR case in [00-principles.md](00-principles.md)).

Sources: [Claude Code — run agents in parallel](https://code.claude.com/docs/en/agents), [subagents](https://code.claude.com/docs/en/sub-agents), [agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees)

### 3. Verification Gates

- **Author ≠ verifier**: the review agent starts from the diff and the criteria, and never receives the reasoning behind the authoring process (it causes anchoring). Reference context the reviewer needs to judge the diff — callers, schemas, convention docs — is fair game; the author's chain of thought is not. Explicitly instruct the reviewer to "flag only correctness/requirement gaps" — if you only ask it to find gaps, it will manufacture issues even in sound code, causing over-engineering.
- **Provide runnable checks**: give the agent verification it can run itself (tests, builds, smoke tests). Without this, "looks right" becomes the only signal, and the human becomes the verification loop.
- **Evidence-based completion**: a completion report must include the commands run and their output. The evidence is actual tool execution results, not produced prose (→ [06-testing-verification.md](06-testing-verification.md)).
- **Check doc-code synchronization**: projects that have adopted docsync document tracking should include "code change ↔ doc update alignment" (whether the managed docs for the changed module were updated together) as a review item (→ [15-doc-tracking.md](15-doc-tracking.md)).
- Attach a deterministic gate (a Stop hook that blocks exit until a verification script passes) to unattended runs.
- **A post-development review is mandatory, and the review tool must be chosen before development starts and recorded in the decomposition table (§2).** Pick from the two paths below: a single-lane review uses one of them, and a multi-lane review mixes both so that not every lane shares a vendor.

**Parallel review lanes**: how many reviews to run and what each one reads is decided before the tool choice below.

A lane is defined by its **input**, not by its attitude. Telling three reviewers to "be critical" over the same input yields three copies of the same findings — the value of parallelism comes from context isolation, which is wasted when the contexts are identical.

| Lane | Input | Looks for |
|---|---|---|
| Module | diff + changed files only | correctness, edge cases, error handling, missing tests |
| Project | diff + callers/callees + convention docs | duplicate implementations, layer violations, contract drift, doc-code sync, naming/structure consistency |
| Critic | **requirement/plan + diff** | negative space — whether the stated problem was actually solved, and what is absent from the diff (rollback path, failure modes, observability) |
| Security *(conditional)* | diff + trust boundaries + input-validation points + [13-secret-management.md](13-secret-management.md) | unvalidated external input, secret handling, authorization gaps on newly reachable paths |

- **The Critic lane's job is absence.** Scope it to what is missing, not to re-reading the changed lines; otherwise it degrades into a second Module lane. It also needs a stated requirement to measure absence against — when the work carried no written plan (§6 permits that for lightweight iteration), write the task statement down before dispatching.
- **Lanes stay independent**: no lane receives another lane's output, and none receives the author's reasoning (the anchoring rule above applies per lane).
- **Fan-out requires fan-in**, and the orchestrator that dispatched the lanes owns the merge. (0) Confirm every dispatched lane actually answered — zero findings is a valid result, a lane that died is not, so re-run it instead of merging a short review. (1) Dedupe by `file:line`. (2) Resolve contradictory advice (one lane says "extract", another says "inline") into a single recommendation, weighting the lane whose input covers the disputed ground — structure and duplication belong to the project lane, edge cases to the module lane. (3) Check each finding against the actual code and mark it confirmed or unverified. (4) Rank by severity. Step 3 matters most: the "reviewers manufacture issues" failure mode above is amplified once per lane, so an unfiltered merge hands the noise to the human. The merge may downgrade a finding but never silently drops one — unverified findings are reported as unverified.
- **Diversify the vendor, not the persona**: run at least one lane on a different vendor's model (Path B below) — the module lane by default, since its input is just the diff and carries across tools cleanly. Personas layered on one model share that model's blind spots. Where only one vendor is available, note it in the review report rather than dropping a lane.

**Path A — Official Codex plugin (inside Claude Code)**: the review runs inside the development session.

- When you turn on the Stop review gate (`/codex:setup --enable-review-gate`), an automatic `ALLOW`/`BLOCK` review runs at the end of every turn that changed code. The review model is whatever default model is configured in the Codex CLI (`model` in `~/.codex/config.toml`).
- After work is complete, run `/codex:review` (standard) and, if needed, `/codex:adversarial-review` (design-adversarial). The plugin returns the review verbatim and **does not auto-fix**, so the orchestrator (the main session) reads the review and applies it. If "parallel review synthesis" is needed, the main session fans out multiple reviews (standard + adversarial, or multiple subagents) and synthesizes them — the plugin itself runs only a single review.

**Path B — cursor CLI (external tool)**: cross-verify with a different vendor's model.

- Deep reasoning: `cursor-agent -p --mode ask --model gpt-5.3-codex-xhigh --output-format text "<review prompt for the change diff>"` — `--mode ask` (or `--plan`) forces read-only mode (both allow analysis/read commands but block edits). Reasoning effort is encoded in the model id suffix `-xhigh`, not a separate flag.
- Fast and cheap: `--model composer-2.5` (no effort variants). **Use `gpt-5.3-codex-xhigh` when depth is needed, and `composer-2.5` when speed/cost take priority.**
- Always run reviews in read-only mode (`--mode ask`/`--plan`). Never use `-p` alone, since it opens up writes and shell access, letting the reviewer modify what it's inspecting. The orchestrator applies the results.

Sources: [Anthropic — Claude Code best practices](https://code.claude.com/docs/en/best-practices), [Cursor — headless CLI](https://cursor.com/docs/cli/headless)

### 4. Using Research Tools

- Check current documentation with context7 before using a library/SDK. Do not write APIs from training-data memory.
- For model/dataset-related work, query the actual registry with HuggingFace tools (hub lookup, hf-cli).
- Before choosing a methodology, check its current maintenance status and alternatives with web search (→ [00-principles.md](00-principles.md)).

### 5. Model Routing

| Task difficulty | Model |
|---|---|
| Lookups, simple reads, mechanical edits | Lightweight (haiku-class) |
| Standard implementation, single-domain refactoring, routine review | Mid-tier (sonnet-class) |
| Architecture, multi-system reasoning, deep debugging, security | Top-tier (opus-class) |

Default to the mid-tier model, and escalate only when there's evidence of difficulty.

### 6. Spec Gating (Optional)

Spec-driven development (GitHub Spec Kit, Kiro, etc.) is not a cure-all. In an empirically measured case, a heavyweight spec pipeline for a small feature produced roughly a 10x time overhead compared to iterative prompting.

- **When to go heavy**: when the spec is an asset shared across multiple PRs/services/workers — that's when the cost of writing the spec pays off. The shared contract in parallel worktree decomposition (§2) is exactly this case.
- **When to go light**: small fixes, exploratory work, prototypes — lightweight iteration (plan → execute → verify) is enough.
- Decide in advance, at the project level, the criteria for whether to fix the spec or the code when a bug is found (to prevent spec-code drift).

Sources: [GitHub — spec-driven development](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/), [Spec Kit empirical critique (Scott Logic)](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html)
