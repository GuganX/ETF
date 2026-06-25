from etf_tracker.diff import diff_snapshots
from etf_tracker.report import EtfReport, render_combined_report, render_report
from etf_tracker.scraper import Holding

HOLDINGS = [
    Holding("2330.TW", "台積電", 10.0, 11_960_000),
    Holding("2454.TW", "聯發科", 7.23, 4_861_000),
]


def test_report_is_standalone_html_with_holdings():
    html = render_report("00981A.TW", "2026-06-22", HOLDINGS, None, None)
    assert html.startswith("<!doctype html>")
    assert "台積電" in html and "2330.TW" in html
    assert "10.00%" in html and "11,960,000" in html
    # no prior snapshot -> shows the empty-diff notice
    assert "還沒有可比較的前一日" in html


def test_report_renders_diff_section():
    old = [Holding("2330.TW", "台積電", 9.0, 11_000_000), Holding("9999.TW", "舊股", 1.0, 500)]
    d = diff_snapshots(old, HOLDINGS)
    html = render_report("00981A.TW", "2026-06-22", HOLDINGS, d, "2026-06-21")
    assert "聯發科" in html          # added
    assert "舊股" in html            # removed
    assert "比例變化" not in html
    assert "11,000,000 → 11,960,000" in html  # shares change


def test_combined_report_has_tab_per_etf():
    reports = [
        EtfReport("00981A.TW", "2026-06-23", HOLDINGS, None, None),
        EtfReport("00991A.TW", "2026-06-23", [Holding("2330.TW", "台積電", 12.68, 3_400_000)], None, None),
    ]
    html = render_combined_report(reports)
    # one tab button + one panel per ETF
    assert html.count("data-target=") == 2
    assert 'data-target="etf-00981A.TW"' in html
    assert 'data-target="etf-00991A.TW"' in html
    assert 'id="etf-00981A.TW"' in html and 'id="etf-00991A.TW"' in html
    # first ETF's panel is active by default
    assert '<div class="etf-panel active" id="etf-00981A.TW">' in html
    # both ETFs' holdings are embedded
    assert "聯發科" in html and "12.68%" in html


def test_combined_report_empty():
    html = render_combined_report([])
    assert "沒有任何 ETF 快照資料" in html


def test_report_escapes_holding_names():
    bad = [Holding("X", "<b>evil</b>", 1.0, 1)]
    html = render_report("E", "2026-06-22", bad, None, None)
    assert "<b>evil</b>" not in html
    assert "&lt;b&gt;evil&lt;/b&gt;" in html
