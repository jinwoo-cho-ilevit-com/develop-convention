# Development Conventions

A collection of development convention documents. Composed of general-purpose development rules plus AI/ML and LLM-specific rules, consumed by both humans and AI agents.

Each doc starts with `## Core Rules` (imperative rules excerptable into agent instruction files) followed by human-oriented details and sources. Every factual claim cites a source verified by research as of 2025-2026.

## Document Map

| Doc | Contents |
|---|---|
| [00-principles.md](conventions/00-principles.md) | Core principles: fresh start, fresh-context, evidence over claims, fact-based judgment, empirical measurement first |
| [01-structure-naming.md](conventions/01-structure-naming.md) | Module separation, structure-follows-design integration, flat layout, PEP 8 semantic naming, comment/emoji policy, dead code/duplication removal |
| [02-config.md](conventions/02-config.md) | No hardcoding, Hydra config groups + validation, ablation combinations, run snapshots |
| [03-environment.md](conventions/03-environment.md) | uv/ruff toolchain, local↔RunPod portability, device abstraction (CPU fallback) |
| [04-pipeline.md](conventions/04-pipeline.md) | Small-sample debugging, atomic save + resume, streaming, progress monitoring |
| [05-performance.md](conventions/05-performance.md) | Async/parallel selection, DataLoader tuning, GPU/RAM profiling, structured logging |
| [06-testing-verification.md](conventions/06-testing-verification.md) | Minimal-meaningful testing, golden files, tolerance bands, CPU smoke tests, completion verification |
| [07-ml-development.md](conventions/07-ml-development.md) | Seed/reproducibility, train-serve skew prevention, experiment tracking, checkpoints/spot pods |
| [08-llm-development.md](conventions/08-llm-development.md) | Training framework routing, FSDP2/bf16, chat template consistency, evaluation reproducibility, LLM-as-judge, data |
| [09-agentic-workflow.md](conventions/09-agentic-workflow.md) | How to write CLAUDE.md/AGENTS.md, workflows-first parallel development (worktree for file isolation only), decomposition and frozen contracts, model routing, spec gating |
| [10-llm-api-inference.md](conventions/10-llm-api-inference.md) | LLM API inference module: adapter structure, calls/rate limits, errors/retries, ensembles, caching/resume, cost/evaluation |
| [11-llm-api-providers.md](conventions/11-llm-api-providers.md) | Provider-specific considerations (OpenAI/Anthropic/Gemini/DeepSeek/OpenRouter) + structured output tiered fallback |
| [12-docs-reference.md](conventions/12-docs-reference.md) | Latest-docs reference procedure (4 tiers) + per-provider canonical URL registry + smoke-test confirmation |
| [13-secret-management.md](conventions/13-secret-management.md) | No hardcoding/committing secrets, central manager (Infisical) injection, reading env in code, container/CI machine identity, scanning/rotation |
| [14-context-management.md](conventions/14-context-management.md) | Minimizing main context (firewall/delegation), understanding compaction/clear behavior, preventing context loss via external files, CLAUDE.md, and auto memory |
| [15-doc-tracking.md](conventions/15-doc-tracking.md) | Doc-code synchronization: 4-tier tracking (contract·module·flow·history), docsync skill (incremental sync + audit), managed/human markers, blind rebuild·RMA verification, ADR supersession |
| [16-research-protocol.md](conventions/16-research-protocol.md) | Fact research protocol: prior knowledge is for queries only, every claim requires a source from this research, source tiers (official registry), verification of negative/universal claims, coverage·contradiction resolution |
| [17-commit-protocol.md](conventions/17-commit-protocol.md) | Commit protocol: Conventional Commits header (English type/scope) + Korean body (Why/What/How/Result), trailers, logical-unit splitting — git log doubles as a research note |
| [18-work-contract.md](conventions/18-work-contract.md) | Work contract: completion criteria (EARS/Given-When-Then + executable verify), lane ownership, done level (auto/reviewed/proven by size × reversibility), field triggers, changing a frozen contract |
| [19-evidence.md](conventions/19-evidence.md) | Evidence artifacts: criteria table instead of narrative, teed execution records with secret masking, provenance and timestamps, human verdict records, recorded bypasses |
| [20-review-gate.md](conventions/20-review-gate.md) | Review gate: author-is-not-verifier, lanes defined by input (module/project/absence/security), fan-in and severity, review tool paths without pinned model ids |

## How to Apply to a New Project

