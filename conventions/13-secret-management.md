# 13. Secret Management

## Core Rules

- Do not hardcode secrets (API keys, tokens, passwords, connection strings) into code, config, logs, or Docker image layers (→ [02-config.md](02-config.md)).
- Do not commit a plaintext `.env` to the repository. Register `.env` in `.gitignore`, and commit only a valueless key list in `.env.example`.
- The single source of truth for secrets is a central secret manager. Do not manage secrets across devices/projects by copying files.
- Supply secrets via runtime injection everywhere — locally, in CI, in containers — and never leave them as plaintext residue on disk. Where an artifact on disk must be restricted, restrict every file carrying the content and not only the one easiest to reach: a sidecar at `0600` beside its data at `0644` reads as protected and is not, and a partial defence is worse than none because it stops the next person looking.
- Coding agents follow the same rules: wrap execution commands in an injection wrapper (`infisical run -- <cmd>`), never create or read plaintext secret files, and check required keys against `.env.example`. In a session whose transcript an AI or a log retains, never run commands that print secret values (`infisical export`, `infisical secrets` and its subcommands) or dump the environment (`env`, `printenv`, `echo $KEY`) — a printed value lands in the transcript before any masking applies (→ [13-secret-management.md](13-secret-management.md) §6; masking of evidence is [19-evidence.md](19-evidence.md)).
- Non-interactive environments such as containers and CI authenticate with a machine identity, not a human account. Scope permissions to the minimum and use short-lived tokens.
- Separate environments (dev/staging/prod), rotate secrets periodically, and revoke and reissue immediately upon any leak.
- Run secret scanning (gitleaks, etc.) in both pre-commit and CI to block leaks at commit time (→ [03-environment.md](03-environment.md)).
- Never write an MCP server's credential into its config file as a value. Inject it into the server's process, not the agent's; never in its arguments or URL (§7).
- A committed MCP config (`.mcp.json` and its equivalents) is in the secret scan's scope like any other file; it is not exempt for being tool configuration (§7).
- An MCP server keeps the upstream credential on its own side and accepts only tokens issued to it. Never pass a client's token through to a downstream API (§7).

## Details

The recommended tool is **Infisical** (open source, free cloud tier + self-hosting). It scales from a single personal device to team RBAC on the same store, and its CLI injection approach applies consistently across local, CI, and container environments. 1Password (`op run`), Doppler, HashiCorp Vault, and cloud-native managers (AWS/GCP Secrets Manager) are also viable alternatives as long as they satisfy the principles below (central storage + injection + machine identity).

### 1. Principle: Injection Instead of Storage

Keeping secrets as files makes copying, syncing, and leaking inevitable. Instead, **treat the central store as the source of truth and inject secrets as process environment variables only at the moment of execution**. Instead of a plaintext `.env`, the project folder holds only reference information (`.infisical.json`, no sensitive data → committable) and a key list (`.env.example`).

```gitignore
# .gitignore
.env
.env.*
!.env.example
```

### 2. Local Development Setup

```bash
brew install infisical/get-cli/infisical   # Install CLI (once per device)
infisical login                            # Browser auth (once per device, stored in OS keychain)
cd <project>
infisical init                             # Select org/project → creates .infisical.json
infisical run --env=dev -- <command>       # Inject secrets only at execution time
```

Principle: **one repo (app) = one secrets project**. Don't mix secrets from multiple apps into one project (it makes separating environments/permissions harder). Don't use hyphens in environment variable names — the shell reads `GEMINI_API_KEY-2` as `$GEMINI_API_KEY` followed by `-2`, not as one variable. Use an underscore (`GEMINI_API_KEY_2`) instead.

