from app.collectors.dart import DartClient


def disclosure_row(title="주요사항보고서(유상증자결정)", report_type="B"):
    return {
        "rcept_no": "20260719000001", "corp_cls": "Y", "corp_code": "00126380",
        "corp_name": "삼성전자", "stock_code": "005930", "report_nm": title,
        "rcept_dt": "20260719", "pblntf_ty": report_type, "flr_nm": "삼성전자", "rm": "",
    }


def test_normalize_maps_stock_market_category_and_importance():
    item = DartClient._normalize(disclosure_row())
    assert item.stock_code == "005930"
    assert item.corp_cls == "Y"
    assert item.category == "주요사항"
    assert item.importance == "high"
    assert item.is_correction is False


def test_correction_and_regular_report_are_classified():
    item = DartClient._normalize(disclosure_row("[기재정정]분기보고서 (2026.03)", "A"))
    assert item.is_correction is True
    assert item.category == "정기공시"
    assert item.importance == "medium"


def test_minor_disclosure_stays_low_importance():
    item = DartClient._normalize(disclosure_row("기업설명회(IR)개최", "E"))
    assert item.importance == "low"


def test_trading_halt_is_high_importance():
    item = DartClient._normalize(disclosure_row("주권매매거래정지기간변경", "I"))
    assert item.category == "거래소공시"
    assert item.importance == "high"
