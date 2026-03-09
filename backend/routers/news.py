"""
News & Sentiment Router
=======================
Location: backend/routers/news.py

Endpoints:
- GET /api/news/{symbol} - Get news for a symbol
- GET /api/news/market - Get market news
- GET /api/sentiment/reddit/{symbol} - Get Reddit sentiment
- GET /api/sentiment/reddit/trending - Get trending tickers
- GET /api/sentiment/aggregate/{symbol} - Get combined sentiment
"""

from fastapi import APIRouter, Query
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.news_service import (
    generate_news_for_symbol,
    get_market_news,
    get_aggregated_sentiment,
    analyze_sentiment
)
from services.reddit_service import (
    get_reddit_sentiment,
    get_trending_tickers
)

router = APIRouter(tags=["news", "sentiment"])


# =============================================================================
# NEWS ENDPOINTS
# =============================================================================

@router.get("/api/news/{symbol}")
async def get_news_for_symbol(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get news headlines for a specific symbol."""
    news = generate_news_for_symbol(symbol.upper(), limit)
    return {
        "symbol": symbol.upper(),
        "count": len(news),
        "news": news
    }


@router.get("/api/news/market/latest")
async def get_latest_market_news(
    limit: int = Query(default=15, ge=1, le=50)
):
    """Get latest market-wide news."""
    news = get_market_news(limit)
    return {
        "category": "market",
        "count": len(news),
        "news": news
    }


# =============================================================================
# REDDIT SENTIMENT ENDPOINTS
# =============================================================================

@router.get("/api/sentiment/reddit/{symbol}")
async def get_symbol_reddit_sentiment(symbol: str):
    """Get Reddit sentiment analysis for a symbol."""
    return get_reddit_sentiment(symbol.upper())


@router.get("/api/sentiment/reddit/trending/list")
async def get_reddit_trending():
    """Get trending tickers on Reddit."""
    trending = get_trending_tickers()
    return {
        "count": len(trending),
        "trending": trending
    }


# =============================================================================
# AGGREGATED SENTIMENT
# =============================================================================

@router.get("/api/sentiment/aggregate/{symbol}")
async def get_combined_sentiment(symbol: str):
    """Get combined sentiment from news and Reddit."""
    symbol = symbol.upper()
    
    # Get news sentiment
    news_sentiment = get_aggregated_sentiment(symbol)
    
    # Get Reddit sentiment
    reddit_sentiment = get_reddit_sentiment(symbol)
    
    # Combine scores (weighted average)
    news_weight = 0.4
    reddit_weight = 0.6
    
    # Normalize Reddit score to -1 to 1 range
    reddit_normalized = (reddit_sentiment['sentiment_score'] - 50) / 50
    
    combined_score = (news_sentiment['score'] * news_weight) + (reddit_normalized * reddit_weight)
    
    if combined_score > 0.15:
        overall = "BULLISH"
    elif combined_score < -0.15:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"
    
    return {
        "symbol": symbol,
        "overall_sentiment": overall,
        "combined_score": round(combined_score, 2),
        "combined_score_100": round((combined_score + 1) * 50),  # 0-100 scale
        "news": {
            "sentiment": news_sentiment['overall'],
            "score": news_sentiment['score'],
            "articles": news_sentiment['total_articles'],
            "bullish_percent": news_sentiment['bullish_percent'],
            "bearish_percent": news_sentiment['bearish_percent'],
        },
        "reddit": {
            "sentiment": reddit_sentiment['overall_sentiment'],
            "score": reddit_sentiment['sentiment_score'],
            "mentions_24h": reddit_sentiment['mentions_24h'],
            "bullish_percent": reddit_sentiment['bullish_percent'],
            "bearish_percent": reddit_sentiment['bearish_percent'],
            "is_trending": reddit_sentiment['is_trending'],
        }
    }


# =============================================================================
# SENTIMENT ANALYSIS
# =============================================================================

@router.post("/api/sentiment/analyze")
async def analyze_text_sentiment(text: str = Query(...)):
    """Analyze sentiment of any text."""
    return analyze_sentiment(text)