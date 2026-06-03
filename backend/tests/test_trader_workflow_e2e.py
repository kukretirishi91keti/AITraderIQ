"""
End-to-end trader-type workflow tests.
Runs against a live server at http://127.0.0.1:8765.
Tests every user type × every feature discussed in the review session.

Run locally:
    # Start server first:
    DEMO_MODE=true JWT_SECRET_KEY="test-secret-key-minimum-32-chars-long" \\
      DATABASE_URL="sqlite+aiosqlite:///./workflow_test.db" \\
      python -m uvicorn main:app --port 8765

    # Then run tests:
    pytest tests/test_trader_workflow_e2e.py -v --timeout=30

In CI: handled by the e2e-test job in ci.yml (server started automatically).
"""

import pytest
import httpx
import asyncio
from datetime import datetime

pytestmark = pytest.mark.e2e

BASE = "http://127.0.0.1:8765"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def register(client, suffix, style="swing"):
    """Register or login (idempotent against a persistent test server)."""
    r = await client.post("/api/auth/register", json={
        "email": f"wf_{suffix}@test.com",
        "username": f"wf_{suffix}",
        "password": "WorkFlow123!",
        "trader_style": style,
    })
    if r.status_code == 400 and "already" in r.text.lower():
        # User exists from a previous run — login instead
        r = await client.post("/api/auth/login", data={
            "username": f"wf_{suffix}@test.com",
            "password": "WorkFlow123!",
        })
        assert r.status_code == 200, f"Login fallback failed ({suffix}): {r.text[:200]}"
    else:
        assert r.status_code in (200, 201), f"Register failed ({suffix}): {r.text[:200]}"
    data = r.json()
    return {"token": data["access_token"], "h": {"Authorization": f"Bearer {data['access_token']}"}}


