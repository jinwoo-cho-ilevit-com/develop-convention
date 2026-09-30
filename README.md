# Development Conventions

A collection of development convention documents. Composed of general-purpose development rules plus AI/ML and LLM-specific rules, consumed by both humans and AI agents.

Each doc starts with `## Core Rules` — imperative rules an agent can act on — followed by human-oriented details and sources. Specific factual claims carry a source fetched in research (2025-2026); a claim no primary source confirmed is marked unverified.

The [`dev-harness` plugin](#how-to-apply-to-a-new-project) in this repository runs these rules rather than copying them: install it once and the conventions, hooks and skills come with it.

## Document Map

Numbers are stable identifiers, not a reading order. The groups below are the order, and every group after Principles is also a skill: install the harness and it loads itself when that kind of work starts. The skill routes to these documents and never copies them, so what you read here is what an agent reads.

### Principles

| Doc | Contents |
|---|---|
| [00-principles.md](conventions/00-principles.md) | Core principles: proportional complexity, behavior-grounded changes, evidence over claims, fact-based judgment, empirical measurement |

Takes precedence over every other document, so it belongs to no single skill and every skill points back at it.

### Plan and delegate — `plan-and-delegate`

| Doc | Contents |
|---|---|
| [21-development-loop.md](conventions/21-development-loop.md) | Direct path for small reversible work; planned loop for larger work: interview, lane briefs, boundary contracts, worktree fan-out, risk-scaled review, merge and end-to-end verification |
| [18-work-contract.md](conventions/18-work-contract.md) | Planned work contract: completion criteria as sentence + command or `[human]` verdict, boundary surfaces and lane ownership, done level (auto/reviewed/proven by impact and reversibility), changing a frozen contract |
| [09-agentic-workflow.md](conventions/09-agentic-workflow.md) | How to write CLAUDE.md/AGENTS.md and the instruction anti-patterns to keep out of them, workflows-first parallel development (worktree for file isolation only), decomposition and frozen contracts, merge-then-cleanup, two-axis (tier + effort) model routing, spec gating |
| [14-context-management.md](conventions/14-context-management.md) | Minimizing main context (firewall/delegation), understanding compaction/clear behavior, preventing context loss via external files, CLAUDE.md, and auto memory |

### Code and config — `code-and-config`

| Doc | Contents |
|---|---|
| [01-structure-naming.md](conventions/01-structure-naming.md) | Module separation, structure-follows-design integration, flat layout, PEP 8 semantic naming, names derived from objects rather than re-spelled as literals, comment/emoji policy, literal UTF-8 over `\uXXXX` escapes, dead code/duplication removal |
| [02-config.md](conventions/02-config.md) | No hardcoding, composable config groups + validation, ablation combinations, run snapshots, LLM prompts externalized to `.md` files |
| [03-environment.md](conventions/03-environment.md) | uv/ruff toolchain, one codebase running unmodified on local macOS/CPU and a remote Linux/CUDA host, device abstraction (CPU fallback) |
| [13-secret-management.md](conventions/13-secret-management.md) | No hardcoding/committing secrets, central manager (Infisical) injection, reading env in code, permissions on every file of a restricted artifact, container/CI machine identity, scanning/rotation, MCP server credentials (env references, no token passthrough) |
| [25-agent-sandboxing.md](conventions/25-agent-sandboxing.md) | Filesystem and network isolation before permission prompts (and auto mode), bypass modes only inside a container or VM, at most two of untrusted input, reachable secrets and outward tools per session (Rule of Two), least-privilege tokens and untrusted events for CI agent steps |

### Commit — `commit`

| Doc | Contents |
|---|---|
| [17-commit-protocol.md](conventions/17-commit-protocol.md) | Commit protocol: Conventional Commits header (English type/scope) + Korean body (Why/What/How/Result), trailers, logical-unit splitting — git log doubles as a research note |

Its own skill rather than part of the group above, because it fires on nearly every change and the rest of that group does not.

### Verify and review — `verify-and-review`

| Doc | Contents |
|---|---|
| [06-testing-verification.md](conventions/06-testing-verification.md) | Smallest relevant existing check first, durable tests only for distinct realistic failures, selective red evidence, sample runs for flows, lane-boundary contracts and schemas, trustworthy fixtures and expected values, completion verification |
| [20-review-gate.md](conventions/20-review-gate.md) | Risk-scaled review: auto may omit independent review, reviewed uses one focused reviewer plus a seam review when lanes merge, proven adds distinct lenses and a plan review; static readings are labeled, findings are checked and ranked |
| [19-evidence.md](conventions/19-evidence.md) | Evidence artifacts: exact command, exit and decisive output, provenance, secret masking, human verdict records, recorded bypasses |

### Data and ML pipelines — `ml-pipeline`

| Doc | Contents |
|---|---|
| [04-pipeline.md](conventions/04-pipeline.md) | Bounded sample debugging, resumable and atomic output with completion identity, memory-budgeted processing, progress monitoring |
| [05-performance.md](conventions/05-performance.md) | Scale/time/memory/cost targets, end-to-end measurement, algorithm and I/O before concurrency, conditional profiling and logging, language choice |
| [07-ml-development.md](conventions/07-ml-development.md) | Seed/reproducibility, train-serve skew prevention, experiment tracking, checkpoints/spot pods |
| [08-llm-development.md](conventions/08-llm-development.md) | Training framework routing, FSDP2/bf16, chat template consistency, evaluation reproducibility, LLM-as-judge, data |
| [22-framework-wrapping.md](conventions/22-framework-wrapping.md) | Wrapping a third-party training framework: a test layer that imports the real package, config-only tiny-model fixtures, image supplies the dependency and the working tree supplies your code, one gate function, the layer's range |
| [23-remote-gpu-iteration.md](conventions/23-remote-gpu-iteration.md) | Local↔remote GPU iteration loop: direct code sync instead of rebuild/push round trips, a `--smoke` mode through the real entry point, preflight before expensive loads, replaying remote failures locally |

### External sources — `external-sources`

| Doc | Contents |
|---|---|
| [12-upstream-docs.md](conventions/12-upstream-docs.md) | Latest-docs reference procedure (5 tiers) + per-provider canonical URL registry + smoke-test confirmation |
| [11-llm-api-providers.md](conventions/11-llm-api-providers.md) | Provider-specific considerations (OpenAI/Anthropic/Gemini/DeepSeek/OpenRouter) + structured output tiered fallback |
| [10-llm-api-inference.md](conventions/10-llm-api-inference.md) | LLM API inference module: adapter structure, calls/rate limits, errors/retries, ensembles, caching/resume, cost/evaluation |
| [16-research-protocol.md](conventions/16-research-protocol.md) | Fact research protocol: prior knowledge is for queries only, every claim requires a source from this research, source tiers (official registry), semantic search (exa) for source discovery, verification of negative/universal claims, coverage·contradiction resolution |

Trained-and-served-by-you models are the group above; this one is everything you call over someone else's API, plus the case where external facts are the deliverable rather than an input.

### Doc tracking — `docsync`

| Doc | Contents |
|---|---|
| [15-doc-tracking.md](conventions/15-doc-tracking.md) | Doc-code synchronization: 4-tier tracking (contract·module·flow·history), docsync skill (incremental sync + audit), managed/human markers, blind rebuild·RMA verification, generated excerpts (fill-excerpts) |

### Explainer docs — `explainer-docs`

| Doc | Contents |
|---|---|
| [24-explainer-docs.md](conventions/24-explainer-docs.md) | Human-facing explanatory deliverables: term glossing, mechanism over name-drop, one-sentence definition opening each mechanism, one analogy carried through the document, one example per concept, visualization triggers (structure/quantities/concept), fresh-reader sizing test, self-contained HTML artifacts, one accessibility contract for every figure |

Doc tracking keeps reference docs matching the code; this group is the other genre — documents whose product is a person's understanding.

## How to Apply to a New Project

Install the harness once per machine. It carries the conventions, the hooks and the skills, so nothing is copied into the project and there is no path to fill in:

```bash
claude plugin marketplace add jinwoo-cho-ilevit-com/develop-convention
claude plugin install dev-harness@develop-convention
```

Then run `/dev-harness:setup` once in each project. It reads the repository, proposes the run/test/lint/smoke commands, and writes a short `AGENTS.md` with them — the only thing the plugin cannot know — plus the sibling `CLAUDE.md` that imports it, since Claude Code reads only `CLAUDE.md` — the cases (an existing file, a symlink, `.claude/CLAUDE.md`) are setup's and [15-doc-tracking.md](conventions/15-doc-tracking.md) §1's. Python projects can also copy [templates/pyproject.toml](templates/pyproject.toml) and `templates/.pre-commit-config.yaml` for the local tool configuration.

### Updating

```bash
claude plugin update dev-harness
```

Then run `/reload-plugins`, or restart, and re-run `/dev-harness:setup` in each existing project so it picks up what setup now writes — currently the `CLAUDE.md` line that imports `AGENTS.md`. Skills take effect immediately in a running session; hooks, MCP servers, agents and output styles do not (→ <https://code.claude.com/docs/en/plugins-reference>). Between the update and the reload the hooks do not fire at all, so the read budget is not merely stale but unenforced — measured in this repository, not documented upstream.

To see which copy is actually running, read `~/.claude/plugins/installed_plugins.json` — it records the active install path, its version and the git commit it was built from, so the live copy is identifiable without inferring it from how a hook behaves.

`/plugin update` keys on the version string in `.claude-plugin/plugin.json` and exits silently when it has not moved, which is indistinguishable from success. It is the only version literal (the marketplace entry declares none on purpose). Bump it whenever anything under `hooks/`, `commands/`, `workflows/`, `skills/`, `conventions/`, `templates/` or `.claude-plugin/` changes; `tests/test_release.py` fails the build if you do not.

Keep `AGENTS.md` to what nobody could infer from the repository. Do not paste convention rules into it: an excerpt is a copy, and a copy drifts from its source while being loaded in every session (→ [15-doc-tracking.md](conventions/15-doc-tracking.md), [09-agentic-workflow.md](conventions/09-agentic-workflow.md)).

### What the Harness Adds

| Command | Does |
|---|---|
| `/dev-harness:spec` | Routes small reversible `auto` work to the direct path; for `reviewed` and `proven` work, develops `PLAN.md` and a brief per lane |
| `/dev-harness:build` | Runs planned `reviewed` or `proven` work: freezes boundaries, fans out worktree-isolated lanes, applies risk-scaled review, merges, checks seams where lanes meet, and verifies |
| `/dev-harness:setup` | Writes the short `AGENTS.md` by hand, and the `CLAUDE.md` line that imports it |

Eight skills load themselves when the work matches, so you do not have to remember which rules apply. Each routes to the documents in its Document Map group and copies none of them — a rule stays in exactly one place, where it can only be wrong once:

| Skill | Loads when |
|---|---|
| `plan-and-delegate` | Work larger than one edit begins — planning, splitting into lanes, deciding what done means, dispatching a subagent |
| `code-and-config` | Files appear or move, config or dependencies change, a credential is in scope, an agent runs unattended, in CI, or on untrusted input |
| `commit` | A commit is about to be written |
| `verify-and-review` | Tests are being chosen or run, a diff is being reviewed, completion is about to be claimed |
| `ml-pipeline` | A preprocessing, training, or evaluation pipeline is being built, or a model is trained or served here |
| `external-sources` | Code calls someone else's model API, or external facts are the deliverable |
| `docsync` | Module docs need to catch up with the code that changed (→ [15-doc-tracking.md](conventions/15-doc-tracking.md)) |
| `explainer-docs` | A report, guide, tutorial, or HTML artifact for a human reader is being written |

Small reversible `auto` work uses direct iteration with a relevant check and a concise result. Planned work uses the main session to coordinate lanes and judge their results. The guard hook meters reads; the routing hook injects the skill map once per user prompt. The routes are in [21-development-loop.md](conventions/21-development-loop.md).

`/dev-harness:build` reports one outcome per lane. Only the first is a completion:

| Outcome | What you do |
|---|---|
| `passed` | Nothing — the criteria passed and review found no blockers, so the lane merges |
| `pending-human` | Give the `[human]` criterion its verdict, before the lane merges rather than after |
| `criteria-failed` | Send the lane back: its own completion criteria did not pass, so it is not done |
| `review-incomplete` | Re-run the lens that returned nothing rather than merging a short review |
| `verification-incomplete` | Decide the blockers yourself; the verifier's answer did not map onto them |
| `unverified-blocker` | Decide it with the user — nothing was run that reproduced or refuted the blocker |
| `criteria-drift` | Restore the brief's criteria — never edit the brief to fit the work |
| `recheck-incomplete` | Resume the lane; the independent re-run of its criteria did not map onto them, or ran on another commit |
| `measurement-failed` | Resume the lane — its head, cleanliness and diff never got measured, so nothing after that ran |
| `dirty-worktree` | Have an agent commit or clean up in that worktree, then resume; reviewers would read a different commit |
| `ownership-violated` | Revert the paths outside the lane's `owns` and resume, or fix the plan's ownership |
| `regression-halt` | Change the approach — the findings are repeating or coming from the last fix |
| `round-cap` | Decide as a person what happens next; the runaway guard fired |
| `develop-failed` / `fix-failed` | Re-run or investigate — the agent died; an infrastructure failure, not a verdict |

### Tool-by-Tool Behavior

| Tool | Behavior |
|---|---|
| Claude Code | Install the plugin. The conventions, hooks, commands and skills come with it; `AGENTS.md` holds only this project's commands, and reaches Claude Code through the sibling `CLAUDE.md` that `/dev-harness:setup` writes — Claude Code does not read `AGENTS.md` itself |
| Codex CLI | Reads `AGENTS.md` natively (root→current-directory chain, with a size cap). Point it at the published docs for the rules themselves |
| Cursor | Co-author of the AGENTS.md standard — reads it natively. Promote only the few rules that must always be enforced to `.cursor/rules/` if needed |
| Other (Gemini CLI, Windsurf, Aider, etc.) | Tools that read the AGENTS.md standard behave the same way. For unsupported tools only, add one line in that tool's instruction file pointing to AGENTS.md |

**Note for cloud-executed agents**: with the plugin installed, `conventions/` travels inside it (see the table above) and its skills read from there — no clone and no path needed. In isolated sandboxes without the plugin (Codex cloud, Cursor background agents, Claude Code web), read the published docs at <https://jinwoo-cho-ilevit-com.github.io/develop-convention/>, or add this repo as a git submodule so a local path resolves there too.

### How to Instruct the AI

**No command is needed for everyday use** — the plugin is loaded and the rules apply. The cases below are the ones that need an explicit command; when you want to make sure a specific doc applies, refer to it by its number.

For small reversible work, describe the change directly. For planned work:
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
Flag violations with their doc number. Use a separate reviewer when the change's risk requires one.
```

Rewrite/refactor:
```
Rewrite this module. Per doc 00, start from the required behavior and compatibility boundaries;
preserve them with the smallest suitable existing check, sample run, or characterization test.
```

Updating conventions (when a stale fact is found, in this repository — from a consuming project, open an issue here instead, → 12):
```
I checked the official docs and the [X] content in doc 11 has changed. Update the convention and commit it.
```

## Full Rule Summary (for Agent Injection)

### Principles ([00](conventions/00-principles.md))

- Start from requirements and observed behavior. Inspect existing interfaces for compatibility while choosing structure from the requirements; add complexity only for a current requirement, observed failure risk, or measured constraint.
- Don't judge from prior knowledge. Verify library/API/model facts against current primary sources before applying them — 16 defines what counts for factual specs, 12 for provider APIs; search results are leads, not proof.
- Use fresh context for independent review and substantial rewrites where risk calls for it. Match claims to evidence: execution for behavior, source inspection for static facts, measurement for performance.
- Preserve required behavior through the smallest suitable existing check, sample run, or characterization test before rewriting. Claim performance/productivity improvements only with empirical measurement.

### Structure & Naming ([01](conventions/01-structure-naming.md))

- Separate by module/feature, with clear input/output contracts. Keep files small and boundaries clear.
- Fit the structure to the design, not the design to the structure: when integrating a new module, restructuring the surrounding project is preferred over force-fitting — behavior pinned by tests, structural moves in separate commits.
- App/research/pipeline code uses a flat layout (src/ is only for distributed libraries). Use uv workspaces for multiple packages.
- Semantic naming, PEP 8. No `_v2`/`_new` suffixes on code — rename in place; evaluation-pinned artifacts (prompts, golden sets) are the exception and version append-only. Never re-spell a module or symbol name as a string literal, least of all on an error path the tests never run — derive it from the object, or let the original error propagate. Delete dead code immediately, scan for duplicates before completion: an unreachable function's docstring is still read as a statement about the system.
- Comments cover only constraints/intent the code can't express — no insider-only context, no TMI, no explaining the obvious. Write them as the module's first author would: what the module is and the constraints it lives under, never the editing session's narrative ("changed to fix X", "added per review"). Cap a comment block at three lines, an inline comment at one. A comment claiming another component enforces something names the call site that enforces it.
- **Edit by rewrite, not by append.** Once a comment block or document section has grown past about half again its size, rewrite it instead of extending it. Comments and documents describe the current state only — change history lives in git. Before adding a rule, find where it already lives; replace the second copy with a reference.
- Minimize emoji in docs, and use none at all in code comments: allow one only where the symbol is the data (a defined legend), never as decoration on headings or bullets. Write status as words (`OK`/`FAILED`/`TODO`) so it stays greppable.
- Write non-ASCII text as literal UTF-8 wherever it lands — tool-call JSON parameters, file content, serialized JSON — never as `\uXXXX` escapes; in code, `json.dumps(..., ensure_ascii=False)` for output humans or agents read. Exempt: escapes JSON itself requires, and code/fixtures where the escape is the point.

### Config ([02](conventions/02-config.md))

- Put values that vary by run, experiment, deployment, or environment in resolved config; keep fixed algorithm and format invariants as named code constants. Compose experiment axes only where needed and fail fast on invalid config.
- Do ablations via config combinations without code changes. Experiments and durable data-processing outputs save their resolved config, git hash, and invocation for reproduction.
- Externalize LLM prompts into dedicated `.md` files rather than inline string literals, so they can be edited and reviewed without a code change.

### Environment ([03](conventions/03-environment.md))

- uv (commit uv.lock) + ruff + pre-commit/CI. Dev tools go in `[dependency-groups]`.
- ML projects targeting both local macOS (CPU/MPS) and remote Linux (CUDA) keep their source portable across those hosts; uv platform markers or `--torch-backend=auto` can route PyTorch installation.
- Where CPU fallback is required, select the device through one helper and avoid inline `.cuda()`.

### Secret Management ([13](conventions/13-secret-management.md))

- Never hardcode secrets in code, config, logs, or images; never commit a plaintext `.env` (`.gitignore` + `.env.example` lists keys only). The single source of truth is a central secret manager (Infisical recommended).
- Supply secrets to local, CI, and container environments alike via runtime injection (`infisical run -- <cmd>`), with no plaintext left on disk. Where an artifact on disk must be restricted, restrict every file carrying the content — a sidecar at `0600` beside its data at `0644` reads as protected and is not. Code reads secrets as env vars as usual (`os.environ[...]`). Coding agents follow the same rule, and in a session whose transcript an AI or a log retains they never run commands that print secret values (`infisical export`, `infisical secrets`) or dump the environment (`env`, `printenv`, `echo $KEY`).
- Containers/CI authenticate via machine identity (Universal Auth) with least privilege and short-lived tokens. Separate environments (dev/staging/prod) + rotate + scan with gitleaks (pre-commit/CI). Immediately rotate and reissue any secret that was already committed.
- An MCP server's credential is never a value in its config: it is injected into the server's process, not the agent's, so the secret stays out of what the agent inherits. That is not out of its reach — the agent's own shell holds the same login — so in CI the server runs outside the agent's job under its own machine identity. A variable reference belongs only in `env` or headers, never in arguments or a URL, and its fallback default is never a secret; adding a server with an inline value writes that value to a file outside the secret scan. The server keeps the upstream credential itself and accepts only tokens issued to it — no token passthrough.

### Agent Sandboxing ([25](conventions/25-agent-sandboxing.md))

- Bound an agent by filesystem and network isolation together; permission prompts and auto mode's classifier are layers inside that boundary, never the boundary. A boundary counts only for what it encloses — the OS sandbox covers Bash alone and a git worktree covers nothing — and a lane the harness runs unattended is a session under these rules.
- Run a mode that removes every check only inside a container or VM that nothing reopens to the host, and review what the agent wrote into the bind-mounted workspace before running any of it on the host. Inject each credential into the process that uses it, not the agent's environment; one that must be out of reach stays outside the boundary, behind a proxy.
- A session holds at most two of untrusted input, secrets or private data a callable tool can reach, and a tool that changes state or communicates externally; with untrusted input present drop one of the other two, and a session needing all three is either supervised — each write or send passes a person — or split, so an unattended lane reads no untrusted text at all and takes what the work needs from outside in its brief. A subagent's summary of untrusted text is still untrusted.
- A CI job running an agent gets only the token scopes, persisted credentials and secrets its step uses, declared in the workflow rather than inherited from a default. Every event carrying a stranger's text is untrusted whoever triggered the run; on a privileged trigger never check out the untrusted head or interpolate event text into a command.

### Pipeline ([04](conventions/04-pipeline.md))

- Data-processing stages expose a bounded sample mode and optional bounded diagnostic dumps where inspection helps.
- For workloads that exceed the memory budget or are costly to restart, process incrementally and resume only from outputs whose completion and input identity are validated. Publish durable output atomically or with an equivalent completion protocol; stream or chunk when full materialization is too costly.
- Long-running tasks show tqdm/rich progress + log processing throughput.
- A bottleneck stage may be ported to a compiled language under 05's conditions; the stage rules apply unchanged, so the stage boundary is the language boundary.

### Performance ([05](conventions/05-performance.md))

- Set expected scale, time or throughput, memory, and relevant cost targets. Start with a correct measurable implementation; profile when it misses a target or repeated-run cost is material.
- Reduce rows, columns, work, and I/O first; improve algorithms, joins, batching, layout, and serialization before adding concurrency. Tune DataLoader and CPU/IO concurrency only for a measured bottleneck.
- Log the stage and resource metrics needed for the decision. Compare correctness, end-to-end elapsed time, peak memory, and cost on the same representative input in a comparable environment before claiming an improvement.
- Language follows the measured bottleneck: port a stage to a compiled language (Rust/PyO3, or a standalone binary) only when it profiles CPU-bound in pure computation, its inputs and outputs are files only, and the Python-side options were measured and fail the throughput criterion the module contract carries (a contract without one makes the module no candidate); the port must build and run unmodified on both hosts 03 names. A port is a rewrite (→ 00, 06, 19).

### Testing & Verification ([06](conventions/06-testing-verification.md))

- Start with the narrowest existing check that reaches changed behavior. For a new flow or entry point, use a representative sample run through the real entry point; an entry point alone does not justify a new test file.
- Add a durable test only when a realistic new behavior, recurring defect, or critical invariant is missed by existing checks. Remove tests that repeat a sample run or assert implementation structure rather than caller-visible behavior; do not chase line coverage.
- A sample run enters where a user or caller enters, mocks no module of your own, runs on a small stored sample, and follows the real sequence of stateful commands — testing commands in isolation hides defects in their order. A lane runs its own stage on the frozen boundary sample it consumes, or its own input sample where its stage comes first; a lane whose entry point imports its siblings, and the assembled project's run, belong to no lane and run on the merged head after the merge.
- Contracts exist only where parallel lanes meet, and they are files, not tests; single-flow work is covered by its sample run. A lane boundary's contract is its sample payload plus a contract file naming each crossing symbol under its caller's name and signature, the value set both sides branch on, and which side calls which. Both are written before the lanes start and owned by none.
- The boundary sample carries every value-set member as rows: it is the consumer lane's sample-run input, and a run checks only what its input carries. A boundary whose payload lands as JSON/YAML/TOML also gets a JSON Schema (draft 2020-12, `minItems: 1`, closed objects, `enum` for the value set): the sample must pass it at freeze, and the producing lane's criterion wipes its dump, re-runs, and checks the fresh output with a pinned `check-jsonschema`. Names, signatures, call direction and schema-less boundaries stay with review — each lane's reviewers, then the merged-whole review. An object crossing more than one lane boundary gets a single sample that every contract file points at: two samples for one object are two definitions nothing compares.
- Build each stored payload so only the correct rule reproduces it — two properties that coincide in the sample let every implementation confusing them pass, so vary one of them in the file. A double may not assert a shape the real system never produces: confirm it against the real thing once and keep that check. No test patches over one of your own components — the substitution does not merely weaken an assertion, it removes that path from the run. Isolate a fixture from the machine it runs on and from the tests that already used it; a module-scoped fixture handed out by reference or shallow copy carries one test's mutation into the next. A sample or stored input taken from real data or traffic has its personal and customer fields replaced before it is committed — the secret scan does not catch them.
- Justify each test: is there a realistic change that would break it, does it catch that change when no other test does, could it ever fail? Reduce the assertion to answer the last — a constant compared to a constant, or two sides through the same normalisation, is an identity wearing a test's name. A test that has never failed is a deletion candidate, and a test that fails when behaviour did not change is its mirror: a change-detector asserting implementation structure catches no defects and taxes every change — delete it or re-point it at the public behaviour.
- Derive expected values from the specification, never by running the code under test and recording what it returns — a recorded output is true by construction, the default failure when one session writes both the implementation and its tests. The one capture allowed is characterization from the base-commit code before a rewrite. Golden values need a source other than the code under test, they update only via an explicit flag, and that diff is reviewed against the specification. Non-deterministic output (LLM text) gets property assertions only; its quality is judged statistically.
- Cover each planned completion criterion with an existing or new executable check, or a recorded `[human]` verdict. A reused check needs no new red run. For a justified new test, observe a real failing baseline; where behavior already exists, temporarily break it and confirm the test fails. A command that could not run is `NO-BASELINE`, not a failing test.
- Decide a bug fix by reproducing the defect before and after, with command and decisive output in the fix commit's `## Result`. Add a durable guard when a serious defect can recur and existing checks miss it. Inspect the fix's neighboring paths. Before completion, run the narrowest relevant verification and broaden only for a concrete remaining risk or required gate.

### AI/ML ([07](conventions/07-ml-development.md))

- Set seeds through a single unified helper. Training/inference import the same preprocessing function (no duplication); check skew with a train/serve assertion inside the sample run. Choose bf16 or optimized attention only when supported and representative checks show acceptable quality and performance.
- Every run is logged to an experiment-tracking tool (Trackio by default; MLflow when self-hosting is a strong requirement) along with its config + commit. Save last-N + best + milestone checkpoints to a network volume/HF Hub. Design training to assume interruption (resumable).

### LLM ([08](conventions/08-llm-development.md))

- Route frameworks by use case (single GPU → Unsloth/TRL, multi-GPU reproducibility → Axolotl, RL → TRL+vLLM, pretraining → torchtitan). torchtune is no longer actively maintained — do not adopt it for new work. Select FSDP2 and bf16 when supported and justified by the workload; checkpointing, optimized attention, and packing require measured quality, time, and memory tradeoffs.
- Chat templates use `apply_chat_template` as the single source; golden-test string identity between training and inference; specify sampling parameters explicitly in config.
- Evaluation records even the harness/task version, fewshot count, and whether a template was applied. Judges use bidirectional ordering + cross-family + length-aware rubrics.

### Framework Wrapping ([22](conventions/22-framework-wrapping.md))

- Test code that drives someone else's training framework through a layer that imports the real package; a double encodes your reading of the source and can never contradict you.
- Shrink the fixture's expensive dimension and keep its structure (config-only tiny model, random weights, the real artifact's identifiers), run it inside the image that ships the framework with your code mounted over the installed copy, and judge with the production gate function rather than a copy.
- Write every deviation the fixture forces into the code at the deviation, state what the layer cannot catch and keep that on the expensive hardware, and make each double able to express the asymmetry it claims to catch.

### Remote GPU Iteration ([23](conventions/23-remote-gpu-iteration.md))

- Keep the loop free of image rebuilds and git round trips: the image supplies dependencies, the working tree reaches the remote by direct sync.
- Every training/evaluation entry point has a `--smoke` mode (real tokenizer, config-only tiny model, a handful of samples, one or two steps, local CPU/MPS) and passing it is the precondition for occupying a GPU; what smoke switches off is recorded as 22 requires of fixture deviations.
- Open every entry point with a preflight that runs before the model or dataset loads (config, first-batch schema, one decoded batch for label masking, output-path writability). Reproduce a remote failure locally by replaying the failing stage on its dumped input.

### LLM API Inference ([10](conventions/10-llm-api-inference.md), [11](conventions/11-llm-api-providers.md), [12](conventions/12-upstream-docs.md))

- Provider abstraction is a thin native SDK adapter + a pure payload builder (checkable at the SDK boundary without network access). "OpenAI-compatible" covers only the wire format — capability/schema/error/token mapping is isolated per provider.
- Use async calls and per-model caps when request volume benefits from concurrent waiting; add adaptive rate-limit control when fixed caps miss throughput or error targets. Classify errors as typed exceptions, keep one retry owner, and isolate failed batch tasks.
- Structured output uses a lowest-common-denominator schema + tiered fallback (native schema → json_object+prompt → parsing → validate-and-retry, capped at 2-3 attempts). Classify `finish_reason` before parsing. No sampling parameters on reasoning calls.
- Response caching is dev/debug-only. Resume must verify a fingerprint (spec+seed+data+prompt). No hardcoding prices/model names — pin dated snapshots, log tokens+cost per row, and cap the budget.
- Before writing provider API code, fetch and check the official docs from the canonical URL registry. For SDK usage, prefer the provider's official skill over ctx7; for exceptions/signatures, use the installed SDK source; confirm behavior not in the docs with an empirical smoke test.

### Agentic Workflow ([09](conventions/09-agentic-workflow.md))

- Keep CLAUDE.md/AGENTS.md concise (bloat causes rules to be ignored), layer them per module — each AGENTS.md with its sibling CLAUDE.md, which Claude Code loads when it reads files in that directory ([15](conventions/15-doc-tracking.md) §1) — and put occasionally-used knowledge into Skills. Keep instruction anti-patterns out of them too: verification rituals, thoroughness boosters, redundant procedures/scratchpads, stale long-reasoning examples, contradictory rules, and dated configuration all cost tokens on current models without adding capability.
- Use the direct path for small reversible work; delegate when independent context or parallel work justifies coordination cost. For planned parallel work, git worktrees isolate writes to disjoint files; overlapping ownership runs sequentially. Record owners, dependencies and integration points, freeze shared contracts, and give locks/migrations one owner. Name a subagent's report channel and confirm it delivered content.
- Merge each branch only after its completion criteria and CI-enforced checks such as lint pass (→ 18, 06, 03) and its review has closed with no blocker (→ 20). The integration runs — one to three per project — happen at a single point, on the merged head after the last merge, not once per lane. Route models on two axes, tier and effort, not tier alone — a stronger model at lower effort can beat a weaker model pushed to high effort, so choose effort per task and re-choose it whenever the model changes rather than carrying the old setting over.
- A merged lane is a closed lane: once the integration runs are green and, for multiple lanes, the merged-seam review has closed (→ 20), remove its worktree and delete its branch (`git worktree remove` without `--force`, `git branch -d` never `-D` — refusals are safety signals). Halted lanes keep theirs; fix rounds resume there.
- Write heavyweight spec documents only when they are an asset shared across PRs or workers; small or exploratory work uses lightweight iteration.

### Context Management ([14](conventions/14-context-management.md))

- Delegate substantial independent exploration when the context saved outweighs coordination overhead; small focused reads can stay in the main context. Dispatch independent work in parallel when useful and run long checks in the background when they block other work.
- Pipeline the stages; do not put a barrier between them. A barrier is justified only when the next stage genuinely needs every result of the previous one at once — "I need to flatten the results first" and "the stages are conceptually separate" are not barriers, and neither is review (→ [20](conventions/20-review-gate.md)).
- Keep the source of truth in files, not the conversation — persist plans/decisions/progress to external files and checkpoint at every milestone. Keep durable rules/facts in CLAUDE.md (loaded every session, re-injected after compaction) and in auto memory (survives `/clear`, but it is a setting that can be off — check before relying on it).
- Only the root CLAUDE.md and auto memory (when enabled) reliably survive a context reset; the conversation does not. Use `/compact <focus>` before it triggers automatically, `/clear` between unrelated tasks, and re-check git status, cwd, and state artifacts right after any resume.

### Development Loop ([21](conventions/21-development-loop.md))

- First choose the direct `auto` path or the planned `reviewed`/`proven` loop. The planned loop interviews, splits, judges and delegates; the direct path records its purpose, relevant check and result without plan artifacts.
- Specify by interview, not by template. Derive the axes from this project: infer from the request and the repository, check once for what recent practice adds, then keep only those naming a way this project could fail. Keep the list open during the interview and record each axis's state — that record is the only account of what was never asked.
- Challenge a `proven` plan before asking for approval. A `reviewed` plan does not require a separate plan-review round.
- Split as far as disjoint file ownership allows, and freeze every boundary with a contract file, sample and (for JSON/YAML/TOML payloads) schema written **before** the lanes start, owned by no lane; separate files do not stop two lanes holding contradictory assumptions about what crosses between them.
- Review a lane the moment it finishes, using one comprehensive reviewer for `reviewed` and expanded lenses for `proven`. Send blockers back to the author and re-review the fix.
- Merge a lane only after its criteria pass and run the integration lane last. For multi-lane work, review the assembled seams and check the end-to-end condition before claiming completion.

### Work Contract ([18](conventions/18-work-contract.md))

- The terms the conventions share — pass, run, round, round cap, review report, end-to-end condition, integration run and lane, producer, unit, lens, fixed review points — are defined once in 18 §1.
- Write the contract before development starts and freeze it during execution. Record changes with a kind (additive/narrowing/breaking); an additive change that touches no existing criterion or ownership boundary updates only the affected lane.
- A plan shown for approval carries a review points table: the pre-approval row carries its exit at approval, and every other row carries one by completion.
- Write completion criteria in EARS or Given-When-Then with `SHALL`, and apply the judgment test: if two agents could disagree about whether it passed, rewrite it.
- Pair every criterion with the command that checks it, or mark it `[human]`. The two halves fail differently: a command with no sentence is never asked whether it checks the right thing, and a sentence with no command defers the judgment to verification time.
- The command must reach a verdict inside the lane that owns the criterion, against that lane's work alone — a command importing a sibling lane's module fails on import and says nothing about the lane it was given to. The end-to-end condition, which is what checks a cross-lane contract file, belongs to no lane: it is checked on the merged head after the last merge.
- Enumerate boundaries by where two lanes could believe differently, not by what data passes between them: payload shape, the name and signature of every symbol one lane calls in another, the accepted value set of a field, and the call graph itself. A consumer-only lane sends nothing outward, so a payload-derived list leaves the widest call surface uncontracted.
- Cover functional, non-functional, and **negative** criteria (what must not happen), and state what is out of scope. A three-to-five-line contract is complete for small work.
- Choose `auto` only for narrow reversible work without external effect, shared boundary, security or data-loss risk; it needs no plan or independent review. `reviewed` is the planned default with one independent unit review; `proven` covers hard-to-reverse or high-impact work with plan challenge, expanded review and a representative real-input run. Every planned criterion needs a check or recorded human verdict; new tests for changed behavior, recurring defects or critical invariants need failing-baseline evidence.
- Reused existing checks and standing invariants need no red record. A new test that could not run at the base commit needs a meaningful failing check after implementation, not a missing-file exit presented as red.
- Give every lane a disjoint set of owned paths — directory prefixes where the work divides that way, cross-cutting files named individually with one owner each, since a prefix rule cannot assign a README or an ignore file. When several kinds of change land in the same documents, slice by file rather than by phase. Assign lock files, migrations, and generated files to a single owner. Record model tier and effort level per lane, never a model id.

### Evidence ([19](conventions/19-evidence.md))

- For planned work, report criteria with each exact command, exit status and decisive output. A concise summary may explain the result; retain full output for failures or when needed to investigate a high-risk claim. Direct `auto` work records the relevant check and result without a plan table.
- Record status as a word (`PASS`/`FAIL`/`PENDING-HUMAN`/`NO-BASELINE`), never a symbol. A reused existing check needs no red evidence; a new test's failing-baseline record stays beside its result.
- Mask secrets in the command line and environment as well as the output, before evidence leaves the machine — the pre-commit scan never sees gitignored artifacts.
- Block completion on `PENDING-HUMAN` at every done level; a human criterion passes only once a verdict, its author, and its timestamp are recorded.
- Name the commit and whether the tree was clean. Record every bypass with its reason — a skipped gate and a passed gate must never look alike in the record.

### Review Gate ([20](conventions/20-review-gate.md))

- `auto` may finish without an independent reviewer. Planned work uses a reviewer who gets the diff and criteria without the author's reasoning; `reviewed` uses one comprehensive unit review, and `proven` expands the lenses. Security review follows actual trust-boundary risk. Multi-lane work gets a merged-seam review; `proven` also challenges the plan before approval.
- A reviewer reports the exact number of commands run. Zero commands is a reading-only review: its source findings may stand, but it does not confirm runtime behavior. Completion claims about behavior use execution evidence from the relevant checks and independent criterion recheck.
- Review inputs are chosen for the risk: the comprehensive lens sees the diff, callers, conventions and missing requirements; expanded `proven` lenses inspect module, project and absence separately. A fresh-reader lens applies where an explainer needs its intended reader's comprehension checked. At applicable `proven` plan and merged points, Claude and Codex review in parallel, with the documented Cursor fallback.
- Fan-out requires fan-in, owned by the dispatching orchestrator: confirm every lane answered *with content*, dedupe by `file:line`, resolve contradictions, verify each finding against the code, rank by severity. A lane that finished is not a lane that answered — an agent can end with its report undelivered. Whatever one lane returns unchecked is multiplied by the lane count, so an unsynthesized merge hands the noise to the human.
- Mark every finding as confirmed by a run, refuted by a run that reproduced nothing, or inferred from reading with zero commands. A refutation is reported as a result. A reproduction that will not run — a gate the change added rejects the input, a state that can no longer be constructed — is a finding about the procedure and never evidence of a fix.
- Severity carries an action: blocker blocks the merge and is re-reviewed by the lane that raised it, major is fixed in the same work, minor becomes a follow-up, nit may be ignored. A finding with no concrete failing scenario is a nit.
- Lanes never switch branches in a shared worktree — one checkout erases every other lane's subject. Pin the review to two explicit commits and do not move the branch while lanes read it: a tool given only a base diffs against whatever HEAD currently is and silently re-targets itself when the dispatcher commits, so the lane reports on a subject nobody asked about — give each lane `<base>..<head>`. A finding that depends on a tool's behaviour names the version tested, and it must be the version the project pins.
- Vendor diversity is paid at the applicable `proven` plan and merged-whole points; unit reviews record the tool that answered. Don't pin model ids in the docs — resolve them at use time and pick by role. For a new or changed critical gate, confirm that it rejects the failure it was added to catch.

### Doc Tracking ([15](conventions/15-doc-tracking.md))

- Docs are split into 4 tiers: for input/output contracts, code is the single source (no hand-written docs); module logic goes in a per-directory AGENTS.md, with the sibling CLAUDE.md that imports it for Claude Code (§1 states when to create one); overall flow goes in ARCHITECTURE.md + Mermaid (generate dependency graphs with a deterministic tool); decision history uses structured commit bodies (record reversed decisions and rollbacks too, with reasons — git log is where they are searched for).
- Agents regenerate only inside `docsync:managed` markers (human sections are off-limits, stamped with a verification commit). Factual claims in managed docs must be citable to a code location (decision rationale/failure history go in human sections or the commit body); the primary update mechanism is incremental sync at change time — periodic runs are audit-only (dead-man's switch + blind-rebuild hallucination audit; semantically equivalent phrasing is not drift).
- When a human edits a managed section, record a reason code so future generation accounts for it (RMA). Include a "code change ↔ doc update consistency" check in the review gate.
- When something ships, update what distributes it in the same change — the installer, the getting-started page, the excerpt loaded elsewhere, the published site's navigation. Docs-follow-code covers the description; nothing covers the delivery path, and that is the one that leaves a working artifact unreachable.
- A copy that drifts is worse than a wrong original: it is loaded everywhere and matches nothing. Prefer a generated excerpt — marker blocks filled verbatim from Core Rules by `scripts/fill-excerpts.py`, which regenerates or fails loudly when the source moves. A hand-authored excerpt instead carries a header naming its source document and commit, checked automatically.

### Explainer Docs ([24](conventions/24-explainer-docs.md))

- An explainer — report, guide, tutorial, HTML artifact, anything whose product is a person's understanding — is judged against its intended reader. Code-adjacent docs (AGENTS.md/ARCHITECTURE.md) are the other genre and stay lean.
- Gloss every term the intended reader wouldn't know at first use. Never name a methodology without its mechanism — what it does and why it solves this problem, or what breaks without it; "uses X" alone is a violation.
- Pair every non-obvious concept with one concrete example: an input→output pair, a before/after, or a scenario.
- Open every mechanism section with a one-sentence definition in words the reader already has; if it cannot be written, the section waits. Choose one analogy for the document's central contrast and carry it through every section that touches it — a second analogy only for what the first cannot carry.
- Visualize by what is shown: structure → diagram (Mermaid in markdown, inline SVG in HTML); 3+ quantities, a trend, or a distribution → table plus one sentence, or an inline SVG chart in HTML; a concept text cannot carry → HTML only, with the same explanation in text. Single facts stay prose; a visual that cannot be introduced as "this shows X" in one sentence is decoration and gets cut.
- Size by the fresh-reader test, not word count: the intended reader can re-explain each mechanism and act without follow-up questions — and nothing longer. Layer as summary → body with examples → deep detail.
- HTML explainers ship as one self-contained file: no external network dependencies, encoding declared in the file, system fonts rather than embedded ones, diagrams inline, text selectable and greppable — and flow body content as one column of readable line length, sections in reading order, with no fixed sidebars (the table of contents goes inline at the top; two small figures may sit side by side). Use a fresh-reader review when the intended audience or mechanism makes comprehension a completion criterion.
- Each visual in an HTML explainer is designed from the trigger table and the mechanism it must show, never from a form picked first; every figure carries the same accessibility contract — no role on `<figure>`, which would cascade onto every descendant, but `role="img"` with a short label on the `<svg>` inside, and no meaning carried by color alone. Numeric runs use a monospace face with tabular figures while Korean labels keep the body face.

### Research Protocol ([16](conventions/16-research-protocol.md))

- Use prior knowledge only to form search queries and hypotheses — never to fix the candidate set or to populate facts in a deliverable. Every factual claim must be traceable to a source fetched in this research; mark anything not found as "unverified — needs research" (never fill gaps from memory).
- Confirm enumeration facts (variants, sizes, dates, licenses) only from the official registry. Search snippets, leaderboards, and blogs are leads, not evidence; when a semantic search tool (exa) is available, use it to discover sources — its results are leads too, so fetch the canonical page before asserting. Establish completeness by querying the registry directly, not by search ranking. Don't assert negative/universal claims ("doesn't exist / all of them / the smallest is N") without primary-source enumeration.
- Fetch each in-scope vendor's/library's official latest page at least once; seed already-cited repo URLs as must-fetch. If it contradicts an existing doc, resolve via the primary source and record the resolution.

### Commits ([17](conventions/17-commit-protocol.md))

- Headers use Conventional Commits (English type/scope, ≤72 characters) — type is one of `feat` `fix` `refactor` `perf` `docs` `test` `chore` `build` `ci` `style` `revert` `exp`, the optional scope is the module or area, and a `!` after type/scope marks a breaking change; summaries and bodies are written in Korean — so git log doubles as a Korean research note. `feat`/`fix`/`refactor`/`perf` commits require a `## Why/What/How/Result` body (the commit-msg hook warns otherwise).
- Never fabricate Result/numbers (write "not measured" instead) — except that a `fix` commit's Result must carry the before/after reproduction 06 requires, masked first because a commit body is pushed (secrets per [19](conventions/19-evidence.md) §2, personal and customer fields per [06](conventions/06-testing-verification.md) §5). Before committing, classify changes by intent so one logical unit = one commit (split hunks with `git add -p`). Link research threads with the `Experiment:` trailer.
- No emoji in the message (header, body, or trailers) — `git log` is read and grepped as plain text.
