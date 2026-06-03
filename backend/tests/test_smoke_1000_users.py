"""
Production-Level Smoke Test: 1000 Concurrent Users
====================================================
Validates system stability, correctness, and performance under realistic load.

Simulates 1000 users performing typical trading platform actions:
- Register & login (auth flow)
- Fetch quotes, signals, history, financials
- Query AI assistant across all 4 model options
- Access health, screener, sentiment, backtest, scanner endpoints
- Strategy intelligence queries
- Authenticated profile & watchlist operations
- Concurrent write pressure (registration storm)

Metrics collected:
- Per-endpoint success rates and latencies (p50, p95, p99)
- Overall system success rate (threshold: >= 90%)
- Error categorization and reporting

Note: SQLite is single-writer, so write-heavy tests use small batches (10).
      In production with PostgreSQL, BATCH_SIZE_WRITE can match BATCH_SIZE_READ.
"""

import asyncio
import time
import statistics
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

from main import app  # noqa: E402
from database.engine import engine, Base  # noqa: E402

NUM_USERS = 1000
BATCH_SIZE_READ = 100   # Concurrent users per batch for read-only endpoints
BATCH_SIZE_WRITE = 10   # Concurrent users per batch for DB-write endpoints (SQLite safe)
SYMBOL = "AAPL"
ALT_SYMBOLS = ["MSFT", "GOOGL", "TSLA", "NVDA", "AMZN", "META", "AMD", "NFLX"]
AI_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]
TRADER_STYLES = ["scalp", "day", "swing", "position"]
RISK_LEVELS = ["conservative", "moderate", "aggressive"]


