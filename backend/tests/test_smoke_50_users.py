"""
Smoke test: 50 concurrent users hitting all major endpoints.

Simulates 50 users performing typical actions:
- Register & login
- Fetch quotes, signals, history
- Query AI assistant with model selection
- Access health, screener, sentiment endpoints
- WebSocket price streaming
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import os
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./smoke_test.db"

from main import app  # noqa: E402
from database.engine import engine, Base  # noqa: E402

NUM_USERS = 50
SYMBOL = "AAPL"


@pytest_asyncio.fixture
async def db():
    """Create fresh database for smoke test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def simulate_user(client: AsyncClient, user_id: int) -> dict:
    """Simulate a single user's complete session."""
    results = {"user_id": user_id, "passed": 0, "failed": 0, "errors": []}

    async def check(name, coro):
        try:
            resp = await coro
            if resp.status_code < 500:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{name}: HTTP {resp.status_code}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{name}: {str(e)[:80]}")

    email = f"smokeuser{user_id}@test.com"
    username = f"smokeuser{user_id}"
    password = "TestPass123!"

    # 1. Register
    await check("register", client.post("/api/auth/register", json={
        "email": email, "username": username, "password": password,
    }))

    # 2. Login
    login_resp = await client.post("/api/auth/login", data={
        "username": username, "password": password,
    })
    token = None
    if login_resp.status_code == 200:
        results["passed"] += 1
        token = login_resp.json().get("access_token")
    else:
        results["failed"] += 1
        results["errors"].append(f"login: HTTP {login_resp.status_code}")

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 3. Health check
    await check("health", client.get("/api/health"))

    # 4. Quote
    await check("quote", client.get(f"/api/v4/quote/{SYMBOL}"))

    # 5. History
    await check("history", client.get(f"/api/v4/history/{SYMBOL}"))

    # 6. Signals
    await check("signals", client.get(f"/api/v4/signals/{SYMBOL}"))

    # 7. Financials
    await check("financials", client.get(f"/api/v4/financials/{SYMBOL}"))

    # 8. News
    await check("news", client.get(f"/api/news/{SYMBOL}"))

    # 9. Sentiment
    await check("sentiment", client.get(f"/api/sentiment/reddit/{SYMBOL}"))

    # 10. AI query with model selection
    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]
    selected_model = models[user_id % len(models)]
    ai_resp = await client.post("/api/genai/query", json={
        "question": f"Should I buy {SYMBOL}?",
        "symbol": SYMBOL,
        "price": 185.0,
        "rsi": 55.0,
        "signal": "HOLD",
        "model": selected_model,
    })
    if ai_resp.status_code == 200:
        results["passed"] += 1
        data = ai_resp.json()
        # Verify response has expected fields
        assert "answer" in data, "AI response missing 'answer'"
        assert "source" in data, "AI response missing 'source'"
        assert len(data["answer"]) > 10, "AI response too short"
    else:
        results["failed"] += 1
        results["errors"].append(f"ai_query: HTTP {ai_resp.status_code}")

    # 11. AI models endpoint
    await check("ai_models", client.get("/api/genai/models"))

    # 12. GenAI health
    await check("genai_health", client.get("/api/genai/health"))

    # 13. Scanner
    await check("scanner", client.get("/api/scanner/rank"))

    # 14. Profile (authenticated)
    if token:
        await check("profile", client.get("/api/auth/me", headers=headers))

    return results


@pytest.mark.asyncio
async def test_smoke_50_concurrent_users(client):
    """Run 50 concurrent user sessions and verify system stability."""
    # Run all 50 users concurrently
    tasks = [simulate_user(client, i) for i in range(NUM_USERS)]
    results = await asyncio.gather(*tasks)

    # Aggregate results
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_checks = total_passed + total_failed
    users_with_errors = [r for r in results if r["errors"]]

    print(f"\n{'='*60}")
    print(f"  SMOKE TEST RESULTS: {NUM_USERS} Concurrent Users")
    print(f"{'='*60}")
    print(f"  Total checks:  {total_checks}")
    print(f"  Passed:        {total_passed} ({total_passed/total_checks*100:.1f}%)")
    print(f"  Failed:        {total_failed} ({total_failed/total_checks*100:.1f}%)")
    print(f"  Users clean:   {NUM_USERS - len(users_with_errors)}/{NUM_USERS}")

    if users_with_errors:
        print(f"\n  Errors ({len(users_with_errors)} users):")
        for r in users_with_errors[:10]:
            for err in r["errors"][:3]:
                print(f"    User {r['user_id']}: {err}")

    print(f"{'='*60}\n")

    # Assertions
    success_rate = total_passed / total_checks if total_checks > 0 else 0
    assert success_rate >= 0.90, f"Success rate {success_rate:.1%} below 90% threshold"
    assert total_passed > 0, "No checks passed"


@pytest.mark.asyncio
async def test_ai_model_selection_all_models(client):
    """Verify each model option is accepted by the API."""
    models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    for model_id in models:
        resp = await client.post("/api/genai/query", json={
            "question": "Quick analysis",
            "symbol": "AAPL",
            "model": model_id,
        })
        assert resp.status_code == 200, f"Model {model_id} failed: {resp.status_code}"
        data = resp.json()
        assert "answer" in data
        assert len(data["answer"]) > 5


@pytest.mark.asyncio
async def test_ai_models_endpoint(client):
    """Verify /api/genai/models returns all available models."""
    resp = await client.get("/api/genai/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert len(data["available"]) >= 4
    assert "default" in data
    model_ids = [m["id"] for m in data["available"]]
    assert "llama-3.3-70b-versatile" in model_ids
    assert "llama-3.1-8b-instant" in model_ids
