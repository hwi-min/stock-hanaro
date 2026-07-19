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

백엔드가 꺼져 있으면 홈은 M1 fallback fixture로 렌더링됩니다. 운영에서는 `NEXT_PUBLIC_API_BASE_URL`을 배포된 API 주소로 설정합니다.

## 검증

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
