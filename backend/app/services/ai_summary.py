import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.issue_summary import IssueSummary
from app.models.kcif_report import KcifReport
from app.repositories.dashboard import DashboardRepository

PROMPT_VERSION = "content-summary-v2-solar"

OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "issues": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "issue_key": {"type": "string"}, "title": {"type": "string"},
                "summary": {"type": "string"},
                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            }, "required": ["issue_key", "title", "summary", "sentiment"],
        }},
        "kcif": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "report_no": {"type": "string"}, "summary": {"type": "string"}, "topic": {"type": "string"},
            }, "required": ["report_no", "summary", "topic"],
        }},
    }, "required": ["issues", "kcif"],
}


def parse_json_content(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("issues"), list) or not isinstance(parsed.get("kcif"), list):
        raise RuntimeError("Solar response did not match the expected summary structure")
    return parsed


class SolarSummaryClient:
    async def generate(self, payload: dict) -> dict:
        if not settings.solar_api_key:
            raise RuntimeError("SOLAR_API_KEY is required")
        system_prompt = (
            "당신은 금융 리서치 편집자입니다. 제공된 출처만 사용하고 추정은 단정하지 마세요. "
            "기사 제목을 단순 복제하지 말고 핵심 사실을 한국어로 간결하게 요약하세요. "
            "반드시 지정된 JSON 구조만 출력하고 마크다운 코드 블록은 사용하지 마세요. "
            f"출력 JSON 스키마: {json.dumps(OUTPUT_SCHEMA, ensure_ascii=False)}"
        )
        request = {
            "model": settings.solar_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        endpoint = f"{settings.solar_api_base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=settings.solar_timeout_seconds) as client:
            response = await client.post(endpoint, headers={
                "Authorization": f"Bearer {settings.solar_api_key}", "Content-Type": "application/json",
            }, json=request)
            if response.is_error:
                try:
                    error = response.json().get("error", {})
                    detail = f"{error.get('code') or error.get('type')}: {error.get('message') or 'request failed'}"
                except (ValueError, AttributeError):
                    detail = f"HTTP {response.status_code}"
                raise RuntimeError(f"Solar Chat API {detail}")
            data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Solar response contained no message content") from exc
        return parse_json_content(content)


class AISummaryService:
    def __init__(self, db: Session):
        self.db = db

    async def run(self) -> int:
        issues = DashboardRepository(self.db).issues()
        report = self.db.scalar(select(KcifReport).order_by(desc(KcifReport.report_date)).limit(1))
        input_payload = {
            "instructions": (
                "각 뉴스 이슈는 제목 25자 이내, 요약 2문장 이내로 작성하고 국내 시장 영향은 "
                "가능성 표현을 사용한다. KCIF는 핵심 사실과 시장 시사점을 3문장 이내로 요약한다."
            ),
            "issues": [{"issue_key": issue["id"], "category": issue["category"], "articles": [
                {"id": article["id"], "title": article["title"]} for article in issue["articles"]
            ]} for issue in issues],
            "kcif": [] if report is None else [{
                "report_no": report.report_no, "title": report.title, "text": report.extracted_text[:12000],
            }],
        }
        output = await SolarSummaryClient().generate(input_payload)
        allowed_issues = {issue["id"]: issue for issue in issues}
        count = 0
        for generated in output["issues"]:
            source = allowed_issues.get(generated.get("issue_key"))
            if source is None:
                continue
            row = self.db.scalar(select(IssueSummary).where(IssueSummary.issue_key == generated["issue_key"]))
            values = {
                "category": source["category"], "title": generated["title"], "summary": generated["summary"],
                "sentiment": generated["sentiment"],
                "article_ids_json": json.dumps([article["id"] for article in source["articles"]]),
                "model": settings.solar_model, "prompt_version": PROMPT_VERSION,
                "generated_at": datetime.now(timezone.utc),
            }
            if row is None:
                self.db.add(IssueSummary(issue_key=generated["issue_key"], **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            count += 1
        if report is not None:
            generated_kcif = next((item for item in output["kcif"] if item.get("report_no") == report.report_no), None)
            if generated_kcif:
                report.ai_summary = generated_kcif["summary"]
                report.ai_topic = generated_kcif["topic"]
                report.ai_model = settings.solar_model
                report.ai_summarized_at = datetime.now(timezone.utc)
                count += 1
        self.db.commit()
        return count
