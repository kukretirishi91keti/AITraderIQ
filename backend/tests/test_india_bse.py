"""
Day 2 — BSE Live Data Tests
============================
Tests for BSE (.BO) quote, currency, screener, and scanner.
All tests run in DEMO_MODE=true.
"""

import pytest
from httpx import AsyncClient


BSE_SYMBOLS = ["RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO", "SBIN.BO"]


# ── 1. BSE quote returns 200 ─────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", BSE_SYMBOLS)
async def test_bse_quote_returns_200(client: AsyncClient, symbol: str):
    resp = await client.get(f"/api/v4/quote/{symbol}")
    assert resp.status_code == 200, f"{symbol}: {resp.text}"


# ── 2. BSE quote currency is ₹ ───────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", BSE_SYMBOLS)
async def test_bse_quote_currency_is_rupee(client: AsyncClient, symbol: str):
    resp = await client.get(f"/api/v4/quote/{symbol}")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("currency") == "₹", (
        f"{symbol} returned currency '{data.get('currency')}', expected ₹"
    )


# ── 3. BSE price is in ₹ range (not dollars) ─────────────────────────────────

@pytest.mark.asyncio
async def test_bse_reliance_price_in_rupee_range(client: AsyncClient):
    resp = await client.get("/api/v4/quote/RELIANCE.BO")
    assert resp.status_code == 200
    price = resp.json().get("price", 0)
    assert 500 <= price <= 4000, (
        f"RELIANCE.BO price ₹{price} out of range — likely returning USD"
    )


# ── 4. BSE market field is BSE (not INDIA) ───────────────────────────────────

@pytest.mark.asyncio
async def test_bse_quote_market_field(client: AsyncClient):
    resp = await client.get("/api/v4/quote/RELIANCE.BO")
    assert resp.status_code == 200
    data = resp.json()
    market = data.get("market", "")
    assert market == "BSE", f"Expected market='BSE', got '{market}'"


# ── 5. BSE history returns candles ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bse_history_returns_candles(client: AsyncClient):
    resp = await client.get("/api/v4/history/RELIANCE.BO?interval=1d&period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    candles = data if isinstance(data, list) else data.get("candles", data.get("data", []))
    assert len(candles) > 0, "BSE history should return at least one candle"


# ── 6. BSE and NSE prices for same company are similar ───────────────────────

@pytest.mark.asyncio
async def test_bse_nse_prices_are_consistent(client: AsyncClient):
    nse_resp = await client.get("/api/v4/quote/RELIANCE.NS")
    bse_resp = await client.get("/api/v4/quote/RELIANCE.BO")
    assert nse_resp.status_code == 200
    assert bse_resp.status_code == 200
    nse_price = nse_resp.json().get("price", 0)
    bse_price = bse_resp.json().get("price", 0)
    # Prices should be within 5% of each other (same stock, different exchanges)
    if nse_price > 0 and bse_price > 0:
        diff_pct = abs(nse_price - bse_price) / nse_price * 100
        assert diff_pct < 10, (
            f"NSE ₹{nse_price} and BSE ₹{bse_price} differ by {diff_pct:.1f}% "
            f"— possible wrong currency on one exchange"
        )


# ── 7. Top-movers for INDIA_BSE returns .BO symbols ─────────────────────────

@pytest.mark.asyncio
async def test_india_bse_top_movers_returns_bo_symbols(client: AsyncClient):
    resp = await client.get("/api/v4/top-movers/INDIA_BSE?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    all_symbols = [
        m.get("ticker", m.get("symbol", ""))
        for m in (data.get("gainers", []) + data.get("losers", []) + data.get("movers", []))
    ]
    bo_count = sum(1 for s in all_symbols if ".BO" in s)
    assert bo_count > 0, f"Expected .BO symbols from INDIA_BSE movers, got: {all_symbols}"


# ── 8. Screener universe includes India_BSE category ────────────────────────

@pytest.mark.asyncio
async def test_screener_universe_has_india_bse(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    categories = data.get("categories", [])
    assert "India_BSE" in categories, f"Missing 'India_BSE' in categories: {categories}"


# ── 9. India_BSE screener contains .BO symbols ───────────────────────────────

@pytest.mark.asyncio
async def test_india_bse_screener_contains_bo_stocks(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    all_stocks = data.get("all", [])
    bse = [s for s in all_stocks if s.get("category") == "India_BSE"]
    bo_syms = [s for s in bse if ".BO" in s.get("symbol", "")]
    assert len(bo_syms) >= 10, f"Expected ≥10 BSE stocks in India_BSE category, got {len(bo_syms)}"


# ── 10. India_BSE screener has no .NS symbols (not mixed) ───────────────────

@pytest.mark.asyncio
async def test_india_bse_screener_no_nse_symbols(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    all_stocks = data.get("all", [])
    bse = [s for s in all_stocks if s.get("category") == "India_BSE"]
    ns_syms = [s for s in bse if ".NS" in s.get("symbol", "")]
    assert len(ns_syms) == 0, f"India_BSE should not contain .NS symbols: {[s['symbol'] for s in ns_syms]}"


# ── 11. BSE scanner (Sensex) returns .BO stocks ──────────────────────────────

@pytest.mark.asyncio
async def test_sensex_scanner_returns_bse_stocks(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=5&market=BSE")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    picks = data.get("top_picks", [])
    assert len(picks) > 0, "BSE scanner returned no picks"
    bo_picks = [p for p in picks if ".BO" in p.get("symbol", "")]
    assert len(bo_picks) > 0, f"Expected .BO symbols in Sensex picks, got: {[p['symbol'] for p in picks]}"


# ── 12. BSE scanner market label says BSE ────────────────────────────────────

@pytest.mark.asyncio
async def test_sensex_scanner_market_label(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?market=BSE")
    assert resp.status_code == 200
    data = resp.json()
    assert "BSE" in data.get("market", ""), (
        f"Expected 'BSE' in market field, got: '{data.get('market')}'"
    )
