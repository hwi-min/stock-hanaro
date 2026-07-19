from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.collectors.kis import kis_client
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness():
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_home_dashboard_contract():
    response = client.get("/api/dashboard/home")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["briefing"]["source_ids"], list)
    assert isinstance(body["metrics"], list)
    if body["metrics"]:
        assert all(float(item["value"].replace(",", "").replace("%", "")) > 0 for item in body["metrics"])
        assert {item["market"] for item in body["metrics"]}.issubset({"us", "kr"})
        assert all(item["basis"] == ("close" if item["market"] == "us" else "delayed") for item in body["metrics"])
    assert not any(item["symbol"] == "BTCUSD" for item in body["metrics"])
    assert all(issue["articles"] for issue in body["issues"])
    assert all(any(article["is_representative"] for article in issue["articles"]) for issue in body["issues"])
    assert isinstance(body["freshness"], list)


def test_internal_runs_are_protected():
    response = client.get("/internal/jobs/runs")
    assert response.status_code == 401


def test_market_stream_status_does_not_expose_credentials():
    response = client.get("/api/market/status")
    assert response.status_code == 200
    body = response.json()
    assert body["expected_subscription_count"] >= body["configured_stock_count"]
    assert "app_key" not in body and "app_secret" not in body


def test_integrated_search_finds_domestic_stock():
    response = client.get("/api/search", params={"q": "삼성전자"})
    assert response.status_code == 200
    assert any(item["id"] == "005930" and item["type"] == "stock" for item in response.json()["items"])


def test_domestic_stock_detail_contract(monkeypatch):
    monkeypatch.setattr(kis_client, "domestic_price", AsyncMock(return_value={
        "price": Decimal("81000"), "change": Decimal("1000"), "change_pct": Decimal("1.25"),
        "volume": Decimal("12345"), "market_cap": Decimal("5000000"),
        "per": Decimal("18.2"), "pbr": Decimal("1.7"), "foreign_ownership_pct": Decimal("51.25"),
        "high_52w": Decimal("90000"), "low_52w": Decimal("52000"),
        "name": "삼성전자", "as_of": datetime.now(timezone.utc),
    }))
    monkeypatch.setattr(kis_client, "domestic_chart", AsyncMock(return_value=[{
        "time": "20260717", "open": Decimal("80000"), "high": Decimal("82000"),
        "low": Decimal("79500"), "close": Decimal("81000"), "volume": Decimal("12345"),
    }]))
    response = client.get("/api/stocks/005930")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "삼성전자"
    assert body["price"] == 81000
    assert body["basis"] == "snapshot"
    assert body["market_cap"] == 5000000
    assert body["foreign_ownership_pct"] == 51.25
    assert body["chart"][0]["close"] == 81000


def test_domestic_stock_weekly_chart_contract(monkeypatch):
    monkeypatch.setattr(kis_client, "domestic_price", AsyncMock(return_value={
        "price": Decimal("81000"), "change": Decimal("1000"), "change_pct": Decimal("1.25"),
        "volume": Decimal("12345"), "name": "삼성전자", "as_of": datetime.now(timezone.utc),
    }))
    monkeypatch.setattr(kis_client, "domestic_chart", AsyncMock(return_value=[{
        "time": "20260717", "open": Decimal("78000"), "high": Decimal("82000"),
        "low": Decimal("77000"), "close": Decimal("81000"), "volume": Decimal("50000"),
    }]))

    response = client.get("/api/stocks/005930", params={"interval": "weekly"})

    assert response.status_code == 200
    assert response.json()["interval"] == "weekly"
    kis_client.domestic_chart.assert_awaited_once_with("005930", "W")
