"""
Day 1 — NSE Live Data Tests
============================
Tests for NSE (.NS) quote, history, screener, and currency correctness.
All tests run in DEMO_MODE=true so no external API calls are made.
"""

import pytest
from httpx import AsyncClient


# ── Helpers ─────────────────────────────────────────────────────────────────

NSE_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS"]
NSE_BASE_PRICES = {  # rough ranges — demo prices should be in ₹ order of magnitude
    "RELIANCE.NS": (500, 4000),
    "TCS.NS": (1000, 8000),
    "HDFCBANK.NS": (500, 4000),
    "INFY.NS": (500, 4000),
    "SBIN.NS": (100, 2000),
}


# ── 1. Quote endpoint returns 200 for NSE symbols ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", NSE_SYMBOLS)
async def test_nse_quote_returns_200(client: AsyncClient, symbol: str):
    resp = await client.get(f"/api/v4/quote/{symbol}")
    assert resp.status_code == 200, f"{symbol}: {resp.text}"


# ── 2. NSE quote schema has required fields ──────────────────────────────────

@pytest.mark.asyncio
async def test_nse_quote_schema(client: AsyncClient):
    resp = await client.get("/api/v4/quote/RELIANCE.NS")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("symbol", "price", "currency"):
        assert field in data, f"Missing field: {field}"


# ── 3. NSE quote currency is ₹ ──────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", NSE_SYMBOLS)
async def test_nse_quote_currency_is_rupee(client: AsyncClient, symbol: str):
    resp = await client.get(f"/api/v4/quote/{symbol}")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("currency") == "₹", (
        f"{symbol} currency should be ₹, got '{data.get('currency')}'"
    )


# ── 4. NSE price is in ₹ range (not single-digit dollars) ───────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol,price_range", NSE_BASE_PRICES.items())
async def test_nse_price_in_rupee_range(client: AsyncClient, symbol: str, price_range: tuple):
    lo, hi = price_range
    resp = await client.get(f"/api/v4/quote/{symbol}")
    assert resp.status_code == 200
    price = resp.json().get("price", 0)
    assert lo <= price <= hi, (
        f"{symbol} price ₹{price} outside expected range ₹{lo}–₹{hi} "
        f"(likely returning USD value)"
    )


# ── 5. NSE symbol with & (M&M) validates correctly ──────────────────────────

@pytest.mark.asyncio
async def test_mnm_symbol_validates(client: AsyncClient):
    resp = await client.get("/api/v4/quote/M%26M.NS")
    assert resp.status_code == 200, f"M&M.NS returned {resp.status_code}: {resp.text}"


# ── 6. Invalid NSE symbol returns 400 ───────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_symbol_returns_400(client: AsyncClient):
    resp = await client.get("/api/v4/quote/../../../../etc/passwd")
    assert resp.status_code in (400, 404, 422)


# ── 7. NSE history returns OHLCV candles ────────────────────────────────────

@pytest.mark.asyncio
async def test_nse_history_returns_candles(client: AsyncClient):
    resp = await client.get("/api/v4/history/RELIANCE.NS?interval=1d&period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    candles = data if isinstance(data, list) else data.get("candles", data.get("data", []))
    assert len(candles) > 0, "History should return at least one candle"
    first = candles[0]
    for field in ("open", "high", "low", "close"):
        assert field in first, f"Candle missing field: {field}"


# ── 8. Top-movers for INDIA returns NSE symbols ──────────────────────────────

@pytest.mark.asyncio
async def test_india_top_movers_returns_nse_symbols(client: AsyncClient):
    resp = await client.get("/api/v4/top-movers/INDIA?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    all_symbols = [
        m.get("ticker", m.get("symbol", ""))
        for m in (data.get("gainers", []) + data.get("losers", []) + data.get("movers", []))
    ]
    nse_count = sum(1 for s in all_symbols if ".NS" in s)
    assert nse_count > 0, f"Expected NSE symbols in India movers, got: {all_symbols}"


# ── 9. Screener universe includes India category ─────────────────────────────

@pytest.mark.asyncio
async def test_screener_universe_has_india(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    # API returns {categories: [...], all: [{...category field...}]}
    categories = data.get("categories", [])
    assert "India" in categories, f"Missing 'India' in categories: {categories}"


# ── 10. India screener category contains .NS symbols ────────────────────────

@pytest.mark.asyncio
async def test_india_screener_contains_nse_stocks(client: AsyncClient):
    resp = await client.get("/api/screener/universe")
    assert resp.status_code == 200
    data = resp.json()
    all_stocks = data.get("all", [])
    india = [s for s in all_stocks if s.get("category") == "India"]
    nse = [s for s in india if ".NS" in s.get("symbol", "")]
    assert len(nse) >= 10, f"Expected ≥10 NSE stocks in India category, got {len(nse)}"


# ── 11. Signals endpoint works for NSE symbol ────────────────────────────────

@pytest.mark.asyncio
async def test_nse_signals(client: AsyncClient):
    resp = await client.get("/api/v4/signals/TCS.NS")
    assert resp.status_code == 200
    data = resp.json()
    assert "signal" in data or "rsi" in data or "signals" in data


# ── 12. Nifty 50 scanner returns Indian stocks ───────────────────────────────

@pytest.mark.asyncio
async def test_nifty50_scanner_returns_nse_stocks(client: AsyncClient):
    resp = await client.get("/api/scanner/nifty50?top_n=5&market=NSE")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    picks = data.get("top_picks", [])
    assert len(picks) > 0, "Scanner returned no picks"
    nse_picks = [p for p in picks if ".NS" in p.get("symbol", "")]
    assert len(nse_picks) > 0, f"Expected .NS symbols in Nifty picks, got: {[p['symbol'] for p in picks]}"
