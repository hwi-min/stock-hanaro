from app.collectors.research import parse_reports


def test_parse_research_report_metadata():
    html = """
    <div class="table_style01"><table><tbody><tr>
      <td class="first txt_number">2026-08-19</td><td>기업</td>
      <td class="text_l"><a href="/analysis/downpdf?report_idx=651788">NICE인프라(063570) 안정적인 외형 성장</a></td>
      <td>정홍식</td><td>LS증권</td><td><a href="/analysis/downpdf?report_idx=651788">첨부</a></td>
    </tr></tbody></table></div>
    """
    reports = parse_reports(html)
    assert len(reports) == 1
    report = reports[0]
    assert report.source_report_id == "651788"
    assert report.category == "기업"
    assert report.broker == "LS증권"
    assert report.analyst == "정홍식"
    assert report.stock_name == "NICE인프라"
    assert report.stock_code == "063570"
    assert report.source_url == "https://consensus.hankyung.com/analysis/downpdf?report_idx=651788"


def test_parse_skips_malformed_rows():
    assert parse_reports('<div class="table_style01"><table><tbody><tr><td>bad</td></tr></tbody></table></div>') == []
