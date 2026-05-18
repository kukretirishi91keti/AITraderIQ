"""
TraderAI Pro - Main Application Entry Point v5.7.1
===================================================
Place this file in: backend/main.py

FIXES in v5.7.1:
- Proper router loading order
- All routers loaded with fallbacks
- Better error handling and logging

Features:
- Demo mode toggle for reliable presentations
- Real sentiment API integration (StockTwits, Reddit)
- Production-hardened with circuit breaker
- Graceful degradation to demo data
"""
from dotenv import load_dotenv
load_dotenv()

from validate_env import validate_environment
validate_environment()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Error tracking (Sentry — no-op when SENTRY_DSN is not set)
try:
    import sentry_sdk
    _sentry_dsn = os.getenv("SENTRY_DSN", "")
    if _sentry_dsn:
        sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1, environment=os.getenv("RAILWAY_ENVIRONMENT", "production"))
        logging.getLogger(__name__).info("Sentry error tracking enabled")
except ImportError:
    pass  # sentry-sdk not installed

# Rate limiting
try:
    from middleware.rate_limit import setup_rate_limiting
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False

# Configure structured logging
try:
    from logging_config import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

# Check demo mode from environment
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
VERSION = "6.0.0"

# Track loaded routers
loaded_routers = []


_NIFTY_WARM_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BAJFINANCE.NS", "BHARTIARTL.NS", "SBIN.NS", "LT.NS", "KOTAKBANK.NS",
    "WIPRO.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
]

async def _warm_nifty_cache():
    """Staggered startup fetch for top NSE stocks — populates LKG cache so
    the first real user request is a cache hit instead of a cold Twelve Data call."""
    await asyncio.sleep(5)  # Let the server finish starting up first
    try:
        from services.market_data_service import get_market_data_service
        svc = get_market_data_service()
        for sym in _NIFTY_WARM_SYMBOLS:
            try:
                await svc.get_quote(sym)
                logger.info(f"Cache warm: {sym}")
            except Exception as e:
                logger.warning(f"Cache warm failed for {sym}: {e}")
            await asyncio.sleep(8)  # 8s gap → max ~7.5 req/min, under Twelve Data 8/min limit
    except Exception as e:
        logger.warning(f"Cache warmer error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Initialize database - CRITICAL for auth to work
    db_ready = False
    monitor_task = None
    try:
        from database.engine import init_db, close_db, AsyncSessionLocal
        await init_db()
        db_ready = True
        logger.info("Database initialized successfully")
        print("  Database: READY (tables created)")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        print(f"  Database: FAILED - {e}")
        print("  WARNING: Login/register will NOT work without database!")
        print("  Check DATABASE_URL in your .env file")

    # Start paper trade stop-loss/take-profit monitor
    if db_ready:
        try:
            from services.paper_trade_monitor import monitor_paper_trades
            monitor_task = asyncio.create_task(
                monitor_paper_trades(AsyncSessionLocal, interval_seconds=60)
            )
            print("  Paper Trade Monitor: RUNNING (60s interval)")
        except Exception as e:
            logger.warning(f"Paper trade monitor failed to start: {e}")

    print("\n" + "=" * 70)
    print(f"  TraderAI Pro API v{VERSION} - PRODUCTION READY")
    print("=" * 70)
    print(f"  AI-Powered Decision Support Dashboard for Day Traders")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Demo Mode: {'ENABLED' if DEMO_MODE else 'DISABLED (Live Mode)'}")
    print("=" * 70)

    # Print loaded routers
    print("\n  Registered Routes:")
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                if method in ['GET', 'POST', 'PUT', 'DELETE']:
                    routes.append(f"   {method:6} {route.path}")

    for r in sorted(routes)[:30]:
        print(r)
    if len(routes) > 30:
        print(f"   ... and {len(routes) - 30} more routes")
    print(f"\n   Total: {len(routes)} API routes registered")

    print("\n" + "=" * 70)
    print("  API Documentation: http://localhost:8000/docs")
    print("  Health Check: http://localhost:8000/api/health")
    print("  WebSocket: ws://localhost:8000/ws/prices")
    print("=" * 70 + "\n")

    # Pre-warm LKG cache for top Nifty 50 stocks so first-user requests hit cache
    asyncio.create_task(_warm_nifty_cache())

    yield

    # Cleanup
    if monitor_task is not None:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    try:
        from database.engine import close_db
        await close_db()
    except Exception:
        pass
    print("\n  TraderAI Pro shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TraderAI Pro API",
    description="AI-Powered Trading Dashboard with Real-Time Analysis",
    version=VERSION,
    lifespan=lifespan
)

# CORS configuration - Allow frontend origins
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    ALLOWED_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://aitraderiq.netlify.app",
    ]

