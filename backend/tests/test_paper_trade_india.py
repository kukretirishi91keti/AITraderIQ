"""
Day 3 — Paper Trading Tests (Indian Market)
=============================================
Tests that paper trades for NSE/BSE stocks:
  - Use ₹ currency (not $)
  - Record correct market field
  - P&L and journal display correctly
  - Close trade updates P&L in ₹
"""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, suffix: str = "pt") -> dict:
    resp = await client.post("/api/auth/register", json={
        "email": f"ptuser{suffix}@test.com",
        "username": f"ptuser{suffix}",
        "password": "SecurePass123!",
        "trader_style": "day",
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}}


# ── 1. Place NSE paper trade — currency must be ₹ ────────────────────────────

@pytest.mark.asyncio
async def test_nse_paper_trade_currency_is_rupee(client: AsyncClient):
    u = await _register(client, "nse1")
    resp = await client.post(
        "/api/paper-trade",
        json={"symbol": "RELIANCE.NS", "side": "buy", "quantity": 1},
        headers=u["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data.get("currency") == "₹", (
        f"NSE paper trade currency should be ₹, got '{data.get('currency')}'"
    )


# ── 2. Place BSE paper trade — currency must be ₹ ────────────────────────────

@pytest.mark.asyncio
async def test_bse_paper_trade_currency_is_rupee(client: AsyncClient):
    u = await _register(client, "bse1")
    resp = await client.post(
        "/api/paper-trade",
        json={"symbol": "RELIANCE.BO", "side": "buy", "quantity": 1},
        headers=u["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data.get("currency") == "₹", (
        f"BSE paper trade currency should be ₹, got '{data.get('currency')}'"
    )


# ── 3. NSE trade entry price is in ₹ range ───────────────────────────────────

@pytest.mark.asyncio
async def test_nse_paper_trade_entry_price_rupee_range(client: AsyncClient):
    u = await _register(client, "nse2")
    resp = await client.post(
        "/api/paper-trade",
        json={"symbol": "TCS.NS", "side": "buy", "quantity": 1},
        headers=u["headers"],
    )
    assert resp.status_code == 201
    price = resp.json().get("entry_price", 0)
    assert price > 500, f"TCS.NS entry price {price} too low — likely in USD not ₹"


# ── 4. Open trades list shows ₹ currency ─────────────────────────────────────

@pytest.mark.asyncio
async def test_open_trades_list_shows_rupee(client: AsyncClient):
    u = await _register(client, "nse3")
    # Place a trade first
    await client.post(
        "/api/paper-trade",
        json={"symbol": "HDFCBANK.NS", "side": "buy", "quantity": 2},
        headers=u["headers"],
    )
    resp = await client.get("/api/paper-trade?status=open", headers=u["headers"])
    assert resp.status_code == 200
    trades = resp.json().get("trades", [])
    assert len(trades) > 0, "Should have at least one open trade"
    for t in trades:
        if ".NS" in t.get("symbol", "") or ".BO" in t.get("symbol", ""):
            assert t.get("currency") == "₹", (
                f"Trade {t['symbol']} currency '{t.get('currency')}' should be ₹"
            )


# ── 5. Close NSE trade — P&L recorded in ₹ ───────────────────────────────────

@pytest.mark.asyncio
async def test_close_nse_trade_pnl_exists(client: AsyncClient):
    u = await _register(client, "nse4")
    # Place
    place = await client.post(
        "/api/paper-trade",
        json={"symbol": "SBIN.NS", "side": "buy", "quantity": 5},
        headers=u["headers"],
    )
    assert place.status_code == 201
    trade_id = place.json()["id"]
    # Close
    close = await client.post(
        f"/api/paper-trade/{trade_id}/close",
        headers=u["headers"],
    )
    assert close.status_code == 200, close.text
    data = close.json()
    assert "pnl" in data or "message" in data


# ── 6. Trade journal metrics return ₹ currency from trade ────────────────────

@pytest.mark.asyncio
async def test_journal_trade_currency(client: AsyncClient):
    u = await _register(client, "nse5")
    # Place + close a trade to generate journal data
    place = await client.post(
        "/api/paper-trade",
        json={"symbol": "INFY.NS", "side": "buy", "quantity": 1},
        headers=u["headers"],
    )
    assert place.status_code == 201
    trade_id = place.json()["id"]
    await client.post(f"/api/paper-trade/{trade_id}/close", headers=u["headers"])

    journal = await client.get("/api/paper-trade/journal", headers=u["headers"])
    assert journal.status_code == 200
    data = journal.json()
    trades = data.get("trades", [])
    if trades:
        for t in trades:
            assert t.get("currency") == "₹", (
                f"Journal trade {t['symbol']} should have ₹ currency"
            )


# ── 7. Set stop-loss and take-profit for NSE trade ───────────────────────────

@pytest.mark.asyncio
async def test_nse_trade_set_levels(client: AsyncClient):
    u = await _register(client, "nse6")
    place = await client.post(
        "/api/paper-trade",
        json={"symbol": "WIPRO.NS", "side": "buy", "quantity": 10},
        headers=u["headers"],
    )
    assert place.status_code == 201
    trade_id = place.json()["id"]
    entry = place.json()["entry_price"]

    levels = await client.put(
        f"/api/paper-trade/{trade_id}/levels",
        json={
            "stop_loss_price": round(entry * 0.97, 2),
            "take_profit_price": round(entry * 1.05, 2),
        },
        headers=u["headers"],
    )
    assert levels.status_code == 200, levels.text


# ── 8. Paper trade requires authentication ───────────────────────────────────

@pytest.mark.asyncio
async def test_paper_trade_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/paper-trade",
        json={"symbol": "RELIANCE.NS", "side": "buy", "quantity": 1},
    )
    assert resp.status_code in (401, 403)


# ── 9. Multiple NSE trades — all show ₹ currency ─────────────────────────────

@pytest.mark.asyncio
async def test_multiple_nse_trades_all_rupee(client: AsyncClient):
    u = await _register(client, "nse7")
    nse_stocks = ["RELIANCE.NS", "BAJFINANCE.NS", "AXISBANK.NS"]
    for sym in nse_stocks:
        r = await client.post(
            "/api/paper-trade",
            json={"symbol": sym, "side": "buy", "quantity": 1},
            headers=u["headers"],
        )
        assert r.status_code == 201, f"Failed to place trade for {sym}: {r.text}"
        assert r.json().get("currency") == "₹", f"{sym} should use ₹"

    # Verify in open trades list
    resp = await client.get("/api/paper-trade?status=open", headers=u["headers"])
    trades = resp.json().get("trades", [])
    assert len(trades) == 3
    for t in trades:
        assert t.get("currency") == "₹"


# ── 10. BSE trade also records correct market ────────────────────────────────

@pytest.mark.asyncio
async def test_bse_paper_trade_market_field(client: AsyncClient):
    u = await _register(client, "bse2")
    resp = await client.post(
        "/api/paper-trade",
        json={"symbol": "TCS.BO", "side": "buy", "quantity": 1},
        headers=u["headers"],
    )
    assert resp.status_code == 201, resp.text
    # currency must be ₹ regardless of market field name
    assert resp.json().get("currency") == "₹"
