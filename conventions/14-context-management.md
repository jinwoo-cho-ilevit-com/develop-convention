# 14. Context Budget Management

## Core Rules

- The main context is the orchestrator. Keep only conclusions, and delegate exploration, search, and large reads to subagents, receiving only summaries back — subagents run in a separate context window and don't pollute the main one (→ [09-agentic-workflow.md](09-agentic-workflow.md)).
- Don't sweep directories or read through large files in the main context. Before reading directly, ask "can a subagent return just the answer?" — if yes, delegate.
- Dispatch independent tasks in parallel in a single batch, and run builds/tests in the background to reduce bottlenecks. However, guard against over-parallelization (merge/review overhead) with empirical measurement.
- Keep the single source of truth in files, not in the conversation. Persist plans, decisions, and progress to external files, and treat conversation context as a volatile resource that can be summarized or lost at any time.
- Put rules and facts that must persist in CLAUDE.md and auto memory (both survive compaction and `/clear`). Don't rely on conversation history to remember rules.
- At every milestone, checkpoint "done / next / key decisions / relevant file paths" into a handoff document. Design work so it can resume as an externalized task.
- Clear context with `/clear` between unrelated tasks. If two corrections don't fix things, `/clear` the contaminated context and restart with a better prompt.
- When compaction is imminent, don't wait for it to run automatically — use `/compact <focus>` to specify what to keep, or summarize to a file first. Specify what to preserve in CLAUDE.md's "Compact Instructions".
- Immediately after resume or compaction, re-check `git status`, cwd, and state artifacts before resuming work (to prevent stale context or working on the wrong branch).

## Details

The two goals — **minimizing the main context** and **preserving context across compaction/clear** — are two sides of the same coin. Sparing the main context delays compaction, and externalizing the source material keeps the main context light. There's one underlying constraint: "the context window fills up fast, and performance degrades as it fills."

Sources: [Claude Code — best practices](https://code.claude.com/docs/en/best-practices)

### 1. Minimizing the Main Context (Context Firewall)

- **Delegate to subagents**: Investigating a codebase means reading many files, which consumes context. A subagent investigates in a separate context window and returns only a summary, so the main context stays clean. Exploration like "investigate how auth token refresh is handled" should be done by a subagent, not the main context.
- **Structured returns**: Receive delegated results as schema-validated, compressed data — file dumps shouldn't accumulate in the main context.
- **Check usage**: Use `/context` to check what's occupying the context (memory files, MCP tools, skills, conversation). MCP tool definitions are deferred (lazy-loaded) by default, and rarely-used skills can be hidden with `skillOverrides`.
- **Minimize bottlenecks**: Dispatch tasks with no dependencies in parallel within a single message, and run long-running work (builds, tests) in the background. Prefer pipelining (streaming) over a barrier (waiting for everything).
- **No re-derivation**: Don't re-read or re-derive facts that have already been established.

Sources: [Claude Code — best practices](https://code.claude.com/docs/en/best-practices), [subagents](https://code.claude.com/docs/en/sub-agents)

### 2. What survives a context reset

Only two things reliably come back: the project root `CLAUDE.md`, re-injected from disk, and auto
memory. Subdirectory `CLAUDE.md` files return only when a file in that directory is read, and the
conversation itself does not return at all — `/compact` replaces it with a summary and `/clear`
discards it. That asymmetry is the whole argument for externalizing state to files.

Compaction settings, command flags, and their exact behaviour belong to the vendor and change
faster than this document: [memory](https://code.claude.com/docs/en/memory),
[commands](https://code.claude.com/docs/en/commands), [settings](https://code.claude.com/docs/en/settings).

### 3. Preventing Context Loss (Externalization + Persistent Memory)

- **Source material into files**: Record plans, decisions, and progress in `PLAN.md`/`PROGRESS.md`/`DECISIONS.md` or handoff artifacts (e.g., `.omc/handoffs/`). These files aren't automatically loaded into context, but the source material survives compaction and can be read again at any time.
- **CLAUDE.md**: Loaded at the start of every session and re-injected after compaction. Commit it to git so the team shares it. Keep each file under 200 lines, and split rules by file type into path-scoped `.claude/rules/` so they load only when matched.
- **auto memory**: Learnings, build commands, and debugging insights that Claude records on its own. Survives both compaction and `/clear`. Split detailed notes into topic files to keep `MEMORY.md` concise.
- **Checkpointing**: Update state in the handoff document at every milestone. `/rewind` (or pressing Esc twice) can roll back conversation and code state from a snapshot, but this is separate from git — it only tracks changes made through Claude's tools, not changes made via Bash.
- **Re-orientation**: Keep persistent rules in CLAUDE.md, not in conversation history. Immediately after resume or compaction, check `git status`, cwd, and state artifacts first before continuing work.

For an individual, auto memory plus handoff files are sufficient; a team should share persistent rules via the project CLAUDE.md (committed to git), while keeping it distinct from personal, local auto memory.

Sources: [Claude Code — memory](https://code.claude.com/docs/en/memory), [best practices](https://code.claude.com/docs/en/best-practices)
