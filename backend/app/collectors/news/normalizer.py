import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_KEYS = {"fbclid", "gclid", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}


@dataclass(frozen=True)
class NormalizedNewsArticle:
    source: str
    source_article_id: str | None
    publisher: str | None
    title: str
    summary: str | None
    canonical_url: str
    url_hash: str
    content_hash: str
    published_at: datetime | None


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def canonicalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = urlencode(
        sorted((key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING_QUERY_KEYS)
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_article(
    *, source: str, title: str, url: str, summary: str | None = None, publisher: str | None = None,
    published_at: datetime | None = None, source_article_id: str | None = None,
) -> NormalizedNewsArticle:
    normalized_title = clean_text(title)
    normalized_summary = clean_text(summary) or None
    canonical_url = canonicalize_url(url)
    if not normalized_title or not canonical_url.startswith(("http://", "https://")):
        raise ValueError("news title and absolute URL are required")
    content_key = "\n".join((normalized_title.casefold(), (normalized_summary or "").casefold()))
    return NormalizedNewsArticle(
        source=source,
        source_article_id=source_article_id,
        publisher=clean_text(publisher) or None,
        title=normalized_title,
        summary=normalized_summary,
        canonical_url=canonical_url,
        url_hash=hashlib.sha256(canonical_url.encode()).hexdigest(),
        content_hash=hashlib.sha256(content_key.encode()).hexdigest(),
        published_at=normalize_datetime(published_at),
    )
