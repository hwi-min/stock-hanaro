from app.collectors.valuation import parse_theinvest, parse_wisereport


def test_parse_theinvest_metrics():
    html = "<div>PSR 4.13배</div><div>PCR 14.72배</div>"
    assert parse_theinvest(html) == (4.13, 14.72)


def test_parse_wisereport_actual_ev_ebitda():
    html = "<table><tr><th>EV/EBITDA</th><td>17.90</td><td>3.22</td></tr></table>"
    assert parse_wisereport(html) == 17.90
