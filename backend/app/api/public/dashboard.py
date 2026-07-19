from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/home", response_model=DashboardResponse)
def get_home_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return DashboardService(db).get_home()
