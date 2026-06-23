"""Fetch and parse ETF holdings from a MoneyDJ Basic0007B page."""

from __future__ import annotations

import re
import ssl
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

BASE_URL = "https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# `名稱(代號)`, e.g. "台積電(2330.TW)" or "國巨*(2327.TW)"
_NAME_CODE_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")

# Page shows "資料日期：2026/06/22" near the holdings table.
_DATA_DATE_RE = re.compile(r"資料日期[：:]\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})")


@dataclass(frozen=True)
class Holding:
    stock_code: str
    stock_name: str
    weight_pct: float
    shares: int


def parse_data_date(html: str) -> str | None:
    """Return the page's stated data date as 'YYYY-MM-DD', or None if absent."""
    soup = BeautifulSoup(html, "lxml")
    match = _DATA_DATE_RE.search(soup.get_text(" ", strip=True))
    if not match:
        return None
    year, month, day = (int(g) for g in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_holdings(html: str) -> list[Holding]:
    """Parse the holdings table out of a Basic0007B page's HTML.

    Returns an empty list if the holdings table cannot be found.
    """
    soup = BeautifulSoup(html, "lxml")
    table = _find_holdings_table(soup)
    if table is None:
        return []

    holdings: list[Holding] = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue  # header row (uses <th>) or layout row
        name_cell = cells[0].get_text(strip=True)
        match = _NAME_CODE_RE.match(name_cell)
        if not match:
            continue
        name, code = match.group(1).strip(), match.group(2).strip()
        weight = _parse_float(cells[1].get_text(strip=True))
        shares = _parse_int(cells[2].get_text(strip=True))
        if weight is None or shares is None:
            continue
        holdings.append(
            Holding(stock_code=code, stock_name=name, weight_pct=weight, shares=shares)
        )
    return holdings


class _RelaxedStrictAdapter(HTTPAdapter):
    """TLS adapter that keeps full cert verification but disables the
    VERIFY_X509_STRICT extension check.

    MoneyDJ's certificate chain is missing the Subject Key Identifier
    extension, which Python 3.13+ rejects by default. The chain, hostname
    and expiry are still verified — only the strict-extension check is relaxed.
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def _build_session() -> requests.Session:
    session = requests.Session()
    session.mount("https://", _RelaxedStrictAdapter())
    session.headers.update({"User-Agent": USER_AGENT})
    return session


@dataclass(frozen=True)
class Snapshot:
    data_date: str | None  # the page's stated 資料日期, or None if not found
    holdings: list[Holding]


def fetch_snapshot(etfid: str, *, timeout: float = 20.0) -> Snapshot:
    """Fetch the page for `etfid`; return its data date and holdings."""
    session = _build_session()
    resp = session.get(BASE_URL, params={"etfid": etfid}, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return Snapshot(parse_data_date(resp.text), parse_holdings(resp.text))


def fetch_holdings(etfid: str, *, timeout: float = 20.0) -> list[Holding]:
    """Fetch the page for `etfid` and parse its holdings (date-agnostic)."""
    return fetch_snapshot(etfid, timeout=timeout).holdings


def _find_holdings_table(soup: BeautifulSoup):
    for table in soup.find_all("table", class_="datalist"):
        header = table.get_text(" ", strip=True)
        if "投資比例" in header and "持有股數" in header:
            return table
    return None


def _parse_float(text: str) -> float | None:
    try:
        return float(text.replace(",", "").replace("%", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
