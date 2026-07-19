# M2 통합 점검 가이드

## 목적

로컬과 배포 환경에서 같은 명령으로 API, DB, 수집 파이프라인과 주요 화면 데이터 계약을 확인한다.
`scripts/check_m2_integration.py`는 Python 표준 라이브러리만 사용하므로 별도 패키지를 설치하지 않는다.
환경변수는 현재 프로세스를 우선하고, 없으면 저장소 루트의 `.env`를 읽는다. 비밀값은 출력하지 않는다.

## 읽기 전용 점검

백엔드를 실행한 뒤 저장소 루트에서 다음 명령을 실행한다.

```bash
python3 scripts/check_m2_integration.py
```

다른 환경을 검사하려면 API 주소를 지정한다.

```bash
python3 scripts/check_m2_integration.py --base-url https://api.stock-hanaro.com
```

점검 대상은 다음과 같다.

- `/health`, `/health/ready`와 DB 연결
- 홈 대시보드 응답 계약
- 시장 지표, 미국 히트맵, 뉴스 이슈, DART, KCIF 데이터 존재 여부
- 공식 일정과 데이터 신선도
- 모든 이슈의 대표 기사와 출처
- 삼성전자 종목 마스터 검색
- KIS REST 현재가, 투자지표와 일봉 차트
- KIS WebSocket 활성화·연결 상태
- Internal Job API의 각 수집기 최신 실행 결과

KIS 검사를 제외하려면 `--skip-kis`를 사용한다. 휴장 중 WebSocket 미연결은 실패가 아니라 경고다.

## 실제 수집 후 점검

다음 명령은 백엔드 데이터를 변경한다. AI 요약을 제외한 수집 작업을 순차 실행한 뒤 전체 점검을 수행한다.

```bash
python3 scripts/check_m2_integration.py --run-jobs
```

기본 실행 순서는 다음과 같다.

1. KRX 종목 마스터
2. 뉴스 및 규칙 기반 이슈
3. 공식 경제 일정
4. DART 공시
5. KCIF
6. 미국 정규장 종가
7. 국내 스냅샷

특정 작업만 실행할 수 있다.

```bash
python3 scripts/check_m2_integration.py \
  --run-jobs \
  --jobs collect-news,collect-calendar,collect-disclosures
```

Job 실행에는 백엔드와 동일한 `INTERNAL_JOB_SECRET`이 필요하다. `--business-date YYYY-MM-DD`를 생략하면
Asia/Seoul 기준 최근 평일을 사용한다. 매 실행은 고유 idempotency key를 만들며, KCIF와 미국 종가는
해당 영업일에 이미 성공한 경우 서버 정책에 따라 `skipped`가 될 수 있다.

## 결과와 종료 코드

- `PASS`: 계약과 데이터가 정상임
- `WARN`: 휴장, 예정 일정 없음, 데이터 지연처럼 즉시 장애로 단정할 수 없음
- `FAIL`: API·DB 장애, 필수 데이터 부재, 검색 실패 또는 Job 실패

기본 모드는 `FAIL`이 하나라도 있으면 종료 코드 1을 반환한다. CI나 배포 승인에서 경고도 실패로
처리하려면 `--strict`를 사용한다. 자동 처리용 JSON은 `--json`으로 출력한다.

```bash
python3 scripts/check_m2_integration.py --strict --json
```

## 운영 권장 순서

1. 배포 직후 `alembic upgrade head` 실행
2. `--run-jobs --skip-kis`로 초기 데이터 적재
3. 읽기 전용 기본 점검 실행
4. 국내 장중에 KIS WebSocket과 `last_tick_at` 재확인
5. GitHub Actions 실행 결과와 점검 결과를 함께 보관

수집 Job 실패 시 `error_summary` 앞 180자만 점검 결과에 표시한다. API Key나 내부 Secret은 결과에
포함하지 않는다.
