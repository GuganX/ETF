from etf_tracker import db
from etf_tracker.diff import diff_snapshots
from etf_tracker.scraper import Holding


def _conn():
    return db.connect(":memory:")


def test_save_and_get_snapshot_roundtrip():
    conn = _conn()
    holdings = [
        Holding("2330.TW", "台積電", 10.0, 11_960_000),
        Holding("2454.TW", "聯發科", 7.23, 4_861_000),
    ]
    n = db.save_snapshot(conn, "00981A.TW", "2026-06-22", holdings)
    assert n == 2
    got = db.get_snapshot(conn, "00981A.TW", "2026-06-22")
    assert {h.stock_code for h in got} == {"2330.TW", "2454.TW"}


def test_resaving_same_day_is_idempotent():
    conn = _conn()
    db.save_snapshot(conn, "X", "2026-06-22", [Holding("A", "a", 1.0, 100)])
    db.save_snapshot(conn, "X", "2026-06-22", [Holding("A", "a", 2.0, 200)])
    got = db.get_snapshot(conn, "X", "2026-06-22")
    assert len(got) == 1
    assert got[0].weight_pct == 2.0
    assert got[0].shares == 200


def test_list_snapshot_dates_sorted():
    conn = _conn()
    db.save_snapshot(conn, "X", "2026-06-23", [Holding("A", "a", 1.0, 1)])
    db.save_snapshot(conn, "X", "2026-06-21", [Holding("A", "a", 1.0, 1)])
    assert db.list_snapshot_dates(conn, "X") == ["2026-06-21", "2026-06-23"]


def test_diff_detects_all_change_types():
    old = [
        Holding("A", "Alpha", 5.0, 1000),   # weight + shares change
        Holding("B", "Beta", 3.0, 500),     # unchanged
        Holding("C", "Gamma", 2.0, 200),    # removed
    ]
    new = [
        Holding("A", "Alpha", 6.0, 1500),
        Holding("B", "Beta", 3.0, 500),
        Holding("D", "Delta", 1.0, 100),    # added
    ]
    d = diff_snapshots(old, new)

    assert [h.stock_code for h in d.added] == ["D"]
    assert [h.stock_code for h in d.removed] == ["C"]

    wc = {c.stock_code: c for c in d.weight_changes}
    assert wc["A"].old_weight == 5.0 and wc["A"].new_weight == 6.0
    assert wc["A"].delta == 1.0
    assert "B" not in wc

    sc = {c.stock_code: c for c in d.shares_changes}
    assert sc["A"].delta == 500
    assert "B" not in sc


def test_diff_empty_when_identical():
    snap = [Holding("A", "Alpha", 5.0, 1000)]
    assert diff_snapshots(snap, list(snap)).is_empty