1. Copy [templates/AGENTS.md](templates/AGENTS.md), [templates/CLAUDE.md](templates/CLAUDE.md), and [templates/pyproject.toml](templates/pyproject.toml) into the new project — plus [templates/contract.md](templates/contract.md) if the project will use work contracts (→ [18-work-contract.md](conventions/18-work-contract.md)), and [templates/scripts/](templates/scripts/contract.py) with it to run those contracts mechanically — `lint`, `red`, `verify`, `human`, `status`, writing the evidence 19 specifies; the subset it enforces is [18 §4](conventions/18-work-contract.md) and what it records is [19 §6](conventions/19-evidence.md), and running a contract by hand instead remains legitimate — fill in the placeholders (`[...]`, `PROJECT_NAME`), then delete or uncomment the optional blocks (ML/LLM API/docsync) that don't apply. Projects that will use docsync doc tracking additionally copy [templates/skills/docsync/](templates/skills/docsync/SKILL.md) to `.claude/skills/docsync/` (→ [15-doc-tracking.md](conventions/15-doc-tracking.md)). The single source of truth for shared guidance is AGENTS.md (an open standard also read by Codex/Cursor and others), and CLAUDE.md imports it via `@AGENTS.md`. The whole step is automated by the [conv-init skill](templates/skills/conv-init/SKILL.md) — copy it to `.claude/skills/conv-init/` once, then bootstrap any project with a single command.
2. Keep instruction files concise — don't paste the entire document, only include the rules needed to prevent mistakes in that project (→ [09-agentic-workflow.md](conventions/09-agentic-workflow.md)). Reference the full conventions via the local path where this repo is cloned (fill it in at `[CONVENTION_PATH]` in the template).

### Tool-by-Tool Behavior

Prerequisite: clone this repo on each machine, and fill in its path at `[CONVENTION_PATH]` in the project's AGENTS.md.

| Tool | Behavior |
|---|---|
| Claude Code | Loads shared guidance via `CLAUDE.md` → `@AGENTS.md` import. Reads the needed convention doc directly by path during work. Add Claude-only instructions to CLAUDE.md only |
| Codex CLI | Reads `AGENTS.md` natively (root→current-directory chain, with a size cap — the excerpt + path-reference structure fits this). No extra setup needed |
| Cursor | Co-author of the AGENTS.md standard — reads it natively. Promote only the few rules that must always be enforced to `.cursor/rules/` if needed |
| Other (Gemini CLI, Windsurf, Aider, etc.) | Tools that read the AGENTS.md standard behave the same way. For unsupported tools only, add one line in that tool's instruction file pointing to AGENTS.md |

**Note for cloud-executed agents**: Local path references are only valid for local execution. In isolated sandboxes (Codex cloud, Cursor background agents, Claude Code web), either include this repo in the project as a git submodule, or make it self-contained by copying a rule summary into AGENTS.md. Switching to the submodule approach is recommended once cloud usage actually begins.

### How to Instruct the AI

Once the template is in the project, **no command is needed for everyday use** — AGENTS.md loads automatically and the rules apply. The cases below are the only ones that need an explicit command; when you want to make sure a specific doc applies, just refer to it by its number.

Bootstrapping a new project (one-time):
```
Copy AGENTS.md, CLAUDE.md, and pyproject.toml from <convention repo path>/templates/
into this project and fill in the placeholders. It's a [one-line description], [general/ML/LLM API] project.
Also copy contract.md if we'll use work contracts.
```

Enforcing a specific rule:
```
Build the preprocessing pipeline. Follow the Core Rules in conventions/04 (small-sample runs, resume).
Add a DeepSeek adapter. Follow the procedure in doc 12 — fetch the official docs first to confirm, then implement.
```

Review:
```
Review this diff against the conventions at <convention repo path>.
Flag violations with their doc number, using a separate review agent, not the authoring session.
```

Rewrite/refactor:
```
Rewrite this module. Per the principles in doc 00: don't be bound by the existing structure,
start from the spec, but lock in existing behavior with a characterization test before rewriting.
```

Updating conventions (when a stale fact is found):
```
I checked the official docs and the [X] content in doc 11 has changed. Update the convention and commit it.
```

## Full Rule Summary (for Agent Injection)

