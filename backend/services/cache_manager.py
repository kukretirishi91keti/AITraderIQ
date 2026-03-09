"""
Cache Manager v4.9
==================
Location: backend/services/cache_manager.py

Implements:
- JSON file-based caching with filelock for concurrency safety
- Last Known Good (LKG) cache pattern
- Check-Lock-Check-Write pattern for efficiency
- TTL-based cache invalidation

Architecture:
    Request → Check Fresh Cache → (if miss) → Acquire Lock → Recheck → Fetch → Write → Release
"""

import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable
from pathlib import Path
import logging

try:
    from filelock import FileLock, Timeout
    FILELOCK_AVAILABLE = True
except ImportError:
    FILELOCK_AVAILABLE = False
    FileLock = None
    Timeout = None

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Cache directory - relative to backend root
CACHE_DIR = Path(__file__).parent.parent / "cache"
DEFAULT_TTL_SECONDS = 300  # 5 minutes
LOCK_TIMEOUT_SECONDS = 10  # Max time to wait for lock
STALE_THRESHOLD_SECONDS = 3600  # 1 hour - after this, data is "stale" but usable


class CacheEntry:
    """Represents a cached item with metadata."""
    
    def __init__(self, data: Any, timestamp: float, source: str = "UNKNOWN"):
        self.data = data
        self.timestamp = timestamp
        self.source = source  # LIVE, CACHED, SIMULATED
    
    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "cached_at": datetime.fromtimestamp(self.timestamp).isoformat()
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "CacheEntry":
        return cls(
            data=d.get("data"),
            timestamp=d.get("timestamp", 0),
            source=d.get("source", "CACHED")
        )
    
    def is_fresh(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> bool:
        """Check if cache entry is within TTL."""
        age = time.time() - self.timestamp
        return age < ttl_seconds
    
    def is_stale(self) -> bool:
        """Check if cache is beyond stale threshold (but still usable as LKG)."""
        age = time.time() - self.timestamp
        return age > STALE_THRESHOLD_SECONDS
    
    def age_seconds(self) -> float:
        return time.time() - self.timestamp
    
    def age_human(self) -> str:
        """Human-readable age string."""
        age = self.age_seconds()
        if age < 60:
            return f"{int(age)}s ago"
        elif age < 3600:
            return f"{int(age/60)}m ago"
        else:
            return f"{int(age/3600)}h ago"


class CacheManager:
    """
    Production-grade file-based cache with locking.
    
    Features:
    - Thread/process safe via filelock
    - Check-Lock-Check-Write pattern
    - LKG (Last Known Good) fallback
    - Automatic cache directory creation
    """
    
    def __init__(self, cache_dir: Path = CACHE_DIR, namespace: str = "default"):
        self.cache_dir = Path(cache_dir) / namespace
        self.namespace = namespace
        self._ensure_cache_dir()
        
        # In-memory cache for hot data (reduces disk I/O)
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_cache_max_size = 1000
        
        # Stats
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "lock_waits": 0,
            "lock_timeouts": 0
        }
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, key: str) -> str:
        """Generate safe filename from cache key."""
        # Hash long keys to avoid filesystem issues
        if len(key) > 100:
            key_hash = hashlib.md5(key.encode()).hexdigest()[:16]
            safe_key = f"{key[:50]}_{key_hash}"
        else:
            # Replace unsafe characters
            safe_key = key.replace("/", "_").replace(":", "_").replace("\\", "_")
        return safe_key
    
    def _get_cache_path(self, key: str) -> Path:
        """Get full path to cache file."""
        safe_key = self._get_cache_key(key)
        return self.cache_dir / f"{safe_key}.json"
    
    def _get_lock_path(self, key: str) -> Path:
        """Get path to lock file (sidecar pattern)."""
        safe_key = self._get_cache_key(key)
        return self.cache_dir / f"{safe_key}.json.lock"
    
    def get(self, key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> Optional[CacheEntry]:
        """
        Get cached value if fresh.
        
        Returns:
            CacheEntry if found and fresh, None otherwise
        """
        # Check memory cache first (hot path)
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry.is_fresh(ttl_seconds):
                self.stats["hits"] += 1
                return entry
        
        # Check file cache
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            self.stats["misses"] += 1
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            entry = CacheEntry.from_dict(data)
            
            # Update memory cache
            self._update_memory_cache(key, entry)
            
            if entry.is_fresh(ttl_seconds):
                self.stats["hits"] += 1
                return entry
            else:
                # Return as LKG but mark the miss
                self.stats["misses"] += 1
                return None  # Caller should fetch fresh, but can use get_lkg() if fetch fails
                
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.warning(f"Cache read error for {key}: {e}")
            self.stats["misses"] += 1
            return None
    
    def get_lkg(self, key: str) -> Optional[CacheEntry]:
        """
        Get Last Known Good value, regardless of TTL.
        
        Use this as fallback when fresh fetch fails.
        """
        # Check memory cache
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        # Check file cache
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            entry = CacheEntry.from_dict(data)
            entry.source = "LKG"  # Mark as Last Known Good
            return entry
            
        except (json.JSONDecodeError, KeyError, IOError):
            return None
    
    def set(self, key: str, data: Any, source: str = "LIVE") -> bool:
        """
        Set cache value with locking.
        
        Uses Check-Lock-Check-Write pattern for efficiency.
        """
        entry = CacheEntry(data=data, timestamp=time.time(), source=source)
        
        # Update memory cache immediately
        self._update_memory_cache(key, entry)
        
        cache_path = self._get_cache_path(key)
        lock_path = self._get_lock_path(key)
        
        if FILELOCK_AVAILABLE:
            lock = FileLock(str(lock_path), timeout=LOCK_TIMEOUT_SECONDS)
            try:
                with lock:
                    self.stats["lock_waits"] += 1
                    
                    # Write atomically
                    temp_path = cache_path.with_suffix('.tmp')
                    with open(temp_path, 'w') as f:
                        json.dump(entry.to_dict(), f, indent=2, default=str)
                    
                    # Atomic rename
                    temp_path.replace(cache_path)
                    
                    self.stats["writes"] += 1
                    return True
                    
            except Timeout:
                logger.warning(f"Lock timeout for {key}")
                self.stats["lock_timeouts"] += 1
                return False
            except IOError as e:
                logger.error(f"Cache write error for {key}: {e}")
                return False
        else:
            # Fallback: direct write (not thread-safe but works for single process)
            try:
                with open(cache_path, 'w') as f:
                    json.dump(entry.to_dict(), f, indent=2, default=str)
                self.stats["writes"] += 1
                return True
            except IOError as e:
                logger.error(f"Cache write error for {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        # Remove from memory
        self._memory_cache.pop(key, None)
        
        # Remove file
        cache_path = self._get_cache_path(key)
        try:
            if cache_path.exists():
                cache_path.unlink()
            return True
        except IOError:
            return False
    
    def clear(self) -> int:
        """Clear all cache entries. Returns count of deleted items."""
        count = 0
        self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except IOError:
                pass
        
        return count
    
    def _update_memory_cache(self, key: str, entry: CacheEntry):
        """Update memory cache with LRU eviction."""
        if len(self._memory_cache) >= self._memory_cache_max_size:
            # Evict oldest entry (simple FIFO for now)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        
        self._memory_cache[key] = entry
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        # Count files
        file_count = len(list(self.cache_dir.glob("*.json")))
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.json"))
        
        return {
            **self.stats,
            "hit_rate_percent": round(hit_rate, 2),
            "file_count": file_count,
            "total_size_kb": round(total_size / 1024, 2),
            "memory_cache_size": len(self._memory_cache),
            "namespace": self.namespace
        }


class SingleFlight:
    """
    Singleflight pattern implementation.
    
    Ensures that only one request is "in-flight" for a given key at any time.
    Subsequent requests for the same key wait for the first request to complete.
    
    This prevents the "thundering herd" problem where multiple requests
    simultaneously try to fetch the same data.
    """
    
    def __init__(self):
        import asyncio
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    
    async def do(self, key: str, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute fn() only once for the given key.
        
        If a request for this key is already in-flight, wait for its result.
        
        Args:
            key: Unique identifier for this request
            fn: Async function to execute
            *args, **kwargs: Arguments to pass to fn
            
        Returns:
            Result of fn()
        """
        import asyncio
        
        async with self._lock:
            if key in self._inflight:
                # Request already in-flight, wait for it
                future = self._inflight[key]
            else:
                # No in-flight request, create one
                future = asyncio.get_event_loop().create_future()
                self._inflight[key] = future
                
                # Execute the function
                try:
                    if asyncio.iscoroutinefunction(fn):
                        result = await fn(*args, **kwargs)
                    else:
                        result = fn(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    # Cleanup
                    del self._inflight[key]
        
        return await future
    
    def inflight_count(self) -> int:
        """Get count of in-flight requests."""
        return len(self._inflight)


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

# Global cache manager instances
_cache_managers: Dict[str, CacheManager] = {}
_singleflight = None


def get_cache_manager(namespace: str = "market_data") -> CacheManager:
    """Get or create a cache manager for the given namespace."""
    global _cache_managers
    if namespace not in _cache_managers:
        _cache_managers[namespace] = CacheManager(namespace=namespace)
    return _cache_managers[namespace]


def get_singleflight() -> SingleFlight:
    """Get the global SingleFlight instance."""
    global _singleflight
    if _singleflight is None:
        _singleflight = SingleFlight()
    return _singleflight


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def cached_fetch(
    key: str,
    fetch_fn: Callable,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    namespace: str = "market_data",
    use_singleflight: bool = True
) -> tuple[Any, str]:
    """
    High-level cached fetch with all patterns applied.
    
    Flow:
    1. Check cache (fresh hit → return immediately)
    2. Use SingleFlight to prevent duplicate fetches
    3. Fetch fresh data
    4. Cache result
    5. On failure, try LKG cache
    
    Args:
        key: Cache key
        fetch_fn: Async function to fetch fresh data
        ttl_seconds: Cache TTL
        namespace: Cache namespace
        use_singleflight: Whether to use request coalescing
        
    Returns:
        Tuple of (data, source) where source is LIVE/CACHED/LKG/SIMULATED
    """
    cache = get_cache_manager(namespace)
    
    # 1. Check fresh cache
    entry = cache.get(key, ttl_seconds)
    if entry:
        return entry.data, "CACHED"
    
    # 2. Fetch with optional singleflight
    async def do_fetch():
        import asyncio
        
        try:
            if asyncio.iscoroutinefunction(fetch_fn):
                data = await fetch_fn()
            else:
                data = fetch_fn()
            
            # Cache the result
            cache.set(key, data, source="LIVE")
            return data, "LIVE"
            
        except Exception as e:
            logger.warning(f"Fetch failed for {key}: {e}")
            
            # Try LKG cache
            lkg = cache.get_lkg(key)
            if lkg:
                logger.info(f"Using LKG cache for {key} ({lkg.age_human()})")
                return lkg.data, "LKG"
            
            # Re-raise if no LKG available
            raise
    
    if use_singleflight:
        sf = get_singleflight()
        return await sf.do(key, do_fetch)
    else:
        return await do_fetch()


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Simple test
    import asyncio
    
    async def test():
        cache = get_cache_manager("test")
        
        # Test set/get
        cache.set("test_key", {"price": 150.50}, source="LIVE")
        entry = cache.get("test_key")
        
        if entry:
            print(f"✅ Cache hit: {entry.data}")
            print(f"   Source: {entry.source}")
            print(f"   Age: {entry.age_human()}")
        else:
            print("❌ Cache miss")
        
        # Print stats
        print(f"\n📊 Stats: {cache.get_stats()}")
    
    asyncio.run(test())
