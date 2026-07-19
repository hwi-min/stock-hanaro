from fastapi import APIRouter

from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/home", response_model=DashboardResponse)
def get_home_dashboard() -> DashboardResponse:
    return DashboardService().get_home()
