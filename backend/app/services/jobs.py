from datetime import date

from sqlalchemy.orm import Session

from app.collectors.news import NaverFinanceNewsCollector
from app.collectors.dart import DartClient
from app.collectors.kis import kis_client
from app.collectors.calendar import OfficialCalendarCollector
from app.collectors.kcif import KcifCollector
from app.core.config import settings
from app.models.pipeline_run import PipelineRun, PipelineStatus
from app.repositories.news import NewsRepository
from app.repositories.pipeline_runs import PipelineRunRepository
from app.repositories.market import MarketRepository
from app.repositories.disclosures import DisclosureRepository
from app.repositories.calendar import CalendarRepository
from app.repositories.kcif import KcifRepository
from app.services.ai_summary import AISummaryService
from app.services.rule_based_issues import RuleBasedIssueService
from app.collectors.stock_master import stock_master_collector
from app.repositories.stock_master import StockMasterRepository
from app.collectors.research import research_collector
from app.repositories.research import ResearchRepository


SUPPORTED_JOBS = {
    "collect-calendar", "collect-disclosures", "collect-kcif", "collect-kr-snapshot",
    "collect-market", "collect-news", "collect-us-close", "summarize-content",
    "collect-stock-master", "collect-research", "build-issues",
}
RETRY_UNTIL_SUCCESS_JOBS = {"collect-kcif", "collect-us-close"}


class JobService:
    def __init__(self, db: Session):
        self.runs = PipelineRunRepository(db)
        self.news = NewsRepository(db)
        self.market = MarketRepository(db)
        self.disclosures = DisclosureRepository(db)
        self.calendar = CalendarRepository(db)
        self.kcif = KcifRepository(db)
        self.stock_master = StockMasterRepository(db)
        self.research = ResearchRepository(db)

    async def execute(
        self, *, job_name: str, idempotency_key: str, business_date: date, trigger_type: str,
        github_run_id: str | None = None, retry_of: str | None = None,
    ) -> tuple[PipelineRun, bool]:
        if job_name not in SUPPORTED_JOBS:
            raise ValueError(f"unsupported job: {job_name}")
        run, created = self.runs.create_or_get(
            job_name=job_name, idempotency_key=idempotency_key, business_date=business_date,
            trigger_type=trigger_type, github_run_id=github_run_id, code_version=settings.git_sha, retry_of=retry_of,
        )
        if not created:
            return run, False
        if job_name in RETRY_UNTIL_SUCCESS_JOBS and self.runs.has_success(
            job_name, business_date, excluding_run_id=run.id
        ):
            self.runs.finish(run, status=PipelineStatus.skipped, skip_count=1, error_summary="already succeeded")
            return run, True
        self.runs.start(run)
        try:
            if job_name == "collect-news":
                items = await NaverFinanceNewsCollector().collect()
                inserted, skipped = self.news.upsert_many(items)
                RuleBasedIssueService(self.runs.db).run()
                errors: list[str] = []
            elif job_name == "collect-market":
                items, errors = await kis_client.collect_market_snapshot()
                inserted, skipped = self.market.upsert_many(items)
            elif job_name == "collect-us-close":
                items, errors = await kis_client.collect_us_close_snapshot()
                inserted, skipped = self.market.upsert_many(items)
            elif job_name == "collect-kr-snapshot":
                items, errors = await kis_client.collect_kr_snapshot()
                inserted, skipped = self.market.upsert_many(items)
            elif job_name == "collect-stock-master":
                items = await stock_master_collector.collect()
                inserted, skipped = self.stock_master.replace(items)
                errors = []
            elif job_name == "collect-research":
                items = await research_collector.collect()
                inserted, skipped = self.research.upsert_many(items)
                errors = []
            elif job_name == "collect-disclosures":
                items = await DartClient().collect(business_date)
                inserted, skipped = self.disclosures.upsert_many(items)
                errors = []
            elif job_name == "collect-calendar":
                items, errors = await OfficialCalendarCollector().collect()
                inserted, skipped = self.calendar.upsert_many(items)
            elif job_name == "collect-kcif":
                item = await KcifCollector().collect(business_date)
                inserted, skipped = self.kcif.upsert(item)
                items, errors = [item], []
            elif job_name == "build-issues":
                inserted = RuleBasedIssueService(self.runs.db).run()
                skipped, items, errors = 0, [None] * inserted, []
            else:
                summarized = await AISummaryService(self.runs.db).run()
                inserted, skipped, items, errors = summarized, 0, [None] * summarized, []
            final_status = PipelineStatus.partial if errors and items else PipelineStatus.failed if errors else PipelineStatus.succeeded
            self.runs.finish(
                run, status=final_status, input_count=len(items) + len(errors), success_count=inserted,
                skip_count=skipped, error_count=len(errors), error_summary="\n".join(errors)[:2000] or None,
            )
        except Exception as exc:
            self.runs.finish(run, status=PipelineStatus.failed, error_count=1, error_summary=str(exc)[:2000])
        return run, True
