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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check demo mode from environment
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
VERSION = "5.7.1"

# Track loaded routers
loaded_routers = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    print("\n" + "=" * 70)
    print(f"🚀 TraderAI Pro API v{VERSION} - PRODUCTION READY")
    print("=" * 70)
    print(f"📊 AI-Powered Decision Support Dashboard for Day Traders")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎮 Demo Mode: {'ENABLED ✅' if DEMO_MODE else 'DISABLED (Live Mode)'}")
    print("=" * 70)
    
    # Print loaded routers
    print("\n📡 Registered Routes:")
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                if method in ['GET', 'POST', 'PUT', 'DELETE']:
                    routes.append(f"   {method:6} {route.path}")
    
    for r in sorted(routes)[:25]:
        print(r)
    if len(routes) > 25:
        print(f"   ... and {len(routes) - 25} more routes")
    print(f"\n   Total: {len(routes)} API routes registered")
    
    print("\n" + "=" * 70)
    print("🌐 API Documentation: http://localhost:8000/docs")
    print("📖 ReDoc Documentation: http://localhost:8000/redoc")
    print("📊 Health Check: http://localhost:8000/api/health")
    print("=" * 70 + "\n")
    
    yield
    
    print("\n🛑 TraderAI Pro shutting down...")


# Create FastAPI app
app = FastAPI(
    title="TraderAI Pro API",
    description="AI-Powered Trading Dashboard with Real-Time Analysis",
    version=VERSION,
    lifespan=lifespan
)

# CORS configuration - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================
# ROUTER IMPORTS - Load all routers with proper fallbacks
# ============================================================

def load_router(module_paths, router_name, description=""):
    """Try to load a router from multiple possible paths."""
    for path in module_paths:
        try:
            if '.' in path:
                parts = path.rsplit('.', 1)
                module = __import__(parts[0], fromlist=[parts[1]])
                router = getattr(module, parts[1])
            else:
                module = __import__(path)
                router = getattr(module, 'router')
            
            app.include_router(router)
            loaded_routers.append(router_name)
            logger.info(f"✅ {router_name} loaded {description}")
            return True
        except ImportError as e:
            continue
        except Exception as e:
            logger.warning(f"Error loading {router_name} from {path}: {e}")
            continue
    
    logger.warning(f"⚠️  {router_name} not available")
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


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
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
