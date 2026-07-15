# stock-hanaro

증권사 영업직원과 PB가 매일 아침 여러 사이트를 돌아다니지 않고, 하나의 웹에서 글로벌 시장, 주요 뉴스, 공시, 시장 이슈와 아침 브리핑을 확인할 수 있도록 하는 공개형 금융 대시보드입니다.

별도 설치 없이 아래 도메인으로 접속하는 웹 서비스를 목표로 합니다.

```text
https://stock-hanaro.com
```

---

## 주요 목표

사용자가 출근 후 약 10분 이내에 다음 내용을 파악할 수 있도록 합니다.

* 간밤 글로벌 증시 흐름
* 금리·환율·원자재 움직임
* 오늘 국내 증시에 영향을 줄 주요 이슈
* 반복 기사가 제거된 이슈별 뉴스
* 관련 산업과 종목
* 고객에게 설명할 수 있는 아침 브리핑

---

## MVP 핵심 기능

* 글로벌 주요 시장 지표
* 미국시장 히트맵
* 네이버 뉴스 통합
* 뉴스 정규화 및 중복 제거
* 이슈 단위 뉴스 군집화
* 대표 기사 선정
* 관련 종목·산업 연결
* 이슈별 AI 요약
* 주요 이슈 중요도 평가
* Open DART 주요 공시
* KCIF 콘텐츠 수동 등록
* 매일 아침 시장 브리핑
* 공개 도메인 배포

---

## MVP 이후 기능

다음 기능은 초기 MVP에서 제외합니다.

* 회원가입 및 로그인
* 관심 종목 저장
* 사용자별 개인화
* Telegram 실제 연동
* 고객 포트폴리오
* 실시간 전체 종목 시세
* AI 챗봇

향후 로그인과 관심 종목을 추가할 수 있도록 DB와 API 구조는 확장 가능하게 설계합니다.

---

## 기술 스택

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* Apache ECharts
* Vercel

### Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* Render 또는 Railway

### Database

* Supabase PostgreSQL
* pgvector

### Automation

* n8n Cloud

### AI

* OpenAI Embedding API
* OpenAI LLM
* Python 기반 규칙 처리 및 후처리

---

## 외부 데이터 소스

* Naver News Search API
* Open DART API
* 글로벌 시장 데이터 API
* KCIF 원문 링크 또는 관리자 수동 입력

Finviz 화면을 직접 크롤링하거나 복제하지 않고, 시장 데이터 API를 기반으로 자체 히트맵을 구현합니다.

---

## 시스템 구조

```text
Users
  ↓
stock-hanaro.com
  ↓
Next.js Dashboard
  ↓
FastAPI
  ├─ Market Aggregation
  ├─ News Normalization
  ├─ News Clustering
  ├─ Stock / Industry Mapping
  ├─ AI Summary
  └─ Internal Job API
  ↓
Supabase PostgreSQL + pgvector
```

자동화 흐름은 n8n이 담당합니다.

```text
n8n Schedule
  ↓
FastAPI Internal Job API
  ↓
뉴스·공시·시장 데이터 수집
  ↓
정규화 및 중복 제거
  ↓
뉴스 군집화
  ↓
AI 요약 및 브리핑 생성
  ↓
Supabase 저장
```

---

## 데이터 처리 흐름

```text
외부 뉴스·공시·시장 데이터
→ n8n 스케줄 실행
→ FastAPI 내부 작업 API 호출
→ 데이터 정규화
→ URL·제목 기반 중복 제거
→ 임베딩 생성
→ 하이브리드 뉴스 군집화
→ 대표 기사 선정
→ 종목·산업 매핑
→ AI 이슈 요약
→ 주요 이슈 중요도 평가
→ 아침 브리핑 생성
→ Supabase 저장
→ Next.js 대시보드 조회
```

---

## 뉴스 군집화 기준

뉴스 군집화는 다음 정보를 함께 사용합니다.

* 정규화 제목 유사도
* 임베딩 유사도
* 기업명 일치
* 인물명 일치
* 산업 키워드 일치
* 사건 키워드 일치
* 게시 시각 차이
* 출처 다양성

같은 기업의 뉴스라도 사건이 다르면 별도 이슈로 분리합니다.

```text
같은 이슈
- 삼성전자 HBM 공급 테스트 통과
- 삼성 HBM3E 엔비디아 검증 완료
- 삼성전자 HBM 납품 기대 확대

다른 이슈
- 삼성전자 HBM 공급 테스트
- 삼성전자 2분기 잠정실적
- 삼성전자 노조 파업
```

---

## 아침 브리핑 구성

아침 브리핑은 다음 데이터를 기반으로 생성합니다.

* 미국 주요 지수
* 국내 주요 지수
* 환율
* 미국 국채금리
* 원자재
* 주요 이슈
* 중요 공시
* KCIF 등록 콘텐츠
* 주요 경제 일정

