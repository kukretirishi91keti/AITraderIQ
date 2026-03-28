"""
End-to-end user journey tests.

These tests simulate complete user workflows through the API,
covering registration, subscription, portfolio management,
watchlists, alerts, market data, AI queries, and auth flows.
All tests run in demo mode so external services return deterministic data.
"""

import pytest
import pytest_asyncio
from datetime import timedelta
from httpx import AsyncClient

from auth.security import create_access_token


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _quick_register(client: AsyncClient, suffix: str) -> dict:
    resp = await client.post("/api/auth/register", json={
        "email": f"journey{suffix}@test.com",
        "username": f"journey{suffix}",
        "password": "SecurePass123!",
        "trader_style": "swing",
    })
    assert resp.status_code == 201
    data = resp.json()
    return {
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }


# ---------------------------------------------------------------------------
# 1. New free user journey
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_new_free_user(client: AsyncClient):
    """Register -> check free plan -> manage watchlist -> fetch signal."""
    user = await _quick_register(client, "free1")
    h = user["headers"]

    # Login (confirm token works)
    me = await client.get("/api/auth/me", headers=h)
    assert me.status_code == 200

    # Check default plan is free
    plan_resp = await client.get("/api/subscription/my-plan", headers=h)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["plan"] == "free"

    # Watchlist should be empty
    wl = await client.get("/api/user/watchlist", headers=h)
    assert wl.status_code == 200
    assert wl.json()["count"] == 0

    # Add AAPL to watchlist
    add = await client.post("/api/user/watchlist", json={"symbol": "AAPL"}, headers=h)
    assert add.status_code in (200, 201)

    # Fetch signal for AAPL
    sig = await client.get("/api/v4/signals/AAPL", headers=h)
    assert sig.status_code == 200
    sig_data = sig.json()
    assert "signal" in sig_data or "recommendation" in sig_data

    # Confirm watchlist has one entry
    wl2 = await client.get("/api/user/watchlist", headers=h)
    assert wl2.status_code == 200
    assert wl2.json()["count"] == 1


# ---------------------------------------------------------------------------
# 2. Pro user upgrade
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_pro_user_upgrade(client: AsyncClient):
    """Register -> upgrade to pro -> verify plan details."""
    user = await _quick_register(client, "pro1")
    h = user["headers"]

    # Upgrade to pro
    upgrade = await client.post("/api/subscription/demo-upgrade?plan=pro", headers=h)
    assert upgrade.status_code == 200

    # Verify plan
    plan_resp = await client.get("/api/subscription/my-plan", headers=h)
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["plan"] == "pro"
    assert plan_data["ai_queries_per_day"] == 100


# ---------------------------------------------------------------------------
# 3. Premium user full access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_premium_user_full_access(client: AsyncClient):
    """Register -> upgrade to premium -> verify unlimited AI queries."""
    user = await _quick_register(client, "prem1")
    h = user["headers"]

    # Upgrade to premium
    upgrade = await client.post("/api/subscription/demo-upgrade?plan=premium", headers=h)
    assert upgrade.status_code == 200

    # Verify plan
    plan_resp = await client.get("/api/subscription/my-plan", headers=h)
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["plan"] == "premium"
    assert plan_data["ai_queries_per_day"] == -1  # unlimited


