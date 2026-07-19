from datetime import datetime, timezone


class DashboardRepository:
    """M1 fixture repository. M2 replaces each collection with persisted source data."""

    def get_snapshot(self) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "briefing": {
                "stance": "risk_on",
                "headline": "기술주 강세가 이어졌지만 금리와 환율을 함께 확인하세요",
                "summary": "미국 기술주 상승이 국내 반도체 투자심리에 우호적일 가능성이 있습니다. 다만 미국 국채금리와 원·달러 환율의 방향이 장중 변동성을 키울 수 있습니다.",
                "keywords": ["미국 기술주", "반도체", "원·달러 환율"],
                "source_ids": ["market:nasdaq", "issue:semiconductor"],
                "as_of": now,
            },
            "metrics": [
                {"symbol": "SPX", "label": "S&P 500", "market": "us", "value": "5,321.41", "change_pct": 0.78, "as_of": now},
                {"symbol": "DJI", "label": "Dow 30", "market": "us", "value": "39,872.99", "change_pct": 0.32, "as_of": now},
                {"symbol": "IXIC", "label": "NASDAQ", "market": "us", "value": "16,832.62", "change_pct": 1.24, "as_of": now},
                {"symbol": "RUT", "label": "Russell 2000", "market": "us", "value": "2,103.77", "change_pct": -0.18, "as_of": now},
                {"symbol": "VIX", "label": "VIX", "market": "us", "value": "13.82", "change_pct": -2.12, "as_of": now},
                {"symbol": "GOLD", "label": "Gold", "market": "us", "value": "2,332.10", "change_pct": 0.41, "as_of": now},
                {"symbol": "KOSPI", "label": "KOSPI", "market": "kr", "value": "2,678.35", "change_pct": 0.45, "as_of": now},
                {"symbol": "KOSDAQ", "label": "KOSDAQ", "market": "kr", "value": "865.43", "change_pct": 0.72, "as_of": now},
                {"symbol": "KOSPI200", "label": "KOSPI 200", "market": "kr", "value": "365.82", "change_pct": 0.49, "as_of": now},
                {"symbol": "USDKRW", "label": "USD/KRW", "market": "kr", "value": "1,356.40", "change_pct": -0.32, "as_of": now},
                {"symbol": "KR3Y", "label": "국고채 3년", "market": "kr", "value": "3.21%", "change_pct": -0.04, "as_of": now},
            ],
            "heatmap": [
                {"symbol": "NVDA", "name": "NVIDIA", "sector": "기술", "industry": "반도체", "price": 171.38, "change_pct": -2.21, "market_cap_weight": 24},
                {"symbol": "AAPL", "name": "Apple", "sector": "기술", "industry": "소비자 전자제품", "price": 210.02, "change_pct": 0.14, "market_cap_weight": 23},
                {"symbol": "MSFT", "name": "Microsoft", "sector": "기술", "industry": "소프트웨어", "price": 510.05, "change_pct": -1.81, "market_cap_weight": 22},
                {"symbol": "AVGO", "name": "Broadcom", "sector": "기술", "industry": "반도체", "price": 274.31, "change_pct": -0.97, "market_cap_weight": 15},
                {"symbol": "AMD", "name": "AMD", "sector": "기술", "industry": "반도체", "price": 155.61, "change_pct": -1.03, "market_cap_weight": 10},
                {"symbol": "ORCL", "name": "Oracle", "sector": "기술", "industry": "소프트웨어", "price": 244.17, "change_pct": 1.77, "market_cap_weight": 9},
                {"symbol": "GOOGL", "name": "Alphabet", "sector": "커뮤니케이션", "industry": "인터넷 콘텐츠", "price": 184.92, "change_pct": -2.17, "market_cap_weight": 22},
                {"symbol": "META", "name": "Meta Platforms", "sector": "커뮤니케이션", "industry": "인터넷 콘텐츠", "price": 702.18, "change_pct": -2.79, "market_cap_weight": 14},
                {"symbol": "NFLX", "name": "Netflix", "sector": "커뮤니케이션", "industry": "엔터테인먼트", "price": 1189.32, "change_pct": -1.26, "market_cap_weight": 8},
                {"symbol": "AMZN", "name": "Amazon", "sector": "경기소비재", "industry": "인터넷 소매", "price": 223.88, "change_pct": -1.06, "market_cap_weight": 18},
                {"symbol": "TSLA", "name": "Tesla", "sector": "경기소비재", "industry": "자동차", "price": 319.41, "change_pct": -2.61, "market_cap_weight": 12},
                {"symbol": "HD", "name": "Home Depot", "sector": "경기소비재", "industry": "주택개선 소매", "price": 338.87, "change_pct": -2.63, "market_cap_weight": 8},
                {"symbol": "JPM", "name": "JPMorgan Chase", "sector": "금융", "industry": "종합은행", "price": 289.91, "change_pct": -0.60, "market_cap_weight": 12},
                {"symbol": "BRK-B", "name": "Berkshire Hathaway", "sector": "금융", "industry": "보험", "price": 472.61, "change_pct": -0.45, "market_cap_weight": 13},
                {"symbol": "V", "name": "Visa", "sector": "금융", "industry": "결제서비스", "price": 349.27, "change_pct": -1.80, "market_cap_weight": 10},
                {"symbol": "LLY", "name": "Eli Lilly", "sector": "헬스케어", "industry": "제약", "price": 779.27, "change_pct": 0.85, "market_cap_weight": 12},
                {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "헬스케어", "industry": "제약", "price": 166.41, "change_pct": 1.23, "market_cap_weight": 9},
                {"symbol": "WMT", "name": "Walmart", "sector": "필수소비재", "industry": "할인점", "price": 95.38, "change_pct": -0.62, "market_cap_weight": 11},
                {"symbol": "KO", "name": "Coca-Cola", "sector": "필수소비재", "industry": "음료", "price": 69.71, "change_pct": -3.96, "market_cap_weight": 8},
                {"symbol": "XOM", "name": "Exxon Mobil", "sector": "에너지", "industry": "통합 석유·가스", "price": 113.27, "change_pct": 0.97, "market_cap_weight": 11},
                {"symbol": "GE", "name": "GE Aerospace", "sector": "산업재", "industry": "항공우주", "price": 258.21, "change_pct": 0.90, "market_cap_weight": 9},
            ],
            "schedules": [
                {"id": "bls-cpi", "source": "bls", "country": "US", "category": "물가", "title": "미국 소비자물가지수(CPI)", "scheduled_at": now.replace(hour=12, minute=30), "importance": "high", "source_url": "https://www.bls.gov/schedule/news_release/cpi.htm"},
                {"id": "fed-speech", "source": "federal_reserve", "country": "US", "category": "통화정책", "title": "연준 위원 연설", "scheduled_at": now.replace(hour=14, minute=0), "importance": "high", "source_url": "https://www.federalreserve.gov/newsevents/calendar.htm"},
                {"id": "bok-ppi", "source": "bok", "country": "KR", "category": "물가", "title": "한국 생산자물가지수", "scheduled_at": now.replace(hour=21, minute=0), "importance": "medium", "source_url": "https://www.bok.or.kr/portal/submain/submain/sts.do?menuNo=200094&viewType=SUBMAIN"},
            ],
            "issues": [
                {"id": "cpi", "title": "미국 물가 둔화 기대", "summary": "인플레이션 둔화 흐름이 금리 인하 기대를 지지하고 있습니다.", "sentiment": "positive", "article_count": 24, "category": "거시·금리", "articles": [
                    {"id": "cpi-1", "title": "미국 소비자물가 둔화, 금리 경로에 관심", "publisher": "연합뉴스", "published_at": now, "url": "https://finance.naver.com/news/", "is_representative": True},
                    {"id": "cpi-2", "title": "인플레이션 압력 완화에 미국 증시 상승", "publisher": "한국경제", "published_at": now, "url": "https://finance.naver.com/news/"},
                    {"id": "cpi-3", "title": "시장 예상과 부합한 CPI, 연준 판단은", "publisher": "매일경제", "published_at": now, "url": "https://finance.naver.com/news/"},
                ]},
                {"id": "hbm", "title": "HBM 수요 기대", "summary": "AI 가속기 수요가 국내 반도체 공급망에 우호적으로 작용할 가능성이 있습니다.", "sentiment": "positive", "article_count": 18, "category": "반도체", "articles": [
                    {"id": "hbm-1", "title": "AI 서버 투자 확대에 HBM 수요 지속", "publisher": "전자신문", "published_at": now, "url": "https://finance.naver.com/news/", "is_representative": True},
                    {"id": "hbm-2", "title": "국내 반도체 공급망, 차세대 HBM 대응", "publisher": "서울경제", "published_at": now, "url": "https://finance.naver.com/news/"},
                    {"id": "hbm-3", "title": "글로벌 AI 투자와 메모리 업황 전망", "publisher": "이데일리", "published_at": now, "url": "https://finance.naver.com/news/"},
                ]},
                {"id": "oil", "title": "국제유가 상승", "summary": "공급 불확실성으로 유가가 상승하며 운송·화학 업종 비용 부담이 커질 수 있습니다.", "sentiment": "negative", "article_count": 15, "category": "에너지", "articles": [
                    {"id": "oil-1", "title": "공급 우려에 국제유가 상승세", "publisher": "아시아경제", "published_at": now, "url": "https://finance.naver.com/news/", "is_representative": True},
                    {"id": "oil-2", "title": "유가 상승이 운송·화학 업종에 미칠 영향", "publisher": "머니투데이", "published_at": now, "url": "https://finance.naver.com/news/"},
                    {"id": "oil-3", "title": "지정학적 긴장과 원유 공급 전망", "publisher": "뉴스1", "published_at": now, "url": "https://finance.naver.com/news/"},
                ]},
            ],
            "disclosures": [
                {"id": "dart-1", "company": "삼성전자", "title": "기업설명회 개최", "importance": "medium", "filed_at": now},
                {"id": "dart-2", "company": "SK하이닉스", "title": "신규 시설투자", "importance": "high", "filed_at": now},
            ],
            "kcif": [
                {"id": "kcif-rates", "title": "미국 국채금리 방향 전환", "summary": "장기 금리 하락은 성장주 가치평가 부담을 일부 낮출 수 있습니다.", "topic": "금리", "source_url": "https://www.kcif.or.kr/annual/newsflashList", "as_of": now},
                {"id": "kcif-oil", "title": "WTI 가격 상승", "summary": "지정학적 불확실성과 공급 우려가 유가에 반영되고 있습니다.", "topic": "원자재", "source_url": "https://www.kcif.or.kr/annual/newsflashList", "as_of": now},
            ],
            "freshness": [
                {"dataset": "market", "label": "시장 데이터", "as_of": now, "stale": False},
                {"dataset": "news", "label": "뉴스·이슈", "as_of": now, "stale": False},
                {"dataset": "disclosure", "label": "공시", "as_of": now, "stale": False},
                {"dataset": "kcif", "label": "KCIF", "as_of": now, "stale": False},
            ],
        }
