"""Tests for security utilities."""

import pytest
from auth.security import hash_password, verify_password, create_access_token
from jose import jwt


def test_password_hashing():
    password = "my-secure-password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_password_wrong():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


def test_create_access_token():
    token = create_access_token({"sub": "1"})
    payload = jwt.decode(token, "test-secret-key-not-for-production", algorithms=["HS256"])
    assert payload["sub"] == "1"
    assert "exp" in payload


def test_token_expiry():
    from datetime import timedelta
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(hours=1))
    payload = jwt.decode(token, "test-secret-key-not-for-production", algorithms=["HS256"])
    assert payload["sub"] == "1"
