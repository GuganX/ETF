#!/usr/bin/env bash
# Daily fetch wrapper for cron/launchd. Logs to fetch.log next to this script.
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/python -m etf_tracker.cli fetch >> fetch.log 2>&1
