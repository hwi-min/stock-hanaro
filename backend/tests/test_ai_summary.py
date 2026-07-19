import asyncio
import pytest

from app.core.config import settings
from app.services.ai_summary import OpenAISummaryClient, OUTPUT_SCHEMA


def test_structured_output_schema_requires_source_identifiers():
    assert set(OUTPUT_SCHEMA["required"]) == {"issues", "kcif"}
    issue = OUTPUT_SCHEMA["properties"]["issues"]["items"]
    assert "issue_key" in issue["required"]
    assert issue["additionalProperties"] is False


def test_ai_summary_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        asyncio.run(OpenAISummaryClient().generate({"issues": [], "kcif": []}))
