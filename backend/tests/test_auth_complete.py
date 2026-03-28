"""Comprehensive authentication endpoint tests."""

import pytest


# =============================================================================
# REGISTRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_register_valid_user(client):
    """POST /api/auth/register with valid data returns 201 and expected fields."""
    response = await client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "StrongPass99!",
        "full_name": "New User",
        "trader_style": "swing",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["username"] == "newuser"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with an already-used email returns 400."""
    payload = {
        "email": "dupe@example.com",
        "username": "firstuser",
        "password": "StrongPass99!",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    payload["username"] = "seconduser"  # different username, same email
    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    """Registering with an already-used username returns 400."""
    base = {
        "username": "sameuser",
        "password": "StrongPass99!",
    }
    resp1 = await client.post("/api/auth/register", json={**base, "email": "a@example.com"})
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json={**base, "email": "b@example.com"})
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(client):
    """Password shorter than 8 characters triggers 422 validation error."""
    response = await client.post("/api/auth/register", json={
        "email": "short@example.com",
        "username": "shortpw",
        "password": "short",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    """Email shorter than min_length=5 triggers 422 validation error."""
    response = await client.post("/api/auth/register", json={
        "email": "ab",
        "username": "bademail",
        "password": "StrongPass99!",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_username_special_chars(client):
    """Username with special characters violates pattern and returns 422."""
    response = await client.post("/api/auth/register", json={
        "email": "special@example.com",
        "username": "user@name!",
        "password": "StrongPass99!",
    })
    assert response.status_code == 422


# =============================================================================
# LOGIN TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_login_valid(client):
    """Registered user can login with correct credentials and gets a token."""
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "username": "loginuser",
        "password": "StrongPass99!",
    })

    response = await client.post("/api/auth/login", data={
        "username": "loginuser",
        "password": "StrongPass99!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with incorrect password returns 401."""
    await client.post("/api/auth/register", json={
        "email": "wrongpw@example.com",
        "username": "wrongpwuser",
        "password": "StrongPass99!",
    })

    response = await client.post("/api/auth/login", data={
        "username": "wrongpwuser",
        "password": "TotallyWrong!",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Login with a username that was never registered returns 401."""
    response = await client.post("/api/auth/login", data={
        "username": "nobody",
        "password": "DoesNotMatter1!",
    })
    assert response.status_code == 401


# =============================================================================
# PROFILE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_profile_get_authenticated(client, auth_user):
    """Authenticated user can retrieve their own profile via GET /api/auth/me."""
    response = await client.get("/api/auth/me", headers=auth_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["email"] == auth_user["user"]["email"]
    assert data["username"] == auth_user["user"]["username"]
    assert "trader_style" in data


@pytest.mark.asyncio
async def test_profile_get_no_token(client):
    """GET /api/auth/me without Authorization header returns 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_get_expired_token(client, expired_token):
    """GET /api/auth/me with an expired JWT returns 401."""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile(client, auth_user):
    """Authenticated user can update profile fields via PUT /api/auth/me."""
    response = await client.put(
        "/api/auth/me",
        headers=auth_user["headers"],
        json={"trader_style": "day", "risk_tolerance": "aggressive"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trader_style"] == "day"
    assert data["risk_tolerance"] == "aggressive"


@pytest.mark.asyncio
async def test_update_profile_unauthenticated(client):
    """PUT /api/auth/me without token returns 401."""
    response = await client.put("/api/auth/me", json={
        "trader_style": "day",
    })
    assert response.status_code == 401