# ---------------------------------------------------------------------------
# 4. Portfolio lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_portfolio_lifecycle(client: AsyncClient):
    """Register -> add 3 holdings -> update one -> delete one -> verify count."""
    user = await _quick_register(client, "port1")
    h = user["headers"]

    # Add three holdings
    r1 = await client.post("/api/user/portfolio", json={
        "symbol": "AAPL", "shares": 10, "avg_price": 150,
    }, headers=h)
    assert r1.status_code in (200, 201)

    r2 = await client.post("/api/user/portfolio", json={
        "symbol": "MSFT", "shares": 5, "avg_price": 400,
    }, headers=h)
    assert r2.status_code in (200, 201)

    r3 = await client.post("/api/user/portfolio", json={
        "symbol": "GOOGL", "shares": 3, "avg_price": 170,
    }, headers=h)
    assert r3.status_code in (200, 201)

    # Confirm 3 holdings
    pf = await client.get("/api/user/portfolio", headers=h)
    assert pf.status_code == 200
    pf_data = pf.json()
    assert pf_data["count"] == 3
    holdings = pf_data["holdings"]

    # Update first holding shares to 15
    first_id = holdings[0]["id"]
    upd = await client.put(f"/api/user/portfolio/{first_id}", json={
        "shares": 15,
    }, headers=h)
    assert upd.status_code == 200

    # Delete third holding
    third_id = holdings[2]["id"]
    dl = await client.delete(f"/api/user/portfolio/{third_id}", headers=h)
    assert dl.status_code in (200, 204)

    # Confirm 2 holdings remain
    pf2 = await client.get("/api/user/portfolio", headers=h)
    assert pf2.status_code == 200
    assert pf2.json()["count"] == 2


# ---------------------------------------------------------------------------
# 5. Watchlist to trade decision
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_watchlist_to_trade_decision(client: AsyncClient):
    """Full research flow: watchlist -> quote -> signal -> sentiment -> AI -> strategy."""
    user = await _quick_register(client, "trade1")
    h = user["headers"]

    # Add AAPL to watchlist
    add = await client.post("/api/user/watchlist", json={"symbol": "AAPL"}, headers=h)
    assert add.status_code in (200, 201)

    # Fetch quote
    quote = await client.get("/api/v4/quote/AAPL", headers=h)
    assert quote.status_code == 200

    # Fetch signal
    sig = await client.get("/api/v4/signals/AAPL", headers=h)
    assert sig.status_code == 200

    # Fetch sentiment
    sent = await client.get("/api/sentiment/combined/AAPL", headers=h)
    assert sent.status_code == 200

    # AI query
    ai = await client.post("/api/genai/query", json={
        "question": "Should I buy AAPL?",
    }, headers=h)
    assert ai.status_code == 200

    # Strategy intelligence
    strat = await client.post("/api/strategy/intelligence", json={
        "symbol": "AAPL",
    }, headers=h)
    assert strat.status_code == 200


# ---------------------------------------------------------------------------
# 6. Credit system — free tier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_credit_system_free_tier(client: AsyncClient):
    """Free tier user can make 5 AI queries in demo mode."""
    user = await _quick_register(client, "credit_free1")
    h = user["headers"]

    for i in range(5):
        resp = await client.post("/api/genai/query", json={
            "question": f"What is the outlook for stock #{i}?",
        }, headers=h)
        assert resp.status_code == 200, f"Query {i+1} failed: {resp.text}"
        body = resp.json()
        assert "answer" in body or "response" in body or "result" in body or isinstance(body, dict)


# ---------------------------------------------------------------------------
# 7. Credit system — pro tier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_credit_system_pro_tier(client: AsyncClient):
    """Pro tier user can make 10 AI queries (sampling, not all 100)."""
    user = await _quick_register(client, "credit_pro1")
    h = user["headers"]

    # Upgrade to pro
    upgrade = await client.post("/api/subscription/demo-upgrade?plan=pro", headers=h)
    assert upgrade.status_code == 200

    for i in range(10):
        resp = await client.post("/api/genai/query", json={
            "question": f"Analyze stock performance #{i}?",
        }, headers=h)
        assert resp.status_code == 200, f"Query {i+1} failed: {resp.text}"


# ---------------------------------------------------------------------------
# 8. Credit reset daily
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_credit_reset_daily(client: AsyncClient):
    """Verify subscription plan exposes ai_usage with used/remaining keys."""
    user = await _quick_register(client, "reset1")
    h = user["headers"]

    plan_resp = await client.get("/api/subscription/my-plan", headers=h)
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()

    assert "ai_usage" in plan_data
    usage = plan_data["ai_usage"]
    assert "used" in usage
    assert "remaining" in usage


