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
from zoneinfo import ZoneInfo

from services.backtest_engine import get_backtest_engine
from services.sentiment_aggregator import get_aggregated_sentiment
from services.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/scanner", tags=["AI Scanner"])

# Default scan universe (US)
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
    "NFLX", "INTC", "SPY", "QQQ", "BTC-USD", "ETH-USD",
]

# Nifty 50 scan universe (NSE India)
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "ASIANPAINT.NS", "AXISBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "NTPC.NS", "POWERGRID.NS",
    "ULTRACEMCO.NS", "NESTLEIND.NS", "TATAMOTORS.NS", "TECHM.NS", "HCLTECH.NS",
    "TATASTEEL.NS", "JSWSTEEL.NS", "ONGC.NS", "DRREDDY.NS", "CIPLA.NS",
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


@router.get("/nifty50")
async def nifty50_scan(
    trader_type: str = Query("Day", description="Day | Swing | Position | Scalper"),
    top_n: int = Query(10, ge=1, le=30, description="Number of top picks to return"),
):
    """
    Nifty 50 Morning Scanner (India).

    Scans all 30 liquid Nifty 50 stocks and returns the top picks ranked by
    composite AI score (technical 40% + backtest accuracy 25% + sentiment 20%
    + risk-adjusted 15%).  Designed to run at market open (9:15 AM IST).

    Also returns overall market bias for the session.
    """
    # Parallel scoring — all 30 symbols simultaneously
    tasks = [_compute_ai_score_cached(sym, trader_type) for sym in NIFTY_50_SYMBOLS]
    all_scores = await asyncio.gather(*tasks)

    all_scores.sort(key=lambda x: x["ai_score"], reverse=True)
    for i, r in enumerate(all_scores):
        r["rank"] = i + 1

    bullish_count = sum(1 for s in all_scores if "BULLISH" in s["direction"])
    bearish_count = sum(1 for s in all_scores if "BEARISH" in s["direction"])
    if bullish_count > bearish_count * 1.5:
        market_bias = "BULLISH"
        bias_label = "More than half the Nifty is showing bullish signals — lean long today"
    elif bearish_count > bullish_count * 1.5:
        market_bias = "BEARISH"
        bias_label = "More than half the Nifty is showing bearish signals — be cautious"
    else:
        market_bias = "NEUTRAL"
        bias_label = "Market is mixed — trade only the highest-conviction setups"

    # NSE session status
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    day = now_ist.weekday()   # 0=Mon … 4=Fri
    hhmm = now_ist.hour * 100 + now_ist.minute
    if day > 4:
        session = "CLOSED_WEEKEND"
    elif hhmm < 900:
        session = "PRE_MARKET"
    elif hhmm < 915:
        session = "PRE_OPEN"
    elif hhmm < 1530:
        session = "OPEN"
    else:
        session = "CLOSED"

    return {
        "success": True,
        "market": "NSE India — Nifty 50",
        "trader_type": trader_type,
        "session": session,
        "market_bias": market_bias,
        "bias_label": bias_label,
        "top_picks": all_scores[:top_n],
        "all_ranked": all_scores,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": len(all_scores) - bullish_count - bearish_count,
        "generated_at": now_ist.isoformat(),
    }
