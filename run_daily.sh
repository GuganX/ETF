#!/usr/bin/env bash
# Daily job for cron/launchd:
#   1. scrape every configured ETF into the SQLite db
#   2. (re)generate the published HTML report as index.html
#   3. commit index.html and push to GitHub (only when it changed)
# Output is appended to fetch.log next to this script.
set -euo pipefail
cd "$(dirname "$0")"

{
  echo "===== run $(date '+%Y-%m-%d %H:%M:%S') ====="
  .venv/bin/python -m etf_tracker.cli fetch --report-path index.html

  # Commit & push the report only when it actually changed.
  if [ -n "$(git status --porcelain -- index.html)" ]; then
    git add index.html
    git commit -m "Daily report $(date '+%Y-%m-%d')"
    git push
    echo "pushed updated index.html"
  else
    echo "index.html unchanged, nothing to push"
  fi
} >> fetch.log 2>&1
