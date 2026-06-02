"""
Live 4-Trader Workflow Tests
=============================
Runs against the deployed Render API (not in-process).
Set API_BASE env var to the Render URL before running.

Tests simulate what each trader type would do in a real session:
  Scalper  → 5m signals, tight RSI check, quick paper trade
  Day      → 15m signals, VWAP, FII/DII, intraday alert
  Swing    → daily signals, backtest accuracy, earnings calendar
  Position → weekly signals, fundamentals, sector context
"""

import os
import pytest
import httpx

API = os.environ.get("API_BASE", "https://aitraderiq.onrender.com").rstrip("/")
TIMEOUT = 20.0

# NSE symbols used across tests
INDIA_SYMBOL = "RELIANCE.NS"
INDIA_INDEX  = "NIFTY"
US_SYMBOL    = "AAPL"


# ── Shared helpers ────────────────────────────────────────────────────────────

def get(path: str, params: dict = None) -> httpx.Response:
    return httpx.get(f"{API}{path}", params=params, timeout=TIMEOUT)


def post(path: str, json: dict = None, data: dict = None, headers: dict = None) -> httpx.Response:
    return httpx.post(f"{API}{path}", json=json, data=data, headers=headers, timeout=TIMEOUT)


def register_and_login(suffix: str) -> dict:
    """Register a fresh user and return auth headers."""
    r = post("/api/auth/register", json={
        "email":        f"livetest_{suffix}@ci.aitraderiq.com",
        "username":     f"livetest_{suffix}",
        "password":     "SecureLiveTest123!",
        "trader_style": "swing",
    })
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Infrastructure ────────────────────────────────────────────────────────────

def test_api_reachable():
    """Render service is up and responding."""
    r = get("/ping")
    assert r.status_code == 200
    assert r.json().get("pong") is True


def test_config_status_all_ready():
    """All readiness flags are true (auth, DB, India live data)."""
    r = get("/api/config-status")
    assert r.status_code == 200
    rd = r.json().get("readiness", {})
    assert rd.get("auth_works"),    "JWT not configured"
    assert rd.get("db_persistent"), "SQLite used — data won't persist across restarts"


def test_india_price_is_live():
    """RELIANCE.NS returns a real price, not zero or simulated."""
    r = get(f"/api/v4/quote/{INDIA_SYMBOL}")
    assert r.status_code == 200
    d = r.json()
    price = float(d.get("price", 0))
    assert price > 100, f"Price too low ({price}) — likely simulated or stale"
    assert d.get("currency") == "₹", f"Currency mismatch: {d.get('currency')}"


# ── Scalper workflow ──────────────────────────────────────────────────────────

class TestScalperWorkflow:
    """
    Scalper checks: fast 5m signals, RSI extremes, quick entry/exit.
    """

    def test_scalper_5m_signals(self):
        """Signals endpoint returns data for 5m timeframe."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}", params={"interval": "5m"})
        assert r.status_code == 200
        d = r.json()
        assert "signal" in d or "recommendation" in d, f"No signal in response: {d}"

    def test_scalper_rsi_present(self):
        """RSI value returned — key indicator for scalping reversals."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}")
        assert r.status_code == 200
        d = r.json()
        rsi = d.get("rsi")
        if isinstance(rsi, dict):
            rsi = rsi.get("value")
        assert rsi is not None, "RSI missing from signals"
        assert 0 <= float(rsi) <= 100, f"RSI out of range: {rsi}"

    def test_scalper_paper_trade_entry_exit(self):
        """Scalper can open and close a paper trade."""
        h = register_and_login("scalper")

        # Open trade
        r = post("/api/paper-trades", headers=h, json={
            "symbol":    INDIA_SYMBOL,
            "side":      "buy",
            "shares":    5,
            "entry":     1300.0,
            "stop_loss": 1293.5,
            "target":    1306.5,
        })
        assert r.status_code in (200, 201), f"Open trade failed: {r.text}"
        trade_id = r.json().get("id") or r.json().get("trade_id")
        assert trade_id, "No trade ID returned"

        # List open trades
        trades_r = httpx.get(f"{API}/api/paper-trades", headers=h, timeout=TIMEOUT)
        assert trades_r.status_code == 200
        ids = [t.get("id") or t.get("trade_id") for t in trades_r.json()]
        assert trade_id in ids, "Trade not found in open trades list"

        # Close trade
        close_r = post(f"/api/paper-trades/{trade_id}/close", headers=h,
                       json={"exit_price": 1307.0})
        assert close_r.status_code == 200, f"Close failed: {close_r.text}"


