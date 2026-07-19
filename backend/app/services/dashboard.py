from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import DashboardResponse


class DashboardService:
    def __init__(self, db: Session):
        self.repository = DashboardRepository(db)

    def get_home(self) -> DashboardResponse:
        now = datetime.now(timezone.utc)
        metrics = self.repository.market_metrics()
        issues = self.repository.issues()
        nasdaq = next((item for item in metrics if item["symbol"] == "NASDAQ"), None)
        stance = "risk_on" if nasdaq and nasdaq["change_pct"] > 0.3 else "risk_off" if nasdaq and nasdaq["change_pct"] < -0.3 else "neutral"
        direction = "강세" if stance == "risk_on" else "약세" if stance == "risk_off" else "혼조"
        keywords = [item["category"] for item in issues[:3]] or ["데이터 수집 대기"]
        source_ids = (["market:NASDAQ"] if nasdaq else []) + [f"news:{item['id']}" for item in issues[:2]]
        briefing = {
            "stance": stance,
            "headline": f"미국 기술주 흐름은 {direction}, 환율과 금리를 함께 확인하세요" if nasdaq else "시장 데이터 수집을 기다리고 있습니다",
            "summary": issues[0]["summary"] if issues else "수집 작업이 완료되면 최신 시장·뉴스 데이터를 바탕으로 브리핑을 제공합니다.",
            "keywords": list(dict.fromkeys(keywords)), "source_ids": source_ids,
            "as_of": nasdaq["as_of"] if nasdaq else now,
        }
        snapshot = {
            "briefing": briefing, "metrics": metrics, "heatmap": self.repository.heatmap(),
            "schedules": self.repository.schedules(now), "issues": issues,
            "disclosures": self.repository.disclosures(), "kcif": self.repository.kcif(),
            "freshness": self.repository.freshness(now),
        }
        return DashboardResponse.model_validate(snapshot)
