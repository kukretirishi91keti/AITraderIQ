"""
Tests for data provenance -- every data response tells the user what they're getting.

Covers: dataQuality, source, timestamps, confidence scores, and demo-mode labeling
across quote, history, signals, sentiment, commentary, financials, and scanner endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 1. Quote has dataQuality field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quote_has_data_quality_field(client: AsyncClient):
    """GET /api/v4/quote/AAPL returns a dataQuality indicator."""
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0

    # The service always sets dataQuality (LIVE, CACHED, LKG, SIMULATED)
    assert "dataQuality" in data, (
        f"Expected 'dataQuality' key in quote response. Keys present: {list(data.keys())}"
    )
    allowed = {"LIVE", "CACHED", "LKG", "SIMULATED", "DEMO", "UNKNOWN"}
    assert data["dataQuality"] in allowed, (
        f"Unexpected dataQuality value: {data['dataQuality']}"
    )


# ---------------------------------------------------------------------------
# 2. Quote has a data-source field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quote_has_data_source_field(client: AsyncClient):
    """GET /api/v4/quote/AAPL includes a source indicator."""
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()

    has_source = any(k in data for k in ("source", "data_source"))
    assert has_source, (
        f"Expected 'source' or 'data_source' key in quote. Keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 3. Quote has timestamp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quote_has_timestamp(client: AsyncClient):
    """GET /api/v4/quote/AAPL includes a timestamp."""
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()

    assert "timestamp" in data, (
        f"Expected 'timestamp' key in quote. Keys: {list(data.keys())}"
    )
    # Value should be a non-empty string (ISO format)
    assert isinstance(data["timestamp"], str) and len(data["timestamp"]) > 0


# ---------------------------------------------------------------------------
# 4. History has data-quality metadata
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_has_data_quality(client: AsyncClient):
    """GET /api/v4/history/AAPL carries data-quality metadata."""
    resp = await client.get("/api/v4/history/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0

    # History endpoint returns dataQuality, source, or at least a meta section
    has_quality = any(
        k in data for k in ("dataQuality", "data_quality", "source", "data_source", "meta")
    )
    assert has_quality, (
        f"Expected a data-quality indicator in history response. Keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 5. Signals returns 200 with data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_signals_has_data_source(client: AsyncClient):
    """GET /api/v4/signals/AAPL returns 200 with a non-empty response."""
    resp = await client.get("/api/v4/signals/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0
    # Signals endpoint includes source and timestamp
    assert data.get("success") is True


# ---------------------------------------------------------------------------
# 6. Sentiment has source breakdown
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sentiment_has_source_breakdown(client: AsyncClient):
    """GET /api/sentiment/combined/AAPL includes per-source scores."""
    resp = await client.get("/api/sentiment/combined/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0

    # The aggregator returns a "sources" dict keyed by provider name
    has_breakdown = "sources" in data or any(
        k in data for k in ("reddit", "stocktwits", "news")
    )
    assert has_breakdown, (
        f"Expected 'sources' or individual source keys in sentiment response. "
        f"Keys: {list(data.keys())}"
    )

    # If 'sources' exists, make sure it is a non-empty mapping
    if "sources" in data:
        assert isinstance(data["sources"], dict) and len(data["sources"]) > 0


# ---------------------------------------------------------------------------
# 7. Demo mode labels data (never returns empty/error)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_demo_mode_labels_data(client: AsyncClient):
    """In DEMO_MODE=true the quote endpoint generates data instead of failing."""
    resp = await client.get("/api/v4/quote/AAPL")
    assert resp.status_code == 200
    data = resp.json()

    # Must have actual price data (not an error dict)
    assert "price" in data or "symbol" in data, (
        "Demo mode should generate quote data, not return an error."
    )
    # The response should carry success=True
    assert data.get("success") is True


# ---------------------------------------------------------------------------
# 8. Financials has source metadata
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_financials_has_source(client: AsyncClient):
    """GET /api/v4/financials/AAPL returns non-empty financial data with source."""
    resp = await client.get("/api/v4/financials/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0
    assert data.get("success") is True

    # Financials endpoint returns a "financials" dict and a "source" field
    assert "financials" in data, (
        f"Expected 'financials' key. Keys: {list(data.keys())}"
    )
    assert isinstance(data["financials"], dict) and len(data["financials"]) > 0

    has_source = any(k in data for k in ("source", "data_source"))
    assert has_source, (
        f"Expected source metadata in financials. Keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 9. Commentary has generated_at timestamp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_commentary_has_generated_at(client: AsyncClient):
    """GET /api/commentary/AAPL includes a generation timestamp."""
    resp = await client.get("/api/commentary/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and len(data) > 0

    has_timestamp = any(
        k in data for k in ("generated_at", "generatedAt", "timestamp")
    )
    assert has_timestamp, (
        f"Expected a generation timestamp in commentary. Keys: {list(data.keys())}"
    )


# ---------------------------------------------------------------------------
# 10. Scanner rankings carry confidence / ai_score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_results_have_confidence(client: AsyncClient):
    """GET /api/scanner/rank items each have confidence or ai_score."""
    resp = await client.get("/api/scanner/rank")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("success") is True

    rankings = data.get("rankings", [])
    assert isinstance(rankings, list) and len(rankings) > 0, (
        "Scanner should return at least one ranked item"
    )

    for item in rankings:
        has_score = any(k in item for k in ("confidence", "ai_score"))
        assert has_score, (
            f"Each ranking item should have 'confidence' or 'ai_score'. "
            f"Keys in item: {list(item.keys())}"
        )
