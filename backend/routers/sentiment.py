"""
Sentiment Router - Combined sentiment from all sources.
Optimized: caching for deterministic sentiment data.
"""

from fastapi import APIRouter, Query
from typing import List

from services.sentiment_aggregator import get_aggregated_sentiment, get_market_sentiment_heatmap
from services.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/sentiment", tags=["Sentiment"])

# Cache for sentiment results (5-minute TTL - deterministic per hour anyway)
_sentiment_cache = get_cache_manager("sentiment")
SENTIMENT_CACHE_TTL = 300  # 5 minutes


@router.get("/combined/{symbol}")
async def get_combined_sentiment(symbol: str):
    """
    Get aggregated sentiment from Reddit, StockTwits, and News.

    Returns a composite score (-100 to +100), individual source scores,
    confidence rating, and a trading recommendation.
    """
    cache_key = f"combined:{symbol.upper()}"
    entry = _sentiment_cache.get(cache_key, SENTIMENT_CACHE_TTL)
    if entry:
        return {"success": True, **entry.data}

    result = get_aggregated_sentiment(symbol)
    _sentiment_cache.set(cache_key, result, source="LIVE")
    return {"success": True, **result}


@router.get("/heatmap")
async def get_sentiment_heatmap(
    symbols: str = Query(
        "AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META,AMD,SPY,QQQ,BTC-USD,ETH-USD",
        description="Comma-separated symbols"
    ),
):
    """
    Get sentiment heatmap for multiple symbols.

    Returns each symbol's sentiment score ranked from most bullish to most bearish,
    plus overall market mood.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    cache_key = f"heatmap:{','.join(symbol_list)}"
    entry = _sentiment_cache.get(cache_key, SENTIMENT_CACHE_TTL)
    if entry:
        return {"success": True, **entry.data}

    result = get_market_sentiment_heatmap(symbol_list)
    _sentiment_cache.set(cache_key, result, source="LIVE")
    return {"success": True, **result}
