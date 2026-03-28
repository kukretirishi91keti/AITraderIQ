"""Tests for sentiment and commentary endpoints."""

import pytest


@pytest.mark.asyncio
async def test_combined_sentiment_schema(client):
    """GET /api/sentiment/combined/AAPL returns success with composite score."""
    resp = await client.get("/api/sentiment/combined/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "composite_score" in data or "score" in data


@pytest.mark.asyncio
async def test_sentiment_score_range(client):
    """Composite score must be between -100 and 100."""
    resp = await client.get("/api/sentiment/combined/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    score = data.get("composite_score", data.get("score"))
    assert score is not None
    assert -100 <= score <= 100


@pytest.mark.asyncio
async def test_sentiment_source_weights(client):
    """Response should contain source-level data."""
    resp = await client.get("/api/sentiment/combined/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    # Should have individual source data (e.g. "sources", "reddit", "stocktwits", "news")
    has_sources = (
        "sources" in data
        or "reddit" in data
        or "stocktwits" in data
        or "news" in data
    )
    assert has_sources, f"Expected source data in response, got keys: {list(data.keys())}"


@pytest.mark.asyncio
async def test_sentiment_different_symbols(client):
    """Both AAPL and TSLA should return 200."""
    resp_aapl = await client.get("/api/sentiment/combined/AAPL")
    resp_tsla = await client.get("/api/sentiment/combined/TSLA")
    assert resp_aapl.status_code == 200
    assert resp_tsla.status_code == 200


@pytest.mark.asyncio
async def test_sentiment_heatmap(client):
    """GET /api/sentiment/heatmap returns success."""
    resp = await client.get("/api/sentiment/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_sentiment_demo_fallback(client):
    """Unknown symbol ZZZZ should still return 200 in demo mode."""
    resp = await client.get("/api/sentiment/combined/ZZZZ")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_commentary_market_digest(client):
    """GET /api/commentary/market/digest returns success."""
    resp = await client.get("/api/commentary/market/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
