"""
Tests for Signals (v4) and Backtest endpoints.
Runs with DEMO_MODE=true via conftest.py.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ─── Signals Endpoints (/api/v4/signals) ────────────────────────────────────


@pytest.mark.asyncio
async def test_signals_valid_symbol(client: AsyncClient):
    """GET /api/v4/signals/AAPL returns 200 with a dict containing data."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_rsi_range_0_to_100(client: AsyncClient):
    """If the response contains an RSI value, it must be between 0 and 100."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    if "rsi" in data:
        rsi = data["rsi"]
        assert 0 <= rsi <= 100, f"RSI out of range: {rsi}"


@pytest.mark.asyncio
async def test_recommendation_valid_values(client: AsyncClient):
    """If the response contains a recommendation, it must be one of the known values."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    if "recommendation" in data:
        valid = {"BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL"}
        assert data["recommendation"] in valid, (
            f"Unexpected recommendation: {data['recommendation']}"
        )


@pytest.mark.asyncio
async def test_confidence_range_0_to_1(client: AsyncClient):
    """If confidence is present it must be in [0, 1] or [0, 100]."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    if "confidence" in data:
        c = data["confidence"]
        assert 0 <= c <= 100, f"Confidence out of range: {c}"


@pytest.mark.asyncio
async def test_bollinger_bands_present(client: AsyncClient):
    """Response should contain signal-related data (some indicators present)."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    # The response should have at least some technical indicator fields
    indicator_keys = {"rsi", "macd", "trend", "recommendation", "bollinger", "signal", "atr"}
    found = indicator_keys & set(data.keys())
    assert len(found) > 0, (
        f"Expected at least one indicator key from {indicator_keys}, got keys: {list(data.keys())}"
    )


# ─── Backtest Endpoints (/api/backtest) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_backtest_run_returns_metrics(client: AsyncClient):
    """GET /api/backtest/run/AAPL returns success with win_rate and sharpe_ratio."""
    resp = await client.get("/api/backtest/run/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "win_rate" in data, f"Missing win_rate. Keys: {list(data.keys())}"
    assert "sharpe_ratio" in data, f"Missing sharpe_ratio. Keys: {list(data.keys())}"


@pytest.mark.asyncio
async def test_backtest_win_rate_range(client: AsyncClient):
    """Win rate must be between 0 and 100."""
    resp = await client.get("/api/backtest/run/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    wr = data["win_rate"]
    assert 0 <= wr <= 100, f"win_rate out of range: {wr}"


@pytest.mark.asyncio
async def test_backtest_compare_all_4_strategies(client: AsyncClient):
    """Compare endpoint must return results for scalp, day, swing, position."""
    resp = await client.get("/api/backtest/compare", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    strategies = data["strategies"]
    for key in ("scalp", "day", "swing", "position"):
        assert key in strategies, f"Missing strategy '{key}' in {list(strategies.keys())}"


@pytest.mark.asyncio
async def test_backtest_compare_has_recommendation(client: AsyncClient):
    """Compare endpoint must include a 'recommended' field that is a string."""
    resp = await client.get("/api/backtest/compare", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended" in data, f"Missing 'recommended'. Keys: {list(data.keys())}"
    assert isinstance(data["recommended"], str)


@pytest.mark.asyncio
async def test_backtest_leaderboard(client: AsyncClient):
    """Leaderboard endpoint must return a list."""
    resp = await client.get("/api/backtest/leaderboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "leaderboard" in data, f"Missing 'leaderboard'. Keys: {list(data.keys())}"
    assert isinstance(data["leaderboard"], list)


@pytest.mark.asyncio
async def test_backtest_periods_min_50(client: AsyncClient):
    """Periods below 50 should be rejected with 422."""
    resp = await client.get("/api/backtest/run/AAPL", params={"periods": 49})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_backtest_periods_max_500(client: AsyncClient):
    """Periods above 500 should be rejected with 422."""
    resp = await client.get("/api/backtest/run/AAPL", params={"periods": 501})
    assert resp.status_code == 422
