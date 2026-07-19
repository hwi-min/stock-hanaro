from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings

router = APIRouter(prefix="/jobs", tags=["internal-jobs"])


@router.get("/runs")
def list_job_runs(x_internal_job_secret: str | None = Header(default=None)):
    if not settings.internal_job_secret or x_internal_job_secret != settings.internal_job_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal job secret")
    return {"items": [], "note": "Job execution is implemented in M2."}