# In demo mode, also allow any netlify preview deploys
if os.getenv("DEMO_MODE", "").lower() == "true":
    ALLOWED_ORIGINS.append("https://*.netlify.app")

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")
print(f"  CORS Origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://aitraderiq\.netlify\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Request logging middleware
try:
    from middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware enabled")
except ImportError:
    logger.warning("Request logging middleware not available")

# Setup rate limiting
if RATE_LIMITING_AVAILABLE:
    setup_rate_limiting(app)
    logger.info("Rate limiting enabled")
else:
    logger.warning("slowapi not installed - rate limiting disabled. Run: pip install slowapi")

# Global exception handler - never leak internal details to clients
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================
# ROUTER IMPORTS - Load all routers with proper fallbacks
# ============================================================

def load_router(module_paths, router_name, description=""):
    """Try to load a router from multiple possible paths."""
    from importlib import import_module
    for path in module_paths:
        try:
            module = import_module(path)
            router = getattr(module, 'router')
            app.include_router(router)
            loaded_routers.append(router_name)
            logger.info(f"  {router_name} loaded {description}")
            return True
        except ImportError:
            continue
        except Exception as e:
            logger.warning(f"Error loading {router_name} from {path}: {e}")
            continue

    logger.warning(f"  {router_name} not available")
    return False


# Load stock router (quotes, history, signals, financials)
load_router(
    ['routers.stock', 'stock'],
    'stock router',
    '(quote, history, signals, financials)'
)

# Load stock_router (additional endpoints)
load_router(
    ['stock_router', 'routers.stock_router'],
    'stock_router',
    '(sentiment, news)'
)

# Load screener
load_router(
    ['routers.screener', 'screener'],
    'screener router',
    '(movers, signals)'
)

# Load screener universe (GET /api/screener/universe — 22 market categories)
load_router(
    ['routers.screener_universe'],
    'screener_universe router',
    '(universe)'
)

# Load health router
load_router(
    ['routers.health', 'health'],
    'health router',
    ''
)

# Load signals router
load_router(
    ['routers.signals', 'signals'],
    'signals router',
    ''
)

# Load genai router
load_router(
    ['routers.genai', 'genai'],
    'genai router',
    '(AI assistant)'
)

# Load roadmap router
load_router(
    ['routers.roadmap', 'roadmap'],
    'roadmap router',
    ''
)

# Load auth router (register, login, profile)
load_router(
    ['routers.auth'],
    'auth router',
    '(register, login, profile)'
)

# Load user data router (watchlist, portfolio, alerts - DB-backed)
load_router(
    ['routers.user_data'],
    'user data router',
    '(watchlist, portfolio, alerts)'
)

# Load WebSocket router (real-time price streaming)
load_router(
    ['routers.websocket'],
    'websocket router',
    '(real-time prices)'
)

# Phase 2: Backtesting, Sentiment, Commentary, Scanner
load_router(
    ['routers.backtest'],
    'backtest router',
    '(signal accuracy, strategy comparison)'
)

load_router(
    ['routers.sentiment'],
    'sentiment router',
    '(combined sentiment aggregation)'
)

load_router(
    ['routers.commentary'],
    'commentary router',
    '(AI market commentary)'
)

load_router(
    ['routers.scanner'],
    'scanner router',
    '(AI-ranked opportunities)'
)

# Load strategy intelligence router
load_router(
    ['routers.strategy'],
    'strategy router',
    '(strategy intelligence, growth projections)'
)

# Load subscription/payment router
load_router(
    ['routers.subscription'],
    'subscription router',
    '(plans, checkout, billing)'
)

# Load paper trade router
load_router(
    ['routers.paper_trade'],
    'paper trade router',
    '(paper trading simulation)'
)


# ============================================================
# ROOT ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "TraderAI Pro API",
        "version": VERSION,
        "status": "running",
        "demo_mode": DEMO_MODE,
        "docs": "/docs",
        "health": "/api/health",
        "loaded_routers": loaded_routers,
        "features": [
            "Multi-market quotes (22 markets)",
            "Technical analysis (RSI, MACD, VWAP, Bollinger)",
            "AI assistant (Groq)",
            "Social sentiment (StockTwits, Reddit)",
            "Screener with RSI filtering",
            "Circuit breaker protection",
            "Demo mode for reliable demos"
        ]
    }


