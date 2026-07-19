from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.pipeline_run import PipelineRun, PipelineStatus


class PipelineRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_get(
        self, *, job_name: str, idempotency_key: str, business_date: date, trigger_type: str,
        github_run_id: str | None, code_version: str, retry_of: str | None = None,
    ) -> tuple[PipelineRun, bool]:
        run = PipelineRun(
            job_name=job_name, idempotency_key=idempotency_key, business_date=business_date,
            trigger_type=trigger_type, github_run_id=github_run_id, code_version=code_version, retry_of=retry_of,
        )
        self.db.add(run)
        try:
            self.db.commit()
            self.db.refresh(run)
            return run, True
        except IntegrityError:
            self.db.rollback()
            existing = self.db.scalar(select(PipelineRun).where(
                PipelineRun.job_name == job_name, PipelineRun.idempotency_key == idempotency_key
            ))
            if existing is None:
                raise
            return existing, False

    def start(self, run: PipelineRun) -> None:
        now = datetime.now(timezone.utc)
        run.status = PipelineStatus.running
        run.started_at = now
        run.heartbeat_at = now
        self.db.commit()

    def finish(
        self, run: PipelineRun, *, status: PipelineStatus, input_count: int = 0, success_count: int = 0,
        skip_count: int = 0, error_count: int = 0, error_summary: str | None = None,
    ) -> None:
        run.status = status
        run.input_count = input_count
        run.success_count = success_count
        run.skip_count = skip_count
        run.error_count = error_count
        run.error_summary = error_summary
        run.finished_at = datetime.now(timezone.utc)
        run.heartbeat_at = run.finished_at
        self.db.commit()

    def get(self, run_id: str) -> PipelineRun | None:
        return self.db.get(PipelineRun, run_id)

    def list(self, limit: int = 50) -> list[PipelineRun]:
        return list(self.db.scalars(select(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(limit)))

    def has_success(self, job_name: str, business_date: date, excluding_run_id: str | None = None) -> bool:
        statement = select(PipelineRun.id).where(
            PipelineRun.job_name == job_name,
            PipelineRun.business_date == business_date,
            PipelineRun.status == PipelineStatus.succeeded,
        )
        if excluding_run_id:
            statement = statement.where(PipelineRun.id != excluding_run_id)
        return self.db.scalar(statement.limit(1)) is not None
