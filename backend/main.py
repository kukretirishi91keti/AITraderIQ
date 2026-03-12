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
import logging
import os
import sys
from datetime import datetime

# Add the backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
VERSION = "6.0.0"  # Production release - March 2026

# Track loaded routers
loaded_routers = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Initialize database
    try:
        from database.engine import init_db, close_db
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init failed (non-fatal): {e}")

    # Start batch data service (pre-fetches popular symbols for 1000+ concurrent users)
    try:
        from services.batch_data_service import get_batch_data_service
        batch_svc = get_batch_data_service()
        await batch_svc.start()
        logger.info("Batch data service started")
    except Exception as e:
        logger.warning(f"Batch data service init failed (non-fatal): {e}")

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

    yield

    # Cleanup
    try:
        from services.batch_data_service import get_batch_data_service
        await get_batch_data_service().stop()
    except Exception:
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

# CORS configuration - Restrict to known frontend origins
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:4173").split(",")
]
# In production, add your deployed frontend domain to CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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
    '(movers, universe, signals)'
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

# Phase 3: Price Alerts
load_router(
    ['routers.alerts'],
    'alerts router',
    '(price alerts engine)'
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
    """Deep health check with subsystem status."""
    subsystems = {}

    # Market data service
    try:
        from services.market_data_service import get_market_data_service
        svc = get_market_data_service()
        svc_status = svc.get_service_status()
        subsystems["market_data"] = {
            "status": svc_status["health"].lower(),
            "yfinance": svc_status["yfinance_available"],
            "circuit_breaker": svc_status["circuit_breaker"]["state"],
        }
    except Exception:
        subsystems["market_data"] = {"status": "unknown"}

    # Batch data service
    try:
        from services.batch_data_service import get_batch_data_service
        batch = get_batch_data_service()
        batch_stats = batch.get_stats()
        subsystems["batch_data"] = {
            "status": "running" if batch_stats["running"] else "stopped",
            "symbols_tracked": batch_stats["symbols_tracked"],
            "cache_size": batch_stats["cache_size"],
        }
    except Exception:
        subsystems["batch_data"] = {"status": "not_available"}

    # Alerts engine
    try:
        from services.alerts_engine import get_alerts_engine
        alerts = get_alerts_engine()
        subsystems["alerts"] = alerts.get_stats()
    except Exception:
        subsystems["alerts"] = {"status": "not_available"}

    # GenAI
    try:
        groq_key = bool(os.getenv("GROQ_API_KEY"))
        subsystems["genai"] = {
            "status": "configured" if groq_key else "fallback_mode",
            "provider": "groq" if groq_key else "rule_based",
        }
    except Exception:
        subsystems["genai"] = {"status": "unknown"}

    overall = "healthy"
    if any(s.get("status") in ("degraded", "critical") for s in subsystems.values()):
        overall = "degraded"

    return {
        "status": overall,
        "version": VERSION,
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now().isoformat(),
        "loaded_routers": loaded_routers,
        "subsystems": subsystems,
        "polling_recommendation": 30 if overall == "healthy" else 60,
    }


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
