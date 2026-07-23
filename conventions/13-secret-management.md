# 13. 시크릿 관리

## 핵심 규칙

- 시크릿(API 키·토큰·비밀번호·커넥션 스트링)을 코드·config·로그·도커 이미지 레이어에 하드코딩하지 않는다 (→ [02-config.md](02-config.md)).
- 평문 `.env`를 저장소에 커밋하지 않는다. `.gitignore`에 `.env`를 등록하고, `.env.example`에는 값 없는 키 목록만 커밋한다.
- 시크릿의 단일 원본(source of truth)은 중앙 시크릿 매니저다. 파일 복사로 기기·프로젝트 간 시크릿을 관리하지 않는다.
- 로컬·CI·컨테이너 어디서든 실행 시점 주입(injection)으로 시크릿을 공급하고, 디스크에 평문으로 잔존시키지 않는다.
- 코딩 에이전트도 동일 규칙을 따른다: 실행 명령을 주입 래퍼로 감싸고, 평문 시크릿 파일을 생성·읽지 않으며, 필요한 키는 `.env.example`에서 확인한다.
- 컨테이너·CI 등 비대화형 환경은 사람 계정이 아니라 머신 신원(machine identity)으로 인증한다. 권한은 최소로 스코프하고 단기 토큰을 쓴다.
- 환경(dev/staging/prod)을 분리하고, 시크릿은 주기적으로 회전(rotation)하며 유출 시 즉시 폐기·재발급한다.
- 시크릿 스캐닝(gitleaks 등)을 pre-commit과 CI에 걸어 커밋 단계에서 유출을 차단한다 (→ [03-environment.md](03-environment.md)).

## 상세

권장 도구는 **Infisical**이다(오픈소스, 무료 클라우드 티어 + 셀프호스팅). 개인 단일 기기부터 팀 RBAC까지 같은 저장소로 확장되고, CLI 주입 방식이 로컬·CI·컨테이너에 일관되게 적용된다. 1Password(`op run`), Doppler, HashiCorp Vault, 클라우드 네이티브 매니저(AWS/GCP Secrets Manager)도 아래 원칙(중앙 저장 + 주입 + 머신 신원)을 만족하면 대안으로 쓸 수 있다.

### 1. 원칙: 저장 대신 주입

시크릿을 파일로 두면 복사·동기화·유출이 필연이다. 대신 **중앙 저장소를 원본으로 두고 실행 순간에만 프로세스 환경변수로 주입**한다. 프로젝트 폴더에는 평문 `.env` 대신 참조 정보(`.infisical.json`, 민감정보 없음 → 커밋 가능)와 키 목록(`.env.example`)만 남는다.

```gitignore
# .gitignore
.env
.env.*
!.env.example
```

### 2. 로컬 개발 세팅

```bash
brew install infisical/get-cli/infisical   # CLI 설치 (기기당 1회)
infisical login                            # 브라우저 인증 (기기당 1회, OS 키체인 저장)
cd <프로젝트>
infisical init                             # 조직·프로젝트 선택 → .infisical.json 생성
infisical run --env=dev -- <실행 명령>      # 실행 시점에만 시크릿 주입
```

원칙: **레포(앱) 1개 = 시크릿 프로젝트 1개**. 여러 앱의 시크릿을 한 프로젝트에 섞지 않는다(환경·권한 분리가 어려워진다). 환경변수 이름에는 하이픈을 쓰지 않는다 — `GEMINI_API_KEY-2`는 셸이 `$GEMINI_API_KEY`와 `-2`로 분리해 읽지 못한다. 언더스코어(`GEMINI_API_KEY_2`)를 쓴다.

