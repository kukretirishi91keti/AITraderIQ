"""Tests for market data endpoints (DEMO_MODE=true)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 1. Quote – valid symbol returns 200 with "symbol" key
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_quote_valid_symbol(client: AsyncClient):
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert "symbol" in data


# ---------------------------------------------------------------------------
# 2. Quote – response schema contains expected keys
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_quote_response_schema(client: AsyncClient):
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "symbol" in data
    # Optional but common fields – verify at least one extra exists
    optional_keys = {"price", "change", "volume", "changesPercentage", "marketCap"}
    assert optional_keys & data.keys(), (
        f"Expected at least one of {optional_keys} in response, got keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 3. History – returns non-empty data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_history_returns_data(client: AsyncClient):
    resp = await client.get("/api/v4/history/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data, "History response should not be empty"


# ---------------------------------------------------------------------------
# 4. History – all interval variants work
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("interval", ["1d", "1h", "5m"])
async def test_history_intervals_all_work(client: AsyncClient, interval: str):
    resp = await client.get(f"/api/v4/history/AAPL?interval={interval}")
    assert resp.status_code == 200, (
        f"Interval '{interval}' returned {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 5. Candles endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_candles_endpoint(client: AsyncClient):
    resp = await client.get("/api/v4/candles/AAPL")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Financials – valid symbol returns non-empty dict
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_financials_valid(client: AsyncClient):
    resp = await client.get("/api/v4/financials/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 0, "Financials response should be a non-empty dict"


# ---------------------------------------------------------------------------
# 7. Batch quotes via POST
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_batch_quotes(client: AsyncClient):
    resp = await client.post(
        "/api/v4/quotes",
        json={"symbols": ["AAPL", "MSFT"]},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. Market overview
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_market_overview(client: AsyncClient):
    resp = await client.get("/api/v4/market-overview")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 9. Top movers – returns data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_top_movers(client: AsyncClient):
    resp = await client.get("/api/v4/top-movers/US")
    assert resp.status_code == 200
    data = resp.json()
    assert data, "Top movers response should contain data"


# ---------------------------------------------------------------------------
# 10. Demo mode guarantee – all core endpoints return 200
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_demo_mode_never_errors(client: AsyncClient):
    endpoints = [
        ("GET", "/api/v4/quote/AAPL"),
        ("GET", "/api/v4/history/AAPL"),
        ("GET", "/api/v4/signals/AAPL"),
        ("GET", "/api/v4/financials/AAPL"),
        ("GET", "/api/v4/market-overview"),
    ]
    for method, path in endpoints:
        resp = await client.request(method, path)
        assert resp.status_code == 200, (
            f"Demo mode: {method} {path} returned {resp.status_code} — "
            f"expected 200. Body: {resp.text[:300]}"
        )
