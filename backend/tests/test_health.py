"""Tests for health endpoints."""

import pytest


@pytest.mark.asyncio
async def test_ping(client):
    response = await client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["pong"] is True
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TraderAI Pro API"
    assert "version" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_status(client):
    response = await client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_ready(client):
    response = await client.get("/api/health/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_live(client):
    response = await client.get("/api/health/live")
    assert response.status_code == 200
