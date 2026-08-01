# 13. Secret Management

## Core Rules

- Do not hardcode secrets (API keys, tokens, passwords, connection strings) into code, config, logs, or Docker image layers (→ [02-config.md](02-config.md)).
- Do not commit a plaintext `.env` to the repository. Register `.env` in `.gitignore`, and commit only a valueless key list in `.env.example`.
- The single source of truth for secrets is a central secret manager. Do not manage secrets across devices/projects by copying files.
- Supply secrets via runtime injection everywhere — locally, in CI, in containers — and never leave them as plaintext residue on disk.
- Coding agents follow the same rules: wrap execution commands in an injection wrapper, never create or read plaintext secret files, and check required keys against `.env.example`.
- Non-interactive environments such as containers and CI authenticate with a machine identity, not a human account. Scope permissions to the minimum and use short-lived tokens.
- Separate environments (dev/staging/prod), rotate secrets periodically, and revoke and reissue immediately upon any leak.
- Run secret scanning (gitleaks, etc.) in both pre-commit and CI to block leaks at commit time (→ [03-environment.md](03-environment.md)).

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

- Enforce secret scanning before commit. Run `gitleaks` doubly, in both a pre-commit hook and CI, to block hardcoded credentials. Scanning matters more once agents are committing: GitGuardian's State of Secrets Sprawl 2026 measured a 3.2% secret-leak rate on Claude Code-assisted commits against a 1.5% baseline across all public GitHub commits (roughly 2x). The report does not publish the sample size or method for that comparison, and cautions against reading it as a tool defect — the developer still decides what gets accepted and pushed — so the control is scanning the commits, not avoiding the tool.
- A secret that's already been committed isn't made safe just by adding it to `.gitignore` — it remains in history, so **rotate and reissue it immediately**, and remove it from history if needed.
- Teams separate dev/staging/prod environments, restrict prod secret access to a minimal set of people/machine identities, and track access via audit logs.

Sources: [gitleaks](https://github.com/gitleaks/gitleaks), [GitGuardian — State of Secrets Sprawl 2026](https://www.gitguardian.com/state-of-secrets-sprawl-report-2026)
