import argparse
import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.services.jobs import JobService


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_name")
    parser.add_argument("--slot", default=os.environ.get("JOB_SLOT"))
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    business_date = now.date()
    slot = args.slot or now.strftime("%H%M")
    key = f"k8s-{args.job_name}-{business_date.isoformat()}-{slot}"
    with SessionLocal() as db:
        run, _ = await JobService(db).execute(
            job_name=args.job_name, idempotency_key=key, business_date=business_date,
            trigger_type="kubernetes-cronjob",
        )
        print(f"{run.job_name}: {run.status} ({run.id})", flush=True)
        value = run.status.value if hasattr(run.status, "value") else str(run.status)
        return 0 if value in {"succeeded", "skipped", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
