"""
Production Data Service for TradingAI Pro
==========================================
Handles all yfinance data fetching with:
- Request coalescing (singleflight pattern) - 100 concurrent users = 1 API call
- fast_info instead of stock.info (10x faster)
- Timeframe-aware TTL caching
- Circuit breaker for upstream failures
- Never-cache-failures guard
- Data freshness status (LIVE/CACHED/STALE/ERROR)

Author: TradingAI Pro Team
Version: 4.0 - Production Ready
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import yfinance as yf
import pandas as pd
import pandas_ta as ta


class DataStatus(Enum):
    """Data freshness status for UI badges"""
    LIVE = "live"           # Fresh from API (< 30 seconds old)
    CACHED = "cached"       # From cache, still valid
    STALE = "stale"         # Cache expired but returned as fallback
    ERROR = "error"         # Fetch failed, using fallback/demo data
    DEMO = "demo"           # Demo/mock data (no real API call)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Dict
    timestamp: datetime
    ttl_seconds: int
    fetch_duration_ms: float = 0
    status: DataStatus = DataStatus.CACHED
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.timestamp).total_seconds()
    
    @property
    def is_valid(self) -> bool:
        return self.age_seconds < self.ttl_seconds
    
    @property
    def is_stale(self) -> bool:
        return self.age_seconds >= self.ttl_seconds
    
    @property
    def freshness_label(self) -> str:
        age = self.age_seconds
        if age < 30:
            return "LIVE"
        elif age < self.ttl_seconds:
            return "CACHED"
        else:
            return "STALE"


class CircuitBreaker:
    """
    Circuit breaker to prevent cascade failures.
    States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing)
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
        self._lock = threading.Lock()
    
    def record_success(self):
        with self._lock:
            self.failures = 0
            self.state = "CLOSED"
    
    def record_failure(self):
        with self._lock:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                print(f"🔴 Circuit breaker OPEN - {self.failures} consecutive failures")
    
    def can_execute(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                # Check if recovery timeout has passed
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self.state = "HALF_OPEN"
                        print("🟡 Circuit breaker HALF_OPEN - testing recovery")
                        return True
                return False
            
            # HALF_OPEN - allow one request to test
            return True


class RequestCoalescer:
    """
    Singleflight pattern implementation.
    When multiple requests come in for the same key simultaneously,
    only ONE actual API call is made and the result is shared.
    
    Example: 100 users request AAPL at the same time = 1 yfinance call
    """
    
    def __init__(self):
        self._pending: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    
    async def call(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute func only once for concurrent calls with the same key.
        All concurrent callers get the same result.
        """
        async with self._lock:
            if key in self._pending:
                # Another request is already in flight - wait for it
                print(f"⏳ Coalescing request for {key}")
                return await self._pending[key]
            
            # First request - create a future and execute
            future = asyncio.get_event_loop().create_future()
            self._pending[key] = future
        
        try:
            # Execute the actual function
            result = await func(*args, **kwargs)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                del self._pending[key]


class DataService:
    """
    Centralized data service for all stock data fetching.
    Uses fast_info, request coalescing, and intelligent caching.
    """
    
    # TTL configuration by data type (in seconds)
    TTL_CONFIG = {
        "quote": 60,           # Real-time quotes: 1 minute
        "1m": 30,              # 1-minute candles: 30 seconds
        "5m": 60,              # 5-minute candles: 1 minute
        "15m": 120,            # 15-minute candles: 2 minutes
        "30m": 300,            # 30-minute candles: 5 minutes
        "1h": 600,             # Hourly candles: 10 minutes
        "1d": 900,             # Daily candles: 15 minutes
        "1w": 3600,            # Weekly candles: 1 hour
        "1M": 7200,            # Monthly candles: 2 hours
        "metadata": 21600,     # Company info: 6 hours
    }
    
    TIMEFRAME_MAP = {
        "1m": {"period": "1d", "interval": "1m"},
        "5m": {"period": "5d", "interval": "5m"},
        "15m": {"period": "5d", "interval": "15m"},
        "30m": {"period": "1mo", "interval": "30m"},
        "1h": {"period": "1mo", "interval": "1h"},
        "1d": {"period": "3mo", "interval": "1d"},
        "1w": {"period": "1y", "interval": "1wk"},
        "1M": {"period": "5y", "interval": "1mo"},
    }
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._coalescer = RequestCoalescer()
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self._lock = threading.Lock()
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "coalesced_requests": 0,
            "api_calls": 0,
            "api_errors": 0,
        }
    
    def _get_cache_key(self, ticker: str, timeframe: str) -> str:
        return f"{ticker.upper()}:{timeframe}"
    
    def _get_ttl(self, timeframe: str) -> int:
        """Get TTL with 10% jitter to prevent thundering herd"""
        base_ttl = self.TTL_CONFIG.get(timeframe, 300)
        jitter = int(base_ttl * 0.1)
        return base_ttl + random.randint(-jitter, jitter)
    
    def _get_cached(self, cache_key: str) -> Optional[CacheEntry]:
        """Get cached data if valid"""
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if entry.is_valid:
                    self._stats["cache_hits"] += 1
                    return entry
                # Return stale cache for fallback
                return entry
        return None
    
    def _set_cache(self, cache_key: str, data: Dict, ttl: int, 
                   fetch_duration_ms: float, status: DataStatus):
        """Store data in cache"""
        with self._lock:
            self._cache[cache_key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                ttl_seconds=ttl,
                fetch_duration_ms=fetch_duration_ms,
                status=status
            )
    
    async def get_stock_data(self, ticker: str, timeframe: str = "1d") -> Dict:
        """
        Get stock data with caching and request coalescing.
        Returns data with freshness status for UI display.
        """
        ticker = ticker.upper().strip()
        cache_key = self._get_cache_key(ticker, timeframe)
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached and cached.is_valid:
            data = cached.data.copy()
            data["_meta"] = {
                "status": DataStatus.CACHED.value,
                "age_seconds": round(cached.age_seconds, 1),
                "cached_at": cached.timestamp.isoformat(),
                "ttl_remaining": round(cached.ttl_seconds - cached.age_seconds, 1),
            }
            return data
        
        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            # Circuit open - return stale cache or fallback
            if cached:
                data = cached.data.copy()
                data["_meta"] = {
                    "status": DataStatus.STALE.value,
                    "age_seconds": round(cached.age_seconds, 1),
                    "reason": "circuit_breaker_open"
                }
                return data
            return self._generate_fallback(ticker, timeframe, "circuit_breaker_open")
        
        # Use request coalescing for the actual fetch
        try:
            data = await self._coalescer.call(
                cache_key,
                self._fetch_stock_data,
                ticker,
                timeframe
            )
            return data
        except Exception as e:
            print(f"❌ Error fetching {ticker}: {e}")
            self._circuit_breaker.record_failure()
            
            # Return stale cache if available
            if cached:
                data = cached.data.copy()
                data["_meta"] = {
                    "status": DataStatus.STALE.value,
                    "age_seconds": round(cached.age_seconds, 1),
                    "error": str(e)
                }
                return data
            
            return self._generate_fallback(ticker, timeframe, str(e))
    
    async def _fetch_stock_data(self, ticker: str, timeframe: str) -> Dict:
        """
        Actual data fetching using fast_info (much faster than .info).
        This is called through the coalescer.
        """
        start_time = time.time()
        self._stats["api_calls"] += 1
        self._stats["cache_misses"] += 1
        
        try:
            # Run yfinance in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                self._fetch_sync, 
                ticker, 
                timeframe
            )
            
            fetch_duration = (time.time() - start_time) * 1000
            
            # Cache the successful result
            cache_key = self._get_cache_key(ticker, timeframe)
            ttl = self._get_ttl(timeframe)
            self._set_cache(cache_key, data, ttl, fetch_duration, DataStatus.LIVE)
            
            # Record success for circuit breaker
            self._circuit_breaker.record_success()
            
            # Add metadata
            data["_meta"] = {
                "status": DataStatus.LIVE.value,
                "fetch_duration_ms": round(fetch_duration, 1),
                "fetched_at": datetime.now().isoformat(),
                "age_seconds": 0,
            }
            
            print(f"✅ Fetched {ticker} in {fetch_duration:.0f}ms")
            return data
            
        except Exception as e:
            self._stats["api_errors"] += 1
            raise
    
    def _fetch_sync(self, ticker: str, timeframe: str) -> Dict:
        """
        Synchronous fetch using fast_info instead of info.
        fast_info is 2-10x faster than info.
        """
        stock = yf.Ticker(ticker)
        tf_config = self.TIMEFRAME_MAP.get(timeframe, {"period": "1d", "interval": "1d"})
        
        # Get historical data
        hist = stock.history(period=tf_config["period"], interval=tf_config["interval"])
        
        if hist.empty or len(hist) < 2:
            raise ValueError(f"No data available for {ticker}")
        
        # Use fast_info for speed (available properties):
        # lastPrice, previousClose, open, dayHigh, dayLow, 
        # volume, marketCap, fiftyDayAverage, twoHundredDayAverage
        fast = stock.fast_info
        
        current_price = float(hist["Close"].iloc[-1])
        
        # Get previous close - try fast_info first, fallback to history
        try:
            previous_close = float(fast.previous_close) if fast.previous_close else float(hist["Close"].iloc[-2])
        except Exception:
            previous_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
        
        change = round(current_price - previous_close, 2)
        change_pct = round((change / previous_close) * 100, 2) if previous_close > 0 else 0
        
        # Technical indicators
        rsi = self._safe_indicator(ta.rsi, hist["Close"], length=14, default=50.0)
        
        macd_data = ta.macd(hist["Close"])
        macd = 0.0
        macd_signal = 0.0
        if macd_data is not None and not macd_data.empty:
            try:
                macd = float(macd_data["MACD_12_26_9"].iloc[-1])
                macd_signal = float(macd_data["MACDs_12_26_9"].iloc[-1])
            except Exception:
                pass

        # Bollinger Bands
        bb = ta.bbands(hist["Close"], length=20)
        bb_upper = current_price * 1.02
        bb_lower = current_price * 0.98
        if bb is not None and not bb.empty:
            try:
                bb_upper = float(bb["BBU_20_2.0"].iloc[-1])
                bb_lower = float(bb["BBL_20_2.0"].iloc[-1])
            except Exception:
                pass

        # Generate recommendation based on RSI
        if rsi < 30:
            recommendation, risk = "STRONG BUY", "Low"
        elif rsi < 45:
            recommendation, risk = "BUY", "Low"
        elif rsi < 55:
            recommendation, risk = "HOLD", "Medium"
        elif rsi < 70:
            recommendation, risk = "HOLD", "Medium"
        else:
            recommendation, risk = "SELL", "High"
        
        # Price history for charts
        price_history = []
        for i in range(min(len(hist), 100)):
            idx = len(hist) - 100 + i if len(hist) > 100 else i
            if idx >= 0:
                price_history.append({
                    "time": hist.index[idx].isoformat() if hasattr(hist.index[idx], 'isoformat') else str(hist.index[idx]),
                    "price": round(float(hist["Close"].iloc[idx]), 2),
                    "open": round(float(hist["Open"].iloc[idx]), 2),
                    "high": round(float(hist["High"].iloc[idx]), 2),
                    "low": round(float(hist["Low"].iloc[idx]), 2),
                    "volume": int(hist["Volume"].iloc[idx]) if pd.notna(hist["Volume"].iloc[idx]) else 0
                })
        
        # Get additional data from fast_info
        try:
            day_high = float(fast.day_high) if fast.day_high else float(hist["High"].iloc[-1])
            day_low = float(fast.day_low) if fast.day_low else float(hist["Low"].iloc[-1])
            market_cap = int(fast.market_cap) if fast.market_cap else 0
            volume = int(hist["Volume"].iloc[-1]) if pd.notna(hist["Volume"].iloc[-1]) else 0
        except Exception:
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])
            market_cap = 0
            volume = int(hist["Volume"].iloc[-1]) if pd.notna(hist["Volume"].iloc[-1]) else 0
        
        # Determine market and currency
        market = self._get_market(ticker)
        currency = self._get_currency(ticker)
        
        return {
            "ticker": ticker,
            "name": ticker,  # fast_info doesn't have name, could fetch separately if needed
            "price": round(current_price, 2),
            "change": change,
            "changePct": change_pct,
            "open": round(float(hist["Open"].iloc[-1]), 2),
            "dayHigh": round(day_high, 2),
            "dayLow": round(day_low, 2),
            "prevClose": round(previous_close, 2),
            "timeframe": timeframe,
            "volume": volume,
            "avgVolume": int(hist["Volume"].mean()) if not hist["Volume"].empty else 0,
            "rsi": round(rsi, 1),
            "macd": round(macd, 2),
            "macdSignal": round(macd_signal, 2),
            "bbUpper": round(bb_upper, 2),
            "bbLower": round(bb_lower, 2),
            "sentiment": round(50 + (rsi - 50) * 0.8, 1),
            "recommendation": recommendation,
            "risk": risk,
            "priceHistory": price_history,
            "marketCap": self._format_market_cap(market_cap),
            "currency": currency,
            "market": market,
            "exchange": self._get_exchange(market),
            "isFallback": False,
        }
    
    def _safe_indicator(self, func, series, default=50.0, **kwargs):
        """Safely calculate technical indicator"""
        try:
            result = func(series, **kwargs)
            if result is not None and not result.empty:
                val = float(result.iloc[-1])
                if pd.notna(val):
                    return round(val, 2)
        except Exception:
            pass
        return default
    
    def _generate_fallback(self, ticker: str, timeframe: str, reason: str) -> Dict:
        """Generate fallback/demo data when API fails"""
        # Use ticker hash for consistent pseudo-random values
        seed = sum(ord(c) for c in ticker)
        random.seed(seed)
        
        market = self._get_market(ticker)
        currency = self._get_currency(ticker)
        
        # Base price varies by market
        if market in ["NS", "BO"]:
            base_price = 500 + random.random() * 4000
        elif market == "T":
            base_price = 1000 + random.random() * 50000
        elif market == "KS":
            base_price = 30000 + random.random() * 300000
        else:
            base_price = 50 + random.random() * 500
        
        change = (random.random() - 0.5) * (base_price * 0.05)
        change_pct = (change / base_price) * 100
        rsi = 30 + random.random() * 40
        
        random.seed()  # Reset seed
        
        return {
            "ticker": ticker,
            "name": ticker,
            "price": round(base_price, 2),
            "change": round(change, 2),
            "changePct": round(change_pct, 2),
            "open": round(base_price * 0.99, 2),
            "dayHigh": round(base_price * 1.02, 2),
            "dayLow": round(base_price * 0.98, 2),
            "prevClose": round(base_price - change, 2),
            "timeframe": timeframe,
            "volume": random.randint(1000000, 50000000),
            "avgVolume": random.randint(1000000, 30000000),
            "rsi": round(rsi, 1),
            "macd": round((random.random() - 0.5) * 5, 2),
            "macdSignal": round((random.random() - 0.5) * 4, 2),
            "bbUpper": round(base_price * 1.03, 2),
            "bbLower": round(base_price * 0.97, 2),
            "sentiment": round(50 + (rsi - 50) * 0.8, 1),
            "recommendation": "HOLD",
            "risk": "Medium",
            "priceHistory": self._generate_price_history(base_price, 50),
            "marketCap": "N/A",
            "currency": currency,
            "market": market,
            "exchange": self._get_exchange(market),
            "isFallback": True,
            "_meta": {
                "status": DataStatus.DEMO.value,
                "reason": reason,
            }
        }
    
    def _generate_price_history(self, base_price: float, count: int) -> list:
        """Generate fake price history for demo mode"""
        history = []
        price = base_price * 0.95
        for i in range(count):
            change = (random.random() - 0.45) * (price * 0.02)
            price = max(price + change, base_price * 0.8)
            history.append({
                "time": (datetime.now() - timedelta(days=count-i)).isoformat(),
                "price": round(price, 2),
                "open": round(price * 0.998, 2),
                "high": round(price * 1.01, 2),
                "low": round(price * 0.99, 2),
                "volume": random.randint(100000, 5000000)
            })
        return history
    
    def _get_market(self, ticker: str) -> str:
        """Determine market from ticker suffix"""
        ticker = ticker.upper()
        suffixes = {
            ".NS": "NS", ".BO": "BO", ".L": "L", ".DE": "DE",
            ".T": "T", ".HK": "HK", ".AX": "AX", ".TO": "TO",
            ".PA": "PA", ".SW": "SW", ".SS": "SS", ".KS": "KS",
            ".SI": "SI", ".SA": "SA"
        }
        for suffix, market in suffixes.items():
            if suffix in ticker:
                return market
        return "US"
    
    def _get_currency(self, ticker: str) -> str:
        """Get currency symbol based on ticker suffix"""
        currencies = {
            ".NS": "₹", ".BO": "₹", ".L": "£", ".DE": "€", ".PA": "€",
            ".T": "¥", ".SS": "¥", ".HK": "HK$", ".AX": "A$",
            ".TO": "C$", ".SW": "CHF", ".KS": "₩", ".SI": "S$", ".SA": "R$"
        }
        ticker = ticker.upper()
        for suffix, currency in currencies.items():
            if suffix in ticker:
                return currency
        return "$"
    
    def _get_exchange(self, market: str) -> str:
        """Get exchange name from market code"""
        exchanges = {
            "US": "NASDAQ/NYSE", "NS": "NSE India", "BO": "BSE India",
            "L": "London Stock Exchange", "DE": "Frankfurt Stock Exchange",
            "T": "Tokyo Stock Exchange", "HK": "Hong Kong Stock Exchange",
            "AX": "ASX", "TO": "Toronto Stock Exchange",
            "PA": "Euronext Paris", "SW": "SIX Swiss Exchange",
            "SS": "Shanghai Stock Exchange", "KS": "Korea Stock Exchange",
            "SI": "Singapore Exchange", "SA": "B3 Brasil"
        }
        return exchanges.get(market, "Unknown")
    
    def _format_market_cap(self, value: float) -> str:
        """Format market cap to human readable"""
        if not value or value == 0:
            return "N/A"
        if value >= 1e12:
            return f"{value/1e12:.1f}T"
        if value >= 1e9:
            return f"{value/1e9:.1f}B"
        if value >= 1e6:
            return f"{value/1e6:.1f}M"
        return str(int(value))
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        cache_size = len(self._cache)
        valid_entries = sum(1 for e in self._cache.values() if e.is_valid)
        
        return {
            **self._stats,
            "cache_size": cache_size,
            "valid_entries": valid_entries,
            "stale_entries": cache_size - valid_entries,
            "circuit_breaker_state": self._circuit_breaker.state,
            "circuit_breaker_failures": self._circuit_breaker.failures,
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._lock:
            self._cache.clear()
            self._stats = {k: 0 for k in self._stats}


# Global singleton instance
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """Get or create the global data service instance"""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
