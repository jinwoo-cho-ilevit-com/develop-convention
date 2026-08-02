# Development Conventions

A collection of development convention documents. Composed of general-purpose development rules plus AI/ML and LLM-specific rules, consumed by both humans and AI agents.

Each doc starts with `## Core Rules` — imperative rules an agent can act on — followed by human-oriented details and sources. Every factual claim cites a source verified by research as of 2025-2026.

The [`dev-harness` plugin](#how-to-apply-to-a-new-project) in this repository runs these rules rather than copying them: install it once and the conventions, hooks and skills come with it.

## Document Map

Numbers are stable identifiers, not a reading order — the groups below are the order.

### Principles

| Doc | Contents |
|---|---|
| [00-principles.md](conventions/00-principles.md) | Core principles: fresh start, fresh-context, evidence over claims, fact-based judgment, empirical measurement first |

### Codebase

| Doc | Contents |
|---|---|
| [01-structure-naming.md](conventions/01-structure-naming.md) | Module separation, structure-follows-design integration, flat layout, PEP 8 semantic naming, comment/emoji policy, dead code/duplication removal |
| [02-config.md](conventions/02-config.md) | No hardcoding, Hydra config groups + validation, ablation combinations, run snapshots |
| [03-environment.md](conventions/03-environment.md) | uv/ruff toolchain, local↔RunPod portability, device abstraction (CPU fallback) |
| [13-secret-management.md](conventions/13-secret-management.md) | No hardcoding/committing secrets, central manager (Infisical) injection, reading env in code, container/CI machine identity, scanning/rotation |

### Execution

| Doc | Contents |
|---|---|
| [04-pipeline.md](conventions/04-pipeline.md) | Small-sample debugging, atomic save + resume, streaming, progress monitoring |
| [05-performance.md](conventions/05-performance.md) | Async/parallel selection, DataLoader tuning, GPU/RAM profiling, structured logging |

### Verification

| Doc | Contents |
|---|---|
| [06-testing-verification.md](conventions/06-testing-verification.md) | Minimal-meaningful testing, golden files, tolerance bands, CPU smoke tests, completion verification |

### ML and LLM

| Doc | Contents |
|---|---|
| [07-ml-development.md](conventions/07-ml-development.md) | Seed/reproducibility, train-serve skew prevention, experiment tracking, checkpoints/spot pods |
| [08-llm-development.md](conventions/08-llm-development.md) | Training framework routing, FSDP2/bf16, chat template consistency, evaluation reproducibility, LLM-as-judge, data |

### LLM API

| Doc | Contents |
|---|---|
| [10-llm-api-inference.md](conventions/10-llm-api-inference.md) | LLM API inference module: adapter structure, calls/rate limits, errors/retries, ensembles, caching/resume, cost/evaluation |
| [11-llm-api-providers.md](conventions/11-llm-api-providers.md) | Provider-specific considerations (OpenAI/Anthropic/Gemini/DeepSeek/OpenRouter) + structured output tiered fallback |
| [12-upstream-docs.md](conventions/12-upstream-docs.md) | Latest-docs reference procedure (4 tiers) + per-provider canonical URL registry + smoke-test confirmation |

### Agent collaboration

| Doc | Contents |
|---|---|
| [09-agentic-workflow.md](conventions/09-agentic-workflow.md) | How to write CLAUDE.md/AGENTS.md, workflows-first parallel development (worktree for file isolation only), decomposition and frozen contracts, model routing, spec gating |
| [14-context-management.md](conventions/14-context-management.md) | Minimizing main context (firewall/delegation), understanding compaction/clear behavior, preventing context loss via external files, CLAUDE.md, and auto memory |
| [21-development-loop.md](conventions/21-development-loop.md) | The loop end to end: interview to axes, plan and lane briefs, boundary contract tests, worktree fan-out, review on each lane's finish, merge and end-to-end verification |

### Work discipline

| Doc | Contents |
|---|---|
| [18-work-contract.md](conventions/18-work-contract.md) | Work contract: completion criteria as sentence + command (EARS/Given-When-Then, `[human]` with a recorded verdict), lane ownership, done level (auto/reviewed/proven by size × reversibility), changing a frozen contract |
| [19-evidence.md](conventions/19-evidence.md) | Evidence artifacts: criteria table instead of narrative, command output with secret masking, provenance, human verdict records, recorded bypasses |
| [20-review-gate.md](conventions/20-review-gate.md) | Review gate: author-is-not-verifier, lanes defined by input (module/project/absence/security), fan-in and severity, review tool paths without pinned model ids |

### Record-keeping

| Doc | Contents |
|---|---|
| [15-doc-tracking.md](conventions/15-doc-tracking.md) | Doc-code synchronization: 4-tier tracking (contract·module·flow·history), docsync skill (incremental sync + audit), managed/human markers, blind rebuild·RMA verification, ADR supersession |
| [16-research-protocol.md](conventions/16-research-protocol.md) | Fact research protocol: prior knowledge is for queries only, every claim requires a source from this research, source tiers (official registry), verification of negative/universal claims, coverage·contradiction resolution |
| [17-commit-protocol.md](conventions/17-commit-protocol.md) | Commit protocol: Conventional Commits header (English type/scope) + Korean body (Why/What/How/Result), trailers, logical-unit splitting — git log doubles as a research note |

## How to Apply to a New Project

Install the harness once per machine. It carries the conventions, the hooks and the skills, so nothing is copied into the project and there is no path to fill in:

```bash
claude plugin marketplace add jinwoo-cho-ilevit-com/develop-convention
claude plugin install dev-harness@develop-convention
```

Then run `/dev-harness:setup` once in each project. It reads the repository, proposes the run/test/lint/smoke commands, and writes a short `AGENTS.md` with them — the only thing the plugin cannot know. Python projects can also copy [templates/pyproject.toml](templates/pyproject.toml) and `templates/.pre-commit-config.yaml` for the local tool configuration.

Keep `AGENTS.md` to what nobody could infer from the repository. Do not paste convention rules into it: an excerpt is a copy, and a copy drifts from its source while being loaded in every session (→ [15-doc-tracking.md](conventions/15-doc-tracking.md), [09-agentic-workflow.md](conventions/09-agentic-workflow.md)).

### What the Harness Adds

| Command | Does |
|---|---|
| `/dev-harness:spec` | Interviews you until the work is specific enough to split, then writes `PLAN.md` and one brief per lane |
| `/dev-harness:build` | Freezes each boundary with a contract test, fans the lanes out to worktree-isolated agents, reviews each lane the moment it finishes, merges and verifies |
| `/dev-harness:setup` | Writes the short `AGENTS.md` by hand |
| `/docsync` | Syncs module docs with the code that changed (→ [15-doc-tracking.md](conventions/15-doc-tracking.md)) |

A hook keeps the main session an orchestrator: it plans, splits and judges, and every edit goes to a subagent. The full loop is [21-development-loop.md](conventions/21-development-loop.md).

`/dev-harness:build` reports one outcome per lane. Only the first is a completion:

| Outcome | What you do |
|---|---|
| `passed` | Nothing — the criteria passed and review found no blockers, so the lane merges |
| `pending-human` | Give the `[human]` criterion its verdict, before the lane merges rather than after |
| `criteria-failed` | Send the lane back: its own completion criteria did not pass, so it is not done |
| `review-incomplete` | Re-run the lens that returned nothing rather than merging a short review |
| `review-unexecuted` | Re-run the lens that ran zero commands — that verdict is a reading, not a review |
| `verification-incomplete` | Decide the blockers yourself; the verifier's answer did not map onto them |
| `regression-halt` | Change the approach — the findings are repeating or coming from the last fix |
| `round-cap` | Decide as a person what happens next; the runaway guard fired |

### Tool-by-Tool Behavior

| Tool | Behavior |
|---|---|
| Claude Code | Install the plugin. The conventions, hooks, commands and skills come with it; `AGENTS.md` holds only this project's commands |
| Codex CLI | Reads `AGENTS.md` natively (root→current-directory chain, with a size cap). Point it at the published docs for the rules themselves |
| Cursor | Co-author of the AGENTS.md standard — reads it natively. Promote only the few rules that must always be enforced to `.cursor/rules/` if needed |
| Other (Gemini CLI, Windsurf, Aider, etc.) | Tools that read the AGENTS.md standard behave the same way. For unsupported tools only, add one line in that tool's instruction file pointing to AGENTS.md |

**Note for cloud-executed agents**: in isolated sandboxes (Codex cloud, Cursor background agents, Claude Code web), read the published docs at <https://jinwoo-cho-ilevit-com.github.io/develop-convention/>, or add this repo as a git submodule so a local path resolves there too.

### How to Instruct the AI

**No command is needed for everyday use** — the plugin is loaded and the rules apply. The cases below are the ones that need an explicit command; when you want to make sure a specific doc applies, refer to it by its number.

Starting a piece of work:
```
/dev-harness:spec  Add a DeepSeek adapter to the inference layer
```

Running the lanes it wrote — the second half of the same flow, once you have read `PLAN.md` and the briefs:
```
/dev-harness:build  deepseek-adapter
```

Enforcing a specific rule:
```
Build the preprocessing pipeline. Follow the Core Rules in doc 04 (small-sample runs, resume).
Add a DeepSeek adapter. Follow the procedure in doc 12 — fetch the official docs first to confirm, then implement.
```

Review:
```
Review this diff against the conventions the plugin carries.
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

### Secret Management

- Never hardcode secrets in code, config, logs, or images; never commit a plaintext `.env` (`.gitignore` + `.env.example` lists keys only). The single source of truth is a central secret manager (Infisical recommended).
- Supply secrets to local, CI, and container environments alike via runtime injection (`infisical run -- <cmd>`), with no plaintext left on disk. Code reads them as env vars as usual (`os.environ[...]`). Coding agents follow the same rule.
- Containers/CI authenticate via machine identity (Universal Auth) with least privilege and short-lived tokens. Separate environments (dev/staging/prod) + rotate + scan with gitleaks (pre-commit/CI). Immediately rotate and reissue any secret that was already committed.

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
- Prefer workflows/subagent orchestration for parallelization. Git worktree is a file-isolation mechanism, so introduce it only when overlapping file edits would conflict. Write a breakdown table (owner, files, dependencies, integration) before starting; freeze shared contracts during execution, and when one changes mid-way let the kind of change decide how much stops (→ 18 §4) rather than restarting everything; assign locks/migrations to a single owner. Confirm a subagent answered with content, not merely that it finished.
- Merge each branch only after its tests pass, then do one integration verification pass. Route models by difficulty (mechanical → lightweight, standard → mid-tier, architecture → top-tier).
- Write heavyweight spec documents only when they are an asset shared across PRs or workers; small or exploratory work uses lightweight iteration.

### Context Management

- The main context is the orchestrator — keep only conclusions, and delegate exploration/search/large reads to subagents (separate context windows), receiving only summaries back. Don't sweep directories or read large files whole in the main context. Dispatch independent work in parallel, and run long-running work in the background.
- Keep the source of truth in files, not the conversation — persist plans/decisions/progress to external files and checkpoint at every milestone. Keep durable rules/facts in CLAUDE.md (loaded every session, re-injected after compaction) and in auto memory (survives even `/clear`).
- Only the root CLAUDE.md and auto memory reliably survive a context reset; the conversation does not. Use `/compact <focus>` before it triggers automatically, `/clear` between unrelated tasks, and re-check git status, cwd, and state artifacts right after any resume.

### Development Loop

- The main session orchestrates and does not develop — it interviews, splits, judges, and delegates every edit to a subagent. Reading a large file there costs the same budget an edit would.
- Specify by interview, not by template. Derive the axes from this project: infer from the request and the repository, check once for what recent practice adds, then keep only those naming a way this project could fail. Keep the list open during the interview and record each axis's state — that record is the only account of what was never asked.
- Split as far as disjoint file ownership allows, and freeze every boundary with a contract test written **before** the lanes start, owned by no lane. Store its representative payload as a sample file and have the factory load it; separate files do not stop two lanes holding contradictory assumptions about what crosses between them.
- Review a lane the moment that lane finishes, not when all of them do. Send findings back to the lane that wrote the code and re-review; end on no blockers, on most findings coming from the previous fix (change the approach), or on a runaway cap that calls a person.
- Merge a lane only after its criteria pass, run the integration lane last, and verify the assembled project end to end before claiming completion.

### Work Contract

- Write the contract before development starts and freeze it during execution. Record changes with a kind (additive/narrowing/breaking); an additive change that touches no existing criterion or ownership boundary updates only the affected lane.
- Write completion criteria in EARS or Given-When-Then with `SHALL`, and apply the judgment test: if two agents could disagree about whether it passed, rewrite it.
- Pair every criterion with the command that checks it, or mark it `[human]`. The two halves fail differently: a command with no sentence is never asked whether it checks the right thing, and a sentence with no command defers the judgment to verification time.
- Cover functional, non-functional, and **negative** criteria (what must not happen), and state what is out of scope. A three-to-five-line contract is complete for small work.
- Declare the done level (`auto`/`reviewed`/`proven`) up front, chosen by size × reversibility. Regardless of level, three things are mandatory: every criterion passes, evidence exists, and each new test was observed failing at the base commit.
- Ask of every criterion whether it was already true at the base commit. If it was, it is a standing invariant — mark it exempt from the red check and say why. Absence criteria almost always are.
- Give every lane a disjoint set of owned paths — directory prefixes where the work divides that way, cross-cutting files named individually with one owner each, since a prefix rule cannot assign a README or an ignore file. When several kinds of change land in the same documents, slice by file rather than by phase. Assign lock files, migrations, and generated files to a single owner. Record model tier per lane, never a model id.

### Evidence

- Report completion as the criteria table plus the output the commands produced — no narrative summary. Prose is where a hallucinated completion hides.
- Fill the table as each criterion turns green, not at the end, and paste what the command printed rather than describing it. Record status as a word (`PASS`/`FAIL`/`PENDING-HUMAN`/`NO-BASELINE`), never a symbol.
- Mask secrets in the command line and environment as well as the output, before evidence leaves the machine — the pre-commit scan never sees gitignored artifacts.
- Block completion on `PENDING-HUMAN` at every done level; a human criterion passes only once a verdict, its author, and its timestamp are recorded.
- Name the commit and whether the tree was clean. Record every bypass with its reason — a skipped gate and a passed gate must never look alike in the record.
### Review Gate

- Every change goes through a review its author did not perform, on a tool chosen before development starts and named in the review report. The reviewer gets the diff and the criteria, never the author's reasoning.
- A lane judging code runs the code, and reports how many commands it ran; a verdict from a lane that ran none is a reading and says so. Measured on one document at one commit, a read-only lane found nothing where an executing lane found ten.
- Scale lanes to risk: a 2+ module or interface/schema change gets three lanes defined by their input — module (diff + changed files), project (diff + callers + convention docs), absence (requirement + diff, hunting for what is missing); anything smaller gets one. Add a security lane only when auth, secrets, or external input is touched.
- Fan-out requires fan-in, owned by the dispatching orchestrator: confirm every lane answered *with content*, dedupe by `file:line`, resolve contradictions, verify each finding against the code, rank by severity. A lane that finished is not a lane that answered — an agent can end with its report undelivered. An unsynthesized merge amplifies manufactured issues once per lane.
- Severity carries an action: blocker blocks the merge and is re-reviewed by the lane that raised it, major is fixed in the same work, minor becomes a follow-up, nit may be ignored. A finding with no concrete failing scenario is a nit.
- Lanes never switch branches in a shared worktree — one checkout erases every other lane's subject. A finding that depends on a tool's behaviour names the version tested, and it must be the version the project pins.
- Run at least one lane on a different vendor's family, and don't pin model ids in the docs — resolve them at use time and pick by role. A gate that passes is not evidence the gate works; confirm once that it fails when it should.

### Doc Tracking

- Docs are split into 4 tiers: for input/output contracts, code is the single source (no hand-written docs); module logic goes in a per-directory AGENTS.md; overall flow goes in ARCHITECTURE.md + Mermaid (generate dependency graphs with a deterministic tool); decision history uses structured commits + append-only ADRs (supersede instead of editing, record reversed decisions/rollbacks too, and reference only currently valid decisions).
- Agents regenerate only inside `docsync:managed` markers (human sections are off-limits, stamped with a verification commit). Factual claims in managed docs must be citable to a code location (decision rationale/failure history go in ADRs/human sections); the primary update mechanism is incremental sync at change time — periodic runs are audit-only (dead-man's switch + blind-rebuild hallucination audit; semantically equivalent phrasing is not drift).
- When a human edits a managed section, record a reason code so future generation accounts for it (RMA). Include a "code change ↔ doc update consistency" check in the review gate.
- When something ships, update what distributes it in the same change — the installer, the getting-started page, the excerpt loaded elsewhere, the published site's navigation. Docs-follow-code covers the description; nothing covers the delivery path, and that is the one that leaves a working artifact unreachable.
- Give an excerpt a header naming its source document and the commit it was taken at, and check the two automatically. A copy that drifts is worse than a wrong original: it is loaded everywhere and matches nothing.

### Research Protocol

- Use prior knowledge only to form search queries and hypotheses — never to fix the candidate set or to populate facts in a deliverable. Every factual claim must be traceable to a source fetched in this research; mark anything not found as "unverified — needs research" (never fill gaps from memory).
- Confirm enumeration facts (variants, sizes, dates, licenses) only from the official registry. Search snippets, leaderboards, and blogs are leads, not evidence. Establish completeness by querying the registry directly, not by search ranking. Don't assert negative/universal claims ("doesn't exist / all of them / the smallest is N") without primary-source enumeration.
- Fetch each in-scope vendor's/library's official latest page at least once; seed already-cited repo URLs as must-fetch. If it contradicts an existing doc, resolve via the primary source and record the resolution.

### Commits

- Headers use Conventional Commits (English type/scope, ≤72 characters); summaries and bodies are written in Korean — so git log doubles as a Korean research note. `feat`/`fix`/`refactor`/`perf` commits require a `## Why/What/How/Result` body (the commit-msg hook warns otherwise).
- Never fabricate Result/numbers (write "not measured" instead). Before committing, classify changes by intent so one logical unit = one commit (split hunks with `git add -p`). Link research threads with the `Experiment:` trailer.
- No emoji in the message (header, body, or trailers) — `git log` is read and grepped as plain text.
