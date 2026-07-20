# stock-hanaro

증권사 영업직원과 PB가 글로벌 시장, 뉴스·이슈, 공시와 고객 설명용 브리핑을 한 화면에서 확인하는 공개형 금융 대시보드입니다.

## M1 구성

```text
frontend/                 Next.js 홈 대시보드와 상세 화면
backend/app/api/public/   공개 Read API
backend/app/api/internal/ 보호된 작업 API
backend/app/services/     업무 규칙
backend/app/repositories/ 데이터 접근
backend/app/models/       SQLAlchemy 모델
backend/alembic/          DB 마이그레이션
config/                   데이터 사용 정책
```

홈 화면은 서비스 전체를 요약하고, 각 카드와 상단 메뉴는 상세 페이지로 연결됩니다. M1의 데이터는 API 계약 검증용 fixture이며 M2부터 실제 수집 데이터로 교체합니다.

## 로컬 실행

### 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

- API 문서: <http://localhost:8000/docs>
- 생존 상태: <http://localhost:8000/health>
- 준비 상태: <http://localhost:8000/health/ready>
- 홈 API: <http://localhost:8000/api/dashboard/home>

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

웹: <http://localhost:3000>

주요 경제 일정 상세 화면은 `/calendar`에서 확인합니다. M1에서는 공식 일정과 동일한 계약의 fixture를 사용하며, M2에서 BLS·BEA·Federal Reserve·한국은행 collector를 Job API에 연결합니다.

운영에서는 `NEXT_PUBLIC_API_BASE_URL`을 배포된 API 주소로 설정합니다. 백엔드 요청 실패를 샘플 데이터로
숨기지 않으며 오류 화면을 표시합니다. 화면 개발용 fixture가 꼭 필요한 경우에만
`ALLOW_DASHBOARD_FALLBACK=true`를 명시적으로 설정합니다.

## M2 자동 수집 설정

GitHub Actions가 배포된 Internal Job API를 호출해 다음 주기로 데이터를 갱신합니다.

- 미국 시장: 미국 정규장 마감 후 한국시간 06:30에 종가 확정, 실패한 경우에만 07:00 재시도
- 국내 시장: KIS WebSocket으로 국내 지수·설정 종목을 장중 실시간 제공, 08:50·15:40 스냅샷을 연결 장애 시 안전망으로 저장
- 뉴스: 매일 한국시간 06:00~18:30, 30분 간격
- DART 공시: 평일 한국시간 09:00~18:30, 30분 간격
- 공식 경제 일정: 매일 한국시간 05:20
- KRX 종목 마스터: 평일 한국시간 07:40에 KIS 공식 KOSPI·KOSDAQ 종목정보를 갱신
- KCIF: 평일 한국시간 07:00, 07:30, 08:00, 08:30, 09:00 순서로 실패 시에만 재시도
- AI 요약: API Billing 활성화 전에는 수동 실행만 제공

모든 워크플로는 Job API의 응답 상태가 `succeeded` 또는 `skipped`가 아니면 실패합니다. GitHub Actions의 성공 표시가 실제 파이프라인 실패를 가리지 않습니다.

GitHub 저장소의 `Settings → Secrets and variables → Actions`에 다음 값을 등록합니다.

- `BACKEND_API_BASE_URL`: 배포된 FastAPI 주소
- `INTERNAL_JOB_SECRET`: FastAPI 환경변수와 동일한 내부 작업 비밀값

각 워크플로는 `workflow_dispatch`로 수동 실행할 수 있습니다. `Summarize Content`는 OpenAI API 사용 한도가 준비된 후 수동 실행합니다.
OpenAI API가 없는 동안 `collect-news`는 실제 기사만 사용한 규칙 기반 이슈 묶음과 추출 요약을 함께
생성합니다. 분류·중복 제거·요약 기준은 [비-AI 뉴스 이슈 생성 정책](docs/rule-based-news-issues.md)을 따릅니다.

국내 실시간 스트림은 항상 실행되는 별도 worker에서 `KIS_REALTIME_ENABLED=true`로 활성화합니다.
`KIS_KR_SYMBOLS`는 홈에서 항상 유지할 기본 종목이며, 상세 화면을 연 국내 종목은 자동 구독되고
마지막 사용자가 화면을 닫으면 자동 해제됩니다. 동시 종목 한도는 지수 3개를 제외하고
`KIS_MAX_REALTIME_STOCKS`(기본 37개)입니다. worker는 틱과 구독 상태를 PostgreSQL에 저장하고
FastAPI는 DB 기반 SSE로 화면에 전달합니다. 미국 지표와 미국시장 히트맵은 실시간 스트림에
연결하지 않고 마지막 정규장 종가 스냅샷을 표시합니다.

휴장 중에도 인증·연결·구독 승인은 다음 명령으로 확인할 수 있습니다. 체결 틱과 화면 갱신은 국내 장중에
`GET /api/market/status`의 `last_tick_at`과 홈의 `실시간` 표시로 최종 확인합니다.

```bash
backend/.venv/bin/python scripts/verify_kis_realtime.py --timeout 15
```

## 검증

M2 API·DB·수집 파이프라인을 읽기 전용으로 통합 점검합니다.

```bash
python3 scripts/check_m2_integration.py
```

AI를 제외한 수집 Job을 실제 실행한 뒤 점검하려면 `--run-jobs`를 사용합니다. 이 명령은 데이터를
변경합니다. 옵션과 판정 기준은 [M2 통합 점검 가이드](docs/m2-integration-check.md)를 참고하세요.

```bash
python3 scripts/validate_data_sources.py
python3 -m unittest discover -s tests -v

cd backend
pytest -q
alembic upgrade head
alembic check

cd ../frontend
npm run lint
npm run build
```

## 데이터 사용 정책

수집기를 추가하기 전에 [`config/data-sources.json`](config/data-sources.json)에 저장, 화면 표시, 재배포, AI 입력 범위를 등록해야 합니다. 자세한 판단은 [`docs/data-source-policy.md`](docs/data-source-policy.md)를 참고하세요.

> AI 요약은 출처 기반 참고 정보이며 투자 권유가 아닙니다. 외부 데이터의 공개 배포 범위는 공급자 정책과 계약을 최종 확인해야 합니다.

## M3 OCI ARM64 배포

운영 환경은 OCI Always Free Ampere A1 단일 VM의 k3s를 기준으로 합니다. Next.js, FastAPI,
KIS WebSocket worker, PostgreSQL 16을 각각 컨테이너로 실행하고 Kustomize와 Argo CD로 배포합니다.
GitHub Actions는 CI 성공 후 ARM64 이미지를 GHCR에 저장합니다.

설치 순서, Secret 생성, HTTPS, 배치, migration, 백업과 복구 절차는
[OCI k3s 배포 가이드](docs/oci-k3s-deployment.md)를 참고하세요. 실제 Secret 값은 저장소에 커밋하지 않습니다.
