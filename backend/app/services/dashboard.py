from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import DashboardResponse


class DashboardService:
    def __init__(self, repository: DashboardRepository | None = None):
        self.repository = repository or DashboardRepository()

    def get_home(self) -> DashboardResponse:
        return DashboardResponse.model_validate(self.repository.get_snapshot())
