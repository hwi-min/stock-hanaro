# M0 데이터 소스 사용 정책

기준일: 2026-07-17  
기준 문서: stock-hanaro 서비스 기획서 v3.0, 0주차 및 12장

## 완료 기준

수집기 구현 전에 각 소스의 저장, 공개 화면 표시, 재배포, AI 입력 범위를
[`config/data-sources.json`](../config/data-sources.json)에 등록한다. `provisional`은 기술 개발을 허용하지만
공개 배포 승인을 뜻하지 않는다. `restricted`와 `blocked` 소스는 허용된 동작 외에는 기본 거부한다.

| 소스 | 저장 | 공개 표시 | 재배포 | AI 입력 | M0 결정 |
|---|---:|---:|---:|---:|---|
| NAVER Finance 뉴스 | 예 | 예 | 아니요 | 예 | `hana-hub` 방식의 메타데이터·요약문·원문 링크 수집 |
| Open DART | 예 | 예 | 아니요 | 예 | 구조화 필드와 원문 링크 사용, 공개 전 최종 검토 |
| KIS Open API | 예 | 예 | 아니요 | 예 | 실시간 시장 데이터의 기본 공급자로 확정 |
| KCIF 국제금융속보 | 예 | 예 | 아니요 | 예 | 당일 PDF 자동 다운로드·추출·AI 요약 |
| 공식 경제 일정 | 예 | 예 | 아니요 | 예 | BLS·BEA·Federal Reserve·한국은행 무료 일정 통합 |

## 근거와 구현 규칙

### NAVER Finance 뉴스

- `/Users/hwkim/Documents/hanaSecurities/hana-hub/backend/app/collectors/naver.py`의 방식을 기준 구현으로 사용한다.
- `finance.naver.com`의 증시 뉴스 목록과 종목 뉴스 탭에서 제목, 제공 요약문, 언론사, 게시 시각, 관련 종목과 원문 링크를 수집한다.
- URL을 중복 키로 사용하며 기사 본문은 저장하지 않는다. AI에는 제목과 제공 요약문만 입력한다.
- 화면에는 생성 요약과 원문 링크를 함께 표시하고, 원문 또는 NAVER가 제공한 콘텐츠 자체를 재배포하지 않는다.
- HTML 구조, robots 정책 또는 이용조건이 바뀌면 수집 실패를 전체 파이프라인의 `partial` 상태로 격리한다.