### Principles
- New development/refactoring starts from requirements and behavior (the spec), not from existing structure, comments, or memory.
- Don't judge from prior knowledge. Verify library/API/model facts as of the current time via context7, web search, or HuggingFace before applying them.
- Perform review/rewrites in a fresh context (a separate subagent/session), and claim completion only with execution evidence. Keep the author separate from the verifier.
- Lock in existing behavior with a characterization test before rewriting. Claim performance/productivity improvements only with empirical measurement.

### Structure & Naming
- Separate by module/feature, with clear input/output contracts. Keep files small and boundaries clear.
- Fit the structure to the design, not the design to the structure: when integrating a new module, restructuring the surrounding project is preferred over force-fitting — scoped to what the integration touches, behavior pinned by tests, structural moves in separate commits.
- App/research/pipeline code uses a flat layout (src/ is only for distributed libraries). Use uv workspaces for multiple packages.
- Semantic naming, PEP 8. No `_v2`/`_new` suffixes on code — rename in place; evaluation-pinned artifacts (prompts, golden sets) are the exception and version append-only. Delete dead code immediately, scan for duplicates before completion.
- Comments cover only constraints/intent the code can't express — no insider-only context, no TMI, no explaining the obvious. Cap a comment block at three lines, an inline comment at one.
- **Edit by rewrite, not by append.** Once a comment block or document section has grown past about half again its size, rewrite it instead of extending it. Comments and documents describe the current state only — change history lives in git and ADRs. Before adding a rule, find where it already lives; replace the second copy with a reference.
- Minimize emoji in docs, and use none at all in code comments: allow one only where the symbol is the data (a defined legend), never as decoration on headings or bullets. Write status as words (`OK`/`FAILED`/`TODO`) so it stays greppable.

### Config
- Absolutely no hardcoding — paths/hyperparameters/constants all live in central config. Compose them with Hydra config groups and fail-fast with type validation.
- Do ablations via config combinations only, without code changes. Every run saves its resolved config + git hash to the output directory.

### Environment
- uv (commit uv.lock) + ruff + pre-commit/CI. Dev tools go in `[dependency-groups]`.
- Runs identically on local (macOS/CPU/MPS) and RunPod (Linux/CUDA) without modification — via uv platform markers or `--torch-backend=auto`.
- Select the device only through a single helper (based on `torch.accelerator`) — no inline `.cuda()`. Must be runnable and testable on CPU when no GPU is available.

### Pipeline
- Every stage supports a `--limit N` small-sample run + input/output dump. Do a small-sample dry-run before the full run.
- Save intermediate results per chunk + resume (skip completed portions). Save atomically via temp→`os.replace`. Stream large volumes — no loading everything into memory.
- Long-running tasks show tqdm/rich progress + log processing throughput.

### Performance
- CPU-bound → multiprocessing, IO-bound → asyncio. Identify bottlenecks with profiling first.
- Log per-stage GPU utilization/VRAM/RAM/CPU + throughput as structured (JSON) logs.

### Testing & Verification
- Three layers: unit tests for non-trivial logic, one contract test per module boundary, and 1-3 end-to-end smoke tests through the project's real entry point. Only the third catches integration failures.
- An end-to-end test enters where a user or CI enters, mocks no module of your own, runs on a small sample, and follows the real sequence of stateful commands — testing commands in isolation hides defects in their order.
- Justify each test: is there a realistic change that would break it, does another test already catch it, could it ever fail? A test that has never failed is a deletion candidate.
- Cover every completion criterion with an executable check, but not one test per criterion — criteria coverage must reach 100%; line coverage is a different measure and is not the target.
- Observe every new test failing at the base commit before it passes, and keep that output. Separate "the check could not run" (missing baseline) from "the check ran and failed"; a missing test path also exits non-zero, so conflating them makes writing no test look like a passing check. Standing invariants are exempt and marked as such.
- Every fixed bug gains exactly one regression test. Assert ML metrics with a tolerance band; update golden files only via an explicit flag. CI smoke-tests GPU paths on CPU with small samples. TODOs/stubs/skips are blockers, not completion.

### AI/ML
- Set seeds through a single unified helper. Training/inference import the same preprocessing function (no duplication); verify skew with sample replay.
- Every run is logged to an experiment-tracking tool along with its config + commit. Save last-N + best + milestone checkpoints to a network volume/HF Hub. Design training to assume interruption (resumable).

### LLM
- Route frameworks by use case (single GPU → Unsloth/TRL, multi-GPU reproducibility → Axolotl, RL → TRL+vLLM, pretraining → torchtitan). torchtune is prohibited (deprecated). FSDP2 + bf16 by default.
- Chat templates use `apply_chat_template` as the single source; golden-test string identity between training and inference; specify sampling parameters explicitly in config.
- Evaluation records even the harness/task version, fewshot count, and whether a template was applied. Judges use bidirectional ordering + cross-family + length-aware rubrics.

