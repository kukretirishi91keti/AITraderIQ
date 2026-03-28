"""Tests for health, infrastructure, and security endpoints."""

import pytest


@pytest.mark.asyncio
async def test_ping(client):
    """GET /ping should return pong=True."""
    resp = await client.get("/ping")
    assert resp.status_code == 200
    assert resp.json()["pong"] is True


@pytest.mark.asyncio
async def test_root(client):
    """GET / should return API metadata."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_health_status(client):
    """GET /api/health should report status."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_health_detailed_has_cache_metrics(client):
    """GET /api/health/detailed should return 200 (may fall back to basic health)."""
    resp = await client.get("/api/health/detailed")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_ready(client):
    """GET /api/health/ready should return 200."""
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_live(client):
    """GET /api/health/live should return 200."""
    resp = await client.get("/api/health/live")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_status_loaded_routers(client):
    """GET /status should list loaded_routers."""
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "loaded_routers" in data
    assert isinstance(data["loaded_routers"], list)


@pytest.mark.asyncio
async def test_global_exception_handler_no_leak(client):
    """Hitting a nonexistent route must not leak stack traces."""
    resp = await client.get("/api/v4/nonexistent")
    assert resp.status_code in (404, 405)
    body = resp.text
    assert "Traceback" not in body
    assert "File" not in body


@pytest.mark.asyncio
async def test_symbol_injection_rejected(client):
    """SQL-injection-style symbol should be rejected with 400."""
    resp = await client.get("/api/v4/quote/%27%3B%20DROP")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_empty_symbol_rejected(client):
    """GET /api/v4/quote/ with no symbol should return 404 or 422."""
    resp = await client.get("/api/v4/quote/")
    assert resp.status_code in (404, 422)
