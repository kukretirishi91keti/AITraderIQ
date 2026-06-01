#!/usr/bin/env bash
# ==============================================================================
# AITraderIQ Daily Load Test
# Run every morning before market open (e.g. 8:45 IST = 03:15 UTC)
#
# Usage:
#   ./loadtest/run_daily.sh                        # targets localhost:8000
#   ./loadtest/run_daily.sh https://your-app.com   # targets production
#
# Cron (from repo root):
#   15 3 * * 1-5  /bin/bash /path/to/AITraderIQ/loadtest/run_daily.sh https://your-app.com >> /var/log/aitraderiq_loadtest.log 2>&1
# ==============================================================================

set -euo pipefail

HOST="${1:-http://localhost:8000}"
DATE=$(date +%Y%m%d_%H%M)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR="$SCRIPT_DIR/reports"
REPORT_HTML="$REPORT_DIR/report_${DATE}.html"
REPORT_CSV="$REPORT_DIR/stats_${DATE}"

mkdir -p "$REPORT_DIR"

echo "======================================================"
echo "  AITraderIQ Load Test  —  $(date)"
echo "  Host    : $HOST"
echo "  Users   : 10"
echo "  Duration: 5 minutes"
echo "======================================================"

locust \
  -f "$SCRIPT_DIR/locustfile.py" \
  --host "$HOST" \
  --users 10 \
  --spawn-rate 2 \
  --run-time 5m \
  --headless \
  --html "$REPORT_HTML" \
  --csv  "$REPORT_CSV" \
  --exit-code-on-error 0

echo ""
echo "Report saved → $REPORT_HTML"
echo "CSV stats   → ${REPORT_CSV}_stats.csv"

# Keep only the last 30 reports to avoid disk bloat
ls -t "$REPORT_DIR"/report_*.html 2>/dev/null | tail -n +31 | xargs -r rm --
ls -t "$REPORT_DIR"/stats_*_stats.csv 2>/dev/null | tail -n +31 | xargs -r rm --

echo "Done. Old reports cleaned (keeping last 30 days)."
