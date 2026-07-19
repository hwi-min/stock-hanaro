from fastapi.testclient import TestClient

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
    assert body["briefing"]["source_ids"]
    assert len(body["metrics"]) == 11
    assert {item["market"] for item in body["metrics"]} == {"us", "kr"}
    assert not any(item["symbol"] == "BTCUSD" for item in body["metrics"])
    assert any(item["symbol"] == "NVDA" for item in body["heatmap"])
    assert all(issue["articles"] for issue in body["issues"])
    assert all(any(article["is_representative"] for article in issue["articles"]) for issue in body["issues"])
    assert body["freshness"]


def test_internal_runs_are_protected():
    response = client.get("/internal/jobs/runs")
    assert response.status_code == 401
