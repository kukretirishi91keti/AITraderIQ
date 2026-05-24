"""
Day 4 — Auth + Indian User Journey
=====================================
Register → Login → Place NSE trade → View watchlist → Close trade.
Tests the full flow an Indian day-trader would use.
"""

import pytest
from httpx import AsyncClient


# ── 1. Register a new user ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "daytrader@test.com",
        "username": "daytrader1",
        "password": "Nifty50@2025",
        "trader_style": "day",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "daytrader1"


# ── 2. Login returns a valid token ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_token(client: AsyncClient):
    # Register first
    await client.post("/api/auth/register", json={
        "email": "login_test@test.com",
        "username": "logintest",
        "password": "Nifty50@2025",
        "trader_style": "swing",
    })
    # Login
    resp = await client.post("/api/auth/login", data={
        "username": "logintest",
        "password": "Nifty50@2025",
    })
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


# ── 3. Wrong password is rejected ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wrong_password_rejected(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "wrongpw@test.com",
        "username": "wrongpw",
        "password": "RealPass123!",
        "trader_style": "day",
    })
    resp = await client.post("/api/auth/login", data={
        "username": "wrongpw",
        "password": "WrongPass999!",
    })
    assert resp.status_code in (400, 401)


# ── 4. Protected profile endpoint needs auth ─────────────────────────────────

@pytest.mark.asyncio
async def test_profile_requires_auth(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)


# ── 5. Full journey: Register → place NSE trade → view it ────────────────────

@pytest.mark.asyncio
async def test_full_nse_journey(client: AsyncClient):
    # Register
    reg = await client.post("/api/auth/register", json={
        "email": "journey_nse@test.com",
        "username": "journey_nse",
        "password": "Sensex2025!",
        "trader_style": "day",
    })
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Place an NSE trade
    trade = await client.post(
        "/api/paper-trade",
        json={"symbol": "RELIANCE.NS", "side": "buy", "quantity": 5},
        headers=headers,
    )
    assert trade.status_code == 201
    assert trade.json()["currency"] == "₹"
    trade_id = trade.json()["id"]

    # View open trades
    list_resp = await client.get("/api/paper-trade?status=open", headers=headers)
    assert list_resp.status_code == 200
    trades = list_resp.json().get("trades", [])
    trade_ids = [t["id"] for t in trades]
    assert trade_id in trade_ids

    # Close the trade
    close = await client.post(f"/api/paper-trade/{trade_id}/close", headers=headers)
    assert close.status_code == 200

    # Check journal shows it
    journal = await client.get("/api/paper-trade/journal", headers=headers)
    assert journal.status_code == 200
    j_trades = journal.json().get("trades", [])
    assert any(t["id"] == trade_id for t in j_trades)


# ── 6. Full journey: Register → place BSE trade → close → journal ────────────

@pytest.mark.asyncio
async def test_full_bse_journey(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "journey_bse@test.com",
        "username": "journey_bse",
        "password": "BSE2025!pass",
        "trader_style": "day",
    })
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Place BSE trade
    trade = await client.post(
        "/api/paper-trade",
        json={"symbol": "TCS.BO", "side": "buy", "quantity": 2},
        headers=headers,
    )
    assert trade.status_code == 201
    assert trade.json()["currency"] == "₹", "BSE trade must be in ₹"
    trade_id = trade.json()["id"]

    # Close it
    close = await client.post(f"/api/paper-trade/{trade_id}/close", headers=headers)
    assert close.status_code == 200

    # Journal
    journal = await client.get("/api/paper-trade/journal", headers=headers)
    assert journal.status_code == 200
    metrics = journal.json().get("metrics", {})
    assert metrics.get("total_closed", 0) >= 1


# ── 7. Watchlist add/remove NSE symbol ───────────────────────────────────────

@pytest.mark.asyncio
async def test_watchlist_nse(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={
        "email": "watchlist@test.com",
        "username": "watchlistuser",
        "password": "WatchPass123!",
        "trader_style": "swing",
    })
    assert reg.status_code == 201, reg.text
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Add NSE stock to watchlist
    add = await client.post(
        "/api/user/watchlist",
        json={"symbol": "HDFCBANK.NS"},
        headers=headers,
    )
    assert add.status_code in (200, 201), add.text

    # Get watchlist — response: {count: N, watchlist: [{symbol,...}]}
    wl = await client.get("/api/user/watchlist", headers=headers)
    assert wl.status_code == 200
    wl_data = wl.json()
    items = wl_data.get("watchlist", wl_data) if isinstance(wl_data, dict) else wl_data
    symbols = [item.get("symbol") for item in items]
    assert "HDFCBANK.NS" in symbols


# ── 8. Duplicate registration is rejected ────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_registration_rejected(client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "username": "dupuser",
        "password": "DupPass123!",
        "trader_style": "day",
    }
    r1 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/auth/register", json=payload)
    assert r2.status_code in (400, 409)


# ── 9. Expired token rejected ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient, expired_token: str):
    resp = await client.get(
        "/api/paper-trade",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code in (401, 403)
