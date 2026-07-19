import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.check_m2_integration import ApiClient, audit_public_api, latest_business_date, run_jobs


class FakeClient(ApiClient):
    def __init__(self, responses, secret="secret"):
        super().__init__("https://example.test", secret)
        self.responses = responses

    def request(self, path, **kwargs):
        return self.responses[path]

    def run_job(self, job, business_date):
        return self.responses[f"job:{job}"]


class M2IntegrationCheckTest(unittest.TestCase):
    def test_latest_business_date_uses_friday_on_weekend(self):
        sunday = datetime(2026, 7, 19, 8, tzinfo=ZoneInfo("Asia/Seoul"))
        self.assertEqual(latest_business_date(sunday), "2026-07-17")

    def test_public_audit_accepts_complete_contract(self):
        dashboard = {
            "briefing": {}, "metrics": [{}], "heatmap": [{}], "schedules": [],
            "issues": [{"id": "i", "articles": [{"is_representative": True}]}],
            "disclosures": [{}], "kcif": [{}], "freshness": [{"dataset": "news", "stale": False}],
        }
        client = FakeClient({
            "/health": {"status": "ok", "version": "test"},
            "/health/ready": {"status": "ready", "database": "ok"},
            "/api/dashboard/home": dashboard,
            "/api/search?q=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90": {"items": [{"id": "005930", "type": "stock"}]},
        })

        results, _ = audit_public_api(client, check_kis=False)

        self.assertFalse(any(result.level == "FAIL" for result in results))
        self.assertTrue(any(result.check == "dataset-schedules" and result.level == "WARN" for result in results))

    def test_public_audit_fails_when_required_dataset_is_empty(self):
        dashboard = {"briefing": {}, "metrics": [], "heatmap": [], "schedules": [], "issues": [],
                     "disclosures": [], "kcif": [], "freshness": []}
        client = FakeClient({
            "/health": {"status": "ok", "version": "test"},
            "/health/ready": {"status": "ready", "database": "ok"},
            "/api/dashboard/home": dashboard,
            "/api/search?q=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90": {"items": []},
        })

        results, _ = audit_public_api(client, check_kis=False)

        self.assertTrue(any(result.level == "FAIL" for result in results))

    def test_job_execution_propagates_failed_status(self):
        client = FakeClient({"job:collect-news": {"status": "failed", "error_count": 1}})

        results = run_jobs(client, ("collect-news",), "2026-07-19")

        self.assertEqual(results[0].level, "FAIL")


if __name__ == "__main__":
    unittest.main()