### LLM API Inference
- Provider abstraction is a thin native SDK adapter + a pure payload builder (testable without network access). "OpenAI-compatible" covers only the wire format — capability/schema/error/token mapping is isolated per provider.
- Cap concurrency per model + adaptively control it based on rate-limit headers. Classify errors as typed exceptions, keep a single owner for retries, and retry ensembles per member. Log failed tasks as error rows and keep the batch running.
- Structured output uses a lowest-common-denominator schema + tiered fallback (native schema → json_object+prompt → parsing → validate-and-retry, capped at 2-3 attempts). Classify `finish_reason` before parsing. No sampling parameters on reasoning calls.
- Response caching is dev/debug-only. Resume must verify a fingerprint (spec+seed+data+prompt). No hardcoding prices/model names — pin dated snapshots, log tokens+cost per row, and cap the budget.
- Before writing provider API code, fetch and check the official docs from the canonical URL registry. For SDK usage, prefer the provider's official skill over ctx7; for exceptions/signatures, use the installed SDK source; confirm behavior not in the docs with an empirical smoke test.

### Agentic Workflow
- Keep CLAUDE.md/AGENTS.md concise (bloat causes rules to be ignored), layer them per module, and put occasionally-used knowledge into Skills.
- Prefer workflows/subagent orchestration for parallelization. Git worktree is a file-isolation mechanism, so introduce it only when overlapping file edits would conflict. Write a breakdown table (owner, files, dependencies, integration) before starting; freeze shared contracts during execution; assign locks/migrations to a single owner.
- Merge each branch only after its tests pass, then do one integration verification pass. Route models by difficulty (mechanical → lightweight, standard → mid-tier, architecture → top-tier).
- Write heavyweight spec documents only when they are an asset shared across PRs or workers; small or exploratory work uses lightweight iteration.

### Review Gate
- Every change goes through a review its author did not perform, on a tool chosen before development starts. The reviewer gets the diff and the criteria, never the author's reasoning.
- Scale lanes to risk: a 2+ module or interface/schema change gets three lanes defined by their input — module (diff + changed files), project (diff + callers + convention docs), absence (requirement + diff, hunting for what is missing); anything smaller gets one. Add a security lane only when auth, secrets, or external input is touched.
- Fan-out requires fan-in, owned by the dispatching orchestrator: confirm every lane answered, dedupe by `file:line`, resolve contradictions, verify each finding against the code, rank by severity. An unsynthesized merge amplifies manufactured issues once per lane.
- Severity carries an action: blocker blocks the merge and is re-reviewed by the lane that raised it, major is fixed in the same work, minor becomes a follow-up, nit may be ignored. A finding with no concrete failing scenario is a nit.
- Lanes never switch branches in a shared worktree — one checkout erases every other lane's subject. A finding that depends on a tool's behaviour names the version tested, and it must be the version the project pins.
- Run at least one lane on a different vendor's family, and don't pin model ids in the docs — resolve them at use time and pick by role. A gate that passes is not evidence the gate works; confirm once that it fails when it should.

### Secret Management
- Never hardcode secrets in code, config, logs, or images; never commit a plaintext `.env` (`.gitignore` + `.env.example` lists keys only). The single source of truth is a central secret manager (Infisical recommended).
- Supply secrets to local, CI, and container environments alike via runtime injection (`infisical run -- <cmd>`), with no plaintext left on disk. Code reads them as env vars as usual (`os.environ[...]`). Coding agents follow the same rule.
- Containers/CI authenticate via machine identity (Universal Auth) with least privilege and short-lived tokens. Separate environments (dev/staging/prod) + rotate + scan with gitleaks (pre-commit/CI). Immediately rotate and reissue any secret that was already committed.

