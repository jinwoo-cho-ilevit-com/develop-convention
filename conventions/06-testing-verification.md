# 06. 테스트 + 검증

## 핵심 규칙

- 불필요한 pytest를 만들지 않는다. 커버리지 숫자를 좇지 않는다.
- 테스트 구성: 핵심 로직 단위 테스트 + 전체 파이프라인 E2E 스모크 1~3개. 함수마다 테스트를 만들지 않는다.
- ML 테스트는 정확한 float 비교 대신 허용 오차 밴드로 단언한다.
- 테스트 데이터는 소수의 현실적인 샘플 fixture를 쓴다 (NaN, 혼합 타입, 엣지 케이스 포함).
- 시드는 세션 스코프 fixture 하나에서 중앙 관리한다.
- CI는 GPU 없이 CPU에서 소수 샘플 스모크로 GPU 코드 경로까지 검증한다.
- 완료 선언 전 검증 명령을 실제 실행하고 전체 출력을 확인한다. TODO/스텁/`test.skip`은 완료가 아니라 블로커다.

## 상세

### 1. 최소-의미 테스트 철학

테스트는 "실제 회귀를 잡는 최소 집합"이다. 트렌드도 최소-but-의미 방향이다.

- 만들 것: 분기/루프/파서 등 비자명한 로직의 단위 테스트, 파이프라인 전체를 소수 샘플로 관통하는 스모크 1~3개.
- 만들지 않을 것: 자명한 one-liner 테스트, getter/setter 테스트, 프레임워크 동작을 재검증하는 테스트, 함수당 기계적 테스트 스위트.
- pytest 설정은 pyproject.toml에 `--strict-markers`로 두고, 공유 fixture는 `conftest.py`, 중복은 `parametrize`로 제거한다.

출처: [pytest best practices 2026](https://qaskills.sh/blog/pytest-best-practices-2026)

### 2. ML 코드 테스트 패턴

- **소수 샘플 fixture**: 장난감 dict가 아니라 현실적인 ~100행 샘플(NaN, 스큐, 혼합 타입 포함)을 fixture factory로 만든다.
- **허용 오차 밴드**: `assert auc == 0.874`가 아니라 `assert 0.85 <= auc <= 0.90`. 비트 단위 재현은 하드웨어 간에 보장되지 않는다 (→ [07-ml-development.md](07-ml-development.md)).
- **golden file**: 기준 출력(전처리 결과, 샘플 예측)을 저장해 두고 관용 diff로 비교. 갱신은 명시적 플래그(`--update-golden`)로만 — 조용한 갱신 금지.
- **중앙 시드 fixture**: 세션 스코프 fixture 하나에서 `PYTHONHASHSEED`/numpy/torch 시드와 CUDA 결정성을 설정한다. 비결정적 코드는 테스트할 수 없다.
- **스키마 계약 테스트**: 학습 입력과 추론 입력의 스키마 일치를 테스트로 고정한다 (train-serve skew 방지).

출처: [ML 테스트 — fixtures, seeds, golden files](https://medium.com/@connect.hashblock/10-ways-to-test-ml-code-fixtures-seeds-golden-files-811310517cae)

### 3. CPU 스모크로 GPU 코드 검증

- 모든 GPU 코드 경로는 device 헬퍼를 통하므로 (→ [03-environment.md](03-environment.md)), CI에서 `device: cpu` + `--limit 10`으로 학습/추론 스모크가 돌아야 한다.
- 이 스모크는 "성능"이 아니라 "동작"을 검증한다: shape 오류, device 불일치, config 오류를 GPU 비용 없이 잡는다.

### 4. 완료 검증 (evidence 원칙의 적용)

- 완료를 주장하려면: 검증 명령(테스트, 스모크 실행)을 실제로 돌리고, 종료 코드와 전체 출력을 확인한 후여야 한다.
- 다음은 완료가 아니라 블로커로 보고한다: TODO 주석, 미구현 분기, 스텁 테스트, `test.skip`/`.only`, "아마 될 것" 상태.
- 재작성/리팩토링 완료 판정에는 characterization test 통과가 포함된다 (→ [00-principles.md](00-principles.md)).
- 검증자는 작성자와 분리한다: 리뷰는 fresh-context 에이전트/세션이 diff와 기준만 보고 수행한다 (→ [09-agentic-workflow.md](09-agentic-workflow.md)).
