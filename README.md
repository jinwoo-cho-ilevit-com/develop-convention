# Development Conventions

A collection of development convention documents. Composed of general-purpose development rules plus AI/ML and LLM-specific rules, consumed by both humans and AI agents.

Each doc starts with `## Core Rules` — imperative rules an agent can act on — followed by human-oriented details and sources. Specific factual claims carry a source fetched in research (2025-2026); a claim no primary source confirmed is marked unverified.

The [`dev-harness` plugin](#how-to-apply-to-a-new-project) in this repository routes to these rules rather than copying them: install it once and the conventions, hooks and skills come with it.

## Document Map

Numbers are stable identifiers, not a reading order. Every group after Principles is also a skill: install the plugin and it loads itself when that kind of work starts. The skill routes to these documents and never copies them, so what you read here is what an agent reads.

### Principles

| Doc | Contents |
|---|---|
| [00-principles.md](conventions/00-principles.md) | Core principles: proportional complexity, behavior-grounded changes, evidence over claims, fact-based judgment, empirical measurement |

Takes precedence over every other document, so it belongs to no single skill and every skill points back at it.

### Code and config — `code-and-config`

| Doc | Contents |
|---|---|
| [01-structure-naming.md](conventions/01-structure-naming.md) | Module separation, flat layout, semantic naming, comment/emoji policy, literal UTF-8 over `\uXXXX` escapes, dead code/duplication removal |
| [02-config.md](conventions/02-config.md) | No hardcoding, composable config groups + validation, run snapshots, LLM prompts externalized to `.md` files |
| [03-environment.md](conventions/03-environment.md) | uv/ruff toolchain, one codebase running unmodified on local macOS/CPU and a remote Linux/CUDA host, device abstraction |

### Commit — `commit`

| Doc | Contents |
|---|---|
| [17-commit-protocol.md](conventions/17-commit-protocol.md) | Conventional Commits header (English type/scope) + Korean body (Why/What/How/Result), trailers, logical-unit splitting |

### Verify and report — `verify-and-review`

| Doc | Contents |
|---|---|
| [06-testing-verification.md](conventions/06-testing-verification.md) | Smallest relevant existing check first, durable tests only for distinct realistic failures, selective red evidence, sample runs, trustworthy fixtures, completion verification |
| [19-evidence.md](conventions/19-evidence.md) | Evidence artifacts: exact command, exit and decisive output, provenance, secret masking, human verdict records, recorded bypasses |

### Data and ML pipelines — `ml-pipeline`

| Doc | Contents |
|---|---|
| [04-pipeline.md](conventions/04-pipeline.md) | Bounded sample debugging, resumable and atomic output, memory-budgeted processing, progress monitoring |
| [05-performance.md](conventions/05-performance.md) | Scale/time/memory/cost targets, end-to-end measurement, algorithm and I/O before concurrency, conditional profiling |
| [07-ml-development.md](conventions/07-ml-development.md) | Seed/reproducibility, train-serve skew prevention, experiment tracking, checkpoints/spot pods |
| [08-llm-development.md](conventions/08-llm-development.md) | Training framework routing, FSDP2/bf16, chat template consistency, evaluation reproducibility, LLM-as-judge, data |
| [22-framework-wrapping.md](conventions/22-framework-wrapping.md) | Wrapping a third-party training framework: a test layer that imports the real package, tiny-model fixtures, local-to-remote GPU iteration, `--smoke` mode and preflight |

### External sources — `external-sources`

| Doc | Contents |
|---|---|
| [12-upstream-docs.md](conventions/12-upstream-docs.md) | Latest-docs reference procedure (5 tiers), per-provider canonical URL registry, smoke-test confirmation |
| [16-research-protocol.md](conventions/16-research-protocol.md) | Fact research protocol: prior knowledge is for queries only, every claim needs a source from this research, source tiers, verification of negative/universal claims |

### Doc tracking — `docsync`

| Doc | Contents |
|---|---|
| [15-doc-tracking.md](conventions/15-doc-tracking.md) | Doc-code synchronization: 4-tier tracking (contract, module, flow, history), docsync skill (incremental sync + audit), managed/human markers, generated excerpts |

## How to Apply to a New Project

```bash
claude plugin marketplace add jinwoo-cho-ilevit-com/develop-convention
claude plugin install dev-harness@develop-convention
claude plugin update dev-harness
```

Run `/dev-harness:setup` once in each project. It writes the short `AGENTS.md` the plugin cannot know (run/test/lint/smoke commands) and the `CLAUDE.md` line that imports it (cases in [15-doc-tracking.md](conventions/15-doc-tracking.md) §1). Python projects can also copy [templates/pyproject.toml](templates/pyproject.toml) and `templates/.pre-commit-config.yaml` for the local tool configuration.

Skills load themselves when the work matches, so you do not have to remember which rules apply:

| Skill | Loads when |
|---|---|
| `code-and-config` | Files appear or move, config or dependencies change |
| `commit` | A commit is about to be written |
| `verify-and-review` | Tests are being chosen or run, completion is about to be claimed |
| `ml-pipeline` | A preprocessing, training, or evaluation pipeline is being built, or a model is trained or served here |
| `external-sources` | Code calls someone else's SDK or model API, or external facts are the deliverable |
| `docsync` | Module docs need to catch up with the code that changed (→ [15-doc-tracking.md](conventions/15-doc-tracking.md)) |

**Note for cloud-executed agents**: with the plugin installed, `conventions/` travels inside it and its skills read from there. In isolated sandboxes without the plugin (Codex cloud, Cursor background agents, Claude Code web), read the published docs at <https://jinwoo-cho-ilevit-com.github.io/develop-convention/>, or add this repo as a git submodule so a local path resolves there too.

## Full Rule Summary (for Agent Injection)

Link index; the rules are each document's `## Core Rules`.

### Principles ([00](conventions/00-principles.md))
### Structure & Naming ([01](conventions/01-structure-naming.md))
### Config ([02](conventions/02-config.md))
### Environment ([03](conventions/03-environment.md))
### Pipeline ([04](conventions/04-pipeline.md))
### Performance ([05](conventions/05-performance.md))
### Testing & Verification ([06](conventions/06-testing-verification.md))
### AI/ML ([07](conventions/07-ml-development.md))
### LLM ([08](conventions/08-llm-development.md))
### Upstream Docs ([12](conventions/12-upstream-docs.md))
### Doc Tracking ([15](conventions/15-doc-tracking.md))
### Research Protocol ([16](conventions/16-research-protocol.md))
### Commits ([17](conventions/17-commit-protocol.md))
### Evidence ([19](conventions/19-evidence.md))
### Framework Wrapping ([22](conventions/22-framework-wrapping.md))
