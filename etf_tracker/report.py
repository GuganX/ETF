"""Render a holdings snapshot (and its diff vs the prior snapshot) as a static HTML page."""

from __future__ import annotations

import html
from dataclasses import dataclass

from .diff import HoldingsDiff
from .scraper import Holding

_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif;
       margin: 0; background: #f5f6f8; color: #1f2933; }
.wrap { max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: #677; font-size: 13px; margin-bottom: 24px; }
section { background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,.06); }
h2 { font-size: 16px; margin: 0 0 12px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 7px 10px; text-align: right; border-bottom: 1px solid #eef1f4; }
th:nth-child(2), td:nth-child(2) { text-align: left; }
thead th { cursor: pointer; user-select: none; background: #fafbfc; color: #556;
           font-weight: 600; position: sticky; top: 0; }
thead th:hover { background: #eef1f4; }
tbody tr:hover { background: #f7f9fb; }
.rank { color: #9aa; }
.bar { background: linear-gradient(to right, #cfe3ff var(--w), transparent 0); }
.added { color: #137333; } .removed { color: #c5221f; }
.up { color: #137333; } .down { color: #c5221f; }
.pill { display: inline-block; min-width: 18px; padding: 1px 7px; border-radius: 10px;
        font-size: 12px; font-weight: 600; margin-left: 8px; }
.pill.g { background: #e6f4ea; color: #137333; } .pill.r { background: #fce8e6; color: #c5221f; }
.empty { color: #889; font-style: italic; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.tab { cursor: pointer; border: 1px solid #d4d9e0; background: #fff; color: #1f2933;
       padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 600; }
.tab:hover { background: #eef1f4; }
.tab.active { background: #1a73e8; border-color: #1a73e8; color: #fff; }
.etf-panel { display: none; }
.etf-panel.active { display: block; }
"""

_SORT_JS = """
document.querySelectorAll('table.sortable').forEach(function(t){
  t.querySelectorAll('thead th').forEach(function(th,i){
    th.addEventListener('click',function(){
      var rows=Array.from(t.tBodies[0].rows);
      var num=th.dataset.num==='1';
      var asc=th.dataset.asc!=='1';
      t.querySelectorAll('thead th').forEach(function(o){o.dataset.asc='';});
      th.dataset.asc=asc?'1':'';
      rows.sort(function(a,b){
        var x=a.cells[i].dataset.v??a.cells[i].innerText;
        var y=b.cells[i].dataset.v??b.cells[i].innerText;
        if(num){x=parseFloat(x)||0;y=parseFloat(y)||0;return asc?x-y:y-x;}
        return asc?(''+x).localeCompare(y):(''+y).localeCompare(x);
      });
      rows.forEach(function(r){t.tBodies[0].appendChild(r);});
    });
  });
});
"""

_TAB_JS = """
document.querySelectorAll('.tab').forEach(function(tab){
  tab.addEventListener('click',function(){
    var id=tab.dataset.target;
    document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('active',t===tab);});
    document.querySelectorAll('.etf-panel').forEach(function(p){
      p.classList.toggle('active', p.id===id);
    });
  });
});
"""


@dataclass(frozen=True)
class EtfReport:
    """One ETF's data needed to render a report panel."""

    etfid: str
    snapshot_date: str
    holdings: list[Holding]
    diff_result: HoldingsDiff | None
    prev_date: str | None


def _render_body(report: EtfReport, e) -> str:
    """Render the inner content (diff + holdings table) for a single ETF."""
    holdings = report.holdings
    max_w = max((h.weight_pct for h in holdings), default=1.0) or 1.0

    rows = []
    for i, h in enumerate(holdings, 1):
        width = f"{h.weight_pct / max_w * 100:.1f}%"
        rows.append(
            f"<tr>"
            f'<td class="rank">{i}</td>'
            f"<td>{e(h.stock_name)}<span style='color:#9aa'> ({e(h.stock_code)})</span></td>"
            f'<td class="bar" data-v="{h.weight_pct}" style="--w:{width}">{h.weight_pct:.2f}%</td>'
            f'<td data-v="{h.shares}">{h.shares:,}</td>'
            f"</tr>"
        )

    holdings_table = (
        '<table class="sortable"><thead><tr>'
        "<th>#</th><th>個股名稱</th>"
        '<th data-num="1">投資比例(%)</th><th data-num="1">持有股數</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )

    diff_html = _render_diff(report.diff_result, report.prev_date, report.snapshot_date, e)

    return (
        f'<div class="sub">快照日期 {e(report.snapshot_date)} · '
        f"共 {len(holdings)} 檔持股 · 點欄位標題可排序</div>"
        f"{diff_html}"
        f'<section><h2>持股明細</h2>{holdings_table}</section>'
    )


def _document(title: str, body: str, *, with_tabs: bool) -> str:
    """Wrap inner HTML in a full standalone document."""
    e = html.escape
    scripts = _SORT_JS + (_TAB_JS if with_tabs else "")
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<style>{_CSS}</style></head>
<body><div class="wrap">
{body}
</div><script>{scripts}</script></body></html>"""


def render_report(
    etfid: str,
    snapshot_date: str,
    holdings: list[Holding],
    diff_result: HoldingsDiff | None,
    prev_date: str | None,
) -> str:
    """Return a full standalone HTML document for a single ETF snapshot."""
    e = html.escape
    report = EtfReport(etfid, snapshot_date, holdings, diff_result, prev_date)
    body = f"<h1>{e(etfid)} 持股報表</h1>{_render_body(report, e)}"
    return _document(f"{etfid} 持股報表 {snapshot_date}", body, with_tabs=False)


def render_combined_report(reports: list[EtfReport]) -> str:
    """Return one standalone HTML document with a clickable tab per ETF."""
    e = html.escape
    tabs = []
    panels = []
    for i, r in enumerate(reports):
        panel_id = f"etf-{e(r.etfid)}"
        active = " active" if i == 0 else ""
        tabs.append(
            f'<button class="tab{active}" data-target="{panel_id}">{e(r.etfid)}</button>'
        )
        panels.append(
            f'<div class="etf-panel{active}" id="{panel_id}">'
            f"<h1>{e(r.etfid)} 持股報表</h1>{_render_body(r, e)}</div>"
        )
    body = (
        f'<div class="tabs">{"".join(tabs)}</div>{"".join(panels)}'
        if reports
        else '<p class="empty">沒有任何 ETF 快照資料。</p>'
    )
    return _document("ETF 持股報表", body, with_tabs=True)


def _render_diff(diff_result, prev_date, snapshot_date, e) -> str:
    if diff_result is None or prev_date is None:
        return (
            '<section><h2>與前一日變化</h2>'
            '<p class="empty">只有這一天的快照,還沒有可比較的前一日資料。</p></section>'
        )

    head = f"<h2>變化 <span class='sub'>{e(prev_date)} → {e(snapshot_date)}</span></h2>"
    if diff_result.is_empty:
        return f'<section>{head}<p class="empty">與前一日相比沒有變化。</p></section>'

    parts = [head]

    if diff_result.added:
        items = "".join(
            f'<li class="added">＋ {e(h.stock_name)} ({e(h.stock_code)}) '
            f"{h.weight_pct:.2f}% · {h.shares:,} 股</li>"
            for h in diff_result.added
        )
        parts.append(f"<b>🟢 新增持股<span class='pill g'>{len(diff_result.added)}</span></b><ul>{items}</ul>")

    if diff_result.removed:
        items = "".join(
            f'<li class="removed">－ {e(h.stock_name)} ({e(h.stock_code)}) '
            f"原 {h.weight_pct:.2f}% · {h.shares:,} 股</li>"
            for h in diff_result.removed
        )
        parts.append(f"<b>🔴 移除持股<span class='pill r'>{len(diff_result.removed)}</span></b><ul>{items}</ul>")

    if diff_result.shares_changes:
        items = "".join(
            f'<li class="{"up" if c.delta >= 0 else "down"}">{e(c.stock_name)} ({e(c.stock_code)}) '
            f'{c.old_shares:,} → {c.new_shares:,} ({"+" if c.delta >= 0 else ""}{c.delta:,})</li>'
            for c in diff_result.shares_changes
        )
        parts.append(f"<b>📈 股數變化<span class='pill g'>{len(diff_result.shares_changes)}</span></b><ul>{items}</ul>")

    return f"<section>{''.join(parts)}</section>"
