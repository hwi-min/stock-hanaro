import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.issue_summary import IssueSummary
from app.models.kcif_report import KcifReport
from app.repositories.dashboard import DashboardRepository

PROMPT_VERSION = "content-summary-v1"

OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "issues": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "issue_key": {"type": "string"}, "title": {"type": "string"},
                "summary": {"type": "string"}, "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            }, "required": ["issue_key", "title", "summary", "sentiment"],
        }},
        "kcif": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"report_no": {"type": "string"}, "summary": {"type": "string"}, "topic": {"type": "string"}},
            "required": ["report_no", "summary", "topic"],
        }},
    }, "required": ["issues", "kcif"],
}


class OpenAISummaryClient:
    async def generate(self, payload: dict) -> dict:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required")
        request = {
            "model": settings.openai_model,
            "input": [
                {"role": "system", "content": "당신은 금융 리서치 편집자다. 제공된 출처만 사용하고 추정은 단정하지 않는다. 한국어로 간결하게 작성한다. 기사 제목과 제공 요약문을 재배포하지 말고 핵심 사실을 새 문장으로 요약한다."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "text": {"format": {"type": "json_schema", "name": "content_summaries", "strict": True, "schema": OUTPUT_SCHEMA}},
        }
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post("https://api.openai.com/v1/responses", headers={
                "Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json",
            }, json=request)
            if response.is_error:
                try:
                    error = response.json().get("error", {})
                    detail = f"{error.get('code') or error.get('type')}: {error.get('message') or 'request failed'}"
                except (ValueError, AttributeError):
                    detail = f"HTTP {response.status_code}"
                raise RuntimeError(f"OpenAI Responses API {detail}")
            data = response.json()
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return json.loads(content["text"])
        raise RuntimeError("OpenAI response contained no output_text")


class AISummaryService:
    def __init__(self, db: Session):
        self.db = db

    async def run(self) -> int:
        issues = DashboardRepository(self.db).issues()
        report = self.db.scalar(select(KcifReport).order_by(desc(KcifReport.report_date)).limit(1))
        input_payload = {
            "instructions": "각 뉴스 이슈는 제목 25자 이내, 요약 2문장 이내로 작성하고 국내 시장 영향은 가능성 표현을 사용한다. KCIF는 핵심 사실과 시장 시사점을 3문장 이내로 요약한다.",
            "issues": [{"issue_key": issue["id"], "category": issue["category"], "articles": [
                {"id": article["id"], "title": article["title"]} for article in issue["articles"]
            ]} for issue in issues],
            "kcif": [] if report is None else [{"report_no": report.report_no, "title": report.title, "text": report.extracted_text[:12000]}],
        }
        output = await OpenAISummaryClient().generate(input_payload)
        allowed_issues = {issue["id"]: issue for issue in issues}
        count = 0
        for generated in output["issues"]:
            source = allowed_issues.get(generated["issue_key"])
            if source is None:
                continue
            row = self.db.scalar(select(IssueSummary).where(IssueSummary.issue_key == generated["issue_key"]))
            values = {
                "category": source["category"], "title": generated["title"], "summary": generated["summary"],
                "sentiment": generated["sentiment"], "article_ids_json": json.dumps([a["id"] for a in source["articles"]]),
                "model": settings.openai_model, "prompt_version": PROMPT_VERSION, "generated_at": datetime.now(timezone.utc),
            }
            if row is None:
                self.db.add(IssueSummary(issue_key=generated["issue_key"], **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            count += 1
        if report is not None:
            generated_kcif = next((item for item in output["kcif"] if item["report_no"] == report.report_no), None)
            if generated_kcif:
                report.ai_summary = generated_kcif["summary"]
                report.ai_topic = generated_kcif["topic"]
                report.ai_model = settings.openai_model
                report.ai_summarized_at = datetime.now(timezone.utc)
                count += 1
        self.db.commit()
        return count
