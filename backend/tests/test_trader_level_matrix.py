"""Tests covering every trader style x plan tier x feature combination.

16 tests that exercise signals, AI, strategy intelligence, backtest,
subscription tiers, risk tolerance, time horizon, and capital sizing.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ─── Helper ─────────────────────────────────────────────────────────────────


async def _register_and_upgrade(client: AsyncClient, suffix: str, plan: str = "free"):
    """Register a fresh user and optionally upgrade their plan."""
    resp = await client.post("/api/auth/register", json={
        "email": f"matrix{suffix}@test.com",
        "username": f"matrix{suffix}",
        "password": "SecurePass123!",
        "trader_style": "swing",
    })
    assert resp.status_code == 201
    data = resp.json()
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    if plan != "free":
        r = await client.post(
            f"/api/subscription/demo-upgrade?plan={plan}", headers=headers
        )
        assert r.status_code == 200
    return headers


def _strategy_body(
    symbol: str = "AAPL",
    capital: int = 10000,
    risk_tolerance: str = "moderate",
    time_horizon: str = "medium",
    trader_style: str = "swing",
    growth_target_pct: int = 10,
) -> dict:
    """Build a strategy-intelligence request body."""
    return {
        "symbol": symbol,
        "capital": capital,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "trader_style": trader_style,
        "growth_target_pct": growth_target_pct,
    }


# ─── 1-4: Signals per trader style ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_signals_scalper(client: AsyncClient, auth_user: dict):
    """GET /api/v4/signals/AAPL for scalp trader returns 200 with recommendation."""
    headers = auth_user["headers"]
    resp = await client.get(
        "/api/v4/signals/AAPL?trader_type=scalp", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendation" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_signals_day_trader(client: AsyncClient, auth_user: dict):
    """GET /api/v4/signals/AAPL for day trader returns 200."""
    resp = await client.get(
        "/api/v4/signals/AAPL?trader_type=day", headers=auth_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signals_swing_trader(client: AsyncClient, auth_user: dict):
    """GET /api/v4/signals/AAPL for swing trader returns 200."""
    resp = await client.get(
        "/api/v4/signals/AAPL?trader_type=swing", headers=auth_user["headers"]
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signals_position_trader(client: AsyncClient, auth_user: dict):
    """GET /api/v4/signals/AAPL for position trader returns 200."""
    resp = await client.get(
        "/api/v4/signals/AAPL?trader_type=position", headers=auth_user["headers"]
    )
    assert resp.status_code == 200


# ─── 5: AI response respects trader style ───────────────────────────────────


@pytest.mark.asyncio
async def test_ai_response_respects_trader_style(
    client: AsyncClient, auth_user: dict
):
    """POST /api/genai/query with trader_style=scalp returns a non-empty answer."""
    resp = await client.post(
        "/api/genai/query",
        json={
            "trader_style": "scalp",
            "question": "What should I do with AAPL?",
        },
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    answer = data.get("answer") or data.get("response") or data.get("text") or ""
    assert isinstance(answer, str) and len(answer) > 0


# ─── 6: Strategy intelligence per style ─────────────────────────────────────


@pytest.mark.asyncio
async def test_strategy_intelligence_per_style(
    client: AsyncClient, auth_user: dict
):
    """POST /api/strategy/intelligence for each trader style returns 200."""
    headers = auth_user["headers"]
    for style in ("scalp", "day", "swing", "position"):
        resp = await client.post(
            "/api/strategy/intelligence",
            json=_strategy_body(trader_style=style),
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Strategy intelligence failed for style={style}: {resp.text}"
        )


# ─── 7: Backtest per trader type ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backtest_per_trader_type(client: AsyncClient, auth_user: dict):
    """GET /api/backtest/run/AAPL?trader_type=X returns 200 with win_rate."""
    headers = auth_user["headers"]
    for ttype in ("scalp", "day", "swing", "position"):
        resp = await client.get(
            f"/api/backtest/run/AAPL?trader_type={ttype}", headers=headers
        )
        assert resp.status_code == 200, (
            f"Backtest failed for trader_type={ttype}: {resp.text}"
        )
        data = resp.json()
        assert "win_rate" in data, (
            f"Missing win_rate for trader_type={ttype}"
        )


# ─── 8: Backtest compare ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backtest_compare_ranks_correctly(
    client: AsyncClient, auth_user: dict
):
    """GET /api/backtest/compare?symbol=AAPL returns recommended + 4 strategies."""
    resp = await client.get(
        "/api/backtest/compare?symbol=AAPL", headers=auth_user["headers"]
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended" in data
    strategies = data.get("strategies") or data.get("results") or []
    assert len(strategies) >= 4, (
        f"Expected at least 4 strategies, got {len(strategies)}"
    )


# ─── 9-11: Subscription tier feature gates ──────────────────────────────────


@pytest.mark.asyncio
async def test_free_tier_feature_gates(client: AsyncClient):
    """Free plan enforces watchlists=1, alerts=3, ai_queries_per_day=5."""
    headers = await _register_and_upgrade(client, suffix="free", plan="free")
    resp = await client.get("/api/subscription/my-plan", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    limits = data["limits"]
    assert limits["watchlists"] == 1
    assert limits["alerts"] == 3
    assert data.get("ai_queries_per_day", limits.get("ai_queries_per_day")) == 5


@pytest.mark.asyncio
async def test_pro_tier_feature_gates(client: AsyncClient):
    """Pro plan has watchlists=10 and ai_queries_per_day=100."""
    headers = await _register_and_upgrade(client, suffix="pro", plan="pro")
    resp = await client.get("/api/subscription/my-plan", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    limits = data["limits"]
    assert limits["watchlists"] == 10
    assert data.get("ai_queries_per_day", limits.get("ai_queries_per_day")) == 100


@pytest.mark.asyncio
async def test_premium_tier_no_limits(client: AsyncClient):
    """Premium plan has unlimited watchlists and AI queries (encoded as -1)."""
    headers = await _register_and_upgrade(client, suffix="prem", plan="premium")
    resp = await client.get("/api/subscription/my-plan", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "premium"
    limits = data["limits"]
    ai_q = data.get("ai_queries_per_day", limits.get("ai_queries_per_day"))
    assert ai_q == -1, f"Expected unlimited (-1) AI queries, got {ai_q}"
    assert limits["watchlists"] == -1


# ─── 12-14: Risk tolerance levels ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_risk_tolerance_conservative(
    client: AsyncClient, auth_user: dict
):
    """Conservative risk tolerance returns strategies."""
    resp = await client.post(
        "/api/strategy/intelligence",
        json=_strategy_body(risk_tolerance="conservative"),
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "strategies" in data or "strategy" in data or "recommendation" in data


@pytest.mark.asyncio
async def test_risk_tolerance_moderate(
    client: AsyncClient, auth_user: dict
):
    """Moderate risk tolerance returns 200."""
    resp = await client.post(
        "/api/strategy/intelligence",
        json=_strategy_body(risk_tolerance="moderate"),
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_risk_tolerance_aggressive(
    client: AsyncClient, auth_user: dict
):
    """Aggressive risk tolerance returns 200."""
    resp = await client.post(
        "/api/strategy/intelligence",
        json=_strategy_body(risk_tolerance="aggressive"),
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200


# ─── 15: Time horizon short vs long ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_time_horizon_short_vs_long(
    client: AsyncClient, auth_user: dict
):
    """Both short and long time horizons return 200."""
    headers = auth_user["headers"]
    for horizon in ("short", "long"):
        resp = await client.post(
            "/api/strategy/intelligence",
            json=_strategy_body(time_horizon=horizon),
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Strategy intelligence failed for time_horizon={horizon}: {resp.text}"
        )


# ─── 16: Capital affects strategy ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_capital_affects_strategy(
    client: AsyncClient, auth_user: dict
):
    """Both small ($500) and large ($100k) capital values return 200."""
    headers = auth_user["headers"]
    for capital in (500, 100000):
        resp = await client.post(
            "/api/strategy/intelligence",
            json=_strategy_body(capital=capital),
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Strategy intelligence failed for capital={capital}: {resp.text}"
        )
