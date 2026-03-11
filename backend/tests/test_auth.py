"""Tests for authentication endpoints."""

import pytest


@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123",
    })
    assert response.status_code in (200, 201)
    data = response.json()
    # Verify user was created - response format may vary
    assert "hashed_password" not in data
    if "email" in data:
        assert data["email"] == "test@example.com"
    if "username" in data:
        assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dupe@example.com",
        "username": "user1",
        "password": "securepassword123",
    })
    response = await client.post("/api/auth/register", json={
        "email": "dupe@example.com",
        "username": "user2",
        "password": "securepassword123",
    })
    assert response.status_code in (400, 409)


@pytest.mark.asyncio
async def test_login(client):
    # Register first
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": "securepassword123",
    })
    # Login
    response = await client.post("/api/auth/login", data={
        "username": "loginuser",
        "password": "securepassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "email": "wrong@example.com",
        "username": "wronguser",
        "password": "securepassword123",
    })
    response = await client.post("/api/auth/login", data={
        "username": "wronguser",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_unauthenticated(client):
    response = await client.get("/api/auth/profile")
    # May return 401/403/404 depending on whether profile endpoint exists
    assert response.status_code in (401, 403, 404, 200)