Sources: [Infisical CLI — overview](https://infisical.com/docs/cli/overview), [usage](https://infisical.com/docs/cli/usage), [run command](https://infisical.com/docs/cli/commands/run)

### 3. Reading Secrets from Code

Injected secrets are ordinary environment variables, so no code change is needed — `os.environ[...]` as usual. Only the launch command changes: `infisical run --env=dev -- python app.py`.

### 4. Containers/CI: Machine Identity

Browser login isn't possible in containers/CI, so authenticate with a **machine identity (Universal Auth)**. Create a machine identity in the dashboard, issue a Client ID/Secret, and add it to the target project with minimal permissions. Credentials are not baked into the image — the deployment platform (K8s Secret, ECS task env, PaaS environment variables) injects them into the container.

```dockerfile
# Install the CLI in the image, inject at the entrypoint (secret values are never baked into the image)
RUN curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | bash \
    && apt-get update && apt-get install -y infisical
CMD infisical run --projectId=$INFISICAL_PROJECT_ID --env=prod -- <command>
```

```bash
# For demo purposes only. Warning: the inline form below exposes the client-secret
# in shell argv (observable via `ps`) and in docker run argv/container config (`docker inspect`),
# so do not use it in production.
docker run \
  -e INFISICAL_TOKEN="$(infisical login --method=universal-auth \
      --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --silent --plain)" \
  -e INFISICAL_PROJECT_ID=<project ID> \
  <image>
```

- **Never pass credentials through argv**: leaving the client-secret/token as a command-line argument or as a literal value in `docker run -e KEY=VALUE` leaves it in the process list, `docker inspect`, and container configuration. Have the deployment platform's secret store (K8s Secret, ECS/Fargate secrets, PaaS secret) inject `INFISICAL_TOKEN` (or the machine identity credentials) directly into the container env, and let the Infisical CLI read that env automatically — bypassing shell substitution and argv entirely.

Inject secret values only at container **startup** and never leave them in image layers. As scale grows, switch from the CLI to the Infisical Agent (sidecar) or the Kubernetes Operator (which syncs Infisical secrets → native K8s Secrets).

Sources: [Infisical — Docker integration](https://infisical.com/docs/integrations/platforms/docker-intro), [Universal Auth (machine identity)](https://infisical.com/docs/documentation/platform/identities/universal-auth)

### 5. Leak Prevention

- Enforce secret scanning before commit. Run `gitleaks` doubly, in both a pre-commit hook and CI, to block hardcoded credentials. Scanning matters more once agents are committing: GitGuardian's State of Secrets Sprawl 2026 measured a 3.2% secret-leak rate on Claude Code-assisted commits against a 1.5% baseline across all public GitHub commits (roughly 2x). GitGuardian's summary gives no sample size or method for that comparison, and cautions against reading it as a tool defect — the developer still decides what gets accepted and pushed — so the control is scanning the commits, not avoiding the tool.
- A secret that's already been committed isn't made safe just by adding it to `.gitignore` — it remains in history, so **rotate and reissue it immediately**, and remove it from history if needed.
- Teams separate dev/staging/prod environments, restrict prod secret access to a minimal set of people/machine identities, and track access via audit logs.

Sources: [gitleaks](https://github.com/gitleaks/gitleaks), [GitGuardian — The State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/) (checked 2026-09-12)

### 6. Coding-Agent Secret Hygiene

An agent session transcript is a log. `infisical run -- <cmd>` injects secrets into the child process env without displaying them, but `infisical export` writes all secrets to stdout by default, and `infisical secrets` / `infisical secrets get NAME` print secret values (with `--plain` printing bare values, one per line) — run inside an agent session, any of these puts plaintext keys into the AI's context and the session log, upstream of where [19-evidence.md](19-evidence.md)'s masking applies (as of: 2026-08).

Projects using Claude Code can additionally deny these commands in `.claude/settings.json` — the `:*` suffix is the documented trailing-wildcard form, matched per subcommand even inside compound commands:

```json
{
  "permissions": {
    "deny": [
      "Bash(infisical export:*)",
      "Bash(infisical secrets:*)",
      "Bash(env:*)",
      "Bash(printenv:*)"
    ]
  }
}
```

Two documented limits: `Bash(env:*)` also blocks benign wrapper uses like `env python x.py` (accepted trade-off), and `echo $KEY` cannot be reliably denied by pattern — the permissions doc states "Bash permission patterns that try to constrain command arguments are fragile" and recommends a PreToolUse hook for mechanical enforcement. So the echo/printf case stays a behavioral rule (Core Rules), with the deny list covering the commands whose sole purpose is printing values.

Sources: [Infisical CLI — export](https://infisical.com/docs/cli/commands/export), [secrets](https://infisical.com/docs/cli/commands/secrets), [run](https://infisical.com/docs/cli/commands/run), [Claude Code — permissions](https://code.claude.com/docs/en/permissions)

### 7. MCP Server Credentials

An MCP config is where the injection principle (§1) is most often skipped. GitGuardian's State of Secrets Sprawl 2026 found 24,008 unique secrets in MCP-related configuration files on public GitHub, 2,117 of them valid credentials, and attributes the pattern partly to setup guides that "recommend putting API keys directly into configuration files, command-line arguments, or embedded connection strings".

The secret belongs to the server's process, not the agent's. Launched as `infisical run -- claude`, every secret in the project lands in the agent's own environment, which every shell command it runs inherits and every stdio server inherits too. Wrap the server instead, so the config names a command and a secrets folder and nothing else:

```json
{
  "mcpServers": {
    "tracker": {
      "command": "infisical",
      "args": ["run", "--path=/mcp/tracker", "--", "npx", "-y", "tracker-mcp-server"]
    }
  }
}
```

`--path` limits the injection to that folder of the secrets project, and `infisical run` puts the values into the child process's environment, not its arguments. Set `CLAUDE_CODE_MCP_ALLOWLIST_ENV=1` as well, so Claude Code spawns stdio servers "with only a safe baseline environment plus the server's configured `env`, instead of inheriting your shell environment" — without it, whatever the agent's shell holds reaches every server. The documentation does not list what that baseline contains, so confirm on each platform that the wrapped server still connects (`claude mcp list`); if it does not, fix the server's own login rather than forwarding a token through its `env`.

The wrapper keeps the secret out of what the agent inherits, not out of its reach. The agent's shell can run the same `infisical` — the same keychain login locally — and read every folder that login reaches, which is why a logged-in CLI counts as a reachable secret for [25-agent-sandboxing.md](25-agent-sandboxing.md) §3. In CI, give the agent's job no Infisical identity at all: run the server outside the agent's job or container, with its own machine identity scoped to its folder (§4), and connect the agent to it over the network. Never forward `INFISICAL_TOKEN` through the server's `env` — the agent's job would then hold the token that unlocks the project.

A remote server authenticates through OAuth, which Claude Code supports, or through `headersHelper`, a command Claude Code runs at connect time to produce the request headers — the way to supply a short-lived token without storing one. The helper's output is a credential: point `headersHelper` at a script rather than writing a command that echoes a token into the config, and never run it in the agent's shell, where its output lands in the transcript (§6).

Where a config must reference a variable, Claude Code expands `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers`. Reference secrets only in `env` or `headers`: expanded into `args` a secret becomes part of the server's command line, which §4 rules out, and expanded into `url` it lands in every log that records the address. The default after `:-` is text committed with the file, so it is never a secret. The same holds for `claude mcp add`: `--env 'KEY=${KEY}'`, single-quoted so the shell does not expand it, stores the reference, while `--env KEY=value` stores the value. At local scope, the default, "the command writes the server into the entry for your current project inside `~/.claude.json`", and user scope is stored there too: a plaintext file outside the repository, and therefore outside the secret scan. A committed config carrying names only is what makes it committable, and it stays inside the scan on the same terms as the rest of the tree, so a value that slips in meets the same pre-commit and CI check as a value anywhere else.

A server that calls a downstream API holds that API's credential itself. The MCP specification forbids the shortcut of forwarding whatever token the client sent: "MCP servers **MUST NOT** accept any tokens that were not explicitly issued for the MCP server." A passed-through token bypasses the server's own controls, erases which client made the call from the downstream logs, and lets a stolen token use the server as a proxy.

Sources: [GitGuardian — The State of Secrets Sprawl 2026](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/), [Infisical CLI — run](https://infisical.com/docs/cli/commands/run), [Claude Code — MCP](https://code.claude.com/docs/en/mcp) (environment variable expansion, scopes, OAuth, `headersHelper`), [Claude Code — environment variables](https://code.claude.com/docs/en/env-vars), [MCP specification 2025-11-25 — Security Best Practices, Token Passthrough](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices) (checked 2026-09-12)
