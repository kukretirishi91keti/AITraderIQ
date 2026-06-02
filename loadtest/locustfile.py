"""
AITraderIQ Daily Load Test — Workflow-Based User Journeys
=========================================================
Simulates four real trader archetypes with full end-to-end workflows instead
of isolated random endpoint hits.

User classes (weighted):
  SignalHunterUser      (weight 4) — authenticated, quote → candles → signals → watchlist
  CasualBrowserUser     (weight 3) — anonymous,     overview → screener → quote → candles
  FundamentalAnalystUser(weight 2) — authenticated, financials → quote → signals
  DayTraderUser         (weight 1) — authenticated, rapid multi-quote → candles(15m) → signals

Data quality tracking:
  SIMULATED / FALLBACK / DEMO responses are counted separately and printed in
  the final summary.  They do NOT affect the pass/fail verdict so that a cold
  start on a fresh Render instance never auto-fails.

Run:
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
           --users 10 --spawn-rate 2 --run-time 5m --headless \
           --html loadtest/reports/report_$(date +%Y%m%d_%H%M).html

Or via GitHub Actions (twice daily on weekdays).
"""

import random
import threading
from locust import HttpUser, task, between, events

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

US_STOCKS  = ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "AMZN", "META"]
IN_STOCKS  = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "WIPRO.NS"]
CRYPTO     = ["BTC-USD", "ETH-USD"]
ETFS       = ["SPY", "QQQ", "VTI"]

ALL_SYMBOLS = US_STOCKS + IN_STOCKS + CRYPTO + ETFS

# For fundamentals only use symbols with reliable yfinance coverage
FUNDAMENTAL_SYMBOLS = US_STOCKS + ["RELIANCE.NS", "TCS.NS"]

TEST_EMAIL    = "loadtest@aitraderiq.dev"
TEST_PASSWORD = "LoadTest123!"

# ---------------------------------------------------------------------------
# Thread-safe data quality counters
# ---------------------------------------------------------------------------

_qlock = threading.Lock()
_quality: dict = {
    "live":      0,
    "simulated": 0,
    "issues":    [],   # list of (endpoint, symbol, tag) — capped at 30
}


def _track_quality(tag: str | None, endpoint: str, symbol: str = "") -> None:
    """Record whether a response carried live or simulated data."""
    if not tag:
        return
    tag_upper = tag.upper()
    with _qlock:
        if tag_upper in ("SIMULATED", "FALLBACK", "DEMO"):
            _quality["simulated"] += 1
            if len(_quality["issues"]) < 30:
                _quality["issues"].append((endpoint, symbol, tag_upper))
        elif tag_upper in ("LIVE", "YFINANCE", "REAL"):
            _quality["live"] += 1


# ---------------------------------------------------------------------------
# Shared auth helper
# ---------------------------------------------------------------------------

def _authenticate(client) -> str | None:
    """Register (ignore conflicts) then login; return JWT or None."""
    with client.post(
        "/api/auth/register",
        json={
            "email":     TEST_EMAIL,
            "username":  "loadtester",
            "password":  TEST_PASSWORD,
            "full_name": "Load Tester",
        },
        name="/api/auth/register",
        catch_response=True,
    ) as r:
        # 409 / 400 "already registered" is fine — suppress it
        if r.status_code in (400, 409):
            r.success()

    res = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
        name="/api/auth/login",
    )
    if res.status_code == 200:
        return res.json().get("access_token")
    return None


# ---------------------------------------------------------------------------
# User class 1 — Signal Hunter (most common authenticated user)
# ---------------------------------------------------------------------------