출처: [Infisical CLI — overview](https://infisical.com/docs/cli/overview), [usage](https://infisical.com/docs/cli/usage), [run 명령](https://infisical.com/docs/cli/commands/run)

### 3. 코드에서 읽는 법

주입된 시크릿은 평범한 환경변수이므로 코드를 바꿀 필요가 없다. 기존 `dotenv` 기반 코드도 그대로 동작한다. 달라지는 것은 실행을 `python app.py` 대신 `infisical run --env=dev -- python app.py`로 하는 것뿐이다.

```python
import os
key = os.environ["OPENAI_API_KEY"]   # os.getenv("OPENAI_API_KEY")
```

전용 SDK로 코드에서 직접 시크릿을 조회하는 방식도 있으나, 기본은 코드 변경이 없는 주입 방식을 쓴다.

### 4. 컨테이너·CI: 머신 신원

컨테이너·CI에서는 브라우저 로그인이 불가능하므로 **머신 신원(Universal Auth)** 으로 인증한다. 대시보드에서 머신 신원을 만들어 Client ID/Secret을 발급하고, 대상 프로젝트에 최소 권한으로 추가한다. 자격증명은 이미지에 굽지 않고 배포 플랫폼(K8s Secret, ECS task env, PaaS 환경변수)이 컨테이너에 주입한다.

```dockerfile
# 이미지에 CLI 설치, 엔트리포인트에서 주입 (시크릿 값은 이미지에 굽지 않음)
RUN curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | bash \
    && apt-get update && apt-get install -y infisical
CMD infisical run --projectId=$INFISICAL_PROJECT_ID --env=prod -- <실행 명령>
```

```bash
# 데모용. 주의: 아래 인라인 형태는 client-secret이 셸 argv(`ps`로 관찰)와
# docker run argv·컨테이너 설정(`docker inspect`)에 노출되므로 프로덕션에서 쓰지 않는다.
docker run \
  -e INFISICAL_TOKEN="$(infisical login --method=universal-auth \
      --client-id=$CLIENT_ID --client-secret=$CLIENT_SECRET --silent --plain)" \
  -e INFISICAL_PROJECT_ID=<프로젝트 ID> \
  <이미지>
```

- **자격증명을 argv로 넘기지 않는다**: client-secret·토큰을 명령행 인자나 `docker run -e KEY=VALUE`의 리터럴 값으로 두면 프로세스 목록·`docker inspect`·컨테이너 설정에 남는다. 배포 플랫폼의 시크릿 스토어(K8s Secret, ECS/Fargate secrets, PaaS secret)가 `INFISICAL_TOKEN`(또는 머신 신원 자격증명)을 컨테이너 env로 직접 주입하게 하고, Infisical CLI가 그 env를 자동으로 읽게 한다 — 셸 치환·argv를 거치지 않는다.

시크릿 값은 컨테이너 **시작 시점**에만 주입하고 이미지 레이어에 남기지 않는다. 규모가 커지면 CLI 대신 Infisical Agent(사이드카)나 Kubernetes Operator(Infisical 시크릿 → 네이티브 K8s Secret 동기화)로 전환한다.

출처: [Infisical — Docker 통합](https://infisical.com/docs/integrations/platforms/docker-intro), [Universal Auth (머신 신원)](https://infisical.com/docs/documentation/platform/identities/universal-auth)

### 5. 유출 방지

- 커밋 전 시크릿 스캐닝을 강제한다. pre-commit 훅 + CI 이중으로 `gitleaks`를 돌려 하드코딩된 자격증명을 차단한다. AI 코딩 어시스턴트가 만든 커밋은 시크릿 유출률이 더 높으므로 스캐닝이 특히 중요하다.
- 이미 커밋된 시크릿은 `.gitignore` 추가만으로 안전해지지 않는다 — 히스토리에 남으므로 **즉시 회전·재발급**하고 필요 시 히스토리에서 제거한다.
- 팀은 dev/staging/prod 환경을 분리하고, prod 시크릿 접근은 최소 인원·머신 신원으로 제한하며 감사 로그로 추적한다.

출처: [gitleaks](https://github.com/gitleaks/gitleaks)
