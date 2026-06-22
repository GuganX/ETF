# ETF Holdings Tracker

抓取 MoneyDJ ETF 持股頁面,每天存成 SQLite 快照,並可查詢任兩天之間的持股變化
(新增 / 移除 / 比例變化 / 股數變化)。

資料來源:`https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm?etfid=<ID>`

## 安裝

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 設定

編輯 `etfs.yaml`,加入要追蹤的 ETF:

```yaml
db_path: etf_holdings.db
etfids:
  - 00981A.TW
  - 0050.TW          # 想追幾檔就加幾檔
```

## 使用

```bash
# 抓取設定檔內所有 ETF,存成今天的快照(可重複跑,同日會覆蓋)
.venv/bin/python -m etf_tracker.cli fetch

# 指定日期(回填或測試用)
.venv/bin/python -m etf_tracker.cli fetch --date 2026-06-22

# 列出某檔 ETF 已有的快照日期
.venv/bin/python -m etf_tracker.cli list 00981A.TW

# 比較變化(不給日期 = 自動比最近兩天)
.venv/bin/python -m etf_tracker.cli diff 00981A.TW
.venv/bin/python -m etf_tracker.cli diff 00981A.TW 2026-06-21 2026-06-22
```

## 每天自動更新

`run_daily.sh` 是給排程用的包裝腳本。設定每天收盤後(例如 18:00)執行:

```bash
chmod +x run_daily.sh
crontab -e
```

加入這一行(請改成你的實際路徑):

```cron
0 18 * * * /Users/brucehsu/claude/etf/run_daily.sh
```

執行紀錄會寫到 `fetch.log`;每次抓取的成功/失敗也會記在資料庫的 `fetch_log` 表。

## 資料表

- `holdings_snapshot` — 每天每檔股票一列
  (`etfid, snapshot_date, stock_code, stock_name, weight_pct, shares`),
  主鍵 `(etfid, snapshot_date, stock_code)`,同日重跑會覆蓋不重複。
- `fetch_log` — 每次抓取的結果與狀態。

## 測試

```bash
.venv/bin/python -m pytest
```

## 備註

MoneyDJ 的 TLS 憑證鏈缺少 Subject Key Identifier 擴充,Python 3.13+ 預設會拒絕。
scraper 只關閉 `VERIFY_X509_STRICT` 這項嚴格檢查,仍會完整驗證憑證鏈、主機名與有效期。