### Doc Tracking
- Docs are split into 4 tiers: for input/output contracts, code is the single source (no hand-written docs); module logic goes in a per-directory AGENTS.md; overall flow goes in ARCHITECTURE.md + Mermaid (generate dependency graphs with a deterministic tool); decision history uses structured commits + append-only ADRs (supersede instead of editing, record reversed decisions/rollbacks too, and reference only currently valid decisions).
- Agents regenerate only inside `docsync:managed` markers (human sections are off-limits, stamped with a verification commit). Factual claims in managed docs must be citable to a code location (decision rationale/failure history go in ADRs/human sections); the primary update mechanism is incremental sync at change time — periodic runs are audit-only (dead-man's switch + blind-rebuild hallucination audit; semantically equivalent phrasing is not drift).
- When a human edits a managed section, record a reason code so future generation accounts for it (RMA). Include a "code change ↔ doc update consistency" check in the review gate.

### Context Management
- The main context is the orchestrator — keep only conclusions, and delegate exploration/search/large reads to subagents (separate context windows), receiving only summaries back. Don't sweep directories or read large files whole in the main context. Dispatch independent work in parallel, and run long-running work in the background.
- Keep the source of truth in files, not the conversation — persist plans/decisions/progress to external files and checkpoint at every milestone. Keep durable rules/facts in CLAUDE.md (loaded every session, re-injected after compaction) and in auto memory (survives even `/clear`).
- Only the root CLAUDE.md and auto memory reliably survive a context reset; the conversation does not. Use `/compact <focus>` before it triggers automatically, `/clear` between unrelated tasks, and re-check git status, cwd, and state artifacts right after any resume.

### Research Protocol
- Use prior knowledge only to form search queries and hypotheses — never to fix the candidate set or to populate facts in a deliverable. Every factual claim must be traceable to a source fetched in this research; mark anything not found as "unverified — needs research" (never fill gaps from memory).
- Confirm enumeration facts (variants, sizes, dates, licenses) only from the official registry. Search snippets, leaderboards, and blogs are leads, not evidence. Establish completeness by querying the registry directly, not by search ranking. Don't assert negative/universal claims ("doesn't exist / all of them / the smallest is N") without primary-source enumeration.
- Fetch each in-scope vendor's/library's official latest page at least once; seed already-cited repo URLs as must-fetch. If it contradicts an existing doc, resolve via the primary source and record the resolution.

### Commits
- Headers use Conventional Commits (English type/scope, ≤72 characters); summaries and bodies are written in Korean — so git log doubles as a Korean research note. `feat`/`fix`/`refactor`/`perf` commits require a `## Why/What/How/Result` body (the commit-msg hook warns otherwise).
- Never fabricate Result/numbers (write "not measured" instead). Before committing, classify changes by intent so one logical unit = one commit (split hunks with `git add -p`). Link research threads with the `Experiment:` trailer.
- No emoji in the message (header, body, or trailers) — `git log` is read and grepped as plain text.

### Work Contract
- Answer five questions before writing criteria — what problem and what if not done, what alternatives were rejected and why, what unknown blocks progress, where it splits and what stays single-owned, how it most plausibly fails. Start when no criterion reads two ways, every unknown is classified, rejections are recorded, and the next question can only be answered by writing code.
- Write the contract before development starts and freeze it during execution. Record changes in `revision` with a kind (additive/narrowing/breaking); an additive change that touches no existing criterion or ownership boundary updates only the affected lane.
- Write completion criteria in EARS or Given-When-Then with `SHALL`, and apply the judgment test: if two agents could disagree about whether it passed, rewrite it. Every criterion carries an executable `verify:` or an explicit `verify: human`.
- Cover functional, non-functional, and **negative** criteria (what must not happen), and state what is out of scope. Fill only the fields the work triggers — a three-line contract is complete for small work.
- Declare `done_level` (`auto`/`reviewed`/`proven`) up front, chosen by size × reversibility. Regardless of level, three things are mandatory: every criterion passes, evidence exists, and each new test was observed failing at the base commit.
- Restrict `owns` to disjoint directory prefixes; assign lock files, migrations, and generated files to a single owner instead of a lane. Record model tier per lane, never a model id.
- Make deviation visible rather than forbidding it: a bypassed gate is recorded as `done_level: bypassed` with a reason. An unrecorded bypass is the blocker.

### Evidence
- Report completion as artifact paths plus the criteria table — no narrative summary. Prose is where a hallucinated completion hides.
- Write execution records by teeing real runs, and mask secrets in the command line and environment as well as the output. Record status as a word (`PASS`/`FAIL`/`PENDING-HUMAN`/`NO-BASELINE`), never a symbol.
- Block completion on `PENDING-HUMAN` at every done level; a human criterion passes only once a verdict, its author, and its timestamp are recorded.
- Record provenance and the timestamps `created_at`, `verify_runs[].at`, `review_rounds` — without them no retrospective measurement of the process is possible at all.