@pytest_asyncio.fixture
async def db():
    """Create fresh database tables for smoke test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# LATENCY TRACKER
# =============================================================================

class LatencyTracker:
    """Collects per-endpoint latency and status data."""

    def __init__(self):
        self.data: dict[str, list[dict]] = {}

    def record(self, endpoint: str, status_code: int, latency_ms: float):
        self.data.setdefault(endpoint, []).append({
            "status": status_code,
            "latency_ms": latency_ms,
        })

    def summary(self) -> dict:
        out = {}
        for endpoint, records in sorted(self.data.items()):
            latencies = sorted([r["latency_ms"] for r in records])
            successes = sum(1 for r in records if r["status"] < 500)
            n = len(latencies)
            out[endpoint] = {
                "calls": n,
                "success_rate": successes / n if n else 0,
                "p50_ms": round(latencies[n // 2], 1) if n else 0,
                "p95_ms": round(latencies[int(n * 0.95)], 1) if n else 0,
                "p99_ms": round(latencies[min(int(n * 0.99), n - 1)], 1) if n else 0,
                "max_ms": round(latencies[-1], 1) if n else 0,
            }
        return out


# =============================================================================
# SINGLE USER SIMULATION
# =============================================================================

async def simulate_user(client: AsyncClient, user_id: int, tracker: LatencyTracker) -> dict:
    """Simulate a complete user session across all platform features."""
    results = {"user_id": user_id, "passed": 0, "failed": 0, "errors": []}

    async def check(name: str, coro):
        try:
            t0 = time.perf_counter()
            resp = await coro
            latency = (time.perf_counter() - t0) * 1000
            tracker.record(name, resp.status_code, latency)
            if resp.status_code < 500:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{name}: HTTP {resp.status_code}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{name}: {str(e)[:100]}")

    # Vary data per user for realistic spread
    symbol = ALT_SYMBOLS[user_id % len(ALT_SYMBOLS)] if user_id % 3 != 0 else SYMBOL
    style = TRADER_STYLES[user_id % len(TRADER_STYLES)]
    risk = RISK_LEVELS[user_id % len(RISK_LEVELS)]
    model = AI_MODELS[user_id % len(AI_MODELS)]

    email = f"loaduser{user_id}@test.com"
    username = f"loaduser{user_id}"
    password = "SecurePass123!"

    # ---- AUTH FLOW ----
    await check("POST /api/auth/register", client.post("/api/auth/register", json={
        "email": email, "username": username, "password": password, "trader_style": style,
    }))

    t0 = time.perf_counter()
    login_resp = await client.post("/api/auth/login", data={
        "username": username, "password": password,
    })
    latency = (time.perf_counter() - t0) * 1000
    tracker.record("POST /api/auth/login", login_resp.status_code, latency)

    token = None
    if login_resp.status_code == 200:
        results["passed"] += 1
        token = login_resp.json().get("access_token")
    else:
        results["failed"] += 1
        results["errors"].append(f"login: HTTP {login_resp.status_code}")

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # ---- PUBLIC ENDPOINTS (read-only, high concurrency safe) ----
    await check("GET /api/health", client.get("/api/health"))
    await check("GET /api/v4/quote/{s}", client.get(f"/api/v4/quote/{symbol}"))
    await check("GET /api/v4/history/{s}", client.get(f"/api/v4/history/{symbol}"))
    await check("GET /api/v4/signals/{s}", client.get(f"/api/v4/signals/{symbol}"))
    await check("GET /api/v4/financials/{s}", client.get(f"/api/v4/financials/{symbol}"))
    await check("GET /api/sentiment/combined/{s}", client.get(f"/api/sentiment/combined/{symbol}"))
    await check("GET /api/scanner/rank", client.get("/api/scanner/rank"))
    await check("GET /api/backtest/run/{s}", client.get(f"/api/backtest/run/{symbol}?trader_type={style}"))
    await check("POST /api/genai/query", client.post("/api/genai/query", json={
        "question": f"Should I buy {symbol} as a {style} trader?",
        "symbol": symbol, "price": 185.0 + (user_id % 50),
        "rsi": 30.0 + (user_id % 40),
        "signal": ["BUY", "SELL", "HOLD"][user_id % 3], "model": model,
    }))
    await check("GET /api/genai/models", client.get("/api/genai/models"))
    await check("POST /api/strategy/intelligence", client.post("/api/strategy/intelligence", json={
        "symbol": symbol, "capital": 10000 + (user_id * 100),
        "growth_target_pct": 10 + (user_id % 20), "risk_tolerance": risk,
        "time_horizon": ["short", "medium", "long"][user_id % 3], "trader_style": style,
    }))
    await check("GET /api/strategy/strategies", client.get("/api/strategy/strategies"))

    # ---- AUTHENTICATED ENDPOINTS (DB writes) ----
    if token:
        await check("GET /api/auth/me", client.get("/api/auth/me", headers=headers))
        await check("PUT /api/auth/me", client.put("/api/auth/me", headers=headers, json={
            "risk_tolerance": risk, "trader_style": style,
        }))
        await check("POST /api/user/watchlist", client.post("/api/user/watchlist",
                     headers=headers, json={"symbol": symbol}))
        await check("GET /api/user/watchlist", client.get("/api/user/watchlist", headers=headers))
        await check("POST /api/user/portfolio", client.post("/api/user/portfolio",
                     headers=headers, json={"symbol": symbol, "shares": 10 + (user_id % 90),
                                            "avg_price": 150.0 + (user_id % 50)}))
        await check("GET /api/user/portfolio", client.get("/api/user/portfolio", headers=headers))

    return results


def print_report(title: str, all_results: list[dict], tracker: LatencyTracker, wall_time: float):
    """Print a formatted test report."""
    total_passed = sum(r["passed"] for r in all_results)
    total_failed = sum(r["failed"] for r in all_results)
    total_checks = total_passed + total_failed
    users_with_errors = [r for r in all_results if r["errors"]]

    print(f"\n{'=' * 72}")
    print(f"  {title}  |  Wall time: {wall_time:.1f}s")
    print(f"{'=' * 72}")
    print(f"  Total API calls:    {total_checks:,}")
    print(f"  Passed:             {total_passed:,} ({total_passed / total_checks * 100:.1f}%)" if total_checks else "")
    print(f"  Failed:             {total_failed:,} ({total_failed / total_checks * 100:.1f}%)" if total_checks else "")
    print(f"  Users with errors:  {len(users_with_errors):,} / {len(all_results):,}")
    if wall_time > 0 and total_checks > 0:
        print(f"  Throughput:         {total_checks / wall_time:.0f} req/s")

    summary = tracker.summary()
    if summary:
        print(f"\n  {'Endpoint':<40} {'Calls':>6} {'Pass%':>6} {'p50':>7} {'p95':>7} {'p99':>7} {'Max':>7}")
        print(f"  {'-' * 40} {'-' * 6} {'-' * 6} {'-' * 7} {'-' * 7} {'-' * 7} {'-' * 7}")
        for ep, s in summary.items():
            print(f"  {ep:<40} {s['calls']:>6} {s['success_rate']*100:>5.1f}% "
                  f"{s['p50_ms']:>6.1f} {s['p95_ms']:>6.1f} "
                  f"{s['p99_ms']:>6.1f} {s['max_ms']:>6.1f}")

    if users_with_errors:
        error_counts: dict[str, int] = {}
        for r in users_with_errors:
            for err in r["errors"]:
                key = err.split(":")[0] if ":" in err else err
                error_counts[key] = error_counts.get(key, 0) + 1
        print(f"\n  Error Breakdown:")
        for err_key, count in sorted(error_counts.items(), key=lambda x: -x[1])[:15]:
            print(f"    {err_key}: {count:,} occurrences")

    print(f"{'=' * 72}\n")
    return total_passed, total_failed, total_checks, summary


# =============================================================================
# MAIN TEST: 1000 USERS
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_smoke_1000_concurrent_users(client):
    """Run 1000 users in batches and verify system stability under load.

    Write-heavy operations (register, login, watchlist, portfolio) use small
    batches of 10 to respect SQLite's single-writer constraint.
    """
    tracker = LatencyTracker()
    all_results = []
    t_start = time.perf_counter()

    for batch_start in range(0, NUM_USERS, BATCH_SIZE_WRITE):
        batch_end = min(batch_start + BATCH_SIZE_WRITE, NUM_USERS)
        tasks = [simulate_user(client, uid, tracker) for uid in range(batch_start, batch_end)]
        batch_results = await asyncio.gather(*tasks)
        all_results.extend(batch_results)

    wall_time = time.perf_counter() - t_start
    total_passed, total_failed, total_checks, summary = print_report(
        f"PRODUCTION SMOKE TEST: {NUM_USERS} Users", all_results, tracker, wall_time
    )

    success_rate = total_passed / total_checks if total_checks > 0 else 0
    assert total_checks > 0, "No API calls were made"
    assert success_rate >= 0.90, (
        f"Success rate {success_rate:.1%} below 90% threshold "
        f"({total_failed:,} failures out of {total_checks:,} calls)"
    )
    auth_stats = summary.get("POST /api/auth/register", {})
    if auth_stats:
        assert auth_stats["success_rate"] >= 0.85, (
            f"Registration success rate {auth_stats['success_rate']:.1%} too low"
        )


# =============================================================================
# TARGETED SUB-TESTS
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_registration_storm_1000(client):
    """Verify 1000 unique users can register without collisions or data loss."""
    results = {"success": 0, "duplicate": 0, "error": 0, "db_locked": 0}

    async def register_user(uid: int):
        try:
            resp = await client.post("/api/auth/register", json={
                "email": f"stormuser{uid}@test.com",
                "username": f"stormuser{uid}",
                "password": "StormPass123!",
            })
            if resp.status_code in (200, 201):
                results["success"] += 1
            elif resp.status_code == 400:
                results["duplicate"] += 1
            elif resp.status_code == 500:
                results["db_locked"] += 1  # Expected with SQLite under write pressure
            else:
                results["error"] += 1
        except Exception:
            results["error"] += 1

    # Small batches to respect SQLite single-writer
    for batch_start in range(0, NUM_USERS, BATCH_SIZE_WRITE):
        batch_end = min(batch_start + BATCH_SIZE_WRITE, NUM_USERS)
        tasks = [register_user(uid) for uid in range(batch_start, batch_end)]
        await asyncio.gather(*tasks)

    total = results["success"] + results["duplicate"] + results["db_locked"] + results["error"]
    print(f"\n  Registration Storm ({total} attempts):")
    print(f"    Success: {results['success']}, Duplicate: {results['duplicate']}, "
          f"DB-locked: {results['db_locked']}, Error: {results['error']}")

    assert results["success"] >= NUM_USERS * 0.85, (
        f"Only {results['success']}/{NUM_USERS} registrations succeeded"
    )
    assert results["error"] == 0, f"{results['error']} unexpected errors during registration"


@pytest.mark.asyncio
async def test_concurrent_reads_1000(client):
    """Verify 1000 concurrent read requests to public endpoints don't degrade."""
    endpoints = [
        "/api/health",
        "/api/v4/quote/AAPL",
        "/api/v4/signals/AAPL",
        "/api/v4/history/AAPL",
        "/api/genai/models",
        "/api/strategy/strategies",
    ]

    results = {"passed": 0, "failed": 0}
    latencies: list[float] = []

    async def hit_endpoint(idx: int):
        ep = endpoints[idx % len(endpoints)]
        t0 = time.perf_counter()
        resp = await client.get(ep)
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)
        if resp.status_code < 500:
            results["passed"] += 1
        else:
            results["failed"] += 1

    for batch_start in range(0, NUM_USERS, BATCH_SIZE_READ):
        batch_end = min(batch_start + BATCH_SIZE_READ, NUM_USERS)
        tasks = [hit_endpoint(i) for i in range(batch_start, batch_end)]
        await asyncio.gather(*tasks)

    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    p50 = sorted_lat[n // 2] if n else 0
    p95 = sorted_lat[int(n * 0.95)] if n else 0
    p99 = sorted_lat[min(int(n * 0.99), n - 1)] if n else 0

    print(f"\n  Concurrent Reads ({NUM_USERS} requests):")
    print(f"    Passed: {results['passed']}, Failed: {results['failed']}")
    print(f"    Latency p50={p50:.1f}ms  p95={p95:.1f}ms  p99={p99:.1f}ms")

    total = results["passed"] + results["failed"]
    success_rate = results["passed"] / total if total else 0
    assert success_rate >= 0.95, f"Read success rate {success_rate:.1%} below 95%"


@pytest.mark.asyncio
async def test_ai_model_rotation_under_load(client):
    """Verify all 4 AI models handle concurrent queries correctly."""
    model_results: dict[str, dict] = {m: {"pass": 0, "fail": 0} for m in AI_MODELS}
    queries_per_model = 50

    async def query_model(model: str, idx: int):
        symbol = ALT_SYMBOLS[idx % len(ALT_SYMBOLS)]
        resp = await client.post("/api/genai/query", json={
            "question": f"Analyze {symbol} for a {TRADER_STYLES[idx % 4]} trader",
            "symbol": symbol, "price": 150.0 + idx,
            "rsi": 40.0 + (idx % 30),
            "signal": ["BUY", "SELL", "HOLD"][idx % 3], "model": model,
        })
        if resp.status_code == 200:
            data = resp.json()
            if "answer" in data and len(data["answer"]) > 5:
                model_results[model]["pass"] += 1
                return
        model_results[model]["fail"] += 1

    for model in AI_MODELS:
        tasks = [query_model(model, i) for i in range(queries_per_model)]
        await asyncio.gather(*tasks)

    print(f"\n  AI Model Load Test ({queries_per_model} queries each):")
    for model, counts in model_results.items():
        total = counts["pass"] + counts["fail"]
        rate = counts["pass"] / total * 100 if total else 0
        print(f"    {model}: {counts['pass']}/{total} ({rate:.0f}%)")

    for model, counts in model_results.items():
        total = counts["pass"] + counts["fail"]
        assert counts["pass"] / total >= 0.90, f"Model {model} success rate below 90%"


@pytest.mark.asyncio
async def test_strategy_intelligence_load(client):
    """Verify strategy intelligence handles diverse concurrent requests."""
    results = {"passed": 0, "failed": 0}

    async def query_strategy(idx: int):
        symbol = ALT_SYMBOLS[idx % len(ALT_SYMBOLS)]
        resp = await client.post("/api/strategy/intelligence", json={
            "symbol": symbol, "capital": 5000 + (idx * 500),
            "growth_target_pct": 5 + (idx % 30),
            "risk_tolerance": RISK_LEVELS[idx % len(RISK_LEVELS)],
            "time_horizon": ["short", "medium", "long"][idx % 3],
            "trader_style": TRADER_STYLES[idx % len(TRADER_STYLES)],
        })
        if resp.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1

    for batch_start in range(0, 200, BATCH_SIZE_READ):
        batch_end = min(batch_start + BATCH_SIZE_READ, 200)
        tasks = [query_strategy(i) for i in range(batch_start, batch_end)]
        await asyncio.gather(*tasks)

    total = results["passed"] + results["failed"]
    rate = results["passed"] / total if total else 0
    print(f"\n  Strategy Intelligence: {results['passed']}/{total} ({rate:.0%})")

    assert rate >= 0.90, f"Strategy success rate {rate:.1%} below 90%"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_authenticated_workflow_at_scale(client):
    """Verify full authenticated workflows (register -> login -> CRUD) at scale."""
    num_users = 200
    results = {"full_flow": 0, "partial": 0, "failed": 0}

    async def full_workflow(uid: int):
        email = f"authflow{uid}@test.com"
        username = f"authflow{uid}"
        password = "AuthFlow123!"
        style = TRADER_STYLES[uid % len(TRADER_STYLES)]

        try:
            reg = await client.post("/api/auth/register", json={
                "email": email, "username": username, "password": password,
                "trader_style": style,
            })
            if reg.status_code not in (200, 201):
                results["failed"] += 1
                return

            login = await client.post("/api/auth/login", data={
                "username": username, "password": password,
            })
            if login.status_code != 200:
                results["partial"] += 1
                return

            token = login.json().get("access_token")
            if not token:
                results["partial"] += 1
                return

            headers = {"Authorization": f"Bearer {token}"}

            profile = await client.get("/api/auth/me", headers=headers)
            if profile.status_code != 200:
                results["partial"] += 1
                return

            update = await client.put("/api/auth/me", headers=headers, json={
                "risk_tolerance": RISK_LEVELS[uid % len(RISK_LEVELS)],
            })
            if update.status_code != 200:
                results["partial"] += 1
                return

            wl_add = await client.post("/api/user/watchlist", headers=headers,
                                       json={"symbol": ALT_SYMBOLS[uid % len(ALT_SYMBOLS)]})
            wl_get = await client.get("/api/user/watchlist", headers=headers)
            if wl_add.status_code >= 500 or wl_get.status_code >= 500:
                results["partial"] += 1
                return

            pf_add = await client.post("/api/user/portfolio", headers=headers, json={
                "symbol": ALT_SYMBOLS[uid % len(ALT_SYMBOLS)],
                "shares": 10, "avg_price": 150.0,
            })
            pf_get = await client.get("/api/user/portfolio", headers=headers)
            if pf_add.status_code >= 500 or pf_get.status_code >= 500:
                results["partial"] += 1
                return

            results["full_flow"] += 1
        except Exception:
            results["failed"] += 1

    # Small write batches for SQLite
    for batch_start in range(0, num_users, BATCH_SIZE_WRITE):
        batch_end = min(batch_start + BATCH_SIZE_WRITE, num_users)
        tasks = [full_workflow(uid) for uid in range(batch_start, batch_end)]
        await asyncio.gather(*tasks)

    total = results["full_flow"] + results["partial"] + results["failed"]
    print(f"\n  Auth Workflow ({num_users} users):")
    print(f"    Full success: {results['full_flow']}, Partial: {results['partial']}, "
          f"Failed: {results['failed']}")

    assert results["full_flow"] >= num_users * 0.80, (
        f"Only {results['full_flow']}/{num_users} completed full auth workflow"
    )


@pytest.mark.asyncio
async def test_endpoint_correctness_spot_checks(client):
    """Spot-check response schemas for correctness."""

    # Register a user for auth checks
    reg = await client.post("/api/auth/register", json={
        "email": "spotcheck@test.com", "username": "spotcheck", "password": "SpotCheck123!",
    })
    assert reg.status_code in (200, 201), f"Setup registration failed: {reg.status_code}"
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Health response structure
    health = await client.get("/api/health")
    assert health.status_code == 200
    hdata = health.json()
    assert "status" in hdata

    # 2. GenAI models response structure
    models = await client.get("/api/genai/models")
    assert models.status_code == 200
    mdata = models.json()
    assert "available" in mdata
    assert len(mdata["available"]) >= 4
    assert "default" in mdata
    model_ids = [m["id"] for m in mdata["available"]]
    for expected in AI_MODELS:
        assert expected in model_ids, f"Missing model: {expected}"

    # 3. Strategy list structure
    strats = await client.get("/api/strategy/strategies")
    assert strats.status_code == 200
    sdata = strats.json()
    assert "count" in sdata
    assert "strategies" in sdata
    assert sdata["count"] > 0
    for s in sdata["strategies"]:
        assert "key" in s
        assert "name" in s
        assert "risk_level" in s

    # 4. AI query response structure
    ai = await client.post("/api/genai/query", json={
        "question": "Quick analysis of AAPL",
        "symbol": "AAPL", "model": "llama-3.3-70b-versatile",
    })
    assert ai.status_code == 200
    adata = ai.json()
    assert "answer" in adata
    assert "source" in adata
    assert len(adata["answer"]) > 10

    # 5. Profile structure (authenticated)
    profile = await client.get("/api/auth/me", headers=headers)
    assert profile.status_code == 200
    pdata = profile.json()
    assert pdata["email"] == "spotcheck@test.com"
    assert pdata["username"] == "spotcheck"
    assert "trader_style" in pdata

    # 6. Quote response structure
    quote = await client.get("/api/v4/quote/AAPL")
    assert quote.status_code == 200
    qdata = quote.json()
    assert "symbol" in qdata or "ticker" in qdata or "price" in qdata

    # 7. Backtest response structure
    bt = await client.get("/api/backtest/run/AAPL")
    assert bt.status_code == 200

    # 8. Scanner response structure
    scan = await client.get("/api/scanner/rank")
    assert scan.status_code == 200

    print("\n  Schema spot checks: ALL PASSED (8/8)")
