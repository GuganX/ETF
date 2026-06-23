from pathlib import Path

from etf_tracker.scraper import Holding, parse_data_date, parse_holdings

FIXTURE = Path(__file__).parent / "fixtures" / "00981A_sample.html"


def _holdings():
    return parse_holdings(FIXTURE.read_text(encoding="utf-8"))


def test_parses_all_fifty_holdings():
    holdings = _holdings()
    assert len(holdings) == 50


def test_top_holding_is_tsmc():
    top = _holdings()[0]
    assert top.stock_code == "2330.TW"
    assert top.stock_name == "台積電"
    assert top.weight_pct == 10.00
    assert top.shares == 11_960_000


def test_handles_name_with_star_marker():
    by_code = {h.stock_code: h for h in _holdings()}
    yageo = by_code["2327.TW"]
    assert yageo.stock_name == "國巨*"
    assert yageo.weight_pct == 8.48
    assert yageo.shares == 23_892_000


def test_all_records_are_well_typed():
    for h in _holdings():
        assert isinstance(h, Holding)
        assert h.stock_code
        assert isinstance(h.weight_pct, float)
        assert isinstance(h.shares, int)


def test_empty_html_returns_empty_list():
    assert parse_holdings("<html><body>no table</body></html>") == []


def test_parses_data_date_from_page():
    # The page shows "資料日期：2026/06/22" -> normalised to ISO.
    assert parse_data_date(FIXTURE.read_text(encoding="utf-8")) == "2026-06-22"


def test_data_date_none_when_absent():
    assert parse_data_date("<html><body>no date here</body></html>") is None
