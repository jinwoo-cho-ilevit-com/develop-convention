# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

개발 컨벤션 문서 저장소. 코드가 아니라 문서가 산출물이다 — 빌드/테스트 명령은 없다.
`README.md`가 문서 맵 + 전체 규칙 요약이고, 실제 규칙은 `conventions/00-*.md`~`09-*.md`에 주제별로 나뉘어 있다. 다른 프로젝트의 CLAUDE.md/AGENTS.md가 이 문서들의 "핵심 규칙" 섹션을 발췌해 쓰는 것이 소비 방식이다.

## Document format (must follow when editing/adding docs)

- 모든 `conventions/*.md`는 본문 첫 헤딩이 `## 핵심 규칙`이어야 한다: 에이전트 지시 파일에 그대로 발췌 가능한 명령형 규칙 목록. 그 뒤에 `## 상세`(사람용 설명 + 출처 링크).
- 본문 한국어, 코드/식별자/도구명 영어.
- 특정 사실 주장(도구의 deprecated 여부, 연구 수치, 비교 결과)은 반드시 해당 섹션에 출처 URL을 단다. 리서치로 확인 안 된 수치·주장은 싣지 않거나 "미확인"으로 표기한다. 일반적 엔지니어링 조언에는 출처 불필요.
- 문서를 수정하면 README.md의 문서 맵과 "전체 규칙 요약"이 모순되지 않는지 함께 확인하고 갱신한다.
- 새 문서는 `NN-topic.md` 번호 체계를 따르고 README 문서 맵에 추가한다.

## Verification

- 완료 전 교차 검증: (1) 모든 conventions 문서에 `## 핵심 규칙` 존재, (2) README 요약 ↔ 개별 문서 모순 없음, (3) 무출처 특정 주장 없음. 규모 있는 변경은 fresh-context 리뷰 에이전트(diff와 기준만 제공)로 검증한다 — 이 저장소의 00-principles.md가 스스로 정한 규칙이다.

## Commits

- 커밋 메시지: Conventional Commits 헤더(영문 type/scope) + 한글 본문(`## Why/What/How/Result`). 문서 변경은 `docs(conventions): ...` 형식을 따른다.
- `.omc/`, `.claude/`는 gitignore된 운영 산출물 — 커밋하지 않는다.
