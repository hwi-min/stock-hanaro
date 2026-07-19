from app.collectors.stock_master import KISStockMasterCollector


def master_line(symbol: str, isin: str, name: str, product_type: str, tail_width: int) -> bytes:
    prefix = f"{symbol:<9}{isin:<12}{name}"
    tail = " " + f"{product_type:<2}" + ("0" * (tail_width - 3))
    return (prefix + tail).encode("cp949")


def test_stock_master_parser_extracts_common_stock():
    content = master_line("005930", "KR7005930003", "삼성전자", "ST", 228)

    rows = KISStockMasterCollector.parse(content, market="KOSPI", tail_width=228)

    assert len(rows) == 1
    assert rows[0].symbol == "005930"
    assert rows[0].isin == "KR7005930003"
    assert rows[0].name == "삼성전자"
    assert rows[0].market == "KOSPI"


def test_stock_master_parser_excludes_non_common_products():
    content = master_line("069500", "KR7069500007", "KODEX 200", "EF", 228)

    assert KISStockMasterCollector.parse(content, market="KOSPI", tail_width=228) == []
