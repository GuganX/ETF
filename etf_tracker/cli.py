"""Command line interface for the ETF holdings tracker.

Subcommands:
  fetch [--date YYYY-MM-DD]            Scrape every configured ETF, store a snapshot.
  list  <etfid>                        List stored snapshot dates for an ETF.
  diff  <etfid> [date_a date_b]        Show change between two dates (default: latest two).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

import requests

from . import db, diff, scraper
from .config import DEFAULT_CONFIG_PATH, load_config


def _today() -> str:
    return dt.date.today().isoformat()


def _now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def cmd_fetch(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    snapshot_date = args.date or _today()
    exit_code = 0
    for etfid in config.etfids:
        try:
            holdings = scraper.fetch_holdings(etfid)
            if not holdings:
                raise ValueError("no holdings parsed (page format changed or empty?)")
            count = db.save_snapshot(conn, etfid, snapshot_date, holdings)
            db.log_fetch(conn, etfid, snapshot_date, _now_iso(), count, "ok")
            print(f"[ok]    {etfid}  {snapshot_date}  {count} holdings")
        except (requests.RequestException, ValueError) as exc:
            db.log_fetch(conn, etfid, snapshot_date, _now_iso(), 0, "error", str(exc))
            print(f"[error] {etfid}  {snapshot_date}  {exc}", file=sys.stderr)
            exit_code = 1
    conn.close()
    return exit_code


def cmd_list(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    dates = db.list_snapshot_dates(conn, args.etfid)
    conn.close()
    if not dates:
        print(f"No snapshots found for {args.etfid}")
        return 1
    print(f"Snapshots for {args.etfid}:")
    for d in dates:
        print(f"  {d}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    dates = db.list_snapshot_dates(conn, args.etfid)

    if args.date_a and args.date_b:
        date_a, date_b = args.date_a, args.date_b
    elif len(dates) >= 2:
        date_a, date_b = dates[-2], dates[-1]
    else:
        print(f"Need at least two snapshots to diff {args.etfid}", file=sys.stderr)
        conn.close()
        return 1

    old = db.get_snapshot(conn, args.etfid, date_a)
    new = db.get_snapshot(conn, args.etfid, date_b)
    conn.close()

    if not old or not new:
        print("One of the requested snapshot dates has no data.", file=sys.stderr)
        return 1

    result = diff.diff_snapshots(old, new)
    _print_diff(args.etfid, date_a, date_b, result)
    return 0


def _print_diff(etfid, date_a, date_b, result: diff.HoldingsDiff) -> None:
    print(f"\nChange for {etfid}: {date_a} -> {date_b}\n")
    if result.is_empty:
        print("  (no changes)")
        return

    if result.added:
        print("🟢 Added:")
        for h in result.added:
            print(f"    {h.stock_name}({h.stock_code})  {h.weight_pct:.2f}%  {h.shares:,} shares")
    if result.removed:
        print("🔴 Removed:")
        for h in result.removed:
            print(f"    {h.stock_name}({h.stock_code})  was {h.weight_pct:.2f}%  {h.shares:,} shares")
    if result.weight_changes:
        print("📊 Weight changes:")
        for c in result.weight_changes:
            sign = "+" if c.delta >= 0 else ""
            print(f"    {c.stock_name}({c.stock_code})  {c.old_weight:.2f}% -> {c.new_weight:.2f}%  ({sign}{c.delta:.2f})")
    if result.shares_changes:
        print("📈 Shares changes:")
        for c in result.shares_changes:
            sign = "+" if c.delta >= 0 else ""
            print(f"    {c.stock_name}({c.stock_code})  {c.old_shares:,} -> {c.new_shares:,}  ({sign}{c.delta:,})")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="etf-tracker", description=__doc__)
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="path to etfs.yaml"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="scrape and store today's snapshot")
    p_fetch.add_argument("--date", help="override snapshot date (YYYY-MM-DD)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_list = sub.add_parser("list", help="list stored snapshot dates")
    p_list.add_argument("etfid")
    p_list.set_defaults(func=cmd_list)

    p_diff = sub.add_parser("diff", help="show change between two snapshots")
    p_diff.add_argument("etfid")
    p_diff.add_argument("date_a", nargs="?", help="older date (default: 2nd latest)")
    p_diff.add_argument("date_b", nargs="?", help="newer date (default: latest)")
    p_diff.set_defaults(func=cmd_diff)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
