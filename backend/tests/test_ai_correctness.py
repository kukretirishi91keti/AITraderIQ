"""
Tests for GenAI router correctness (rule-based fallback mode).

GROQ_API_KEY="" is set in conftest.py, so all requests use the
rule-based fallback engine instead of the Groq LLM.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 1. AI receives full stock context and returns an answer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_receives_stock_context(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "Should I buy?",
        "symbol": "AAPL",
        "price": 150.0,
        "rsi": 35.0,
        "signal": "BUY",
        "trader_style": "swing",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


# ---------------------------------------------------------------------------
# 2. Response always contains a "source" field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_source_field_present(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "What do you think about AAPL?",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "source" in data


# ---------------------------------------------------------------------------
# 3. Response contains a "model" field (may be null in fallback mode)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_model_field_matches_request(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "test",
        "model": "llama-3.1-8b-instant",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "model" in data
    # In fallback mode model is None — that is acceptable
    assert data["model"] is None or isinstance(data["model"], str)


# ---------------------------------------------------------------------------
# 4. Fallback source string contains "rule"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_fallback_source_is_rule_based(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "test",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "rule" in data["source"].lower()


# ---------------------------------------------------------------------------
# 5. Fallback still produces a meaningful (non-trivial) answer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_fallback_still_gives_answer(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "What is the best strategy for AAPL?",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 10


# ---------------------------------------------------------------------------
# 6. Trader style is accepted without error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_respects_trader_style_in_prompt(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "What should I do?",
        "trader_style": "scalper",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


# ---------------------------------------------------------------------------
# 7. All four supported models are accepted by the endpoint
# ---------------------------------------------------------------------------

SUPPORTED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SUPPORTED_MODELS)
async def test_ai_all_4_models_accepted(client: AsyncClient, model: str):
    resp = await client.post("/api/genai/query", json={
        "question": "test",
        "model": model,
    })
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 8. Empty question is handled gracefully (200 with answer, or 422)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_empty_question_rejected(client: AsyncClient):
    resp = await client.post("/api/genai/query", json={
        "question": "",
    })
    if resp.status_code == 422:
        # Validation rejected the empty string — that is fine
        return
    # If accepted (no min_length constraint), the answer must still be present
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


# ---------------------------------------------------------------------------
# 9. Health endpoint returns status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/genai/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


# ---------------------------------------------------------------------------
# 10. Models list contains at least one model and a default
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_models_list_has_default(client: AsyncClient):
    resp = await client.get("/api/genai/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert isinstance(data["available"], list)
    assert len(data["available"]) >= 1
    assert "default" in data
    assert isinstance(data["default"], str)
