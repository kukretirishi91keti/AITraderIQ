"""
Day 5 — Screener + Scanner Tests
==================================
Tests for the NSE/BSE screener universe and Nifty/Sensex scanner.
Validates category correctness, RSI signals, and scanner scoring.
"""

import pytest
from httpx import AsyncClient


# ── 1. Screener universe returns 200 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_screener_universe_ok(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 5, "Expected multiple market categories"


# ── 2. India NSE category has ≥ 50 stocks ────────────────────────────────────

@pytest.mark.asyncio
async def test_india_nse_category_size(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    data = resp.json()
    # API: {categories:[...], all:[{symbol,category,...}]}
    all_stocks = data.get("all", [])
    india = [s for s in all_stocks if s.get("category") == "India"]
    assert len(india) >= 50, f"Expected ≥50 Nifty stocks, got {len(india)}"


# ── 3. India BSE category has ≥ 30 stocks ────────────────────────────────────

@pytest.mark.asyncio
async def test_india_bse_category_size(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    data = resp.json()
    all_stocks = data.get("all", [])
    bse = [s for s in all_stocks if s.get("category") == "India_BSE"]
    assert len(bse) >= 30, f"Expected ≥30 Sensex stocks, got {len(bse)}"


# ── 4. Each India NSE stock has required fields ───────────────────────────────

@pytest.mark.asyncio
async def test_india_nse_stock_fields(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    data = resp.json()
    all_stocks = data.get("all", [])
    india = [s for s in all_stocks if s.get("category") == "India"]
    assert india, "India category is empty"
    for item in india[:5]:
        assert "symbol" in item, f"Missing symbol in: {item}"
        assert "price" in item or "rsi" in item, f"Missing price/rsi in: {item}"


# ── 5. Each India_BSE stock has .BO suffix ───────────────────────────────────

@pytest.mark.asyncio
async def test_india_bse_stocks_have_bo_suffix(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    data = resp.json()
    all_stocks = data.get("all", [])
    bse = [s for s in all_stocks if s.get("category") == "India_BSE"]
    for item in bse:
        sym = item.get("symbol", "")
        assert ".BO" in sym, f"BSE stock {sym} should have .BO suffix"


# ── 6. All RSI values in universe are 0–100 ───────────────────────────────────

@pytest.mark.asyncio
async def test_screener_rsi_values_in_range(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    all_stocks = data.get("all", [])
    rsi_stocks = [s for s in all_stocks if s.get("rsi") is not None]
    assert len(rsi_stocks) > 0, "No stocks with RSI data found"
    for s in rsi_stocks[:20]:
        assert 0 <= s["rsi"] <= 100, f"RSI {s['rsi']} out of range for {s.get('symbol')}"


# ── 7. Nifty 50 scanner (NSE) — basic response ───────────────────────────────

@pytest.mark.asyncio
async def test_nifty50_scanner_basic(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=10&market=NSE")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert "top_picks" in data
    assert "market_bias" in data
    assert data["market_bias"] in ("BULLISH", "BEARISH", "NEUTRAL")


# ── 8. Sensex 30 scanner (BSE) — basic response ──────────────────────────────

@pytest.mark.asyncio
async def test_sensex_scanner_basic(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=10&market=BSE")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    picks = data.get("top_picks", [])
    assert len(picks) > 0


# ── 9. Scanner picks have AI score between 0 and 100 ─────────────────────────

@pytest.mark.asyncio
async def test_scanner_ai_scores_in_range(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=20&market=NSE")
    data = resp.json()
    for pick in data.get("top_picks", []):
        score = pick.get("ai_score", 0)
        assert 0 <= score <= 100, f"AI score {score} out of range for {pick.get('symbol')}"


# ── 10. Scanner rank is sequential ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_scanner_ranks_sequential(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=10&market=NSE")
    picks = resp.json().get("top_picks", [])
    ranks = [p.get("rank", 0) for p in picks]
    assert ranks == list(range(1, len(ranks) + 1)), f"Ranks not sequential: {ranks}"


# ── 11. Scanner trader_type parameter works ───────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("style", ["Day", "Swing", "Position", "Scalper"])
async def test_scanner_trader_types(client: AsyncClient, style: str):
    resp = await client.get(f"/api/scanner/nifty50?trader_type={style}&top_n=5&market=NSE")
    assert resp.status_code == 200, f"trader_type={style} failed: {resp.text}"


# ── 12. Session field is a known value ───────────────────────────────────────

@pytest.mark.asyncio
async def test_scanner_session_field(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?market=NSE")
    data = resp.json()
    assert data.get("session") in (
        "OPEN", "PRE_OPEN", "PRE_MARKET", "CLOSED", "CLOSED_WEEKEND"
    ), f"Unknown session value: '{data.get('session')}'"
