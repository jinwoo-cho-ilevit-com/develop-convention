# 03. 툴체인 + 환경 이식성

## 핵심 규칙

- Python 프로젝트는 uv로 관리한다: `pyproject.toml` + `uv.lock`(커밋) + `.python-version`. 실행은 `uv run`.
- lint와 포맷은 ruff 하나로 통일한다 (`ruff check` + `ruff format`).
- 개발 도구는 `[dependency-groups]`의 dev 그룹에 넣는다. 런타임 `dependencies`에 섞지 않는다.
- pre-commit(로컬) + CI(강제) 이중으로 lint/format을 검사한다.
- 코드는 로컬(macOS, CPU/MPS)과 RunPod(Linux, CUDA)에서 수정 없이 동일하게 실행되어야 한다.
- GPU가 없으면 CPU로 실행·테스트 가능해야 한다. device는 단일 헬퍼 함수로만 선택하고, `.cuda()` 인라인 호출 금지.
- PyTorch 설치는 uv platform marker 또는 `--torch-backend=auto`로 플랫폼별 자동 라우팅한다.

## 상세

### 1. 2026 표준 툴체인

- **uv**: pip/pipenv/pyenv/virtualenv를 대체하는 단일 도구. `uv.lock`은 크로스 플랫폼 잠금 파일로 반드시 커밋하고 손으로 편집하지 않는다. `uv run`은 매 실행 전 lockfile↔pyproject↔env 동기화를 검증한다. 핵심 명령: `uv init`, `uv add`, `uv add --dev`, `uv sync`, `uv run`.
- **ruff**: black/flake8/isort/pyupgrade를 전부 대체. `[tool.ruff]` 단일 설정. 권장 lint 셋: `["E", "F", "I", "UP", "B"]`.
- **타입체커**: 기본 권고는 mypy(안전, 호환성 최대). 속도가 필요하면 pyrefly(1.0 안정) 또는 ty(uv/ruff 생태계 네이티브, 아직 beta) 중 하나를 프로젝트에서 명시적으로 하나만 선택한다. 혼용 금지.
- **pre-commit**: `astral-sh/ruff-pre-commit` 훅 사용. 로컬 훅은 건너뛸 수 있으므로 CI에서 `uvx pre-commit run --all-files`로 최종 강제한다.

pyproject.toml 기준형:

```toml
[project]
name = "my-project"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

출처: [uv — projects guide](https://docs.astral.sh/uv/guides/projects/), [ruff](https://docs.astral.sh/ruff/), [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), [타입체커 비교](https://pydevtools.com/handbook/explanation/how-do-mypy-pyright-and-ty-compare/)

### 2. 로컬 ↔ RunPod 이식성

단일 pyproject.toml이 두 환경을 모두 커버해야 한다. PyTorch는 macOS용 CUDA 빌드가 없으므로 플랫폼별 인덱스 라우팅이 필요하다.

방법 A — platform marker 자동 라우팅 (권장):

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cpu",  marker = "sys_platform != 'linux'" },
  { index = "pytorch-cuda", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cuda"
url = "https://download.pytorch.org/whl/cu130"  # CUDA 버전은 대상 pod에 맞춤
explicit = true
```

방법 B — `--torch-backend=auto` (또는 `UV_TORCH_BACKEND=auto`): 설치 시점에 CUDA 드라이버를 탐지해 인덱스를 선택하고 없으면 CPU로 폴백. RunPod처럼 GPU 구성이 바뀌는 임시 환경에 적합하다.

출처: [uv — PyTorch integration](https://docs.astral.sh/uv/guides/integration/pytorch/)

### 3. Device 추상화 (CPU fallback)

device 선택은 프로젝트당 헬퍼 함수 하나로만 한다. `torch.accelerator` API(CUDA/MPS/XPU 통합 추상화)를 기반으로 하되, 구버전 torch에는 이 API가 없으므로 가드한다.

```python
def get_device() -> torch.device:
    if hasattr(torch, "accelerator") and torch.accelerator.is_available():
        return torch.accelerator.current_accelerator()
    return torch.device("cpu")
```

- config로 오버라이드 가능해야 한다 (`device: cpu`로 강제 CPU 테스트).
- `.cuda()`, `"cuda:0"` 문자열 인라인 금지 — CPU 폴백을 깨는 주범이다.
- CI는 CPU에서 소수 샘플 스모크 테스트로 GPU 코드 경로를 검증한다 (→ [06-testing-verification.md](06-testing-verification.md)).

출처: [PyTorch — accelerator device API](https://docs.pytorch.org/docs/main/accelerator/device.html)

### 4. Docker

Docker를 쓸 때는 uv와 결합해 얇게 유지한다: lockfile과 pyproject.toml만 먼저 복사 → `uv sync`를 캐시 레이어로 → 그 다음 소스 복사. 재현성은 uv.lock이, Linux/CUDA 런타임은 이미지가 담당한다.
