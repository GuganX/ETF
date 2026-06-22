"""Render a holdings snapshot (and its diff vs the prior snapshot) as a static HTML page."""

from __future__ import annotations

import html

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


def render_report(
    etfid: str,
    snapshot_date: str,
    holdings: list[Holding],
    diff_result: HoldingsDiff | None,
    prev_date: str | None,
) -> str:
    """Return a full standalone HTML document for one snapshot."""
    e = html.escape
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

    diff_html = _render_diff(diff_result, prev_date, snapshot_date, e)

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(etfid)} 持股報表 {e(snapshot_date)}</title>
<style>{_CSS}</style></head>
<body><div class="wrap">
<h1>{e(etfid)} 持股報表</h1>
<div class="sub">快照日期 {e(snapshot_date)} · 共 {len(holdings)} 檔持股 · 點欄位標題可排序</div>
{diff_html}
<section><h2>持股明細</h2>{holdings_table}</section>
</div><script>{_SORT_JS}</script></body></html>"""


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

    if diff_result.weight_changes:
        items = "".join(
            f'<li class="{"up" if c.delta >= 0 else "down"}">{e(c.stock_name)} ({e(c.stock_code)}) '
            f'{c.old_weight:.2f}% → {c.new_weight:.2f}% ({"+" if c.delta >= 0 else ""}{c.delta:.2f})</li>'
            for c in diff_result.weight_changes
        )
        parts.append(f"<b>📊 比例變化<span class='pill g'>{len(diff_result.weight_changes)}</span></b><ul>{items}</ul>")

    if diff_result.shares_changes:
        items = "".join(
            f'<li class="{"up" if c.delta >= 0 else "down"}">{e(c.stock_name)} ({e(c.stock_code)}) '
            f'{c.old_shares:,} → {c.new_shares:,} ({"+" if c.delta >= 0 else ""}{c.delta:,})</li>'
            for c in diff_result.shares_changes
        )
        parts.append(f"<b>📈 股數變化<span class='pill g'>{len(diff_result.shares_changes)}</span></b><ul>{items}</ul>")

    return f"<section>{''.join(parts)}</section>"
