"""CRUD tests for watchlist, portfolio, and alerts endpoints."""

import pytest


# ─── WATCHLIST ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_watchlist_empty_initially(client, auth_user):
    resp = await client.get("/api/user/watchlist", headers=auth_user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_watchlist_add_and_retrieve(client, auth_user):
    resp = await client.post(
        "/api/user/watchlist",
        json={"symbol": "AAPL"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 201

    resp = await client.get("/api/user/watchlist", headers=auth_user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["watchlist"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_watchlist_add_duplicate(client, auth_user):
    headers = auth_user["headers"]
    resp1 = await client.post(
        "/api/user/watchlist", json={"symbol": "AAPL"}, headers=headers
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/user/watchlist", json={"symbol": "AAPL"}, headers=headers
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_watchlist_remove(client, auth_user):
    headers = auth_user["headers"]
    await client.post(
        "/api/user/watchlist", json={"symbol": "AAPL"}, headers=headers
    )

    resp = await client.delete("/api/user/watchlist/AAPL", headers=headers)
    assert resp.status_code == 200

    resp = await client.get("/api/user/watchlist", headers=headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_watchlist_remove_nonexistent(client, auth_user):
    resp = await client.delete(
        "/api/user/watchlist/ZZZZ", headers=auth_user["headers"]
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_isolation(client, auth_user, auth_user_b):
    await client.post(
        "/api/user/watchlist",
        json={"symbol": "AAPL"},
        headers=auth_user["headers"],
    )

    resp = await client.get(
        "/api/user/watchlist", headers=auth_user_b["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ─── PORTFOLIO ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_portfolio_add_item(client, auth_user):
    resp = await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": 10, "avg_price": 150.0},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_portfolio_update_item(client, auth_user):
    headers = auth_user["headers"]
    resp = await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": 10, "avg_price": 150.0},
        headers=headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.put(
        f"/api/user/portfolio/{item_id}",
        json={"shares": 20},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_portfolio_delete_item(client, auth_user):
    headers = auth_user["headers"]
    resp = await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": 10, "avg_price": 150.0},
        headers=headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/user/portfolio/{item_id}", headers=headers
    )
    assert resp.status_code == 200

    resp = await client.get("/api/user/portfolio", headers=headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_portfolio_negative_shares_rejected(client, auth_user):
    resp = await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": -5, "avg_price": 150.0},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_portfolio_zero_price_rejected(client, auth_user):
    resp = await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": 10, "avg_price": 0},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_portfolio_update_nonexistent(client, auth_user):
    resp = await client.put(
        "/api/user/portfolio/99999",
        json={"shares": 20},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_portfolio_isolation(client, auth_user, auth_user_b):
    await client.post(
        "/api/user/portfolio",
        json={"symbol": "AAPL", "shares": 10, "avg_price": 150.0},
        headers=auth_user["headers"],
    )

    resp = await client.get(
        "/api/user/portfolio", headers=auth_user_b["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ─── ALERTS ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alerts_create(client, auth_user):
    resp = await client.post(
        "/api/user/alerts",
        json={"symbol": "AAPL", "condition": "above", "target_value": 200.0},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_alerts_invalid_condition(client, auth_user):
    resp = await client.post(
        "/api/user/alerts",
        json={"symbol": "AAPL", "condition": "invalid", "target_value": 200.0},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_alerts_delete(client, auth_user):
    headers = auth_user["headers"]
    resp = await client.post(
        "/api/user/alerts",
        json={"symbol": "AAPL", "condition": "above", "target_value": 200.0},
        headers=headers,
    )
    assert resp.status_code == 201
    alert_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/user/alerts/{alert_id}", headers=headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_alerts_delete_nonexistent(client, auth_user):
    resp = await client.delete(
        "/api/user/alerts/99999", headers=auth_user["headers"]
    )
    assert resp.status_code == 404


# ─── AUTH REQUIRED ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_crud_requires_auth(client):
    endpoints = [
        ("GET", "/api/user/watchlist"),
        ("POST", "/api/user/watchlist"),
        ("GET", "/api/user/portfolio"),
        ("POST", "/api/user/portfolio"),
        ("GET", "/api/user/alerts"),
        ("POST", "/api/user/alerts"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url)
        assert resp.status_code == 401, (
            f"{method} {url} returned {resp.status_code}, expected 401"
        )
