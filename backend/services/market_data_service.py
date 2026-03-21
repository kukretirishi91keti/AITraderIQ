"""
Market Data Service v4.9
========================
Location: backend/services/market_data_service.py

PRODUCTION-GRADE DATA PIPELINE:
    1. yfinance (LIVE) - Primary source, uses fast_info
    2. LKG Cache (CACHED) - Last Known Good fallback
    3. MME Simulator (SIMULATED) - Final fallback

Features:
- Uses fast_info instead of info (avoids scraping)
- File-based caching with locking
- SingleFlight pattern to prevent thundering herd
- Circuit breaker for rate limit protection
- Proper async/sync bridging via run_in_threadpool
"""

import random
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Third-party imports with fallbacks
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

try:
    from starlette.concurrency import run_in_threadpool
except ImportError:
    # Fallback for testing outside FastAPI
    async def run_in_threadpool(func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

# Local imports
try:
    from services.cache_manager import (
        get_cache_manager, get_singleflight, CacheEntry,
        DEFAULT_TTL_SECONDS, STALE_THRESHOLD_SECONDS
    )
except ImportError:
    # Running standalone
    from cache_manager import (
        get_cache_manager, get_singleflight, CacheEntry,
        DEFAULT_TTL_SECONDS, STALE_THRESHOLD_SECONDS
    )

logger = logging.getLogger(__name__)

# =============================================================================
# MARKET CONFIGURATIONS WITH CORRECT CURRENCIES
# =============================================================================

MARKET_CONFIG = {
    'US': {'currency': '$', 'name': 'United States', 'suffix': ''},
    'INDIA': {'currency': '₹', 'name': 'India', 'suffix': '.NS'},
    'UK': {'currency': '£', 'name': 'United Kingdom', 'suffix': '.L'},
    'GERMANY': {'currency': '€', 'name': 'Germany', 'suffix': '.DE'},
    'FRANCE': {'currency': '€', 'name': 'France', 'suffix': '.PA'},
    'JAPAN': {'currency': '¥', 'name': 'Japan', 'suffix': '.T'},
    'CHINA': {'currency': '¥', 'name': 'China', 'suffix': '.SS'},
    'HONGKONG': {'currency': 'HK$', 'name': 'Hong Kong', 'suffix': '.HK'},
    'AUSTRALIA': {'currency': 'A$', 'name': 'Australia', 'suffix': '.AX'},
    'CANADA': {'currency': 'C$', 'name': 'Canada', 'suffix': '.TO'},
    'BRAZIL': {'currency': 'R$', 'name': 'Brazil', 'suffix': '.SA'},
    'KOREA': {'currency': '₩', 'name': 'South Korea', 'suffix': '.KS'},
    'SINGAPORE': {'currency': 'S$', 'name': 'Singapore', 'suffix': '.SI'},
    'SWITZERLAND': {'currency': 'CHF', 'name': 'Switzerland', 'suffix': '.SW'},
    'NETHERLANDS': {'currency': '€', 'name': 'Netherlands', 'suffix': '.AS'},
    'SPAIN': {'currency': '€', 'name': 'Spain', 'suffix': '.MC'},
    'ITALY': {'currency': '€', 'name': 'Italy', 'suffix': '.MI'},
    'SWEDEN': {'currency': 'kr', 'name': 'Sweden', 'suffix': '.ST'},
    'CRYPTO': {'currency': '$', 'name': 'Cryptocurrency', 'suffix': ''},
    'ETF': {'currency': '$', 'name': 'ETFs', 'suffix': ''},
    'FOREX': {'currency': '$', 'name': 'Forex', 'suffix': ''},
    'COMMODITIES': {'currency': '$', 'name': 'Commodities', 'suffix': ''},
}

# =============================================================================
# GLOBAL STOCKS DATABASE
# =============================================================================

GLOBAL_STOCKS = {
    # US STOCKS
    'AAPL': {'name': 'Apple Inc.', 'market': 'US', 'basePrice': 250},
    'MSFT': {'name': 'Microsoft', 'market': 'US', 'basePrice': 430},
    'GOOGL': {'name': 'Alphabet Inc.', 'market': 'US', 'basePrice': 175},
    'AMZN': {'name': 'Amazon', 'market': 'US', 'basePrice': 225},
    'NVDA': {'name': 'NVIDIA Corp.', 'market': 'US', 'basePrice': 140},
    'TSLA': {'name': 'Tesla Inc.', 'market': 'US', 'basePrice': 250},
    'META': {'name': 'Meta Platforms', 'market': 'US', 'basePrice': 580},
    'NFLX': {'name': 'Netflix Inc.', 'market': 'US', 'basePrice': 900},
    'AMD': {'name': 'AMD Inc.', 'market': 'US', 'basePrice': 140},
    'CRM': {'name': 'Salesforce Inc.', 'market': 'US', 'basePrice': 350},
    'JPM': {'name': 'JPMorgan Chase', 'market': 'US', 'basePrice': 200},
    'V': {'name': 'Visa Inc.', 'market': 'US', 'basePrice': 315},
    'MA': {'name': 'Mastercard Inc.', 'market': 'US', 'basePrice': 530},
    'DIS': {'name': 'Walt Disney Co.', 'market': 'US', 'basePrice': 115},
    
    # INDIA STOCKS
    'RELIANCE.NS': {'name': 'Reliance Industries', 'market': 'INDIA', 'basePrice': 1280},
    'TCS.NS': {'name': 'Tata Consultancy', 'market': 'INDIA', 'basePrice': 4100},
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'market': 'INDIA', 'basePrice': 1750},
    'INFY.NS': {'name': 'Infosys Ltd.', 'market': 'INDIA', 'basePrice': 1900},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'market': 'INDIA', 'basePrice': 1250},
    'SBIN.NS': {'name': 'State Bank of India', 'market': 'INDIA', 'basePrice': 850},
    'BHARTIARTL.NS': {'name': 'Bharti Airtel', 'market': 'INDIA', 'basePrice': 1650},
    'WIPRO.NS': {'name': 'Wipro Ltd.', 'market': 'INDIA', 'basePrice': 450},
    'HINDUNILVR.NS': {'name': 'Hindustan Unilever', 'market': 'INDIA', 'basePrice': 2400},
    'LT.NS': {'name': 'Larsen & Toubro', 'market': 'INDIA', 'basePrice': 3500},
    
    # UK STOCKS
    'HSBA.L': {'name': 'HSBC Holdings', 'market': 'UK', 'basePrice': 750},
    'BP.L': {'name': 'BP plc', 'market': 'UK', 'basePrice': 480},
    'AZN.L': {'name': 'AstraZeneca', 'market': 'UK', 'basePrice': 11500},
    'SHEL.L': {'name': 'Shell plc', 'market': 'UK', 'basePrice': 2800},
    
    # GERMANY STOCKS
    'SAP.DE': {'name': 'SAP SE', 'market': 'GERMANY', 'basePrice': 220},
    'SIE.DE': {'name': 'Siemens AG', 'market': 'GERMANY', 'basePrice': 185},
    'BMW.DE': {'name': 'BMW AG', 'market': 'GERMANY', 'basePrice': 85},
    
    # CRYPTO
    'BTC-USD': {'name': 'Bitcoin', 'market': 'CRYPTO', 'basePrice': 105000},
    'ETH-USD': {'name': 'Ethereum', 'market': 'CRYPTO', 'basePrice': 4000},
    'SOL-USD': {'name': 'Solana', 'market': 'CRYPTO', 'basePrice': 220},
    
    # ETFs
    'SPY': {'name': 'S&P 500 ETF', 'market': 'ETF', 'basePrice': 600},
    'QQQ': {'name': 'Nasdaq 100 ETF', 'market': 'ETF', 'basePrice': 530},
    'IWM': {'name': 'Russell 2000 ETF', 'market': 'ETF', 'basePrice': 230},
}


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for rate limit protection.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, block requests
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, max_failures: int = 5, reset_timeout: int = 60):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
        self.total_429_errors = 0
    
    def record_success(self):
        """Record successful API call."""
        self.failures = 0
        self.is_open = False
    
    def record_failure(self, is_rate_limit: bool = False):
        """Record failed API call."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if is_rate_limit:
            self.total_429_errors += 1
        
        if self.failures >= self.max_failures:
            self.is_open = True
            logger.warning(f"Circuit breaker OPENED after {self.failures} failures")
    
    def can_proceed(self) -> bool:
        """Check if we can make an API call."""
        if not self.is_open:
            return True
        
        # Check if reset timeout has passed
        if self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed >= self.reset_timeout:
                logger.info("Circuit breaker HALF-OPEN, testing...")
                self.is_open = False
                self.failures = 0
                return True
        
        return False
    
    def get_status(self) -> dict:
        return {
            "state": "OPEN" if self.is_open else "CLOSED",
            "failures": self.failures,
            "total_429_errors": self.total_429_errors,
            "can_proceed": self.can_proceed()
        }


# Global circuit breaker
_circuit_breaker = CircuitBreaker()


# =============================================================================
# YFINANCE WRAPPER (fast_info)
# =============================================================================

def _fetch_yfinance_quote_sync(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous yfinance fetch using fast_info (not info!).
    
    fast_info uses JSON API endpoints instead of HTML scraping.
    This is the ONLY method that should be used in production.
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available")
        return None
    
    if not _circuit_breaker.can_proceed():
        logger.warning(f"Circuit breaker OPEN, skipping yfinance for {symbol}")
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Use fast_info - NOT info!
        # fast_info uses JSON API, info uses HTML scraping
        fi = ticker.fast_info
        
        if fi is None or not hasattr(fi, 'last_price'):
            logger.warning(f"fast_info empty for {symbol}")
            return None
        
        # Get price data from fast_info
        price = fi.last_price if hasattr(fi, 'last_price') else None
        prev_close = fi.previous_close if hasattr(fi, 'previous_close') else None
        
        if price is None:
            return None
        
        # Calculate change
        change = 0
        change_pct = 0
        if prev_close and prev_close > 0:
            change = price - prev_close
            change_pct = (change / prev_close) * 100
        
        # Get additional data
        day_high = fi.day_high if hasattr(fi, 'day_high') else price * 1.01
        day_low = fi.day_low if hasattr(fi, 'day_low') else price * 0.99
        open_price = fi.open if hasattr(fi, 'open') else prev_close
        volume = fi.last_volume if hasattr(fi, 'last_volume') else 0
        market_cap = fi.market_cap if hasattr(fi, 'market_cap') else None
        
        # Determine market from symbol
        market = _get_market_from_symbol(symbol)
        currency = MARKET_CONFIG.get(market, {}).get('currency', '$')
        
        # Get company name (fallback to GLOBAL_STOCKS or symbol)
        name = GLOBAL_STOCKS.get(symbol, {}).get('name', symbol)
        
        _circuit_breaker.record_success()
        
        return {
            'symbol': symbol,
            'price': round(price, 2),
            'change': round(change, 2),
            'changePercent': round(change_pct, 2),
            'previousClose': round(prev_close, 2) if prev_close else None,
            'prevClose': round(prev_close, 2) if prev_close else None,
            'open': round(open_price, 2) if open_price else None,
            'dayOpen': round(open_price, 2) if open_price else None,
            'high': round(day_high, 2) if day_high else None,
            'dayHigh': round(day_high, 2) if day_high else None,
            'low': round(day_low, 2) if day_low else None,
            'dayLow': round(day_low, 2) if day_low else None,
            'volume': int(volume) if volume else 0,
            'marketCap': market_cap,
            'market': market,
            'currency': currency,
            'name': name,
            'companyName': name,
            'shortName': name,
            'dataQuality': 'LIVE',
            'source': 'YFINANCE',
            'timestamp': datetime.now().isoformat(),
        }
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = '429' in error_str or 'rate' in error_str or 'too many' in error_str
        
        _circuit_breaker.record_failure(is_rate_limit=is_rate_limit)
        logger.warning(f"yfinance error for {symbol}: {e}")
        
        return None


def _fetch_yfinance_history_sync(
    symbol: str, 
    period: str = "1mo",
    interval: str = "1d"
) -> Optional[List[Dict]]:
    """
    Fetch historical OHLCV data from yfinance.
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    if not _circuit_breaker.can_proceed():
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return None
        
        candles = []
        for idx, row in hist.iterrows():
            candles.append({
                'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
        
        _circuit_breaker.record_success()
        return candles
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = '429' in error_str or 'rate' in error_str
        _circuit_breaker.record_failure(is_rate_limit=is_rate_limit)
        logger.warning(f"yfinance history error for {symbol}: {e}")
        return None


# =============================================================================
# MME SIMULATOR (FALLBACK)
# =============================================================================

def _generate_mme_quote(symbol: str) -> Dict[str, Any]:
    """
    Market Model Engine - Simulated fallback.
    
    Generates deterministic but realistic-looking price data
    when yfinance is unavailable.
    """
    # Get stock info
    stock_info = GLOBAL_STOCKS.get(symbol, {})
    market = stock_info.get('market') or _get_market_from_symbol(symbol)
    base_price = stock_info.get('basePrice', 100)
    name = stock_info.get('name', symbol)
    currency = MARKET_CONFIG.get(market, {}).get('currency', '$')
    
    # Generate deterministic but varying price
    seed = f"{symbol}:{datetime.now().strftime('%Y%m%d%H%M')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    price = base_price * (0.95 + rng.random() * 0.10)
    prev_close = base_price * (0.96 + rng.random() * 0.08)
    change = price - prev_close
    change_pct = (change / prev_close) * 100 if prev_close else 0
    
    return {
        'symbol': symbol,
        'price': round(price, 2),
        'change': round(change, 2),
        'changePercent': round(change_pct, 2),
        'previousClose': round(prev_close, 2),
        'prevClose': round(prev_close, 2),
        'open': round(prev_close * (1 + (rng.random() - 0.5) * 0.01), 2),
        'dayOpen': round(prev_close * (1 + (rng.random() - 0.5) * 0.01), 2),
        'high': round(max(price, prev_close) * (1 + rng.random() * 0.02), 2),
        'dayHigh': round(max(price, prev_close) * (1 + rng.random() * 0.02), 2),
        'low': round(min(price, prev_close) * (1 - rng.random() * 0.02), 2),
        'dayLow': round(min(price, prev_close) * (1 - rng.random() * 0.02), 2),
        'volume': int(rng.random() * 50000000),
        'market': market,
        'currency': currency,
        'name': name,
        'companyName': name,
        'shortName': name,
        'dataQuality': 'SIMULATED',
        'source': 'MME',
        'timestamp': datetime.now().isoformat(),
    }


def _generate_mme_history(
    symbol: str, 
    period: str = "1mo",
    interval: str = "1d"
) -> List[Dict]:
    """Generate simulated historical data."""
    stock_info = GLOBAL_STOCKS.get(symbol, {})
    base_price = stock_info.get('basePrice', 100)
    
    # Determine number of candles
    period_days = {'1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365}
    days = period_days.get(period, 30)
    
    interval_map = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '1d': 1440}
    
    seed = f"history:{symbol}:{period}:{interval}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    candles = []
    current_price = base_price
    
    for i in range(min(days * 2, 200)):  # Cap at 200 candles
        timestamp = datetime.now() - timedelta(days=days - i)
        
        # Random walk
        change_pct = (rng.random() - 0.48) * 3  # Slight upward bias
        current_price *= (1 + change_pct / 100)
        
        open_price = current_price * (1 + (rng.random() - 0.5) * 0.01)
        close_price = current_price
        high = max(open_price, close_price) * (1 + rng.random() * 0.015)
        low = min(open_price, close_price) * (1 - rng.random() * 0.015)
        
        candles.append({
            'timestamp': timestamp.isoformat(),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': int(rng.random() * 20000000)
        })
    
    return candles


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_market_from_symbol(symbol: str) -> str:
    """Determine market from symbol suffix."""
    symbol = symbol.upper()
    
    if symbol in GLOBAL_STOCKS:
        return GLOBAL_STOCKS[symbol].get('market', 'US')
    
    if '.NS' in symbol:
        return 'INDIA'
    elif '.L' in symbol:
        return 'UK'
    elif '.DE' in symbol:
        return 'GERMANY'
    elif '.PA' in symbol:
        return 'FRANCE'
    elif '.T' in symbol:
        return 'JAPAN'
    elif '.SS' in symbol or '.SZ' in symbol:
        return 'CHINA'
    elif '.HK' in symbol:
        return 'HONGKONG'
    elif '.AX' in symbol:
        return 'AUSTRALIA'
    elif '.TO' in symbol:
        return 'CANADA'
    elif '.SA' in symbol:
        return 'BRAZIL'
    elif '.KS' in symbol:
        return 'KOREA'
    elif '-USD' in symbol:
        return 'CRYPTO'
    elif '=X' in symbol:
        return 'FOREX'
    elif '=F' in symbol:
        return 'COMMODITIES'
    
    return 'US'


def get_currency_symbol(market: str) -> str:
    """Get currency symbol for a market."""
    return MARKET_CONFIG.get(market.upper(), {}).get('currency', '$')


def get_stocks_for_market(market: str) -> List[Dict]:
    """Get all stocks for a specific market."""
    market = market.upper()
    return [
        {'symbol': sym, **info}
        for sym, info in GLOBAL_STOCKS.items()
        if info.get('market', '').upper() == market
    ]


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class MarketDataService:
    """
    Production-grade market data service.
    
    Data flow:
        1. yfinance (LIVE) → Primary source
        2. LKG Cache (CACHED) → Fallback when live fails
        3. MME (SIMULATED) → Final fallback
    """
    
    def __init__(self):
        self.cache = get_cache_manager("market_data")
        self.singleflight = get_singleflight()
        self.stocks = GLOBAL_STOCKS
        self.markets = MARKET_CONFIG
        
        # Stats
        self.stats = {
            "live_fetches": 0,
            "cache_hits": 0,
            "lkg_fallbacks": 0,
            "mme_fallbacks": 0,
            "last_live_fetch": None
        }
    
    async def get_quote(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get quote with full fallback chain.
        
        Flow: yfinance → LKG Cache → MME Simulator
        """
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"
        
        # 1. Check fresh cache (unless force refresh)
        if not force_refresh:
            entry = self.cache.get(cache_key, ttl_seconds=60)  # 1 minute TTL for quotes
            if entry:
                self.stats["cache_hits"] += 1
                data = entry.data
                data['dataQuality'] = 'CACHED'
                data['cacheAge'] = entry.age_human()
                return data
        
        # 2. Try yfinance via SingleFlight (prevents thundering herd)
        async def fetch_live():
            return await run_in_threadpool(_fetch_yfinance_quote_sync, symbol)
        
        try:
            live_data = await self.singleflight.do(f"quote:{symbol}", fetch_live)
            
            if live_data:
                # Cache the live data
                self.cache.set(cache_key, live_data, source="LIVE")
                self.stats["live_fetches"] += 1
                self.stats["last_live_fetch"] = datetime.now().isoformat()
                return live_data
        
        except Exception as e:
            logger.warning(f"Live fetch failed for {symbol}: {e}")
        
        # 3. Try LKG cache (any age)
        lkg = self.cache.get_lkg(cache_key)
        if lkg:
            self.stats["lkg_fallbacks"] += 1
            data = lkg.data
            data['dataQuality'] = 'LKG'
            data['cacheAge'] = lkg.age_human()
            data['source'] = 'LKG_CACHE'
            logger.info(f"Using LKG for {symbol} ({lkg.age_human()})")
            return data
        
        # 4. Final fallback: MME simulator
        self.stats["mme_fallbacks"] += 1
        logger.info(f"Using MME simulator for {symbol}")
        return _generate_mme_quote(symbol)
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Tuple[List[Dict], str]:
        """
        Get historical data with fallback.
        
        Returns: (candles, source)
        """
        symbol = symbol.upper()
        cache_key = f"history:{symbol}:{period}:{interval}"
        
        # Check cache first
        entry = self.cache.get(cache_key, ttl_seconds=300)  # 5 min TTL for history
        if entry:
            return entry.data, "CACHED"
        
        # Try yfinance
        async def fetch_live():
            return await run_in_threadpool(
                _fetch_yfinance_history_sync, symbol, period, interval
            )
        
        try:
            live_data = await self.singleflight.do(cache_key, fetch_live)
            
            if live_data:
                self.cache.set(cache_key, live_data, source="LIVE")
                return live_data, "LIVE"
        
        except Exception as e:
            logger.warning(f"History fetch failed for {symbol}: {e}")
        
        # LKG fallback
        lkg = self.cache.get_lkg(cache_key)
        if lkg:
            return lkg.data, "LKG"
        
        # MME fallback
        return _generate_mme_history(symbol, period, interval), "SIMULATED"
    
    async def get_top_movers(self, market: str, limit: int = 5) -> Dict[str, Any]:
        """Get top gainers and losers for a market."""
        market = market.upper()
        currency = get_currency_symbol(market)
        
        # Get stocks for this market
        market_stocks = get_stocks_for_market(market)
        
        if not market_stocks:
            market_stocks = get_stocks_for_market('US')
        
        # Fetch quotes for all stocks
        movers = []
        for stock in market_stocks[:20]:  # Limit to prevent rate limiting
            try:
                quote = await self.get_quote(stock['symbol'])
                movers.append({
                    'symbol': quote['symbol'],
                    'name': quote.get('name', quote['symbol']),
                    'shortName': quote.get('shortName', quote['symbol']),
                    'price': quote['price'],
                    'change': quote['change'],
                    'changePercent': quote['changePercent'],
                    'currency': currency,
                    'market': market,
                    'dataQuality': quote.get('dataQuality', 'UNKNOWN')
                })
            except Exception as e:
                logger.warning(f"Failed to get quote for {stock['symbol']}: {e}")
        
        # Sort by change percent
        movers.sort(key=lambda x: x['changePercent'], reverse=True)
        gainers = [m for m in movers if m['changePercent'] > 0][:limit]
        losers = [m for m in movers if m['changePercent'] < 0]
        losers.sort(key=lambda x: x['changePercent'])
        losers = losers[:limit]
        
        return {
            'market': market,
            'currency': currency,
            'gainers': gainers,
            'losers': losers,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch quotes for multiple symbols at once.

        Returns: {results: {SYMBOL: quote_data, ...}, asOf: timestamp}
        """
        results = {}
        for symbol in symbols:
            sym = symbol.upper().strip()
            if not sym:
                continue
            try:
                quote = await self.get_quote(sym)
                # Add asOf field that some callers expect
                quote['asOf'] = quote.get('timestamp', datetime.now().isoformat())
                results[sym] = quote
            except Exception as e:
                logger.warning(f"Batch quote failed for {sym}: {e}")

        return {
            "results": results,
            "count": len(results),
            "asOf": datetime.now().isoformat()
        }

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 100
    ) -> Dict[str, Any]:
        """
        Get OHLCV candles for a symbol.

        Maps interval/lookback to period for get_history().
        Returns: {symbol, interval, count, candles, source, dataQuality}
        """
        symbol = symbol.upper()

        # Map lookback + interval to a yfinance-compatible period
        if interval in ("1m", "5m", "15m", "30m"):
            period = "5d"
        elif interval in ("1h", "4h"):
            period = "1mo"
        elif interval == "1d":
            if lookback <= 30:
                period = "1mo"
            elif lookback <= 90:
                period = "3mo"
            elif lookback <= 180:
                period = "6mo"
            else:
                period = "1y"
        elif interval in ("1w", "1wk"):
            period = "1y"
        else:
            period = "1mo"

        candles, source = await self.get_history(symbol, period=period, interval=interval)

        # Trim to lookback
        candles = candles[-lookback:] if len(candles) > lookback else candles

        market = _get_market_from_symbol(symbol)
        currency = get_currency_symbol(market)

        return {
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "candles": candles,
            "source": source,
            "dataQuality": source,
            "currency": currency,
        }

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get a broad market overview across key indices and sectors."""
        overview_symbols = ["SPY", "QQQ", "DIA", "IWM", "BTC-USD", "GC=F"]

        results = {}
        for sym in overview_symbols:
            try:
                quote = await self.get_quote(sym)
                results[sym] = {
                    "symbol": sym,
                    "name": quote.get("name", sym),
                    "price": quote["price"],
                    "change": quote["change"],
                    "changePercent": quote["changePercent"],
                    "dataQuality": quote.get("dataQuality", "UNKNOWN"),
                }
            except Exception as e:
                logger.warning(f"Overview fetch failed for {sym}: {e}")

        return {
            "overview": results,
            "timestamp": datetime.now().isoformat()
        }

    async def get_health(self) -> Dict[str, Any]:
        """Get detailed service health including circuit breaker state."""
        status = self.get_service_status()

        return {
            "status": status["health"],
            "yfinance": {
                "available": status["yfinance_available"],
                "breaker": status["circuit_breaker"],
            },
            "cache": status["cache"],
            "stats": status["stats"],
            "timestamp": status["timestamp"]
        }

    def get_roadmap(self) -> Dict[str, Any]:
        """Get product roadmap / feature status."""
        return {
            "version": "4.9",
            "features": {
                "live_quotes": {"status": "GA", "description": "Real-time quotes via yfinance"},
                "historical_data": {"status": "GA", "description": "OHLCV history with caching"},
                "top_movers": {"status": "GA", "description": "18 global markets"},
                "signals": {"status": "GA", "description": "RSI, MACD, Bollinger, ATR"},
                "strategy_intelligence": {"status": "GA", "description": "AI-powered strategy ranking"},
                "sentiment": {"status": "GA", "description": "Multi-source sentiment aggregation"},
                "ai_chatbot": {"status": "GA", "description": "Groq Llama 3.3 70B with fallback"},
                "payments_stripe": {"status": "GA", "description": "Stripe checkout integration"},
                "payments_razorpay": {"status": "GA", "description": "Razorpay for India/INR"},
                "websockets": {"status": "BETA", "description": "Real-time price streaming"},
                "portfolio_tracking": {"status": "PLANNED", "description": "Track user portfolios"},
                "alerts": {"status": "PLANNED", "description": "Price and signal alerts"},
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_service_status(self) -> Dict[str, Any]:
        """Get service health status."""
        cache_stats = self.cache.get_stats()
        circuit_status = _circuit_breaker.get_status()
        
        # Determine overall health
        health = "HEALTHY"
        if circuit_status["state"] == "OPEN":
            health = "DEGRADED"
        if self.stats["mme_fallbacks"] > self.stats["live_fetches"]:
            health = "DEGRADED"
        
        return {
            "health": health,
            "yfinance_available": YFINANCE_AVAILABLE,
            "circuit_breaker": circuit_status,
            "cache": cache_stats,
            "stats": self.stats,
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get singleton market data service instance."""
    global _service
    if _service is None:
        _service = MarketDataService()
    return _service


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = get_market_data_service()
        
        print("\n" + "="*60)
        print("MARKET DATA SERVICE TEST")
        print("="*60)
        
        # Test quote
        print("\n📊 Testing AAPL quote...")
        quote = await service.get_quote("AAPL")
        print(f"   Price: ${quote['price']}")
        print(f"   Change: {quote['changePercent']:.2f}%")
        print(f"   Source: {quote['dataQuality']} ({quote.get('source', 'N/A')})")
        
        # Test history
        print("\n📈 Testing AAPL history...")
        history, source = await service.get_history("AAPL", "5d", "1d")
        print(f"   Candles: {len(history)}")
        print(f"   Source: {source}")
        
        # Service status
        print("\n⚙️ Service Status:")
        status = service.get_service_status()
        print(f"   Health: {status['health']}")
        print(f"   yfinance: {status['yfinance_available']}")
        print(f"   Circuit: {status['circuit_breaker']['state']}")
        
    asyncio.run(test())
