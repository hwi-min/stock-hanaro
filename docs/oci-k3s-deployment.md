# OCI Always Free ARM64 배포 가이드

stock-hanaro를 OCI `VM.Standard.A1.Flex` 단일 인스턴스의 k3s에 배포한다. 이 구성은 개인 MVP와 최소 비용을 목표로 하며 고가용성을 제공하지 않는다.

## 1. 전제와 리소스 예산

- OCI Ampere A1: 2 OCPU, 12GB RAM
- Ubuntu 24.04 ARM64
- boot volume: 100GB
- 공인 IPv4 1개
- 도메인의 A 레코드가 공인 IPv4를 가리킴
- OCI NSG 인바운드: TCP 80/443 공개, TCP 22는 관리자 IP만 허용
- PostgreSQL data PVC 20Gi, 로컬 backup PVC 10Gi

OCI 콘솔에서 인스턴스와 볼륨에 `Always Free Eligible` 표시가 있는지 확인한다. Kubernetes API 6443, PostgreSQL 5432, Next.js 3000, FastAPI 8000은 외부에 개방하지 않는다.

## 2. 저장소 placeholder 교체

배포 전 다음 값을 실제 값으로 교체한다.

- `deploy/overlays/production/kustomization.yaml`: `OWNER`
- `deploy/argocd/application.yaml`: `OWNER`와 저장소 이름
- `deploy/overlays/production/production-ingress.patch.yaml`: `stock.example.com`
- `deploy/overlays/production/production-config.patch.yaml`: `stock.example.com`
- `deploy/overlays/production/cluster-issuer.yaml`: 관리자 이메일

이미지는 변경 불가능한 Git commit SHA 태그를 사용한다. `latest`는 운영 overlay에서 사용하지 않는다.

## 3. k3s와 기본 구성요소

서버 업데이트 후 공식 k3s 설치 절차로 단일 server 노드를 설치한다. k3s 기본 Traefik과 local-path provisioner는 유지한다. kubeconfig는 root만 읽을 수 있게 보호한다.

cert-manager와 Argo CD는 각 프로젝트의 공식 Helm 저장소에서 설치하고 설치 시점의 stable 버전을 명시적으로 고정한다. 자동으로 `latest`를 추적하지 않는다.

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version <PINNED_CERT_MANAGER_VERSION> \
  --set crds.enabled=true
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --version <PINNED_ARGO_CD_CHART_VERSION>
```

Argo CD UI는 공개 Ingress로 노출하지 않는다. 필요할 때 SSH 터널과 `kubectl port-forward`로만 접근한다.

## 4. Secret 생성

`deploy/base/secret.example.yaml`은 키 이름 확인용이며 실제 배포 대상에 포함되지 않는다. 실제 값은 로컬의 커밋되지 않는 env 파일 또는 비밀 관리자에서 읽어 생성한다.

먼저 namespace를 만든다.

```bash
kubectl create namespace stock-hanaro
```

PostgreSQL Secret에는 다음 키가 필요하다.

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

애플리케이션 Secret에는 다음 키가 필요하다.

```text
DATABASE_URL
INTERNAL_JOB_SECRET
KIS_APP_KEY
KIS_APP_SECRET
DART_API_KEY
BOK_ECOS_API_KEY
OPENAI_API_KEY
```

`DATABASE_URL` 형식은 다음과 같다.

```text
postgresql+psycopg://<USER>:<URL_ENCODED_PASSWORD>@stock-hanaro-postgres:5432/<DATABASE>
```

GHCR package가 private이면 read-only classic PAT의 `read:packages` 권한으로 image pull Secret을 만든다.

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --namespace stock-hanaro \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB_USER> \
  --docker-password=<READ_PACKAGES_PAT>
```

저장소가 private이면 Argo CD에도 별도의 read-only repository credential을 등록한다. Git push 권한이나 GHCR write 권한을 서버에 저장하지 않는다.

## 5. GitOps 배포

1. Pull request에서 기존 `CI`가 backend, frontend, policy 검사를 수행한다.
2. main의 CI가 성공하면 `Build ARM64 Images` workflow가 Buildx/QEMU로 `linux/arm64` 이미지를 생성한다.
3. backend와 frontend 이미지를 `ghcr.io/<owner>/...:<commit-sha>`에 push한다.
4. workflow가 production Kustomize overlay의 두 이미지 태그를 같은 SHA로 변경해 main에 커밋한다.
5. Argo CD가 변경을 감지하고 자동 sync한다.
6. PostgreSQL이 먼저 준비되고 Alembic migration Sync Job이 성공해야 애플리케이션 리소스가 sync된다.

