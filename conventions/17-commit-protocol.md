# 17. Commit Protocol

## Core Rules

- Write every commit so a future research/dev note can be reconstructed from `git log` alone. The header follows Conventional Commits; the body and trailers carry the research narrative.
- **Language policy**: summary and body in **Korean** (git log doubles as a Korean research note); `type`/`scope` in lowercase English; code identifiers verbatim (`parse_header()`, `commit.md`, `core.hooksPath`).
- Header (required, imperative, **<=72 characters** — counted in characters, not bytes, so a Korean summary gets the full 72): `<type>(<scope>): <summary>`.
- **type**: `feat` `fix` `refactor` `perf` `docs` `test` `chore` `build` `ci` `style` `revert` `exp` (experiment). **scope**: module/area, optional. Breaking change: append `!` after type/scope.
- Body is **required** for `feat`/`fix`/`refactor`/`perf`, recommended otherwise, using the Korean markdown sections `## Why` / `## What` / `## How` / `## Result`. Trivial commits (typo, formatting, one-liner) may use header + a one-line `## Why` only.
- Never fabricate `## Result` or metrics — write "측정 안 함" (not measured) if unverified.
- No emoji anywhere in the message — header, body, or trailers. `git log` output is scanned and grepped as plain text (→ [01-structure-naming.md](01-structure-naming.md)).
- One logical change per commit. Before committing, survey the working tree and group changes by intent; never commit a mixed bag (feature + reformatting + incidental refactor).
- Machine-parseable trailers when relevant: `Intent:` (classification tag), `Impact:` (one-line effect), `Refs:` (files, #issues, doc paths), `Experiment:` (stable research id, reused across a series of related commits).
- Enforcement is mechanical: the commit-msg git hook (deployed via claude-config) warns — non-blocking — when a `feat`/`fix`/`refactor`/`perf` commit ships without a body.

## Details

### 1. Header

```
<type>(<scope>): <summary>
```

- Imperative mood, <=72 characters counted in characters (Korean summaries are not penalized by byte counting).
- scope examples: `(snapshots)`, `(corpus)`.

### 2. Body template

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
```

### 3. Trailers (machine-parseable footer)

```
Intent: <classification tag, e.g. bugfix-hotpath>
Impact: <one-line effect, e.g. 로그인 p99 1200ms -> 180ms>
Refs: <files, #issues, docs paths>
Experiment: <stable research id, e.g. auth-cache-2026-06-13>
```

- The `Experiment:` trailer ties a series of commits to one research thread; reuse the same id across related commits.
- Extraction later: `git log --format='%h %s%n%b' --grep='Experiment: <id>'`.

### 4. Full example

Korean summary + Korean body + English type/scope:

```
fix(auth): JWT 공개키를 캐시해 토큰 검증 지연 제거

## Why
- 매 요청마다 JWKS를 네트워크에서 다시 받아 p99에 ~1s가 더해졌다.
- #482에서 부하 시 간헐적 로그인 타임아웃이 보고됐다.

## What
- `auth/jwks.py`에 JWKS용 인메모리 TTL 캐시 추가.
- 캐시 미스 또는 `kid` 불일치 시에만 지연 갱신.

## How
- issuer 키로 10분 TTL. 시작 시 스레드를 늘리지 않으려고 백그라운드 워커 대신
  지연 갱신 방식을 택했다.

## Result
- 로그인 p99 1200ms -> 180ms (로컬 부하 테스트, 200 rps).
- auth 테스트 전부 통과, 토큰 검증 로직 변경 없음.

Intent: bugfix-hotpath
Impact: 로그인 p99 지연 1200ms -> 180ms
Refs: auth/jwks.py, #482
```

### 5. Splitting into logical units

Before committing, inspect the working tree and group changes by intent — never commit a mixed bag.

1. **Survey**: run `git status` and `git diff` (and `git diff --staged`) to see every pending change.
2. **Classify** each change into one logical group: feature, fix, refactor, formatting, docs, test, chore. A different *intent* means a different commit, even within one file.
3. **Stage per group**, then commit before moving to the next:
   - Whole-file groups: `git add <path> ...`
   - Mixed changes inside one file: `git add -p <path>` to select only the relevant hunks (interactive `git add -i` is unavailable in some harnesses; prefer `-p`, or split via temporary `git stash -p`).
4. **Verify isolation**: `git diff --staged` should show only the current group before each commit.
5. **Order** commits so each one builds/tests green on its own (dependencies first).

Never mix unrelated work — e.g. a feature + reformatting + an incidental refactor — in a single commit.

### 6. Why git log as a research note

A commit body written to this protocol makes `git log` a self-contained research narrative: motivation, alternatives considered, and measured outcomes survive even when the surrounding docs rot. This is the L4 history layer of [15-doc-tracking.md](15-doc-tracking.md) — structured commits carry commit-granularity history, ADRs carry structural decisions.
