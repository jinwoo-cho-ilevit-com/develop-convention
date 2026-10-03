# Development Conventions

A collection of development convention documents. Composed of general-purpose development rules plus pipeline rules, consumed by both humans and AI agents.

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
| [02-config.md](conventions/02-config.md) | No hardcoding, composable config groups, run snapshots, LLM prompts externalized to `.md` files |

### Commit — `commit`

| Doc | Contents |
|---|---|
| [06-commit-protocol.md](conventions/06-commit-protocol.md) | Conventional Commits header (English type/scope) + Korean body (Why/What/How/Result), trailers, logical-unit splitting |

### Data and ML pipelines — `ml-pipeline`

| Doc | Contents |
|---|---|
| [03-pipeline.md](conventions/03-pipeline.md) | Bounded sample debugging, resumable and atomic output, memory-budgeted processing, progress monitoring |

### External sources — `external-sources`

| Doc | Contents |
|---|---|
| [04-upstream-docs.md](conventions/04-upstream-docs.md) | Latest-docs reference procedure (5 tiers), per-provider canonical URL registry, smoke-test confirmation |
| [05-research-protocol.md](conventions/05-research-protocol.md) | Fact research protocol: prior knowledge is for queries only, every claim needs a source from this research, source tiers, verification of negative/universal claims |

## How to Apply to a New Project

```bash
claude plugin marketplace add jinwoo-cho-ilevit-com/develop-convention
claude plugin install dev-harness@develop-convention
claude plugin update dev-harness
```

Run `/dev-harness:setup` once in each project. It writes the short `AGENTS.md` the plugin cannot know (run/test/lint/smoke commands) and the `CLAUDE.md` line that imports it. Python projects can also copy [templates/pyproject.toml](templates/pyproject.toml) and `templates/.pre-commit-config.yaml` for the local tool configuration.

Skills load themselves when the work matches, so you do not have to remember which rules apply:

| Skill | Loads when |
|---|---|
| `code-and-config` | Files appear or move, config or dependencies change |
| `commit` | A commit is about to be written |
| `ml-pipeline` | A preprocessing, training, or evaluation pipeline is being built, or a model is trained or served here |
| `external-sources` | Code calls someone else's SDK or model API, or external facts are the deliverable |

**Note for cloud-executed agents**: with the plugin installed, `conventions/` travels inside it and its skills read from there. In isolated sandboxes without the plugin (Codex cloud, Cursor background agents, Claude Code web), read the published docs at <https://jinwoo-cho-ilevit-com.github.io/develop-convention/>, or add this repo as a git submodule so a local path resolves there too.

## Full Rule Summary (for Agent Injection)

Link index; the rules are each document's `## Core Rules`.

### Principles ([00](conventions/00-principles.md))
### Structure & Naming ([01](conventions/01-structure-naming.md))
### Config ([02](conventions/02-config.md))
### Pipeline ([03](conventions/03-pipeline.md))
### Upstream Docs ([04](conventions/04-upstream-docs.md))
### Research Protocol ([05](conventions/05-research-protocol.md))
### Commits ([06](conventions/06-commit-protocol.md))
