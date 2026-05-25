#!/usr/bin/env bash
# ============================================================
# run_daily_check.sh
# Runs the full test suite + data-quality report for one day.
#
# Usage (from backend/ directory):
#   ./run_daily_check.sh               # DEMO_MODE, in-process
#   BASE_URL=https://… ./run_daily_check.sh   # live backend
#
# Output:
#   reports/YYYY-MM-DD.json     — data-quality numbers
#   reports/YYYY-MM-DD.html     — human-readable report
#   reports/YYYY-MM-DD_tests.json — pytest results (pass/fail counts)
# ============================================================

set -euo pipefail

TODAY=$(date +%Y-%m-%d)
REPORT_DIR="$(dirname "$0")/reports"
mkdir -p "$REPORT_DIR"

PYTEST_JSON="$REPORT_DIR/${TODAY}_tests.json"
PYTEST_HTML="$REPORT_DIR/${TODAY}_tests.html"

# ── 1. Run test suite ────────────────────────────────────────
echo "━━━ Running test suite ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$(dirname "$0")"

# Ensure report plugins are installed (no-op if already present)
pip install --quiet pytest-html>=4.0.0 pytest-json-report>=1.5.0 2>/dev/null || true

DEMO_MODE=true pytest tests/ \
  --json-report --json-report-file="$PYTEST_JSON" \
  --html="$PYTEST_HTML" --self-contained-html \
  -q --tb=short \
  --ignore=tests/test_smoke_1000_users.py \
  --ignore=tests/test_smoke_50_users.py \
  2>&1 || true   # don't abort if tests fail — still run data report

# Print quick summary from JSON report if available
if [ -f "$PYTEST_JSON" ]; then
  TOTAL=$(python3 -c "import json; d=json.load(open('$PYTEST_JSON')); s=d.get('summary',{}); print(s.get('total',0))" 2>/dev/null || echo "?")
  PASSED=$(python3 -c "import json; d=json.load(open('$PYTEST_JSON')); s=d.get('summary',{}); print(s.get('passed',0))" 2>/dev/null || echo "?")
  FAILED=$(python3 -c "import json; d=json.load(open('$PYTEST_JSON')); s=d.get('summary',{}); print(s.get('failed',0))" 2>/dev/null || echo "?")
  echo ""
  echo "  Tests: $PASSED/$TOTAL passed, $FAILED failed"
  echo "  Full pytest report → $PYTEST_JSON"
fi

echo ""

# ── 2. Run data-quality report ───────────────────────────────
echo "━━━ Running data-quality report ━━━━━━━━━━━━━━━━━━━━━━━━"
python3 run_daily_report.py

# ── 3. Merge pytest summary into data report JSON ───────────
if [ -f "$PYTEST_JSON" ] && [ -f "$REPORT_DIR/${TODAY}.json" ]; then
  python3 - <<'PYEOF'
import json, sys
from pathlib import Path
from datetime import date

today = str(date.today())
report_dir = Path("reports")
data_path = report_dir / f"{today}.json"
test_path = report_dir / f"{today}_tests.json"

if not data_path.exists() or not test_path.exists():
    sys.exit(0)

data = json.loads(data_path.read_text())
tests = json.loads(test_path.read_text())

summary = tests.get("summary", {})
data["pytest_summary"] = {
    "total": summary.get("total", 0),
    "passed": summary.get("passed", 0),
    "failed": summary.get("failed", 0),
    "error": summary.get("error", 0),
    "skipped": summary.get("skipped", 0),
    "duration_sec": round(tests.get("duration", 0), 1),
}

# Collect failed test names for quick review
failed_tests = [
    t["nodeid"]
    for t in tests.get("tests", [])
    if t.get("outcome") == "failed"
]
data["pytest_summary"]["failed_tests"] = failed_tests[:20]  # cap at 20

data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print(f"  Merged pytest summary → {data_path}")
PYEOF
fi

# ── 4. Final summary ─────────────────────────────────────────
echo ""
echo "━━━ Done ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Data report  → $REPORT_DIR/${TODAY}.html"
echo "  Data report  → $REPORT_DIR/${TODAY}.json"
echo "  Pytest HTML  → $PYTEST_HTML"
echo "  Pytest JSON  → $PYTEST_JSON"
echo ""
echo "  Open the HTML report to review actual ₹ prices, RSI"
echo "  values, AI scores, and P&L for manual correctness check."
