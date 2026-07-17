# stock-hanaro

증권사 영업직원과 PB를 위한 공개형 금융 대시보드입니다.

## 현재 단계

기획서 v3.0의 M0(0주차 데이터 사용조건)을 진행하고 있습니다. 데이터 수집 코드를 추가하기 전에
[`config/data-sources.json`](config/data-sources.json)에 저장, 화면 표시, 재배포, AI 입력 가능 범위가
등록되고 검증을 통과해야 합니다.

```bash
python3 scripts/validate_data_sources.py
python3 -m unittest discover -s tests -v
```

정책 판단과 운영 절차는 [`docs/data-source-policy.md`](docs/data-source-policy.md)를 참고하세요.

> 이 저장소의 정책 표는 개발 안전장치이며 법률 자문을 대신하지 않습니다. 공개 배포 전 서비스
> 운영 주체의 최종 검토가 필요합니다.