출력 형태는 다음과 같습니다.

* 시장 상태: 위험선호 / 중립 / 위험회피
* 30초 브리핑
* 3분 브리핑
* 국내시장 체크포인트
* 주요 업종 및 종목
* 반대 요인과 리스크
* PB 고객 설명용 문장

---

## 주요 데이터 테이블

```text
news
issue_groups
issue_news
stocks
news_stock_relations
market_snapshots
disclosures
briefings
source_documents
pipeline_runs
```

---

## 프로젝트 구조

```text
stock-hanaro/
├─ frontend/
│  └─ Next.js
├─ backend/
│  └─ FastAPI
├─ database/
│  └─ schema 및 migration
├─ n8n/
│  └─ workflow export
├─ docs/
│  └─ 기획 및 설계 문서
├─ .env.example
└─ README.md
```

---

## 개발 일정

### Week 1

* 프로젝트 초기화
* Supabase 연결
* DB 기본 스키마
* 더미 데이터 기반 메인 대시보드

### Week 2

* 뉴스 수집
* Open DART 공시 수집
* 시장 데이터 수집
* 히트맵 데이터 구성
* KCIF 수동 등록

### Week 3

* 뉴스 정규화
* 기업·종목 별칭 사전
* 임베딩 생성
* 뉴스 군집화
* 대표 기사 선정
* 종목·산업 매핑
* 군집화 평가 데이터셋

### Week 4

* 이슈별 AI 요약
* 출처 검증
* 중요도 평가
* 아침 브리핑 생성
* 브리핑 품질 평가
* 프롬프트 버전 관리

### Week 5

* 실제 데이터 화면 연동
* 뉴스·이슈 상세 화면
* 공시 및 종목 검색
* n8n 자동화
* 로그인·개인화 확장 구조 준비

### Week 6

* Vercel·Render·Supabase 배포
* 도메인 연결
* 군집화·브리핑 품질 개선
* 비용 제한 및 장애 대응
* MVP 릴리스

---

## 배포 구조

```text
stock-hanaro.com
  → Vercel
  → Next.js

api.stock-hanaro.com
  → Render 또는 Railway
  → FastAPI

Database
  → Supabase PostgreSQL

Automation
  → n8n Cloud
```

AWS와 Docker는 MVP 필수 사항이 아닙니다.

---

## 운영 원칙

* 페이지 요청 시마다 외부 API를 호출하지 않습니다.
* n8n이 주기적으로 데이터를 수집하고 처리합니다.
* 사용자는 DB에 저장된 결과를 조회합니다.
* 같은 뉴스는 다시 요약하지 않습니다.
* 같은 입력에 대한 AI 결과는 캐싱합니다.
* 숫자 계산은 Python 코드에서 처리합니다.
* LLM은 요약과 해석에 사용합니다.
* 모든 AI 결과에 출처와 생성 시각을 표시합니다.
* 외부 API 장애 시 마지막 정상 데이터를 제공합니다.
* 모든 API 키는 서버 환경변수로 관리합니다.

---

## 로컬 실행

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 환경변수

`.env.example`을 복사해 환경에 맞게 설정합니다.

```env
DATABASE_URL=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

DART_API_KEY=
MARKET_DATA_API_KEY=

OPENAI_API_KEY=

INTERNAL_JOB_SECRET=
FRONTEND_URL=http://localhost:3000
```

실제 비밀키는 GitHub에 올리지 않습니다.

---


`/internal/jobs/*` 경로는 n8n에서만 호출하며 별도의 Secret 검증을 적용합니다.

---

## 현재 개발 우선순위

1. 프로젝트 초기화
2. DB 스키마
3. 더미 UI
4. 뉴스 수집
5. 뉴스 군집화
6. 관련 종목·산업 매핑
7. AI 이슈 요약
8. 아침 브리핑
9. n8n 자동화
10. 공개 배포

---

## 주의사항

* 뉴스 기사 전문을 무단으로 저장하거나 재배포하지 않습니다.
* 화면에는 기사 제목, 출처, 요약, 원문 링크를 중심으로 제공합니다.
* KCIF 콘텐츠는 원문 링크 또는 관리자가 입력한 요약 데이터를 사용합니다.
* 실시간 시세 공개는 데이터 제공 조건을 별도로 확인해야 합니다.
* AI 분석은 투자 권유가 아닌 정보 제공 목적으로 사용합니다.

---

## Disclaimer

stock-hanaro에서 제공하는 데이터와 AI 요약은 정보 제공을 목적으로 합니다.

서비스에서 제공하는 내용은 특정 금융상품의 매수 또는 매도를 권유하지 않으며, 실제 투자 판단과 책임은 사용자에게 있습니다.
