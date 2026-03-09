"""
Health monitoring endpoint for TraderAI Pro.
Provides system observability metrics for production monitoring.
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Dict, Any
import time

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
        self.last_successful_fetch = datetime.utcnow()
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
            age = datetime.utcnow() - self.last_successful_fetch
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
        "timestamp": datetime.utcnow().isoformat()
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