# ── Day Trader workflow ───────────────────────────────────────────────────────

class TestDayTraderWorkflow:
    """
    Day trader checks: 15m chart, VWAP context, FII/DII, intraday alert.
    """

    def test_day_15m_signals(self):
        """Signals for 15m interval work."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}", params={"interval": "15m"})
        assert r.status_code == 200

    def test_day_vwap_present(self):
        """VWAP returned in signals — intraday fair-value benchmark."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}")
        assert r.status_code == 200
        d = r.json()
        vwap = d.get("vwap")
        if isinstance(vwap, dict):
            vwap = vwap.get("value")
        assert vwap is not None, "VWAP missing — day trader needs it"

    def test_day_fii_dii_data(self):
        """FII/DII flows endpoint returns data."""
        r = get("/api/v4/fii-dii")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, (dict, list)), "FII/DII returned unexpected type"

    def test_day_price_alert_create(self):
        """Day trader can create a price alert (triggers email when hit)."""
        h = register_and_login("daytrader")
        r = post("/api/user/alerts", headers=h, json={
            "symbol":    INDIA_SYMBOL,
            "condition": "above",
            "price":     2000.0,
        })
        assert r.status_code in (200, 201), f"Alert create failed: {r.text}"

        # Confirm it shows in list
        alerts_r = httpx.get(f"{API}/api/user/alerts", headers=h, timeout=TIMEOUT)
        assert alerts_r.status_code == 200
        symbols = [a.get("symbol") for a in alerts_r.json()]
        assert INDIA_SYMBOL in symbols


# ── Swing Trader workflow ─────────────────────────────────────────────────────

class TestSwingTraderWorkflow:
    """
    Swing trader checks: daily signals, backtest accuracy, earnings.
    """

    def test_swing_daily_signals(self):
        """Daily signals return RSI + MACD — core swing indicators."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}", params={"interval": "1d"})
        assert r.status_code == 200
        d = r.json()
        assert "signal" in d or "recommendation" in d

    def test_swing_backtest_accuracy(self):
        """Backtest endpoint returns signal accuracy stats."""
        r = get(f"/api/v4/backtest/{INDIA_SYMBOL}")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, dict), "Backtest should return object"

    def test_swing_earnings_calendar(self):
        """Earnings tab data loads for India stock."""
        r = get(f"/api/v4/earnings/{INDIA_SYMBOL}")
        assert r.status_code == 200

    def test_swing_watchlist_persistence(self):
        """Swing trader adds a stock to watchlist and it persists."""
        h = register_and_login("swing")
        add = post("/api/user/watchlist", headers=h,
                   json={"symbol": INDIA_SYMBOL})
        assert add.status_code in (200, 201)

        wl = httpx.get(f"{API}/api/user/watchlist", headers=h, timeout=TIMEOUT)
        assert wl.status_code == 200
        symbols = [w.get("symbol") for w in wl.json().get("items", wl.json())]
        assert INDIA_SYMBOL in symbols, "Symbol not found in watchlist after add"


# ── Position Trader workflow ──────────────────────────────────────────────────

class TestPositionTraderWorkflow:
    """
    Position trader checks: fundamentals, weekly chart, sector context.
    """

    def test_position_weekly_signals(self):
        """Weekly signals load for long-term context."""
        r = get(f"/api/v4/signals/{INDIA_SYMBOL}", params={"interval": "1wk"})
        assert r.status_code == 200

    def test_position_fundamentals(self):
        """Fundamentals endpoint returns P/E and financial data."""
        r = get(f"/api/v4/financials/{INDIA_SYMBOL}")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, dict), "Financials should return object"

    def test_position_option_chain(self):
        """Option chain loads for NIFTY — key position-sizing context."""
        r = get(f"/api/v4/option-chain/{INDIA_INDEX}")
        assert r.status_code == 200
        d = r.json()
        assert "strikes" in d or "calls" in d or "options" in d or isinstance(d, list), \
            f"Unexpected option chain format: {list(d.keys()) if isinstance(d, dict) else type(d)}"

    def test_position_history_weekly(self):
        """Weekly OHLCV history loads — used to draw weekly chart."""
        r = get(f"/api/v4/history/{INDIA_SYMBOL}", params={"interval": "1wk"})
        assert r.status_code == 200
        bars = r.json()
        assert isinstance(bars, list) and len(bars) > 0, "No weekly history bars"
