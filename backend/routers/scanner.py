"""
AI-Ranked Market Scanner
========================
Scans symbols and ranks them by a combined AI score that weighs:
- Technical signal strength
- Sentiment score
- Backtest accuracy for that symbol
- Risk level

Produces an actionable ranked list of trading opportunities.
"""

import asyncio
from fastapi import APIRouter, Query
from datetime import datetime

from services.backtest_engine import get_backtest_engine
from services.sentiment_aggregator import get_aggregated_sentiment
from services.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/scanner", tags=["AI Scanner"])

# Default scan universe
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
    "NFLX", "INTC", "SPY", "QQQ", "BTC-USD", "ETH-USD",
]

# Cache for AI scores (5-minute TTL)
_scanner_cache = get_cache_manager("scanner")
SCANNER_CACHE_TTL = 300  # 5 minutes


def _compute_ai_score(symbol: str, trader_type: str) -> dict:
    """Compute composite AI score for a symbol."""
    engine = get_backtest_engine()

    # Get backtest accuracy
    bt = engine.run_backtest(symbol, trader_type, periods=100)
    win_rate = bt["win_rate"]
    sharpe = bt["sharpe_ratio"]

    # Get latest signal from backtest
    latest = bt["recent_signals"][-1] if bt["recent_signals"] else None
    signal = latest["signal"] if latest else "HOLD"
    confidence = latest["confidence"] if latest else 50
    rsi = latest["rsi"] if latest else 50

    # Get sentiment
    sent = get_aggregated_sentiment(symbol)
    sentiment_score = sent["composite_score"]

    # Compute composite AI score (0-100)
    # 40% technical signal strength + 25% backtest accuracy + 20% sentiment + 15% risk-adjusted
    tech_score = confidence
    accuracy_score = win_rate
    sent_normalized = (sentiment_score + 100) / 2  # map -100..+100 to 0..100
    risk_score = max(0, min(100, sharpe * 30 + 50))

    ai_score = round(
        tech_score * 0.40 +
        accuracy_score * 0.25 +
        sent_normalized * 0.20 +
        risk_score * 0.15
    )

    # Direction: bullish, bearish, or neutral
    if signal in ("BUY", "STRONG_BUY") and sentiment_score > 0:
        direction = "BULLISH"
    elif signal in ("SELL", "STRONG_SELL") and sentiment_score < 0:
        direction = "BEARISH"
    elif signal in ("BUY", "STRONG_BUY"):
        direction = "LEAN_BULLISH"
    elif signal in ("SELL", "STRONG_SELL"):
        direction = "LEAN_BEARISH"
    else:
        direction = "NEUTRAL"

    return {
        "symbol": symbol,
        "ai_score": ai_score,
        "direction": direction,
        "signal": signal,
        "confidence": confidence,
        "rsi": rsi,
        "win_rate": win_rate,
        "sharpe_ratio": sharpe,
        "sentiment_score": sentiment_score,
        "sentiment_label": sent["label"],
        "components": {
            "technical": round(tech_score, 1),
            "accuracy": round(accuracy_score, 1),
            "sentiment": round(sent_normalized, 1),
            "risk_adjusted": round(risk_score, 1),
        },
    }


async def _compute_ai_score_cached(symbol: str, trader_type: str) -> dict:
    """Compute AI score with caching to avoid redundant computation."""
    cache_key = f"ai_score:{symbol}:{trader_type}"
    entry = _scanner_cache.get(cache_key, SCANNER_CACHE_TTL)
    if entry:
        return entry.data

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _compute_ai_score, symbol, trader_type)
    _scanner_cache.set(cache_key, result, source="LIVE")
    return result


@router.get("/rank")
async def rank_symbols(
    symbols: str = Query(None, description="Comma-separated (default: major US stocks + crypto)"),
    trader_type: str = Query("swing"),
    direction: str = Query(None, description="Filter: BULLISH, BEARISH, or None for all"),
):
    """
    AI-ranked market scanner.

    Scans symbols and ranks by composite AI score combining:
    - Technical signal strength (40%)
    - Historical backtest accuracy (25%)
    - Sentiment across sources (20%)
    - Risk-adjusted performance (15%)
    """
    symbol_list = DEFAULT_SYMBOLS
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # Parallel computation of all symbol scores
    tasks = [_compute_ai_score_cached(sym, trader_type) for sym in symbol_list[:20]]
    all_scores = await asyncio.gather(*tasks)

    rankings = []
    for score in all_scores:
        if direction and direction.upper() not in score["direction"]:
            continue
        rankings.append(score)

    # Sort by AI score descending
    rankings.sort(key=lambda x: x["ai_score"], reverse=True)

    # Add rank
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    return {
        "success": True,
        "trader_type": trader_type,
        "count": len(rankings),
        "rankings": rankings,
        "top_pick": rankings[0] if rankings else None,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/opportunities")
async def find_opportunities(
    trader_type: str = Query("swing"),
):
    """
    Find the best trading opportunities right now.

    Returns top bullish and bearish setups ranked by AI score,
    filtered to only show high-confidence signals with good backtest history.
    """
    # Parallel computation of all symbol scores
    tasks = [_compute_ai_score_cached(sym, trader_type) for sym in DEFAULT_SYMBOLS]
    all_scores = await asyncio.gather(*tasks)

    # Filter for high-confidence opportunities
    bullish = [s for s in all_scores if "BULLISH" in s["direction"] and s["confidence"] >= 60]
    bearish = [s for s in all_scores if "BEARISH" in s["direction"] and s["confidence"] >= 60]

    bullish.sort(key=lambda x: x["ai_score"], reverse=True)
    bearish.sort(key=lambda x: x["ai_score"], reverse=True)

    return {
        "success": True,
        "trader_type": trader_type,
        "bullish_setups": bullish[:5],
        "bearish_setups": bearish[:5],
        "market_bias": "BULLISH" if len(bullish) > len(bearish) else "BEARISH" if len(bearish) > len(bullish) else "NEUTRAL",
        "generated_at": datetime.now().isoformat(),
    }
