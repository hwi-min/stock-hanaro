# M1 아키텍처

## 요청 흐름

```text
브라우저 → Next.js → FastAPI Read API → repository → PostgreSQL/Supabase
GitHub Actions → Internal Job API → pipeline → repository → PostgreSQL/Supabase
```

M1에서는 `DashboardRepository`가 계약 검증용 fixture를 반환합니다. M2부터 저장소 구현만 DB 조회로 교체하며 라우터와 화면 계약은 유지합니다.

## 의존 방향

- API 라우터는 service만 호출한다.
- service는 repository 또는 collector를 호출한다.
- repository는 DB 접근을 담당한다.
- collector와 pipeline은 화면을 알지 못한다.
- 공개 조회 요청에서 외부 API나 AI를 호출하지 않는다.

## 홈 화면 계약

`GET /api/dashboard/home`은 브리핑, 시장 지표, 미국 히트맵, 일정, 이슈, 공시, KCIF 요약과 신선도를 한 번에 반환합니다. 각 항목은 상세 화면으로 연결되며, 공개 브리핑은 `source_ids`로 근거를 추적합니다.

## 상태와 버전

- `/health`: 프로세스 생존과 앱 버전
- `/health/ready`: DB 연결 준비 상태
- `/api/meta/freshness`: 데이터 종류별 기준 시각과 지연 여부
- `/api/meta/version`: 앱 버전과 Git SHA

운영 배포에서는 `GIT_SHA`를 배포 커밋으로 주입합니다.
