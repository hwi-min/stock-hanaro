import asyncio
import pytest

from app.core.config import settings
from app.services.ai_summary import OUTPUT_SCHEMA, SolarSummaryClient, parse_json_content


def test_structured_output_schema_requires_source_identifiers():
    assert set(OUTPUT_SCHEMA["required"]) == {"issues", "kcif"}
    issue = OUTPUT_SCHEMA["properties"]["issues"]["items"]
    assert "issue_key" in issue["required"]
    assert issue["additionalProperties"] is False


def test_ai_summary_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "solar_api_key", "")
    with pytest.raises(RuntimeError, match="SOLAR_API_KEY"):
        asyncio.run(SolarSummaryClient().generate({"issues": [], "kcif": []}))


def test_parse_solar_json_content():
    assert parse_json_content('```json\n{"issues": [], "kcif": []}\n```') == {"issues": [], "kcif": []}


def test_parse_solar_json_content_rejects_wrong_shape():
    with pytest.raises(RuntimeError, match="expected summary structure"):
        parse_json_content('{"items": []}')
