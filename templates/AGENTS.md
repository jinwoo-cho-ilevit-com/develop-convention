# AGENTS.md

이 저장소에서 작업하는 코딩 에이전트를 위한 지침.

## Project

[한 줄: 이 프로젝트가 무엇인지]

## Commands

- 실행: `uv run python -m [ENTRY]`
- 테스트: `uv run pytest`
- lint/format: `uv run ruff check && uv run ruff format --check`
- 소수 샘플 스모크: `[스모크 명령 — 예: uv run python -m ENTRY --limit 10 device=cpu]`

## Conventions

전체 컨벤션: `[CONVENTION_PATH]` (develop-convention 저장소를 clone한 로컬 경로) — 작업 유형에 해당하는 문서의 "핵심 규칙"을 따른다 (문서 맵은 그 저장소의 README.md).

이 프로젝트에서 특히 지킬 것:
- 하드코딩 금지, 모든 값은 중앙 config (02)
- 모든 파이프라인 스테이지는 `--limit N` 소수 샘플 실행 + 중간 저장/resume 가능 (04)
- 완료 전 중복/dead code 스캔, `_v2`/`_new` 네이밍 금지 (01)

[ML 프로젝트면 유지, 아니면 삭제]
- 시드 통합 헬퍼 + 학습/추론 전처리 코드 단일화, device는 단일 헬퍼로만 (03/07)

[LLM API 프로젝트면 유지, 아니면 삭제]
- provider API 코드 작성/수정 전: `[CONVENTION_PATH]/conventions/12-docs-reference.md`의 해당 provider 공식 문서를 fetch해 확인
- SDK 사용법은 ctx7, 예외/시그니처는 설치된 SDK 소스가 기준
- 문서에 없는 동작은 추측하지 말고 provider 스모크 테스트로 확정 (10/11/12)

## Verification

완료 전: `uv run pytest` + 위 스모크 명령 실행, 전체 출력 확인. 실행 증거 없이 완료 주장 금지. TODO/스텁/`test.skip`은 완료가 아니라 블로커.
