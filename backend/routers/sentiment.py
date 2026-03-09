"""
Sentiment Router - Combined sentiment from all sources.
"""

from fastapi import APIRouter, Query
from typing import List

from services.sentiment_aggregator import get_aggregated_sentiment, get_market_sentiment_heatmap

router = APIRouter(prefix="/api/sentiment", tags=["Sentiment"])


@router.get("/combined/{symbol}")
async def get_combined_sentiment(symbol: str):
    """
    Get aggregated sentiment from Reddit, StockTwits, and News.

    Returns a composite score (-100 to +100), individual source scores,
    confidence rating, and a trading recommendation.
    """
    result = get_aggregated_sentiment(symbol)
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
    result = get_market_sentiment_heatmap(symbol_list)
    return {"success": True, **result}
