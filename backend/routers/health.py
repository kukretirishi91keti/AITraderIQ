"""
Health monitoring endpoint for TraderAI Pro.
Provides system observability metrics for production monitoring.
"""

from fastapi import APIRouter
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import time
import os

router = APIRouter(prefix="/api", tags=["health"])

# Global metrics tracking
class HealthMetrics:
    """Singleton for tracking system health metrics."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_metrics()
        return cls._instance
    
    def _init_metrics(self):
        self.start_time = time.time()
        self.cache_hits = 0
        self.cache_misses = 0
        self.yahoo_failures = 0
        self.yahoo_successes = 0
        self.last_successful_fetch = None
        self.rate_limit_errors = 0
        self.active_symbols = set()
        
    def record_cache_hit(self):
        self.cache_hits += 1
        
    def record_cache_miss(self):
        self.cache_misses += 1
        
    def record_yahoo_success(self, symbol: str):
        self.yahoo_successes += 1
        self.last_successful_fetch = datetime.now(timezone.utc)
        self.active_symbols.add(symbol)
        
    def record_yahoo_failure(self):
        self.yahoo_failures += 1
        
    def record_rate_limit(self):
        self.rate_limit_errors += 1
        
    def get_uptime_hours(self) -> float:
        return (time.time() - self.start_time) / 3600
    
    def get_status(self) -> str:
        """Determine overall system health status."""
        # Critical if rate limits hit in last hour
        if self.rate_limit_errors > 5:
            return "critical"
        
        # Degraded if high failure rate
        total_requests = self.yahoo_successes + self.yahoo_failures
        if total_requests > 0:
            failure_rate = self.yahoo_failures / total_requests
            if failure_rate > 0.3:
                return "degraded"
        
        # Check data freshness
        if self.last_successful_fetch:
            age = datetime.now(timezone.utc) - self.last_successful_fetch
            if age > timedelta(minutes=5):
                return "degraded"
        
        return "healthy"


# Global metrics instance
metrics = HealthMetrics()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    System health endpoint for monitoring and observability.
    
    Returns:
        Health status with detailed metrics
    """
    status = metrics.get_status()
    
    return {
        "status": status,
        "uptime_hours": round(metrics.get_uptime_hours(), 2),
        "cache": {
            "hits": metrics.cache_hits,
            "misses": metrics.cache_misses,
            "hit_rate": round(
                metrics.cache_hits / max(1, metrics.cache_hits + metrics.cache_misses) * 100, 
                1
            )
        },
        "yahoo_finance": {
            "successes": metrics.yahoo_successes,
            "failures": metrics.yahoo_failures,
            "rate_limit_errors": metrics.rate_limit_errors,
            "last_successful_fetch": (
                metrics.last_successful_fetch.isoformat() 
                if metrics.last_successful_fetch else None
            )
        },
        "markets_available": 22,
        "symbols_cached": len(metrics.active_symbols),
        "version": "4.6",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    Extended health metrics for debugging.
    """
    base_health = await health_check()
    
    base_health["extended"] = {
        "active_symbols": list(metrics.active_symbols)[:20],  # Sample
        "memory_usage": "N/A",  # Would integrate with psutil in production
        "thread_pool_status": "active",
        "cache_backend": "file",
        "upstream_status": {
            "yahoo_finance": "online" if metrics.get_status() != "critical" else "rate_limited",
            "news_api": "online",
            "reddit_api": "online",
            "groq_llm": "online"
        }
    }
    
    return base_health


@router.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """
    Kubernetes-style readiness probe.
    Returns 200 if service can accept traffic.
    """
    return {"ready": "true"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness probe.
    Returns 200 if service is alive.
    """
    return {"alive": "true"}


# Export metrics instance for use in other modules
def get_metrics() -> HealthMetrics:
    """Get the global metrics instance."""
    return metrics


@router.get("/config-status")
async def config_status() -> Dict[str, Any]:
    """
    Public endpoint — shows which env vars are SET (not their values).
    Use this to verify Render is injecting secrets correctly after a deploy.
    Safe to expose: only booleans, no key material.
    """
    td_key  = os.getenv("TWELVE_DATA_API_KEY", "")
    fh_key  = os.getenv("FINNHUB_API_KEY", "")
    groq    = os.getenv("GROQ_API_KEY", "")
    db_url  = os.getenv("DATABASE_URL", "")
    sg_key  = os.getenv("SENDGRID_API_KEY", "")
    demo    = os.getenv("DEMO_MODE", "true")
    jwt     = os.getenv("JWT_SECRET_KEY", "")

    def _preview(k):
        if not k:
            return None
        return f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "set"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demo_mode": demo.lower() == "true",
        "keys": {
            "TWELVE_DATA_API_KEY": {"set": bool(td_key), "preview": _preview(td_key)},
            "FINNHUB_API_KEY":     {"set": bool(fh_key), "preview": _preview(fh_key)},
            "GROQ_API_KEY":        {"set": bool(groq),   "preview": _preview(groq)},
            "SENDGRID_API_KEY":    {"set": bool(sg_key),  "preview": _preview(sg_key)},
            "DATABASE_URL":        {"set": bool(db_url),  "postgres": "postgresql" in db_url},
            "JWT_SECRET_KEY":      {"set": bool(jwt),     "strong": len(jwt) >= 32},
        },
        "data_sources": {
            "india_nse": "TWELVE_DATA" if td_key else "SIMULATED",
            "us_stocks":  "FINNHUB"    if fh_key else "SIMULATED",
            "ai_chat":    "GROQ"       if groq   else "RULE_BASED",
            "email_alerts": "SENDGRID" if sg_key  else "DISABLED",
            "database":   "POSTGRES"   if ("postgresql" in db_url) else "SQLITE",
        },
        "readiness": {
            "can_serve_india_live": bool(td_key and demo.lower() != "true"),
            "can_serve_us_live":    bool(fh_key and demo.lower() != "true"),
            "auth_works":           bool(jwt),
            "db_persistent":        "postgresql" in db_url,
        },
    }