"""
AITraderIQ Daily Load Test — 10 Simulated Users
================================================
Simulates realistic user sessions: search, view stock, check signals,
browse watchlist, and market overview.

Run:
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
           --users 10 --spawn-rate 2 --run-time 5m --headless \
           --html loadtest/reports/report_$(date +%Y%m%d).html

Or with the daily script:
    ./loadtest/run_daily.sh
"""

import random
from locust import HttpUser, task, between, events

# Symbols spread across US, India, Crypto, ETF
SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "TSLA",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
    "BTC-USD", "ETH-USD",
    "SPY", "QQQ",
]

# Test credentials — use a throwaway account in dev
TEST_EMAIL    = "loadtest@aitraderiq.dev"
TEST_PASSWORD = "LoadTest123!"


class TraderUser(HttpUser):
    """
    Simulates a logged-in retail trader browsing the app.
    Wait 1–3 seconds between requests (realistic human pace).
    """
    wait_time = between(1, 3)
    token: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def on_start(self):
        """Register (ignore 409 if already exists) then log in to get a JWT."""
        self.client.post(
            "/api/auth/register",
            json={"email": TEST_EMAIL, "username": "loadtester", "password": TEST_PASSWORD, "full_name": "Load Tester"},
            name="/api/auth/register",
        )
        # Login uses OAuth2PasswordRequestForm — must be form-encoded, not JSON
        res = self.client.post(
            "/api/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
            name="/api/auth/login",
        )
        if res.status_code == 200:
            self.token = res.json().get("access_token")

    def _auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ------------------------------------------------------------------
    # Core flows — weighted by real usage patterns
    # ------------------------------------------------------------------

    @task(5)
    def view_stock(self):
        """Most common action: look up a stock."""
        symbol = random.choice(SYMBOLS)
        self.client.get(f"/api/v4/quote/{symbol}", name="/api/v4/quote/[symbol]")

    @task(4)
    def view_candles(self):
        symbol = random.choice(SYMBOLS)
        interval = random.choice(["1d", "1h", "15m"])
        self.client.get(
            f"/api/v4/candles/{symbol}?interval={interval}&lookback=100",
            name="/api/v4/candles/[symbol]",
        )

    @task(3)
    def view_signals(self):
        symbol = random.choice(SYMBOLS)
        self.client.get(f"/api/v4/signals/{symbol}", name="/api/v4/signals/[symbol]")

    @task(2)
    def view_financials(self):
        symbol = random.choice(["AAPL", "MSFT", "NVDA", "RELIANCE.NS", "TCS.NS"])
        self.client.get(f"/api/v4/financials/{symbol}", name="/api/v4/financials/[symbol]")

    @task(2)
    def market_overview(self):
        self.client.get("/api/v4/market-overview", name="/api/v4/market-overview")

    @task(2)
    def watchlist(self):
        symbols = ",".join(random.sample(SYMBOLS, 5))
        self.client.get(
            f"/api/v4/watchlist?symbols={symbols}",
            headers=self._auth_headers(),
            name="/api/v4/watchlist",
        )

    @task(1)
    def screener(self):
        self.client.get("/api/screener/universe", name="/api/screener/universe")

    @task(1)
    def health_check(self):
        self.client.get("/api/v4/health", name="/api/v4/health")


# ------------------------------------------------------------------
# End-of-run summary printed to terminal
# ------------------------------------------------------------------

@events.quitting.add_listener
def print_summary(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    print("\n" + "=" * 60)
    print("  AITraderIQ Load Test — Summary")
    print("=" * 60)
    print(f"  Total requests : {total.num_requests}")
    print(f"  Failures       : {total.num_failures}")
    print(f"  Avg resp time  : {total.avg_response_time:.0f} ms")
    print(f"  95th pct       : {total.get_response_time_percentile(0.95):.0f} ms")
    fail_rate = (total.num_failures / total.num_requests * 100) if total.num_requests else 0
    status = "✅ PASS" if fail_rate < 1 and total.avg_response_time < 2000 else "❌ FAIL"
    print(f"\n  Result: {status}  (fail rate {fail_rate:.1f}%, avg {total.avg_response_time:.0f}ms)")
    print("=" * 60)
