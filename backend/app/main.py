import asyncio
from contextlib import asynccontextmanager, suppress

from sqlalchemy import text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.internal.jobs import router as jobs_router
from app.api.public.dashboard import router as dashboard_router
from app.api.public.meta import router as meta_router
from app.api.public.market import router as market_router
from app.api.public.stocks import router as stocks_router
from app.core.config import settings
from app.core.database import engine
from app.realtime import market_stream


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(market_stream.run()) if settings.kis_realtime_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Internal-Job-Secret", "X-Job-Idempotency-Key"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": settings.app_version, "git_sha": settings.git_sha}


@app.get("/health/ready", tags=["health"])
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        return {"status": "not_ready", "database": "unavailable", "detail": type(exc).__name__}
    return {"status": "ready", "database": "ok", "git_sha": settings.git_sha}


app.include_router(dashboard_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(stocks_router, prefix="/api")
app.include_router(jobs_router, prefix="/internal")
