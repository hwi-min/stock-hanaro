from app.collectors.kcif import extract_pdf_text, parse_kcif_list


def test_parse_kcif_list_item():
    html = """<ul class="page_list"><li><div class="tit_box">
      <a href="/annual/reportView?rpt_no=37319&mn=001002"><p>[7.18] 시장 동향</p></a>
      <span>백진규 2026.07.18</span></div><div class="download">
      <button class="btn down" onclick="reportdownload('abc%2Fdef%3D%3D');">다운로드</button>
      <a href="javascript:;" onclick="reportdownload('abc%2Fdef%3D%3D');" title="BR260718.pdf">BR260718.pdf</a>
      </div></li></ul>"""
    item = parse_kcif_list(html)[0]
    assert item.report_no == "37319"
    assert item.file_name == "BR260718.pdf"
    assert item.download_token == "abc%2Fdef%3D%3D"
    assert item.report_date.isoformat() == "2026-07-18"


def test_pdf_extractor_rejects_non_pdf():
    try:
        extract_pdf_text(b"not a pdf")
    except RuntimeError as exc:
        assert "did not return a PDF" in str(exc)
    else:
        raise AssertionError("non-PDF content must be rejected")
