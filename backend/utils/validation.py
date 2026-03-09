"""
Symbol and input validation utilities.
Prevents path traversal, injection, and invalid input.
"""

import re
from fastapi import HTTPException

# Valid symbol pattern: alphanumeric, dots, hyphens, equals, carets
# Examples: AAPL, RELIANCE.NS, BTC-USD, EURUSD=X, GC=F, ^GSPC
SYMBOL_PATTERN = re.compile(r'^[A-Za-z0-9\.\-\=\^]{1,20}$')

# Valid market names
VALID_MARKETS = {
    "US", "INDIA", "UK", "GERMANY", "FRANCE", "JAPAN", "CHINA",
    "HONGKONG", "AUSTRALIA", "CANADA", "BRAZIL", "KOREA",
    "SINGAPORE", "SWITZERLAND", "NETHERLANDS", "SPAIN", "ITALY",
    "SWEDEN", "TAIWAN", "CRYPTO", "ETF", "FOREX", "COMMODITIES",
    # Aliases
    "EUROPE", "EU", "DE", "FR", "JP", "CN", "HK", "AU", "CA", "BR", "KR", "SG", "CH",
}

# Valid intervals
VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1wk", "1mo"}

# Valid periods
VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"}


def validate_symbol(symbol: str) -> str:
    """Validate and normalize a stock symbol. Raises HTTPException on invalid input."""
    if not symbol or not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid symbol: '{symbol}'. Symbols must be 1-20 alphanumeric characters with optional . - = ^"
        )
    return symbol.upper().strip()


def validate_symbols(symbols: list[str], max_count: int = 50) -> list[str]:
    """Validate a list of symbols."""
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")
    if len(symbols) > max_count:
        raise HTTPException(status_code=400, detail=f"Too many symbols (max {max_count})")
    return [validate_symbol(s) for s in symbols]


def validate_market(market: str) -> str:
    """Validate a market identifier."""
    m = market.upper().strip()
    if m not in VALID_MARKETS:
        raise HTTPException(status_code=400, detail=f"Invalid market: '{market}'")
    return m


def validate_interval(interval: str) -> str:
    """Validate a chart interval."""
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Invalid interval: '{interval}'. Valid: {sorted(VALID_INTERVALS)}")
    return interval


def validate_period(period: str) -> str:
    """Validate a history period."""
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period: '{period}'. Valid: {sorted(VALID_PERIODS)}")
    return period
