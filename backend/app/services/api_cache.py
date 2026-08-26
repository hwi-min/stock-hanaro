import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.api_cache import ApiCache


_locks: dict[str, asyncio.Lock] = {}


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"cannot cache {type(value).__name__}")


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class ApiCacheService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, cache_key: str, *, allow_expired: bool = False) -> tuple[Any, datetime] | None:
        row = self.db.get(ApiCache, cache_key)
        if row is None:
            return None
        expires_at = _aware(row.expires_at)
        if not allow_expired and expires_at <= datetime.now(timezone.utc):
            return None
        return json.loads(row.payload_json), _aware(row.updated_at)

    def put(self, cache_key: str, payload: Any, ttl_seconds: int) -> tuple[Any, datetime]:
        now = datetime.now(timezone.utc)
        row = self.db.get(ApiCache, cache_key)
        encoded = json.dumps(payload, ensure_ascii=False, default=_json_default, separators=(",", ":"))
        if row is None:
            row = ApiCache(cache_key=cache_key, payload_json=encoded,
                           expires_at=now + timedelta(seconds=ttl_seconds), updated_at=now)
            self.db.add(row)
        else:
            row.payload_json = encoded
            row.expires_at = now + timedelta(seconds=ttl_seconds)
            row.updated_at = now
        self.db.commit()
        return json.loads(encoded), now

    async def get_or_fetch(
        self,
        cache_key: str,
        ttl_seconds: int,
        fetcher: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, datetime, bool]:
        cached = self.get(cache_key)
        if cached:
            return cached[0], cached[1], True

        lock = _locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self.get(cache_key)
            if cached:
                return cached[0], cached[1], True
            try:
                payload = await fetcher()
            except Exception:
                stale = self.get(cache_key, allow_expired=True)
                if stale:
                    return stale[0], stale[1], True
                raise
            payload, updated_at = self.put(cache_key, payload, ttl_seconds)
            return payload, updated_at, False
