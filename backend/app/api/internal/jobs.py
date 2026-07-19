from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.repositories.pipeline_runs import PipelineRunRepository
from app.services.jobs import JobService

router = APIRouter(prefix="/jobs", tags=["internal-jobs"])


class JobRequest(BaseModel):
    business_date: date | None = None
    trigger_type: str = "manual"
    github_run_id: str | None = None
    retry_of: str | None = None


def authorize(x_internal_job_secret: str | None = Header(default=None)) -> None:
    if not settings.internal_job_secret or x_internal_job_secret != settings.internal_job_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal job secret")


def serialize_run(run):
    return {
        "run_id": run.id, "job_name": run.job_name, "business_date": run.business_date,
        "status": run.status, "input_count": run.input_count, "success_count": run.success_count,
        "skip_count": run.skip_count, "error_count": run.error_count, "error_summary": run.error_summary,
        "started_at": run.started_at, "finished_at": run.finished_at, "code_version": run.code_version,
    }


@router.get("/runs")
def list_job_runs(
    _: None = Depends(authorize), db: Session = Depends(get_db), limit: int = Query(default=50, ge=1, le=200)
):
    return {"items": [serialize_run(run) for run in PipelineRunRepository(db).list(limit)]}


@router.get("/runs/{run_id}")
def get_job_run(run_id: str, _: None = Depends(authorize), db: Session = Depends(get_db)):
    run = PipelineRunRepository(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="job run not found")
    return serialize_run(run)


@router.post("/{job_name}", status_code=status.HTTP_202_ACCEPTED)
async def execute_job(
    job_name: str, payload: JobRequest, _: None = Depends(authorize), db: Session = Depends(get_db),
    x_job_idempotency_key: str | None = Header(default=None),
):
    if not x_job_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Job-Idempotency-Key header is required")
    try:
        run, created = await JobService(db).execute(
            job_name=job_name, idempotency_key=x_job_idempotency_key,
            business_date=payload.business_date or date.today(), trigger_type=payload.trigger_type,
            github_run_id=payload.github_run_id, retry_of=payload.retry_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {**serialize_run(run), "created": created}