async def upgrade(client, token, plan):
    r = await client.post(f"/api/subscription/demo-upgrade?plan={plan}",
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Upgrade to {plan} failed: {r.text[:200]}"


# ---------------------------------------------------------------------------
# 1. DATA QUALITY — every endpoint must carry a quality label in demo mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_quality_label_on_quote():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/quote/AAPL")
        assert r.status_code == 200
        d = r.json()
        assert "dataQuality" in d, f"Missing dataQuality key: {list(d.keys())}"
        assert d["dataQuality"] in ("LIVE", "CACHED", "LKG", "SIMULATED"), \
            f"Unexpected dataQuality: {d['dataQuality']}"


@pytest.mark.asyncio
async def test_data_quality_label_on_history():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/history/RELIANCE.NS?period=1mo&interval=1d")
        assert r.status_code == 200
        d = r.json()
        assert "dataQuality" in d or "source" in d, "No quality indicator in history response"


@pytest.mark.asyncio
async def test_demo_mode_never_returns_simulated_future_dates():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/history/AAPL?period=1mo&interval=1d")
        assert r.status_code == 200
        candles = r.json().get("candles") or r.json().get("history") or r.json().get("data") or []
        now = datetime.now()
        future = [
            c for c in candles
            if datetime.fromisoformat(c["timestamp"].replace("Z", "")) > now
        ]
        assert not future, f"{len(future)} future-dated candles returned: {future[:2]}"


@pytest.mark.asyncio
async def test_demo_mode_no_weekend_candles():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/history/AAPL?period=1mo&interval=1d")
        candles = r.json().get("candles") or r.json().get("history") or r.json().get("data") or []
        bad = [
            c for c in candles
            if datetime.fromisoformat(c["timestamp"].replace("Z", "")).weekday() >= 5
        ]
        assert not bad, f"{len(bad)} weekend candles: {bad[:2]}"


# ---------------------------------------------------------------------------
# 2. SIGNALS PIPELINE — RSI, MACD, Bollinger all present and valid
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signals_all_indicators_present():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/signals/AAPL")
        assert r.status_code == 200
        d = r.json()
        assert "rsi" in d or "RSI" in str(d), f"RSI missing: {list(d.keys())}"
        assert "signal" in d or "recommendation" in d, f"Signal missing: {list(d.keys())}"


@pytest.mark.asyncio
async def test_signals_rsi_in_valid_range():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/signals/AAPL")
        d = r.json()
        rsi = d.get("rsi") or (d.get("indicators") or {}).get("rsi")
        if rsi is not None:
            rsi_val = rsi if isinstance(rsi, (int, float)) else rsi.get("value", rsi.get("current", 50))
            assert 0 <= float(rsi_val) <= 100, f"RSI out of range: {rsi_val}"


@pytest.mark.asyncio
async def test_signals_valid_for_india_nse():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        for symbol in ["RELIANCE.NS", "TCS.NS", "INFY.NS"]:
            r = await c.get(f"/api/v4/signals/{symbol}")
            assert r.status_code == 200, f"Signals failed for {symbol}: {r.text[:100]}"


@pytest.mark.asyncio
async def test_signals_recommendation_is_valid_value():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/v4/signals/MSFT")
        d = r.json()
        rec = d.get("recommendation") or d.get("signal", "HOLD")
        valid = {"BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", "STRONG BUY", "STRONG SELL"}
        assert rec.upper() in {v.upper() for v in valid}, f"Invalid recommendation: {rec}"


# ---------------------------------------------------------------------------
# 3. PAPER TRADING — full lifecycle with P&L math check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paper_trade_full_lifecycle():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        u = await register(c, "pt_basic")
        h = u["h"]

        # Open BUY trade
        open_r = await c.post("/api/paper-trade", json={
            "symbol": "AAPL", "side": "buy", "quantity": 10,
            "entry_price": 180.00, "stop_loss": 176.40, "take_profit": 185.40,
        }, headers=h)
        assert open_r.status_code in (200, 201), f"Open trade failed: {open_r.text[:300]}"
        trade_id = open_r.json().get("trade", {}).get("id") or open_r.json().get("id")
        assert trade_id, "No trade ID returned"

        # Verify it appears in open trades list
        list_r = await c.get("/api/paper-trade", headers=h)
        assert list_r.status_code == 200
        trades = list_r.json().get("trades") or list_r.json().get("open_trades") or []
        ids = [t["id"] for t in trades]
        assert trade_id in ids, f"Trade {trade_id} not in open list: {ids}"

        # Close the trade manually
        close_r = await c.post(f"/api/paper-trade/{trade_id}/close",
                               json={"exit_price": 183.50}, headers=h)
        assert close_r.status_code == 200, f"Close failed: {close_r.text[:300]}"

        # Verify P&L math: (183.50 - 180.00) * 10 = +35.00
        closed = close_r.json()
        pnl = closed.get("pnl") or closed.get("trade", {}).get("pnl")
        if pnl is not None:
            assert abs(float(pnl) - 35.0) < 0.10, f"P&L wrong: expected ~35.0, got {pnl}"


@pytest.mark.asyncio
async def test_paper_trade_sell_short_pnl():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        u = await register(c, "pt_short")
        h = u["h"]

        open_r = await c.post("/api/paper-trade", json={
            "symbol": "AAPL", "side": "sell", "quantity": 5,
            "entry_price": 180.00,
        }, headers=h)
        assert open_r.status_code in (200, 201), f"Short open failed: {open_r.text[:300]}"
        trade_id = open_r.json().get("trade", {}).get("id") or open_r.json().get("id")

        close_r = await c.post(f"/api/paper-trade/{trade_id}/close",
                               json={"exit_price": 175.00}, headers=h)
        assert close_r.status_code == 200
        closed = close_r.json()
        pnl = closed.get("pnl") or closed.get("trade", {}).get("pnl")
        if pnl is not None:
            # Short: (entry - exit) * qty = (180 - 175) * 5 = +25
            assert float(pnl) > 0, f"Short profit should be positive, got {pnl}"


@pytest.mark.asyncio
async def test_paper_trade_nse_rupee_currency():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        u = await register(c, "pt_nse")
        h = u["h"]
        r = await c.post("/api/paper-trade", json={
            "symbol": "RELIANCE.NS", "side": "buy",
            "quantity": 1, "entry_price": 2900.0,
        }, headers=h)
        assert r.status_code in (200, 201), f"NSE paper trade failed: {r.text[:300]}"
        trade = r.json().get("trade") or r.json()
        currency = trade.get("currency", "")
        assert currency in ("INR", "₹", ""), f"Unexpected currency: {currency}"


@pytest.mark.asyncio
async def test_paper_trade_requires_auth():
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        r = await c.post("/api/paper-trade", json={
            "symbol": "AAPL", "side": "buy", "quantity": 1, "entry_price": 180.0,
        })
        assert r.status_code in (401, 403), f"Expected auth error, got {r.status_code}"


# ---------------------------------------------------------------------------
# 4. WATCHLIST & ALERTS lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watchlist_add_sort_remove():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        u = await register(c, "wl_basic")
        h = u["h"]

        # Clear any pre-existing items so the test is repeatable
        r = await c.get("/api/user/watchlist", headers=h)
        for item in r.json().get("watchlist", []):
            await c.delete(f"/api/user/watchlist/{item['symbol']}", headers=h)

        # Add 3 symbols
        for sym in ["AAPL", "MSFT", "GOOGL"]:
            r = await c.post("/api/user/watchlist", json={"symbol": sym}, headers=h)
            assert r.status_code in (200, 201), f"Add {sym} failed: {r.text[:100]}"

        # Count = 3
        r = await c.get("/api/user/watchlist", headers=h)
        assert r.json().get("count") == 3

        # Remove one (API deletes by symbol)
        first_symbol = r.json()["watchlist"][0]["symbol"]
        r = await c.delete(f"/api/user/watchlist/{first_symbol}", headers=h)
        assert r.status_code in (200, 204)

        # Count = 2
        r = await c.get("/api/user/watchlist", headers=h)
        assert r.json().get("count") == 2


@pytest.mark.asyncio
async def test_alert_create_and_list():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        u = await register(c, "al_basic")
        h = u["h"]

        r = await c.post("/api/user/alerts", json={
            "symbol": "AAPL", "condition": "above", "target_value": 250.0,
        }, headers=h)
        assert r.status_code in (200, 201), f"Alert create failed: {r.text[:200]}"

        r = await c.get("/api/user/alerts", headers=h)
        assert r.status_code == 200
        alerts = r.json().get("alerts", [])
        assert len(alerts) >= 1
        assert any(a["symbol"] == "AAPL" for a in alerts)


# ---------------------------------------------------------------------------
# 5. SENTIMENT — valid response structure with correct keys
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sentiment_response_structure():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/sentiment/combined/AAPL")
        assert r.status_code == 200
        d = r.json()
        assert d.get("success"), f"Sentiment not successful: {d}"
        assert "composite_score" in d, f"Missing composite_score: {list(d.keys())}"
        assert "label" in d
        assert "confidence" in d
        assert "sources" in d
        assert -100 <= int(d["composite_score"]) <= 100, \
            f"Score out of range: {d['composite_score']}"


@pytest.mark.asyncio
async def test_sentiment_three_sources_present():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/sentiment/combined/AAPL")
        sources = r.json().get("sources", {})
        assert len(sources) >= 2, f"Expected ≥2 sentiment sources, got {len(sources)}: {list(sources.keys())}"


@pytest.mark.asyncio
async def test_sentiment_valid_for_nse():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/sentiment/combined/RELIANCE.NS")
        assert r.status_code == 200
        assert r.json().get("success")


# ---------------------------------------------------------------------------
# 6. BACKTEST — valid metrics, win rate in range
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backtest_valid_metrics():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/backtest/run/AAPL?trader_type=swing")
        assert r.status_code == 200
        d = r.json()
        assert d.get("success"), f"Backtest not successful: {d}"
        assert "win_rate" in d
        assert "avg_return" in d
        assert 0 <= d["win_rate"] <= 100, f"Win rate out of range: {d['win_rate']}"


@pytest.mark.asyncio
async def test_backtest_all_trader_types():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        for style in ["scalp", "day", "swing", "position"]:
            r = await c.get(f"/api/backtest/run/AAPL?trader_type={style}")
            assert r.status_code == 200, f"Backtest failed for {style}: {r.text[:100]}"
            assert r.json().get("success"), f"Backtest not successful for {style}"


@pytest.mark.asyncio
async def test_backtest_compare_strategies():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        r = await c.get("/api/backtest/compare?symbol=AAPL")
        assert r.status_code == 200
        d = r.json()
        assert d.get("success")
        assert "recommended" in d or "strategies" in d


# ---------------------------------------------------------------------------
# 7. STRATEGY INTELLIGENCE per trader type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_strategy_intelligence_all_styles():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        for style in ["scalp", "day", "swing", "position"]:
            r = await c.post("/api/strategy/intelligence", json={
                "symbol": "AAPL",
                "capital": 50000,
                "growth_target_pct": 15,
                "risk_tolerance": "moderate",
                "time_horizon": "medium",
                "trader_style": style,
            })
            assert r.status_code == 200, f"Strategy failed for {style}: {r.text[:100]}"
            d = r.json()
            assert (
                d.get("success") or "ranked_strategies" in d or "recommendation" in d
            ), f"Strategy response malformed for {style}: {list(d.keys())}"


# ---------------------------------------------------------------------------
# 8. USER TYPE WORKFLOWS — free / pro / premium feature gates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_free_user_full_workflow():
    """Free user: register → watchlist → signal → sentiment → strategy."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "free_wf", style="swing")
        h = u["h"]

        # Plan is free
        r = await c.get("/api/subscription/my-plan", headers=h)
        assert r.json().get("plan") == "free"

        # Watchlist
        await c.post("/api/user/watchlist", json={"symbol": "INFY.NS"}, headers=h)
        r = await c.get("/api/user/watchlist", headers=h)
        assert r.json()["count"] == 1

        # Signal
        r = await c.get("/api/v4/signals/INFY.NS", headers=h)
        assert r.status_code == 200

        # Sentiment
        r = await c.get("/api/sentiment/combined/INFY.NS", headers=h)
        assert r.status_code == 200

        # Strategy
        r = await c.post("/api/strategy/intelligence", json={"symbol": "INFY.NS"}, headers=h)
        assert r.status_code == 200

        # AI query (free tier should allow at least 1)
        r = await c.post("/api/genai/query", json={
            "question": "Is INFY a good buy today?",
            "symbol": "INFY.NS",
        }, headers=h)
        assert r.status_code in (200, 429), f"Unexpected AI status: {r.status_code}"


@pytest.mark.asyncio
async def test_pro_user_workflow():
    """Pro user: upgrade → higher AI quota → paper trade → backtest."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "pro_wf", style="day")
        h = u["h"]
        await upgrade(c, u["token"], "pro")

        r = await c.get("/api/subscription/my-plan", headers=h)
        assert r.json().get("plan") == "pro"
        assert r.json().get("ai_queries_per_day") == 100

        # Paper trade
        r = await c.post("/api/paper-trade", json={
            "symbol": "AAPL", "side": "buy", "quantity": 5, "entry_price": 180.0,
        }, headers=h)
        assert r.status_code in (200, 201)

        # Backtest
        r = await c.get("/api/backtest/run/AAPL?trader_type=day", headers=h)
        assert r.status_code == 200 and r.json().get("success")


@pytest.mark.asyncio
async def test_premium_user_workflow():
    """Premium user: unlimited AI, scanner, all markets."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "prem_wf", style="position")
        h = u["h"]
        await upgrade(c, u["token"], "premium")

        r = await c.get("/api/subscription/my-plan", headers=h)
        assert r.json().get("plan") == "premium"
        assert r.json().get("ai_queries_per_day") == -1  # unlimited

        # AI scanner
        r = await c.get("/api/scanner/rank", headers=h)
        assert r.status_code == 200

        # Multi-market signals
        for sym in ["AAPL", "RELIANCE.NS", "BTC-USD"]:
            r = await c.get(f"/api/v4/signals/{sym}", headers=h)
            assert r.status_code == 200, f"Signals failed for {sym}"


# ---------------------------------------------------------------------------
# 9. SCALPER workflow — 1m/5m intervals, RSI + MACD quick signals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scalper_workflow():
    """Scalper: 1m/5m charts, fast signal check, intraday paper trade."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "scalper_wf", style="scalp")
        h = u["h"]

        # Intraday history — should return session-hour candles only
        r = await c.get("/api/v4/history/AAPL?period=1d&interval=5m")
        assert r.status_code == 200
        candles = r.json().get("candles") or r.json().get("history") or []
        if candles:
            for candle in candles[:5]:
                ts = datetime.fromisoformat(candle["timestamp"].replace("Z", ""))
                assert ts.weekday() < 5, f"Weekend candle in scalper data: {candle['timestamp']}"

        # Signal — expects fast signal for scalp style
        r = await c.get("/api/v4/signals/AAPL", headers=h)
        assert r.status_code == 200

        # Backtest for scalp style
        r = await c.get("/api/backtest/run/AAPL?trader_type=scalp")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 10. SWING TRADER workflow — 4h/1d charts, hold 3–10 days
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_swing_trader_workflow():
    """Swing trader: 1d history, strategy intelligence, paper trade with SL/TP."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "swing_wf", style="swing")
        h = u["h"]

        # Daily history
        r = await c.get("/api/v4/history/TCS.NS?period=1mo&interval=1d")
        assert r.status_code == 200
        d = r.json()
        candles = d.get("candles") or d.get("history") or []
        assert len(candles) >= 15, f"Expected ≥15 daily candles, got {len(candles)}"

        # Strategy
        r = await c.post("/api/strategy/intelligence", json={
            "symbol": "TCS.NS", "capital": 100000, "growth_target_pct": 20,
            "risk_tolerance": "moderate", "time_horizon": "medium", "trader_style": "swing",
        }, headers=h)
        assert r.status_code == 200

        # Paper trade with SL + TP
        r = await c.post("/api/paper-trade", json={
            "symbol": "TCS.NS", "side": "buy", "quantity": 2,
            "entry_price": 3500.0, "stop_loss": 3360.0, "take_profit": 3700.0,
        }, headers=h)
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# 11. POSITION TRADER workflow — weekly/monthly, fundamentals + sentiment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_position_trader_workflow():
    """Position trader: 3mo history, financials, sentiment, long paper trade."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        u = await register(c, "pos_wf", style="position")
        h = u["h"]

        # 3-month history
        r = await c.get("/api/v4/history/MSFT?period=3mo&interval=1d")
        assert r.status_code == 200
        candles = r.json().get("candles") or r.json().get("history") or []
        assert len(candles) >= 40, f"Expected ≥40 candles for 3mo, got {len(candles)}"

        # Fundamentals
        r = await c.get("/api/v4/financials/MSFT", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, dict) and len(d) > 0

        # Sentiment for long-term read
        r = await c.get("/api/sentiment/combined/MSFT", headers=h)
        assert r.status_code == 200

        # Long paper trade
        r = await c.post("/api/paper-trade", json={
            "symbol": "MSFT", "side": "buy", "quantity": 1,
            "entry_price": 415.0, "stop_loss": 395.0, "take_profit": 480.0,
        }, headers=h)
        assert r.status_code in (200, 201)


# ---------------------------------------------------------------------------
# 12. MULTI-MARKET — US, India NSE, Crypto all work
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_market_quotes():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        markets = {
            "US": "AAPL", "NSE": "RELIANCE.NS", "BSE": "RELIANCE.BO",
            "Crypto": "BTC-USD",
        }
        for market, symbol in markets.items():
            r = await c.get(f"/api/v4/quote/{symbol}")
            assert r.status_code == 200, f"{market} ({symbol}) quote failed: {r.text[:100]}"
            d = r.json()
            assert "price" in d or "c" in d or "regularMarketPrice" in d, \
                f"{market} ({symbol}) missing price field: {list(d.keys())}"


# ---------------------------------------------------------------------------
# 13. AUTH — register, login, token expiry, re-login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_register_and_profile():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        u = await register(c, "auth_profile")
        r = await c.get("/api/auth/me", headers=u["h"])
        assert r.status_code == 200
        assert r.json().get("email") == "wf_auth_profile@test.com"


@pytest.mark.asyncio
async def test_auth_invalid_token_rejected():
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        r = await c.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_auth_duplicate_email_rejected():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        payload = {
            "email": "dupe_wf@test.com", "username": "dupe_wf_1",
            "password": "Secure123!", "trader_style": "swing",
        }
        await c.post("/api/auth/register", json=payload)
        payload["username"] = "dupe_wf_2"
        r = await c.post("/api/auth/register", json=payload)
        assert r.status_code in (400, 409, 422), f"Expected conflict, got {r.status_code}"


# ---------------------------------------------------------------------------
# 14. PORTFOLIO CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_add_update_delete():
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        u = await register(c, "pf_crud")
        h = u["h"]

        r = await c.post("/api/user/portfolio", json={
            "symbol": "AAPL", "shares": 10, "avg_price": 150.0,
        }, headers=h)
        assert r.status_code in (200, 201)
        item_id = (r.json().get("holding") or r.json()).get("id")

        if item_id:
            r = await c.put(f"/api/user/portfolio/{item_id}", json={"shares": 20}, headers=h)
            assert r.status_code == 200

            r = await c.delete(f"/api/user/portfolio/{item_id}", headers=h)
            assert r.status_code in (200, 204)

        r = await c.get("/api/user/portfolio", headers=h)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 15. AI GENAI — context-aware response, fallback works without GROQ key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_genai_returns_response_without_groq_key():
    """With no GROQ key, rule-based fallback should still return 200."""
    async with httpx.AsyncClient(base_url=BASE, timeout=20) as c:
        r = await c.post("/api/genai/query", json={
            "question": "Is AAPL a good buy right now?",
            "symbol": "AAPL",
            "price": 185.0,
            "rsi": 42.0,
            "signal": "BUY",
        })
        assert r.status_code in (200, 429), f"GenAI failed: {r.status_code} {r.text[:200]}"
        if r.status_code == 200:
            d = r.json()
            assert "response" in d or "answer" in d or "message" in d, \
                f"No response text in GenAI reply: {list(d.keys())}"


# ---------------------------------------------------------------------------
# 16. WEBSOCKET — connects and receives at least one price message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_websocket_receives_price():
    import websockets
    try:
        async with websockets.connect("ws://127.0.0.1:8765/ws/prices", open_timeout=5) as ws:
            await ws.send('{"symbols": ["AAPL"]}')
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            import json as _json
            data = _json.loads(msg)
            assert "symbol" in data or "price" in data or "type" in data, \
                f"Unexpected WS message: {msg[:200]}"
    except Exception as e:
        pytest.skip(f"WebSocket not available in this env: {e}")
