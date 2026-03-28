"""Tests for subscription plans, billing, and credits."""

import pytest


@pytest.mark.asyncio
async def test_plans_list_has_three_tiers(client):
    """GET /api/subscription/plans should return exactly 3 tiers."""
    resp = await client.get("/api/subscription/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["plans"]) == 3


@pytest.mark.asyncio
async def test_plans_have_usd_and_inr_prices(client):
    """Each plan must include price_usd and price_inr."""
    resp = await client.get("/api/subscription/plans")
    assert resp.status_code == 200
    for plan in resp.json()["plans"]:
        assert "price_usd" in plan, f"Plan {plan.get('name')} missing price_usd"
        assert "price_inr" in plan, f"Plan {plan.get('name')} missing price_inr"


@pytest.mark.asyncio
async def test_plans_have_limits_defined(client):
    """Each plan must have a limits dict and ai_queries_per_day."""
    resp = await client.get("/api/subscription/plans")
    assert resp.status_code == 200
    for plan in resp.json()["plans"]:
        assert "limits" in plan, f"Plan {plan.get('name')} missing limits"
        assert isinstance(plan["limits"], dict)
        assert "ai_queries_per_day" in plan, f"Plan {plan.get('name')} missing ai_queries_per_day"


@pytest.mark.asyncio
async def test_my_plan_returns_current_tier(client, auth_user):
    """Authenticated user should see their current plan."""
    resp = await client.get("/api/subscription/my-plan", headers=auth_user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data


@pytest.mark.asyncio
async def test_my_plan_unauthenticated(client):
    """GET /api/subscription/my-plan without auth should return 401."""
    resp = await client.get("/api/subscription/my-plan")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_checkout_requires_auth(client):
    """POST /api/subscription/checkout without auth should return 401."""
    resp = await client.post("/api/subscription/checkout", json={"plan": "pro"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_checkout_invalid_plan(client, auth_user):
    """POST /api/subscription/checkout with invalid plan should return 422."""
    resp = await client.post(
        "/api/subscription/checkout",
        json={"plan": "invalid"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_demo_upgrade_changes_plan(client, auth_user):
    """Demo upgrade to pro should change the user's plan."""
    resp = await client.post(
        "/api/subscription/demo-upgrade?plan=pro",
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200

    # Verify plan changed
    resp2 = await client.get("/api/subscription/my-plan", headers=auth_user["headers"])
    assert resp2.status_code == 200
    assert resp2.json()["plan"] == "pro"
