import asyncio
from datetime import date
from decimal import Decimal

from app.collectors.kis import KISClient
from app.collectors.sp500 import Sp500MasterCollector, kis_symbol_candidates, normalize_kis_symbol


def test_ivv_parser_excludes_non_equities_and_zero_weight_rows():
    text = """Test Fund\nFund Holdings as of,"Aug 26, 2026"\nTicker,Name,Sector,Asset Class,Weight (%),Exchange\nAAPL,APPLE INC,Information Technology,Equity,7.00,NASDAQ\nUSD,USD CASH,Cash,Cash,0.10,-\nOLD,OLD CORP,Industrials,Equity,0.00,New York Stock Exchange Inc.\n"""
    # The production guard expects the full index, so exercise its row rules with
    # enough synthetic holdings while preserving a real representative row.
    rows = text + "\n".join(
        f"T{i},TEST {i},Industrials,Equity,0.10,NASDAQ" for i in range(490)
    )
    items = Sp500MasterCollector._parse_holdings(rows, {"AAPL": ("Information Technology", "Technology Hardware")})
    symbols = {item.symbol for item in items}
    assert "AAPL" in symbols
    assert "USD" not in symbols
    assert "OLD" not in symbols


def test_kis_symbol_normalizes_class_shares_from_ivv_format():
    assert normalize_kis_symbol("BRKB") == "BRK/B"
    assert normalize_kis_symbol("BFB") == "BF/B"
    assert normalize_kis_symbol("BRK.B") == "BRK/B"
    assert normalize_kis_symbol("AAPL") == "AAPL"
    assert kis_symbol_candidates("BRKB", "BRKB")[:2] == ["BRKB", "BRK/B"]
    assert kis_symbol_candidates("BFB", "BFB")[:2] == ["BFB", "BF/B"]


def test_regular_close_uses_1600_open_and_regular_session_volume(monkeypatch):
    async def fake_get(*_args, **_kwargs):
        return {"output2": [
            {"xymd": "20260825", "xhms": "160000", "open": "213.05", "last": "213.19", "evol": "100"},
            {"xymd": "20260825", "xhms": "155500", "open": "212.90", "last": "213.00", "evol": "50"},
            {"xymd": "20260825", "xhms": "092500", "open": "210.00", "last": "210.10", "evol": "999"},
        ]}

    client = KISClient()
    monkeypatch.setattr(client, "_get", fake_get)
    result = asyncio.run(client.overseas_regular_close("NVDA", "NAS", date(2026, 8, 25)))
    assert result["close"] == Decimal("213.05")
    assert result["volume"] == Decimal("150")