최초 이미지가 한 번 GHCR에 push된 뒤 Argo CD Application을 적용한다.

```bash
kubectl apply -f deploy/argocd/application.yaml
```

배포 전 렌더링 결과를 확인한다.

```bash
kubectl kustomize deploy/overlays/production
```

## 6. 실행 단위

- `stock-hanaro-frontend`: Next.js standalone server, replica 1
- `stock-hanaro-api`: FastAPI HTTP/SSE, replica 1
- `stock-hanaro-kis-worker`: KIS WebSocket 연결과 DB 저장, replica 1
- `stock-hanaro-postgres`: PostgreSQL 16 StatefulSet, replica 1
- CronJob: 뉴스·공시·시장·KCIF·요약 수집
- `stock-hanaro-migration`: PostgreSQL 다음, 애플리케이션 이전 wave의 Argo CD Alembic Job

API와 worker는 메모리를 공유하지 않는다. worker가 실시간 틱, 구독 요청, 연결 heartbeat를 PostgreSQL에 기록하고 API가 이를 읽어 브라우저 SSE로 전달한다. Redis나 Kafka는 사용하지 않는다.

## 7. 배치 정책

정기 수집은 Kubernetes CronJob을 기준으로 한다. 기존 GitHub Actions 수집 workflow는 장애 대응용 수동 실행만 유지한다.

KCIF는 평일 07:00에 처음 실행하고 07:30, 08:00, 08:30, 09:00에 재실행한다. JobService의 당일 성공 기록을 확인하므로 앞선 실행이 성공했다면 뒤의 CronJob은 `skipped`로 끝난다.

CronJob은 `concurrencyPolicy: Forbid`로 중복 실행을 차단한다. Job은 DB에 idempotency key와 실행 결과를 남긴다.

## 8. 데이터와 백업

매일 03:10 PostgreSQL `pg_dump`를 gzip으로 압축해 별도 local-path PVC에 저장하고 14일보다 오래된 파일을 삭제한다. 이 PVC도 같은 OCI VM에 있으므로 디스크 또는 인스턴스 장애에 대한 원격 백업은 아니다.

운영 시작 후 다음 중 하나를 반드시 추가한다.

- OCI Block Volume 예약 백업
- OCI Object Storage로 dump 복사
- 관리 PC 또는 다른 서버로 정기 복사

복구 훈련은 새 DB에서 다음 순서로 수행한다.

```text
새 PostgreSQL 준비 → gzip dump 복원 → alembic upgrade head → API readiness 확인
```

## 9. 장애 정책

- Deployment Pod는 실패 시 Kubernetes가 자동 재시작한다.
- API와 frontend는 readiness/liveness probe를 사용한다.
- worker는 KIS 연결 실패 시 최대 60초의 지수 backoff로 재연결한다.
- worker heartbeat가 45초 이상 갱신되지 않으면 API는 worker를 살아 있지 않은 것으로 표시한다.
- DB migration 실패 시 Argo CD sync를 실패 처리해 새 애플리케이션 배포를 막는다.
- 단일 노드 재부팅과 StatefulSet 재시작 동안 서비스 중단을 허용한다.
- `Recreate` 전략으로 제한된 ARM VM에서 구버전과 신버전 Pod의 동시 자원 사용을 피한다.

## 10. 운영 확인

```bash
kubectl get pods -n stock-hanaro
kubectl get jobs,cronjobs -n stock-hanaro
kubectl get certificate -n stock-hanaro
kubectl logs -n stock-hanaro deployment/stock-hanaro-api
kubectl logs -n stock-hanaro deployment/stock-hanaro-kis-worker
kubectl exec -n stock-hanaro statefulset/stock-hanaro-postgres -- pg_isready
```

장중 최종 확인 항목은 `/api/market/status`의 `worker_alive`, `connected`, `last_tick_at`과 국내 종목 화면의 실시간 가격 변경이다.

## 11. 초기 범위 밖

Redis, Kafka, managed database, OKE, multi-node k3s, autoscaling, 여러 replica, public Argo CD, Prometheus/Grafana/Loki는 초기 배포에 포함하지 않는다. 트래픽이나 운영 불편이 실제로 확인된 뒤 추가한다.
