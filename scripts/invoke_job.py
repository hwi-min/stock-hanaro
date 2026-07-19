#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"required environment variable is missing: {name}")
    return value


def main() -> None:
    base_url = required("BACKEND_API_BASE_URL").rstrip("/")
    secret = required("INTERNAL_JOB_SECRET")
    job_name = required("JOB_NAME")
    business_date = os.environ.get("BUSINESS_DATE") or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    idempotency_key = os.environ.get("IDEMPOTENCY_KEY") or f"{job_name}-{business_date}-{run_id}-{attempt}"
    payload = json.dumps({
        "business_date": business_date, "trigger_type": "github_actions", "github_run_id": run_id,
    }).encode()
    request = urllib.request.Request(
        f"{base_url}/internal/jobs/{job_name}", data=payload, method="POST",
        headers={"Content-Type": "application/json", "X-Internal-Job-Secret": secret,
                 "X-Job-Idempotency-Key": idempotency_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:2000]
        raise SystemExit(f"Job API HTTP {exc.code}: {body}") from exc
    safe_result = {key: result.get(key) for key in (
        "run_id", "job_name", "business_date", "status", "input_count", "success_count", "skip_count",
        "error_count", "error_summary", "created",
    )}
    print(json.dumps(safe_result, ensure_ascii=False))
    if result.get("status") not in {"succeeded", "skipped"}:
        raise SystemExit(f"Job finished with non-success status: {result.get('status')}")


if __name__ == "__main__":
    main()