class SignalHunterUser(HttpUser):
    """
    Authenticated trader who searches for buy/sell signals.
    Journey: quote → candles → signals → watchlist (repeat with fresh symbol).
    """
    weight    = 4
    wait_time = between(1, 3)
    token: str | None = None

    def on_start(self):
        self.token = _authenticate(self.client)

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task
    def signal_hunting_session(self):
        symbol = random.choice(ALL_SYMBOLS)

        # Step 1 — get live price
        r = self.client.get(
            f"/api/v4/quote/{symbol}",
            name="/api/v4/quote/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "quote", symbol)
            price = (data.get("price") or data.get("regularMarketPrice") or 0)
            if price is not None and float(price) <= 0:
                with _qlock:
                    if len(_quality["issues"]) < 30:
                        _quality["issues"].append(("quote", symbol, "NULL_PRICE"))

        # Step 2 — load 1-hour candles
        r = self.client.get(
            f"/api/v4/candles/{symbol}?interval=1h&lookback=50",
            name="/api/v4/candles/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "candles", symbol)
            candles = data.get("candles") or data.get("results") or []
            if not candles:
                with _qlock:
                    if len(_quality["issues"]) < 30:
                        _quality["issues"].append(("candles", symbol, "EMPTY"))

        # Step 3 — fetch signal
        r = self.client.get(
            f"/api/v4/signals/{symbol}",
            name="/api/v4/signals/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("source") or data.get("dataQuality"), "signals", symbol)

        # Step 4 — watchlist (auth required)
        watchlist_symbols = ",".join(random.sample(ALL_SYMBOLS, min(5, len(ALL_SYMBOLS))))
        self.client.get(
            f"/api/v4/watchlist?symbols={watchlist_symbols}",
            headers=self._auth(),
            name="/api/v4/watchlist",
        )


# ---------------------------------------------------------------------------
# User class 2 — Casual Browser (anonymous visitor)
# ---------------------------------------------------------------------------

class CasualBrowserUser(HttpUser):
    """
    Anonymous user who browses the market overview and looks up a stock.
    Journey: market-overview → screener → quote → candles(1d).
    """
    weight    = 3
    wait_time = between(2, 5)   # slower — casual browsing pace

    @task
    def browse_session(self):
        # Step 1 — land on market overview
        self.client.get("/api/v4/market-overview", name="/api/v4/market-overview")

        # Step 2 — browse screener
        self.client.get("/api/screener/universe", name="/api/screener/universe")

        # Step 3 — click a stock
        symbol = random.choice(ALL_SYMBOLS)
        r = self.client.get(
            f"/api/v4/quote/{symbol}",
            name="/api/v4/quote/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "quote", symbol)

        # Step 4 — view daily chart
        r = self.client.get(
            f"/api/v4/candles/{symbol}?interval=1d&lookback=90",
            name="/api/v4/candles/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "candles", symbol)

    @task(1)
    def health_ping(self):
        self.client.get("/api/v4/health", name="/api/v4/health")


# ---------------------------------------------------------------------------
# User class 3 — Fundamental Analyst (slow, thorough)
# ---------------------------------------------------------------------------

class FundamentalAnalystUser(HttpUser):
    """
    Authenticated user doing deep-dive fundamental research.
    Journey: financials → quote → signals → candles(1d, long lookback).
    Validates that key financial fields are present.
    """
    weight    = 2
    wait_time = between(3, 8)   # reads carefully — longer pauses
    token: str | None = None

    def on_start(self):
        self.token = _authenticate(self.client)

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task
    def deep_dive_session(self):
        symbol = random.choice(FUNDAMENTAL_SYMBOLS)

        # Step 1 — pull financials (most important for this persona)
        r = self.client.get(
            f"/api/v4/financials/{symbol}",
            name="/api/v4/financials/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "financials", symbol)
            fin = data.get("financials") or {}
            if symbol in US_STOCKS and fin.get("pe_ratio") is None:
                with _qlock:
                    if len(_quality["issues"]) < 30:
                        _quality["issues"].append(("financials", symbol, "NULL_PE_RATIO"))

        # Step 2 — current price check
        r = self.client.get(
            f"/api/v4/quote/{symbol}",
            name="/api/v4/quote/[symbol]",
        )
        if r.status_code == 200:
            _track_quality(
                r.json().get("dataQuality") or r.json().get("source"), "quote", symbol
            )

        # Step 3 — signal for context
        r = self.client.get(
            f"/api/v4/signals/{symbol}",
            name="/api/v4/signals/[symbol]",
        )
        if r.status_code == 200:
            _track_quality(
                r.json().get("source") or r.json().get("dataQuality"), "signals", symbol
            )

        # Step 4 — long daily candle history
        r = self.client.get(
            f"/api/v4/candles/{symbol}?interval=1d&lookback=200",
            name="/api/v4/candles/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "candles", symbol)


# ---------------------------------------------------------------------------
# User class 4 — Day Trader (fast, high-frequency)
# ---------------------------------------------------------------------------

class DayTraderUser(HttpUser):
    """
    Authenticated active trader refreshing prices rapidly.
    Journey: 3× rapid quotes on different symbols → 15-min candles → signal.
    """
    weight    = 1
    wait_time = between(0.5, 1.5)   # fast — market is moving!
    token: str | None = None

    def on_start(self):
        self.token = _authenticate(self.client)

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task
    def rapid_trading_session(self):
        # Step 1 — scan 3 symbols quickly
        sample = random.sample(US_STOCKS + IN_STOCKS, 3)
        for sym in sample:
            r = self.client.get(
                f"/api/v4/quote/{sym}",
                name="/api/v4/quote/[symbol]",
            )
            if r.status_code == 200:
                _track_quality(
                    r.json().get("dataQuality") or r.json().get("source"), "quote", sym
                )

        # Step 2 — pick the most interesting, load 15-min candles
        focus = random.choice(sample)
        r = self.client.get(
            f"/api/v4/candles/{focus}?interval=15m&lookback=80",
            name="/api/v4/candles/[symbol]",
        )
        if r.status_code == 200:
            data = r.json()
            _track_quality(data.get("dataQuality") or data.get("source"), "candles", focus)
            candles = data.get("candles") or data.get("results") or []
            if not candles:
                with _qlock:
                    if len(_quality["issues"]) < 30:
                        _quality["issues"].append(("candles-15m", focus, "EMPTY"))

        # Step 3 — confirm with signal
        r = self.client.get(
            f"/api/v4/signals/{focus}",
            name="/api/v4/signals/[symbol]",
        )
        if r.status_code == 200:
            _track_quality(
                r.json().get("source") or r.json().get("dataQuality"), "signals", focus
            )


# ---------------------------------------------------------------------------
# End-of-run summary
# ---------------------------------------------------------------------------

@events.quitting.add_listener
def print_summary(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    fail_rate = (
        total.num_failures / total.num_requests * 100
    ) if total.num_requests else 0

    passed = fail_rate < 2.0 and total.avg_response_time < 3000

    print("\n" + "=" * 65)
    print("  AITraderIQ Load Test — Summary")
    print("=" * 65)
    print(f"  Total requests : {total.num_requests}")
    print(f"  Failures       : {total.num_failures}  ({fail_rate:.1f}%)")
    print(f"  Avg resp time  : {total.avg_response_time:.0f} ms")
    print(f"  95th pct       : {total.get_response_time_percentile(0.95):.0f} ms")

    # Data quality section
    print()
    print("  Data Quality")
    print("  " + "-" * 40)
    with _qlock:
        live      = _quality["live"]
        simulated = _quality["simulated"]
        total_dq  = live + simulated
        pct_live  = (live / total_dq * 100) if total_dq else 0
        print(f"  Live responses     : {live}")
        print(f"  Simulated/Fallback : {simulated}  ({100 - pct_live:.0f}% of tracked)")
        if _quality["issues"]:
            print(f"  Notable issues ({min(10, len(_quality['issues']))} shown):")
            for ep, sym, tag in _quality["issues"][:10]:
                sym_str = f" [{sym}]" if sym else ""
                print(f"    • {ep}{sym_str} → {tag}")

    # Verdict — SIMULATED data is informational only, not a failure
    print()
    verdict = "✅ PASS" if passed else "❌ FAIL"
    print(f"  Result: {verdict}")
    print(f"  Criteria: fail rate < 2.0% (got {fail_rate:.1f}%), "
          f"avg < 3 000 ms (got {total.avg_response_time:.0f} ms)")
    print("=" * 65)