@app.get("/ping")
async def ping():
    """Simple ping endpoint for health checks."""
    return {"pong": True, "timestamp": datetime.now().isoformat()}


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "api": "running",
        "version": VERSION,
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now().isoformat(),
        "loaded_routers": loaded_routers
    }


@app.get("/api/health")
async def api_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": VERSION,
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now().isoformat(),
        "loaded_routers": loaded_routers
    }


@app.get("/api/debug/data-pipeline")
async def debug_data_pipeline():
    """
    Diagnostic: tests every data source for RELIANCE.NS and reports results.
    Visit this URL in your browser to see exactly why live data is/isn't working.
    """
    import os, httpx
    results = {}

    # 1. Env vars (masked)
    td_key = os.getenv("TWELVE_DATA_API_KEY", "")
    fh_key = os.getenv("FINNHUB_API_KEY", "")
    results["env"] = {
        "DEMO_MODE": os.getenv("DEMO_MODE", "true"),
        "TWELVE_DATA_API_KEY": f"{td_key[:6]}...{td_key[-4:]}" if len(td_key) > 10 else ("SET(short)" if td_key else "NOT SET"),
        "FINNHUB_API_KEY": f"{fh_key[:4]}..." if fh_key else "NOT SET",
        "GROQ_API_KEY": "SET" if os.getenv("GROQ_API_KEY") else "NOT SET",
    }

    # 2. Twelve Data test (RELIANCE:NSE)
    if td_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.twelvedata.com/quote",
                    params={"symbol": "RELIANCE:NSE", "apikey": td_key},
                )
                d = r.json()
            results["twelve_data"] = {
                "status": d.get("status", "unknown"),
                "has_close": "close" in d,
                "price": d.get("close"),
                "error": d.get("message") if d.get("status") == "error" else None,
                "code": d.get("code"),
            }
        except Exception as e:
            results["twelve_data"] = {"error": str(e)}
    else:
        results["twelve_data"] = {"error": "TWELVE_DATA_API_KEY not set"}

    # 3. yfinance test (RELIANCE.NS)
    try:
        import asyncio
        from starlette.concurrency import run_in_threadpool
        import yfinance as yf
        def _test_yf():
            t = yf.Ticker("RELIANCE.NS")
            fi = t.fast_info
            return {"price": fi.last_price, "currency": fi.currency}
        yf_result = await asyncio.wait_for(run_in_threadpool(_test_yf), timeout=10.0)
        results["yfinance"] = {"ok": True, **yf_result}
    except Exception as e:
        results["yfinance"] = {"ok": False, "error": str(e)}

    # 4. Service layer result
    try:
        from services.market_data_service import get_market_data_service, _circuit_breaker
        svc = get_market_data_service()
        quote = await svc.get_quote("RELIANCE.NS", force_refresh=True)
        results["service_quote"] = {
            "price": quote.get("price"),
            "source": quote.get("source"),
            "dataQuality": quote.get("dataQuality"),
        }
        results["circuit_breaker"] = _circuit_breaker.get_status()
    except Exception as e:
        results["service_quote"] = {"error": str(e)}

    return results


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    print(f"\n🚀 Starting TraderAI Pro on {host}:{port}")
    print(f"   Demo Mode: {'ENABLED' if DEMO_MODE else 'DISABLED'}")
    print(f"   Hot Reload: {'ENABLED' if reload else 'DISABLED'}\n")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
