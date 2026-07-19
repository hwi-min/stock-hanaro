from decimal import Decimal

from app.collectors.kis import DOMESTIC_INDICES, OPTIONAL_OVERSEAS_INDICES, OVERSEAS_INDICES, US_HEATMAP_UNIVERSE, decimal_or_none


def test_market_universe_has_required_taxonomy_and_exchange():
    assert len(US_HEATMAP_UNIVERSE) >= 20
    assert {item["exchange"] for item in US_HEATMAP_UNIVERSE.values()} == {"NAS", "NYS"}
    assert all(item["sector"] and item["industry"] for item in US_HEATMAP_UNIVERSE.values())


def test_dashboard_indices_are_configured():
    assert {item[0] for item in DOMESTIC_INDICES} == {"KOSPI", "KOSDAQ", "KOSPI200"}
    assert {item[0] for item in OVERSEAS_INDICES} == {"SPX", "NASDAQ", "DOW30", "RUSSELL2000", "VIX"}
    assert OPTIONAL_OVERSEAS_INDICES == {"RUSSELL2000", "VIX"}


def test_decimal_parser_handles_api_values():
    assert decimal_or_none("1,234.50") == Decimal("1234.50")
    assert decimal_or_none("") is None
