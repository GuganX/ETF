# ETF Holdings Tracker — Design

Date: 2026-06-22

## Goal

Scrape ETF holdings from MoneyDJ daily, store full snapshots in SQLite, and
report the change between any two snapshot dates.

Source page format (per etfid):
`https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm?etfid=<ID>`

Each page renders a holdings table with columns:
- 個股名稱 — stock name + ticker code, e.g. `台積電(2330.TW)`
- 投資比例(%) — weight percentage
- 持有股數 — shares held

## Architecture

Single Python package `etf_tracker/`:

| Module        | Responsibility |
|---------------|----------------|
| `config.py`   | Load `etfs.yaml` (list of etfids to track). |
| `scraper.py`  | Fetch one etfid page, parse holdings into a list of `Holding` records. |
| `db.py`       | SQLite schema + idempotent upsert; query helpers. |
| `diff.py`     | Compare two snapshot dates → added / removed / weight-changed / shares-changed. |
| `cli.py`      | Entry point: `fetch`, `diff`, `list` subcommands. |

## Data Model (SQLite)

`holdings_snapshot`
- `etfid TEXT`
- `snapshot_date TEXT` (YYYY-MM-DD)
- `stock_code TEXT`
- `stock_name TEXT`
- `weight_pct REAL`
- `shares INTEGER`
- PRIMARY KEY `(etfid, snapshot_date, stock_code)` → re-running same day upserts, no dupes.

`fetch_log`
- `etfid TEXT`
- `snapshot_date TEXT`
- `fetched_at TEXT` (ISO timestamp)
- `holding_count INTEGER`
- `status TEXT` (`ok` | `error`)
- `message TEXT`

## Scraping

- `requests` + `beautifulsoup4` (lxml parser).
- Send a browser User-Agent header.
- Stock code parsed from the `名稱(代號)` cell; weight parsed as float; shares parsed
  as int after stripping commas.
- On parse failure / empty table: write nothing to `holdings_snapshot`, record
  `status=error` in `fetch_log`.

## Change Tracking

`diff <etfid> <date_a> <date_b>` (dates optional → default to latest two):
- 🟢 Added: stock_code present in B but not A
- 🔴 Removed: present in A but not B
- 📊 Weight change: weight_pct differs
- 📈 Shares change: shares differs

## Scheduling

App runs as a one-shot "fetch all configured ETFs". A macOS crontab/launchd example
is provided to run daily after market close (e.g. 18:00).

## Testing

- `scraper` parsing tested against a saved HTML sample fixture.
- `db` and `diff` logic tested against an in-memory SQLite database.

## Out of Scope (YAGNI)

- Email/notification on change.
- Web UI / charts.
- Historical price data (holdings only).
