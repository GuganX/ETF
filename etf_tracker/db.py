"""SQLite storage for ETF holdings snapshots."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .scraper import Holding

SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings_snapshot (
    etfid         TEXT    NOT NULL,
    snapshot_date TEXT    NOT NULL,
    stock_code    TEXT    NOT NULL,
    stock_name    TEXT    NOT NULL,
    weight_pct    REAL    NOT NULL,
    shares        INTEGER NOT NULL,
    PRIMARY KEY (etfid, snapshot_date, stock_code)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    etfid         TEXT    NOT NULL,
    snapshot_date TEXT    NOT NULL,
    fetched_at    TEXT    NOT NULL,
    holding_count INTEGER NOT NULL,
    status        TEXT    NOT NULL,
    message       TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    """Open (or create) a database and ensure the schema exists."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_snapshot(
    conn: sqlite3.Connection,
    etfid: str,
    snapshot_date: str,
    holdings: Iterable[Holding],
) -> int:
    """Replace the snapshot for (etfid, snapshot_date) with `holdings`.

    Idempotent: re-running for the same day overwrites that day's rows.
    Returns the number of holdings written.
    """
    holdings = list(holdings)
    with conn:
        conn.execute(
            "DELETE FROM holdings_snapshot WHERE etfid = ? AND snapshot_date = ?",
            (etfid, snapshot_date),
        )
        conn.executemany(
            """INSERT INTO holdings_snapshot
               (etfid, snapshot_date, stock_code, stock_name, weight_pct, shares)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (etfid, snapshot_date, h.stock_code, h.stock_name, h.weight_pct, h.shares)
                for h in holdings
            ],
        )
    return len(holdings)


def log_fetch(
    conn: sqlite3.Connection,
    etfid: str,
    snapshot_date: str,
    fetched_at: str,
    holding_count: int,
    status: str,
    message: str | None = None,
) -> None:
    with conn:
        conn.execute(
            """INSERT INTO fetch_log
               (etfid, snapshot_date, fetched_at, holding_count, status, message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (etfid, snapshot_date, fetched_at, holding_count, status, message),
        )


def get_snapshot(
    conn: sqlite3.Connection, etfid: str, snapshot_date: str
) -> list[Holding]:
    rows = conn.execute(
        """SELECT stock_code, stock_name, weight_pct, shares
           FROM holdings_snapshot
           WHERE etfid = ? AND snapshot_date = ?
           ORDER BY weight_pct DESC""",
        (etfid, snapshot_date),
    ).fetchall()
    return [
        Holding(r["stock_code"], r["stock_name"], r["weight_pct"], r["shares"])
        for r in rows
    ]


def list_snapshot_dates(conn: sqlite3.Connection, etfid: str) -> list[str]:
    """Return distinct snapshot dates for an ETF, oldest first."""
    rows = conn.execute(
        """SELECT DISTINCT snapshot_date FROM holdings_snapshot
           WHERE etfid = ? ORDER BY snapshot_date""",
        (etfid,),
    ).fetchall()
    return [r["snapshot_date"] for r in rows]