참조: [NAVER Finance 뉴스](https://finance.naver.com/news/news_list.naver), [NAVER 이용약관](https://policy.naver.com/policy/service.html)

### Open DART

- Open DART는 공시 원문과 주요 공시·재무 정보를 API로 활용할 수 있다고 안내한다.
- 공시 목록, 회사명, 접수번호, 공시 유형, 접수일과 구조화된 주요 필드를 저장한다. 화면에는 `Open DART` 출처와 DART 원문 링크를 제공한다.
- AI가 만든 긍정·부정 영향은 공시 사실과 분리하고 `추정`으로 표시한다. 원문 XML/PDF 자체는 공개 서버에서 재배포하지 않는다.
- 인증키, 요청 제한, 제3자 권리와 약관 변경을 배포 전 다시 확인한다.

공식 문서: [Open DART 소개](https://opendart.fss.or.kr/intro/main.do), [Open DART 이용약관](https://opendart.fss.or.kr/intro/terms.do)

### KIS Open API

- KIS Open API를 시장 데이터의 기본 공급자로 확정하되, 미국과 국내 시장의 시의성 정책을 분리한다.
- `hana-hub/backend/app/collectors/kis.py`의 OAuth 토큰 캐시, 동시 재발급 잠금, 실패 쿨다운과 API 호출 구조를 재사용한다.
- KOSPI·KOSDAQ과 설정된 국내 종목은 KIS WebSocket 실시간 체결을 활용하며, 08:50·15:40 REST 스냅샷을 장애 시 안전망으로 저장한다.
- 미국 증시 히트맵은 미국 정규장 마감 후 KIS 해외주식 API에서 종목별 종가와 등락률을 수집하고, 별도 종목-업종 마스터와 결합해 업종별로 집계한다.
- 미국 마감 수집은 한국시간 06:30에 실행하고 실패한 경우에만 07:00에 재시도한다. 동일 `business_date`에 성공 기록이 있으면 재시도는 `skipped`로 종료한다.
- 히트맵 면적 기준은 시가총액, 색상 기준은 등락률로 하며 모든 값에 KIS 데이터 기준 시각을 표시한다.
- 공개 화면에는 원시 응답 대신 필요한 값, 등락률, 기준 시각과 함께 미국은 `마지막 정규장 종가`, 국내는 `실시간` 또는 `최근 스냅샷`으로 표시한다.
- 앱 키와 시크릿은 백엔드에만 저장하며 로그나 브라우저에 노출하지 않는다.

공식 문서: [KIS Developers](https://apiportal.koreainvestment.com/)

### KCIF 국제금융속보

- [국제금융속보 목록](https://www.kcif.or.kr/annual/newsflashList)에서 당일 보고서 PDF 링크를 찾아 다운로드한다.
- PDF 텍스트를 추출해 출처 기반 AI 요약을 만들고, 원본 PDF는 공개 재배포하지 않는다.
- Kubernetes CronJob은 평일 `07:00`, `07:30`, `08:00`, `08:30`, `09:00`에 작업을 실행한다. 시간대는 `Asia/Seoul` 기준이다.
- 첫 성공 전까지만 다음 예약 시각에 재시도한다. `business_date`별 성공 기록이 있으면 이후 호출은 `skipped`로 종료해 PDF 다운로드와 AI 요약을 반복하지 않는다.
- `09:00` 실행도 실패하면 해당 날짜 실행을 `failed`로 확정하고 운영 상태에 노출한다.
- 공개 화면에는 요약, 보고서 기준일, 생성 시각, KCIF 출처와 원문 링크를 표시한다.
- 처리용 PDF 보존 기간은 최대 30일이며 운영 환경에서는 가능한 한 요약 완료 직후 삭제한다.

구현 참고: [GPTers KCIF 자동화 가이드](https://www.gpters.org/wealth/post/7step-guide-automating-your-596ebN0wqXBUScG)

### 공식 경제 일정

- BLS의 공개 ICS, BEA의 JSON/ICS, Federal Reserve 캘린더와 한국은행 통계공표 일정을 통합한다.
- 매일 05:50 Asia/Seoul에 갱신하고 실패할 때만 06:10에 다시 시도한다.
- 원본 시각을 UTC로 저장하고 화면에는 한국시간을 표시한다. 홈에는 향후 24시간의 중요 일정만 노출한다.
- 중요도는 CPI, PCE, 고용, GDP, FOMC, 금통위 등 사전에 검토한 화이트리스트로 결정한다.
- 공식 원천이 제공하지 않는 시장 예상치나 실제치를 임의로 만들지 않는다.

공식 문서: [BLS ICS](https://www.bls.gov/schedule/news_release/bls.ics), [BEA Calendar](https://www.bea.gov/news/schedule/icalendar), [Federal Reserve Calendar](https://www.federalreserve.gov/newsevents/calendar.htm), [한국은행 통계공표일정](https://www.bok.or.kr/portal/submain/submain/sts.do?menuNo=200094&viewType=SUBMAIN)

## 승인 절차

1. 담당자가 공식 약관과 상품 계약을 검토하고 근거 URL 및 검토일을 갱신한다.
2. 공개 배포 주체가 사용 범위를 승인한다. 불명확하면 공급자에게 서면으로 문의한다.
3. `config/data-sources.json`을 수정하고 검증 및 테스트를 통과시킨다.
4. 소스별 수집기는 정책의 `allowed` 값보다 넓은 동작을 요청할 수 없도록 한다.
5. 분기별 및 공급자 공지 발생 시 재검토한다.

이 문서는 제품 구현 정책이며 법률 자문이 아니다.
