import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.issue_summary import IssueSummary
from app.models.news_article import NewsArticle
from app.models.stock_master import StockMaster

RULE_MODEL = "rule-based-extractive"
RULE_VERSION = "issue-cluster-v1"

TOPICS = {
    "반도체": {"반도체", "hbm", "파운드리", "메모리", "d램", "낸드"},
    "거시·금리": {"금리", "연준", "fed", "fomc", "국채", "물가", "cpi"},
    "환율": {"환율", "달러", "원화", "엔화"},
    "에너지": {"유가", "원유", "wti", "opec", "천연가스"},
    "중국": {"중국", "인민은행", "부양책", "위안화"},
    "증시": {"코스피", "코스닥", "증시", "주가", "상승", "하락"},
    "실적": {"실적", "매출", "영업이익", "순이익", "흑자", "적자"},
}
EVENTS = {"실적", "수주", "공급", "계약", "인수", "합병", "규제", "관세", "발표", "인하", "인상",
          "상승", "하락", "급등", "급락", "투자", "증설", "출시", "승인", "중단", "재개"}
INSTITUTIONS = {"연준", "fed", "fomc", "한국은행", "금융위원회", "금융감독원", "정부", "미국", "중국",
                "유럽중앙은행", "ecb", "opec"}
STOPWORDS = {"관련", "대한", "통해", "위해", "이번", "지난", "오늘", "내일", "전망", "기대", "가능성",
             "시장", "업계", "기자", "종합", "단독", "속보", "억원", "조원"}


def normalize_title(value: str) -> str:
    value = re.sub(r"^\s*[\[【(](속보|단독|종합|특징주|마켓)[^\]】)]*[\]】)]\s*", "", value, flags=re.I)
    return re.sub(r"[^0-9a-z가-힣]+", " ", value.lower()).strip()


def tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[0-9a-z가-힣]+", normalize_title(value))
            if len(token) >= 2 and token not in STOPWORDS}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 0


@dataclass
class ArticleFeatures:
    article: NewsArticle
    title_tokens: set[str]
    entities: set[str]
    topics: set[str]
    events: set[str]


