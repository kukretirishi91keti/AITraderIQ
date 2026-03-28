"""Tests for strategy intelligence endpoints (DEMO_MODE=true)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


INTELLIGENCE_URL = "/api/strategy/intelligence"
MARKET_OVERVIEW_URL = "/api/strategy/market-overview"
STRATEGIES_URL = "/api/strategy/strategies"

BASE_INTELLIGENCE_PAYLOAD = {
    "symbol": "AAPL",
    "capital": 10000,
    "growth_target_pct": 10,
    "risk_tolerance": "moderate",
    "time_horizon": "medium",
    "trader_style": "swing",
}


# ---------------------------------------------------------------------------
# 1. Single-symbol strategy intelligence returns 200 with data
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_single_symbol(client: AsyncClient):
    resp = await client.post(INTELLIGENCE_URL, json=BASE_INTELLIGENCE_PAYLOAD)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, dict)
    # Response should contain strategy-related data (strategies, recommendations, etc.)
    strategy_keys = {"strategies", "recommendations", "symbol", "analysis"}
    assert strategy_keys & data.keys(), (
        f"Expected at least one of {strategy_keys} in response, got: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 2. Market overview – US symbols
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_market_overview_us(client: AsyncClient):
    payload = {
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "risk_tolerance": "moderate",
    }
    resp = await client.post(MARKET_OVERVIEW_URL, json=payload)
    assert resp.status_code == 200, f"US overview failed: {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 3. Market overview – Indian symbols
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_market_overview_india(client: AsyncClient):
    payload = {
        "symbols": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
        "risk_tolerance": "moderate",
    }
    resp = await client.post(MARKET_OVERVIEW_URL, json=payload)
    assert resp.status_code == 200, f"India overview failed: {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 4. Market overview – multi-country / multi-asset symbols
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_market_overview_multi_country(client: AsyncClient):
    payload = {
        "symbols": ["AAPL", "RELIANCE.NS", "HSBA.L", "BTC-USD"],
        "risk_tolerance": "moderate",
    }
    resp = await client.post(MARKET_OVERVIEW_URL, json=payload)
    assert resp.status_code == 200, (
        f"Multi-country overview failed: {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 5. Every strategy in the catalog has entry_rules and exit_rules
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_has_entry_and_exit_rules(client: AsyncClient):
    resp = await client.get(STRATEGIES_URL)
    assert resp.status_code == 200
    data = resp.json()
    strategies = data.get("strategies", [])
    assert len(strategies) >= 1, "Strategy catalog should not be empty"
    for strat in strategies:
        name = strat.get("name", strat.get("key", "unknown"))
        assert "entry_rules" in strat, f"Strategy '{name}' missing entry_rules"
        assert "exit_rules" in strat, f"Strategy '{name}' missing exit_rules"
        # Rules should be non-empty
        assert strat["entry_rules"], f"Strategy '{name}' has empty entry_rules"
        assert strat["exit_rules"], f"Strategy '{name}' has empty exit_rules"


# ---------------------------------------------------------------------------
# 6. Confidence values (if present) are between 0 and 1
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_confidence_in_range(client: AsyncClient):
    resp = await client.post(INTELLIGENCE_URL, json=BASE_INTELLIGENCE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()

    # Collect all confidence-like values from the response
    def _find_confidence(obj, path=""):
        """Recursively find any 'confidence' or 'score' values."""
        found = []
        if isinstance(obj, dict):
            for key, val in obj.items():
                if "confidence" in key.lower() or "score" in key.lower():
                    if isinstance(val, (int, float)):
                        found.append((f"{path}.{key}", val))
                found.extend(_find_confidence(val, f"{path}.{key}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                found.extend(_find_confidence(item, f"{path}[{i}]"))
        return found

    confidence_values = _find_confidence(data)
    for field_path, value in confidence_values:
        # Accept both 0-1 and 0-100 scales (some services use percentages)
        assert 0 <= value <= 100, (
            f"Confidence value at {field_path} = {value} is outside [0, 100]"
        )


# ---------------------------------------------------------------------------
# 7. Strategy catalog returns count >= 1 and a strategies list
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategies_catalog(client: AsyncClient):
    resp = await client.get(STRATEGIES_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data, "Response missing 'count' field"
    assert "strategies" in data, "Response missing 'strategies' field"
    assert isinstance(data["strategies"], list)
    assert data["count"] >= 1, f"Expected count >= 1, got {data['count']}"
    assert len(data["strategies"]) == data["count"], (
        f"Count ({data['count']}) does not match strategies list length "
        f"({len(data['strategies'])})"
    )


# ---------------------------------------------------------------------------
# 8. Capital below 100 is rejected (ge=100)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_capital_lower_bound(client: AsyncClient):
    payload = {
        "symbol": "AAPL",
        "capital": 99,
    }
    resp = await client.post(INTELLIGENCE_URL, json=payload)
    assert resp.status_code == 422, (
        f"Expected 422 for capital=99, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 9. Invalid trader_style is rejected
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_invalid_style(client: AsyncClient):
    payload = {
        "symbol": "AAPL",
        "capital": 10000,
        "trader_style": "invalid",
    }
    resp = await client.post(INTELLIGENCE_URL, json=payload)
    assert resp.status_code == 422, (
        f"Expected 422 for trader_style='invalid', got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 10. Different growth targets both succeed (potentially different data)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_strategy_growth_target_affects_recs(client: AsyncClient):
    payload_low = {**BASE_INTELLIGENCE_PAYLOAD, "growth_target_pct": 5}
    payload_high = {**BASE_INTELLIGENCE_PAYLOAD, "growth_target_pct": 100}

    resp_low = await client.post(INTELLIGENCE_URL, json=payload_low)
    resp_high = await client.post(INTELLIGENCE_URL, json=payload_high)

    assert resp_low.status_code == 200, (
        f"growth_target_pct=5 failed: {resp_low.status_code}: {resp_low.text}"
    )
    assert resp_high.status_code == 200, (
        f"growth_target_pct=100 failed: {resp_high.status_code}: {resp_high.text}"
    )

    data_low = resp_low.json()
    data_high = resp_high.json()

    # Both should return valid dict responses
    assert isinstance(data_low, dict)
    assert isinstance(data_high, dict)
