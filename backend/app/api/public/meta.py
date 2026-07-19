from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.services.dashboard import DashboardService

router = APIRouter(tags=["meta"])


@router.get("/meta/freshness")
def get_freshness():
    return {"data": DashboardService().get_home().freshness, "generated_at": datetime.now(timezone.utc)}


@router.get("/meta/version")
def get_version():
    return {"version": settings.app_version, "git_sha": settings.git_sha}
