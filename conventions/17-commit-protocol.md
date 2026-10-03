# 17. Commit Protocol

## Core Rules

- Write every commit so a future research/dev note can be reconstructed from `git log` alone. The header follows Conventional Commits; the body and trailers carry the research narrative.
- **Language policy**: summary and body in **Korean** (git log doubles as a Korean research note); `type`/`scope` in lowercase English; code identifiers verbatim (`parse_header()`, `commit.md`, `core.hooksPath`).
- Header (required, imperative, **<=72 characters** — counted in characters, not bytes, so a Korean summary gets the full 72): `<type>(<scope>): <summary>`.
- **type**: `feat` `fix` `refactor` `perf` `docs` `test` `chore` `build` `ci` `style` `revert` `exp` (experiment). **scope**: module/area, optional. Breaking change: append `!` after type/scope.
- Body is **required** for `feat`/`fix`/`refactor`/`perf`, recommended otherwise, using the Korean markdown sections `## Why` / `## What` / `## How` / `## Result`. Trivial commits (typo, formatting, one-liner) may use header + a one-line `## Why` only.
- Never fabricate `## Result` or metrics — write "측정 안 함" (not measured) if unverified. A `fix` commit cannot write "측정 안 함": its `## Result` carries the defect's reproduction before and after the fix, command and decisive output ([06-testing-verification.md](06-testing-verification.md) Core Rules), masked first because a commit body is pushed (secrets, and personal and customer fields per [06-testing-verification.md](06-testing-verification.md) §4).
- No emoji anywhere in the message — header, body, or trailers. `git log` output is scanned and grepped as plain text (→ [01-structure-naming.md](01-structure-naming.md)).
- One logical change per commit. Before committing, survey the working tree and group changes by intent; never commit a mixed bag (feature + reformatting + incidental refactor).
- Machine-parseable trailers when relevant: `Intent:` (classification tag), `Impact:` (one-line effect), `Refs:` (files, #issues, doc paths), `Experiment:` (stable research id, reused across a series of related commits).
- Enforcement is mechanical: the commit-msg git hook (deployed via claude-config) warns — non-blocking — when a `feat`/`fix`/`refactor`/`perf` commit ships without a body.

## Details

### 1. Body template

Write it so that **왜·무엇을·어떻게·결과** (why / what / how / result) is understandable much later without opening the diff. The template below is copied verbatim into commit bodies (section descriptions in Korean by policy):

```
## Why
- 배경·문제·동기 — 왜 지금 이 변경이 필요한가

## What
- 무엇을 바꿨나 — 파일/모듈 단위로 구체적으로

## How
- 어떻게 접근했나 — 고려한 대안과 그것을 버린 이유

## Result
- before -> after, 검증 결과(테스트·실측), 영향 범위. 측정 안 했으면 "측정 안 함"
- fix면 결함 재현 명령과 수정 전/후 결정적 출력 (마스킹 후, "측정 안 함" 불가)
```

### 2. Trailers (machine-parseable footer)

```
Intent: <classification tag, e.g. bugfix-hotpath>
Impact: <one-line effect, e.g. 로그인 p99 1200ms -> 180ms>
Refs: <files, #issues, docs paths>
Experiment: <stable research id, e.g. auth-cache-2026-06-13>
```

- The `Experiment:` trailer ties a series of commits to one research thread; reuse the same id across related commits.
- Extraction later: `git log --format='%h %s%n%b' --grep='Experiment: <id>'`.

### 3. Result example

A `fix` commit's `## Result`:

```
## Result
- 재현: `uv run python scripts/bench_login.py --rps 200 --duration 60`
  - 수정 전: `p99=1203ms jwks_fetches=11874`
  - 수정 후: `p99=181ms jwks_fetches=3`
- auth 테스트 전부 통과, 토큰 검증 로직 변경 없음.
```