class RuleBasedIssueService:
    def __init__(self, db: Session):
        self.db = db

    def _company_names(self) -> set[str]:
        names = self.db.scalars(select(StockMaster.name).where(StockMaster.active.is_(True))).all()
        # Two-character company names often overlap ordinary Korean words (e.g. 대상),
        # so exact company anchors start at three characters for conservative clustering.
        return {name.lower() for name in names if 3 <= len(name) <= 30}

    def _features(self, article: NewsArticle, company_names: set[str]) -> ArticleFeatures:
        text = f"{article.title} {article.summary or ''}".lower()
        found_topics = {topic for topic, words in TOPICS.items() if any(word in text for word in words)}
        found_entities = {name for name in company_names if name in text}
        found_entities |= {name for name in INSTITUTIONS if name in text}
        return ArticleFeatures(article, tokens(article.title), found_entities, found_topics,
                               {event for event in EVENTS if event in text})

    @staticmethod
    def _is_duplicate(candidate: ArticleFeatures, existing: ArticleFeatures) -> bool:
        return (candidate.article.content_hash == existing.article.content_hash
                or jaccard(candidate.title_tokens, existing.title_tokens) >= .82)

    @staticmethod
    def _similarity(candidate: ArticleFeatures, cluster: list[ArticleFeatures]) -> float:
        best = 0.0
        for other in cluster:
            shared_entities = candidate.entities & other.entities
            shared_topics = candidate.topics & other.topics
            shared_events = candidate.events & other.events
            title_score = jaccard(candidate.title_tokens, other.title_tokens)
            has_anchor = bool(shared_entities) or (bool(shared_topics) and bool(shared_events) and title_score >= .12)
            if not has_anchor:
                continue
            score = min(len(shared_entities), 2) * 4 + min(len(shared_topics), 2) * 1.5
            score += min(len(shared_events), 2) * 1.5 + title_score * 4
            best = max(best, score)
        return best

    @staticmethod
    def _summary(cluster: list[ArticleFeatures]) -> str:
        sentences: list[tuple[float, str]] = []
        anchors = set().union(*(item.entities | item.events for item in cluster))
        for rank, item in enumerate(cluster):
            source = re.sub(r"\s+", " ", item.article.summary or "").strip()
            for sentence in re.split(r"(?<=[.!?다요])\s+", source):
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                score = sum(2 for anchor in anchors if anchor in sentence.lower())
                score += 2 if re.search(r"\d", sentence) else 0
                score += max(0, 3 - rank) * .2
                sentences.append((score, sentence))
        selected: list[str] = []
        for _, sentence in sorted(sentences, key=lambda item: item[0], reverse=True):
            if any(jaccard(tokens(sentence), tokens(existing)) >= .72 for existing in selected):
                continue
            selected.append(sentence)
            if len(selected) == 2 or len(" ".join(selected)) >= 180:
                break
        summary = " ".join(selected).strip()
        if not summary:
            summary = cluster[0].article.summary or cluster[0].article.title
        return summary[:240].rstrip()

    @staticmethod
    def _issue_key(cluster: list[ArticleFeatures]) -> str:
        anchors = sorted(set().union(*(item.entities | item.events | item.topics for item in cluster)))
        seed = "|".join(anchors[:8]) or normalize_title(cluster[0].article.title)
        return f"rule-{hashlib.sha1(seed.encode()).hexdigest()[:12]}"

    def run(self, *, now: datetime | None = None, limit: int = 120) -> int:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        rows = self.db.scalars(select(NewsArticle).where(
            NewsArticle.published_at >= cutoff,
        ).order_by(desc(NewsArticle.published_at), desc(NewsArticle.collected_at)).limit(limit)).all()
        company_names = self._company_names()
        features: list[ArticleFeatures] = []
        for row in rows:
            candidate = self._features(row, company_names)
            if any(self._is_duplicate(candidate, existing) for existing in features):
                continue
            features.append(candidate)

        clusters: list[list[ArticleFeatures]] = []
        for candidate in features:
            scores = [self._similarity(candidate, cluster) for cluster in clusters]
            best = max(range(len(scores)), key=scores.__getitem__) if scores else None
            if best is not None and scores[best] >= 4:
                clusters[best].append(candidate)
            else:
                clusters.append([candidate])

        count = 0
        active_keys: set[str] = set()
        for cluster in sorted((group for group in clusters if len(group) >= 2), key=len, reverse=True)[:8]:
            publishers = {item.article.publisher or item.article.source for item in cluster}
            if len(publishers) < 2 and len(cluster) < 3:
                continue
            key = self._issue_key(cluster)
            active_keys.add(key)
            representative = max(cluster, key=lambda item: (len(item.entities) + len(item.events),
                                                               len(item.article.summary or "")))
            category_counts = {topic: sum(topic in item.topics for item in cluster) for topic in TOPICS}
            category = max(category_counts, key=category_counts.get) if any(category_counts.values()) else "주요 뉴스"
            ordered = [representative, *(item for item in cluster if item is not representative)]
            values = {
                "category": category, "title": representative.article.title,
                "summary": self._summary(cluster), "sentiment": "neutral",
                "article_ids_json": json.dumps([item.article.id for item in ordered[:12]]),
                "model": RULE_MODEL, "prompt_version": RULE_VERSION, "generated_at": now,
            }
            row = self.db.scalar(select(IssueSummary).where(IssueSummary.issue_key == key))
            if row is None:
                self.db.add(IssueSummary(issue_key=key, **values))
            else:
                for field, value in values.items():
                    setattr(row, field, value)
            count += 1
        stale = self.db.scalars(select(IssueSummary).where(IssueSummary.model == RULE_MODEL)).all()
        for row in stale:
            if row.issue_key not in active_keys:
                self.db.delete(row)
        self.db.commit()
        return count
