#!/usr/bin/env bash
# Pre-launch smoke test for AITraderIQ
# Usage: ./scripts/smoke_test.sh [API_BASE_URL]
# Default: https://aitraderiq.onrender.com

set -euo pipefail

API="${1:-https://aitraderiq.onrender.com}"
PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}  PASS${NC}  $1"; ((PASS++)); }
fail() { echo -e "${RED}  FAIL${NC}  $1"; ((FAIL++)); }
warn() { echo -e "${YELLOW}  WARN${NC}  $1"; ((WARN++)); }

check_json_field() {
  local url="$1" field="$2" expected="$3" label="$4"
  local val
  val=$(curl -sf --max-time 15 "$url" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field','MISSING'))" 2>/dev/null || echo "ERROR")
  if [[ "$val" == "$expected" ]]; then
    pass "$label (got '$val')"
  else
    fail "$label — expected '$expected' got '$val'"
  fi
}

check_http() {
  local url="$1" label="$2"
  local code
  code=$(curl -o /dev/null -sw "%{http_code}" --max-time 15 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    pass "$label (HTTP $code)"
  else
    fail "$label (HTTP $code)"
  fi
}

echo "============================================================"
echo "  AITraderIQ Smoke Test"
echo "  API: $API"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""

echo "── Core endpoints ───────────────────────────────────────────"
check_http "$API/ping"          "GET /ping"
check_http "$API/"              "GET /"
check_http "$API/api/health"    "GET /api/health"
check_http "$API/api/health/ready" "GET /api/health/ready"
check_http "$API/api/config-status" "GET /api/config-status"
echo ""

echo "── Config readiness ─────────────────────────────────────────"
STATUS=$(curl -sf --max-time 15 "$API/api/config-status" 2>/dev/null || echo "{}")
AUTH=$(echo "$STATUS"    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readiness',{}).get('auth_works','false'))" 2>/dev/null || echo "false")
DB=$(echo "$STATUS"      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readiness',{}).get('db_persistent','false'))" 2>/dev/null || echo "false")
INDIA=$(echo "$STATUS"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('readiness',{}).get('can_serve_india_live','false'))" 2>/dev/null || echo "false")

[[ "$AUTH"   == "True" || "$AUTH"   == "true" ]]  && pass "JWT auth configured" || fail "JWT auth NOT configured"
[[ "$DB"     == "True" || "$DB"     == "true" ]]  && pass "Persistent DB (Postgres)" || warn "SQLite (not persistent across restarts)"
[[ "$INDIA"  == "True" || "$INDIA"  == "true" ]]  && pass "India live data ready" || warn "India data in simulated mode"
echo ""

echo "── Market data ──────────────────────────────────────────────"
check_http "$API/api/v4/quote/RELIANCE.NS"          "India quote RELIANCE.NS"
check_http "$API/api/v4/quote/AAPL"                 "US quote AAPL"
check_http "$API/api/v4/quote/HDFCBANK.NS"          "India quote HDFCBANK.NS"
check_http "$API/api/v4/history/RELIANCE.NS?interval=1d" "History RELIANCE.NS 1d"
check_http "$API/api/v4/signals/RELIANCE.NS"        "Signals RELIANCE.NS"
echo ""

echo "── Screener ─────────────────────────────────────────────────"
check_http "$API/api/screener/universe"             "Screener universe"
check_http "$API/api/v4/screener/top-movers"        "Top movers"
echo ""

echo "── India-specific ───────────────────────────────────────────"
check_http "$API/api/v4/option-chain/NIFTY"         "Option chain NIFTY"
check_http "$API/api/v4/fii-dii"                    "FII/DII data"
check_http "$API/api/v4/earnings/RELIANCE.NS"       "Earnings RELIANCE.NS"
echo ""

echo "── AI / Signals ─────────────────────────────────────────────"
check_http "$API/api/v4/sentiment/RELIANCE.NS"      "Sentiment RELIANCE.NS"
check_http "$API/api/signals"                        "Signals list"
echo ""

echo "── Auth endpoints (expect 422 on empty body, not 500) ───────"
code_auth=$(curl -o /dev/null -sw "%{http_code}" --max-time 10 -X POST "$API/api/auth/login" -H "Content-Type: application/x-www-form-urlencoded" -d "" 2>/dev/null || echo "000")
[[ "$code_auth" == "422" ]] && pass "POST /api/auth/login rejects empty body (422)" || warn "POST /api/auth/login returned $code_auth (expected 422)"

code_reg=$(curl -o /dev/null -sw "%{http_code}" --max-time 10 -X POST "$API/api/auth/register" -H "Content-Type: application/json" -d "{}" 2>/dev/null || echo "000")
[[ "$code_reg" == "422" ]] && pass "POST /api/auth/register rejects empty body (422)" || warn "POST /api/auth/register returned $code_reg (expected 422)"
echo ""

echo "── Data quality ─────────────────────────────────────────────"
QUOTE=$(curl -sf --max-time 15 "$API/api/v4/quote/RELIANCE.NS" 2>/dev/null || echo "{}")
PRICE=$(echo "$QUOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('price','MISSING'))" 2>/dev/null || echo "MISSING")
SOURCE=$(echo "$QUOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source','MISSING'))" 2>/dev/null || echo "MISSING")
QUALITY=$(echo "$QUOTE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('dataQuality','MISSING'))" 2>/dev/null || echo "MISSING")

if [[ "$PRICE" != "MISSING" && "$PRICE" != "null" && "$PRICE" != "0" ]]; then
  pass "RELIANCE.NS price: ₹$PRICE (source=$SOURCE, quality=$QUALITY)"
else
  fail "RELIANCE.NS price missing or zero"
fi
echo ""

echo "============================================================"
echo "  Results: ${PASS} PASS  |  ${WARN} WARN  |  ${FAIL} FAIL"
echo "============================================================"

if [[ $FAIL -gt 0 ]]; then
  echo -e "${RED}  SMOKE TEST FAILED — $FAIL critical failures${NC}"
  exit 1
elif [[ $WARN -gt 0 ]]; then
  echo -e "${YELLOW}  SMOKE TEST PASSED WITH WARNINGS${NC}"
  exit 0
else
  echo -e "${GREEN}  ALL CHECKS PASSED — ready to go live${NC}"
  exit 0
fi
