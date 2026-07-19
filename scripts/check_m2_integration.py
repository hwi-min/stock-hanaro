#!/usr/bin/env python3
"""Run a deployment-friendly M2 integration audit using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOBS = (
    "collect-stock-master", "collect-news", "collect-calendar", "collect-disclosures",
    "collect-kcif", "collect-us-close", "collect-kr-snapshot",
)
SUCCESS_STATUSES = {"succeeded", "skipped"}


@dataclass
class CheckResult:
    level: str
    check: str
    message: str


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class ApiClient:
    def __init__(self, base_url: str, secret: str = "", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout

    def request(self, path: str, *, method: str = "GET", payload: dict | None = None,
                headers: dict[str, str] | None = None, timeout: int | None = None) -> Any:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, method=method, headers={
            **({"Content-Type": "application/json"} if payload is not None else {}), **(headers or {}),
        })
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"connection failed: {exc.reason if hasattr(exc, 'reason') else exc}") from exc

    def internal_headers(self) -> dict[str, str]:
        if not self.secret:
            raise RuntimeError("INTERNAL_JOB_SECRET is not configured")
        return {"X-Internal-Job-Secret": self.secret}

    def run_job(self, job: str, business_date: str) -> dict:
        return self.request(f"/internal/jobs/{job}", method="POST", timeout=600,
                            payload={"business_date": business_date, "trigger_type": "integration_check"},
                            headers={**self.internal_headers(),
                                     "X-Job-Idempotency-Key": f"audit-{job}-{business_date}-{uuid.uuid4().hex[:10]}"})


def add(results: list[CheckResult], level: str, check: str, message: str) -> None:
    results.append(CheckResult(level, check, message))


def latest_business_date(now: datetime | None = None) -> str:
    current = (now or datetime.now(ZoneInfo("Asia/Seoul"))).date()
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.isoformat()


def audit_public_api(client: ApiClient, *, check_kis: bool) -> tuple[list[CheckResult], dict | None]:
    results: list[CheckResult] = []
    dashboard: dict | None = None
    try:
        health = client.request("/health")
        add(results, "PASS" if health.get("status") == "ok" else "FAIL", "health",
            f"API {health.get('status', 'unknown')} · version {health.get('version', '-')}")
    except RuntimeError as exc:
        add(results, "FAIL", "health", str(exc))
        return results, None
    try:
        ready = client.request("/health/ready")
        add(results, "PASS" if ready.get("status") == "ready" else "FAIL", "readiness",
            f"database {ready.get('database', 'unknown')}")
    except RuntimeError as exc:
        add(results, "FAIL", "readiness", str(exc))

    try:
        dashboard = client.request("/api/dashboard/home")
        required = {"briefing", "metrics", "heatmap", "schedules", "issues", "disclosures", "kcif", "freshness"}
        missing = sorted(required - dashboard.keys())
        add(results, "FAIL" if missing else "PASS", "dashboard-contract",
            f"missing keys: {', '.join(missing)}" if missing else "required response fields present")
        for key, label in (("metrics", "market"), ("heatmap", "US heatmap"), ("issues", "news issues"),
                           ("disclosures", "DART"), ("kcif", "KCIF")):
            count = len(dashboard.get(key) or [])
            add(results, "PASS" if count else "FAIL", f"dataset-{key}", f"{label}: {count} item(s)")
        metric_symbols = {item.get("symbol") for item in dashboard.get("metrics") or []}
        missing_optional = sorted({"RUSSELL2000", "VIX"} - metric_symbols)
        add(results, "WARN" if missing_optional else "PASS", "optional-us-indices",
            f"KIS unavailable: {', '.join(missing_optional)}" if missing_optional else "Russell 2000 and VIX present")
        schedules = len(dashboard.get("schedules") or [])
        add(results, "PASS" if schedules else "WARN", "dataset-schedules",
            f"official calendar: {schedules} upcoming item(s)")
        freshness = dashboard.get("freshness") or []
        stale = [item.get("label", item.get("dataset", "unknown")) for item in freshness if item.get("stale")]
        add(results, "WARN" if stale else "PASS", "freshness",
            f"stale: {', '.join(stale)}" if stale else f"{len(freshness)} dataset(s) fresh")
        invalid_issues = [item.get("id") for item in dashboard.get("issues", [])
                          if not item.get("articles") or not any(a.get("is_representative") for a in item["articles"])]
        add(results, "FAIL" if invalid_issues else "PASS", "issue-sources",
            f"missing sources: {invalid_issues}" if invalid_issues else "all issues include a representative source")
    except RuntimeError as exc:
        add(results, "FAIL", "dashboard", str(exc))

    try:
        search = client.request("/api/search?" + urllib.parse.urlencode({"q": "삼성전자"}))
        found = any(item.get("id") == "005930" and item.get("type") == "stock" for item in search.get("items", []))
        add(results, "PASS" if found else "FAIL", "stock-search", "삼성전자 005930 found" if found else "005930 missing")
    except RuntimeError as exc:
        add(results, "FAIL", "stock-search", str(exc))

    if check_kis:
        try:
            detail = client.request("/api/stocks/005930?interval=daily", timeout=60)
            chart = detail.get("chart") or []
            indicators = all(detail.get(key) is not None for key in ("market_cap", "per", "pbr", "high_52w", "low_52w"))
            add(results, "PASS" if detail.get("price", 0) > 0 and chart else "FAIL", "kis-rest-stock",
                f"price {detail.get('price', 0):,.0f} · chart {len(chart)} point(s)")
            add(results, "PASS" if indicators else "WARN", "kis-investment-indicators",
                "market cap/PER/PBR/52-week range present" if indicators else "one or more indicators missing")
        except RuntimeError as exc:
            add(results, "WARN", "kis-rest-stock", str(exc))
        try:
            status = client.request("/api/market/status")
            if not status.get("enabled"):
                add(results, "WARN", "kis-websocket", "disabled in this environment")
            elif status.get("connected"):
                add(results, "PASS", "kis-websocket", f"{status.get('accepted_subscription_count', 0)} subscription(s) accepted")
            else:
                detail = status.get("last_connection_error") or "not connected; verify during KRX trading hours"
                add(results, "WARN", "kis-websocket", detail)
        except RuntimeError as exc:
            add(results, "WARN", "kis-websocket", str(exc))
    return results, dashboard


def audit_runs(client: ApiClient, jobs: tuple[str, ...]) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not client.secret:
        add(results, "WARN", "pipeline-runs", "INTERNAL_JOB_SECRET missing; internal run history skipped")
        return results
    try:
        payload = client.request("/internal/jobs/runs?limit=200", headers=client.internal_headers())
        latest: dict[str, dict] = {}
        for run in payload.get("items", []):
            latest.setdefault(run.get("job_name", ""), run)
        for job in jobs:
            run = latest.get(job)
            if run is None:
                add(results, "WARN", f"run-{job}", "no run recorded")
            else:
                status = run.get("status", "unknown")
                level = "PASS" if status in SUCCESS_STATUSES else "FAIL"
                message = f"{status} · success {run.get('success_count', 0)} · errors {run.get('error_count', 0)}"
                if run.get("error_summary"):
                    message += f" · {str(run['error_summary'])[:180]}"
                add(results, level, f"run-{job}", message)
    except RuntimeError as exc:
        add(results, "FAIL", "pipeline-runs", str(exc))
    return results


def run_jobs(client: ApiClient, jobs: tuple[str, ...], business_date: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not client.secret:
        return [CheckResult("FAIL", "job-execution", "INTERNAL_JOB_SECRET is required for --run-jobs")]
    for job in jobs:
        try:
            run = client.run_job(job, business_date)
            status = run.get("status", "unknown")
            message = f"{status} · input {run.get('input_count', 0)} · success {run.get('success_count', 0)} · errors {run.get('error_count', 0)}"
            if run.get("error_summary"):
                message += f" · {str(run['error_summary'])[:180]}"
            add(results, "PASS" if status in SUCCESS_STATUSES else "FAIL", f"execute-{job}", message)
        except RuntimeError as exc:
            add(results, "FAIL", f"execute-{job}", str(exc))
    return results


def print_report(results: list[CheckResult], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"checks": [asdict(result) for result in results],
                          "summary": {level: sum(r.level == level for r in results) for level in ("PASS", "WARN", "FAIL")}},
                         ensure_ascii=False, indent=2))
        return
    for result in results:
        print(f"[{result.level:<4}] {result.check}: {result.message}")
    print("-" * 72)
    print(" ".join(f"{level}={sum(r.level == level for r in results)}" for level in ("PASS", "WARN", "FAIL")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check stock-hanaro M2 data collection and API integration")
    parser.add_argument("--base-url", default="", help="FastAPI base URL; defaults to BACKEND_API_BASE_URL/NEXT_PUBLIC_API_BASE_URL")
    parser.add_argument("--run-jobs", action="store_true", help="execute collectors before auditing (mutates backend data)")
    parser.add_argument("--jobs", default=",".join(DEFAULT_JOBS), help="comma-separated Job API names")
    parser.add_argument("--business-date", default="", help="KST business date in YYYY-MM-DD")
    parser.add_argument("--skip-kis", action="store_true", help="skip KIS REST and WebSocket checks")
    parser.add_argument("--strict", action="store_true", help="return non-zero for warnings as well as failures")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()
    base_url = (args.base_url or os.environ.get("BACKEND_API_BASE_URL")
                or os.environ.get("NEXT_PUBLIC_API_BASE_URL") or "http://localhost:8000")
    secret = os.environ.get("INTERNAL_JOB_SECRET", "").strip()
    jobs = tuple(job.strip() for job in args.jobs.split(",") if job.strip())
    business_date = args.business_date or latest_business_date()
    client = ApiClient(base_url, secret)
    results: list[CheckResult] = []
    if args.run_jobs:
        results.extend(run_jobs(client, jobs, business_date))
    public_results, _ = audit_public_api(client, check_kis=not args.skip_kis)
    results.extend(public_results)
    results.extend(audit_runs(client, jobs))
    print_report(results, as_json=args.json)
    failed = any(result.level == "FAIL" for result in results)
    warned = any(result.level == "WARN" for result in results)
    return 1 if failed or (args.strict and warned) else 0


if __name__ == "__main__":
    raise SystemExit(main())
