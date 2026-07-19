from app.collectors.kis import US_HEATMAP_UNIVERSE


KR_STOCKS = {
    "005930": {"name": "삼성전자", "market": "kr", "exchange": "KRX", "sector": "반도체", "industry": "전자·반도체"},
    "000660": {"name": "SK하이닉스", "market": "kr", "exchange": "KRX", "sector": "반도체", "industry": "반도체"},
    "005380": {"name": "현대차", "market": "kr", "exchange": "KRX", "sector": "경기소비재", "industry": "자동차"},
    "373220": {"name": "LG에너지솔루션", "market": "kr", "exchange": "KRX", "sector": "산업재", "industry": "2차전지"},
}


def stock_catalog() -> dict[str, dict]:
    us = {symbol: {**metadata, "market": "us"} for symbol, metadata in US_HEATMAP_UNIVERSE.items()}
    return {**KR_STOCKS, **us}
