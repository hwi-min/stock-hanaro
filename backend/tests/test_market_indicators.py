from datetime import date

from app.collectors.kis import KISClient


def test_gold_contract_selects_next_bimonthly_contract():
    assert KISClient.gold_contract(date(2026, 7, 19)) == "1OZQ26"
    assert KISClient.gold_contract(date(2026, 8, 1)) == "1OZV26"
    assert KISClient.gold_contract(date(2026, 12, 1)) == "1OZG27"