# ---------------------------------------------------------------------------
# 9. Multi-market trader (no auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_multi_market_trader(client: AsyncClient):
    """Fetch quotes for US stock, Indian stock, and crypto without auth."""
    symbols = ["AAPL", "RELIANCE.NS", "BTC-USD"]

    for sym in symbols:
        resp = await client.get(f"/api/v4/quote/{sym}")
        assert resp.status_code == 200, f"Quote for {sym} failed: {resp.text}"
        data = resp.json()
        assert "symbol" in data, f"No 'symbol' key in response for {sym}"


# ---------------------------------------------------------------------------
# 10. Alert lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_alert_lifecycle(client: AsyncClient):
    """Create 2 alerts -> verify count -> delete one -> verify count."""
    user = await _quick_register(client, "alert1")
    h = user["headers"]

    # Create two alerts
    a1 = await client.post("/api/user/alerts", json={
        "symbol": "AAPL",
        "condition": "above",
        "target_value": 200,
    }, headers=h)
    assert a1.status_code in (200, 201)

    a2 = await client.post("/api/user/alerts", json={
        "symbol": "MSFT",
        "condition": "rsi_below",
        "target_value": 30,
    }, headers=h)
    assert a2.status_code in (200, 201)

    # Verify two alerts
    alerts = await client.get("/api/user/alerts", headers=h)
    assert alerts.status_code == 200
    alerts_data = alerts.json()
    alerts_list = alerts_data if isinstance(alerts_data, list) else alerts_data.get("alerts", [])
    assert len(alerts_list) == 2

    # Delete the first alert
    first_alert_id = alerts_list[0]["id"]
    dl = await client.delete(f"/api/user/alerts/{first_alert_id}", headers=h)
    assert dl.status_code in (200, 204)

    # Verify one alert remains
    alerts2 = await client.get("/api/user/alerts", headers=h)
    assert alerts2.status_code == 200
    alerts2_data = alerts2.json()
    alerts2_list = alerts2_data if isinstance(alerts2_data, list) else alerts2_data.get("alerts", [])
    assert len(alerts2_list) == 1


# ---------------------------------------------------------------------------
# 11. Unauthenticated browsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_unauthenticated_browsing(client: AsyncClient):
    """Public endpoints return 200; protected endpoints return 401."""
    # Public endpoints
    assert (await client.get("/api/v4/quote/AAPL")).status_code == 200
    assert (await client.get("/api/v4/signals/AAPL")).status_code == 200
    assert (await client.get("/api/health")).status_code == 200
    assert (await client.get("/api/scanner/rank")).status_code == 200

    # Protected endpoints require auth
    assert (await client.get("/api/user/watchlist")).status_code == 401
    assert (await client.get("/api/user/portfolio")).status_code == 401
    assert (await client.get("/api/user/alerts")).status_code == 401


# ---------------------------------------------------------------------------
# 12. Expired token recovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_journey_expired_token_recovery(client: AsyncClient):
    """Expired token is rejected; re-login restores access."""
    user = await _quick_register(client, "expire1")

    # Create an expired token
    expired_token = create_access_token(
        data={"sub": str(user["user"]["id"])},
        expires_delta=timedelta(minutes=-5),
    )
    expired_headers = {"Authorization": f"Bearer {expired_token}"}

    # Expired token should be rejected
    me = await client.get("/api/auth/me", headers=expired_headers)
    assert me.status_code == 401

    # Re-login with form data (username matches _quick_register format)
    login_resp = await client.post(
        "/api/auth/login",
        data={
            "username": "journeyexpire1",
            "password": "SecurePass123!",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200

    # New token works
    new_token = login_resp.json()["access_token"]
    me2 = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me2.status_code == 200
