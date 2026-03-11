"""
Backtest Router - Signal accuracy tracking and backtesting endpoints.
Optimized: caching + parallel execution for compare/leaderboard.
"""

import asyncio
from fastapi import APIRouter, Query
from datetime import datetime

from services.backtest_engine import get_backtest_engine
from services.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])

# Cache for backtest results (5-minute TTL - deterministic data doesn't change often)
_backtest_cache = get_cache_manager("backtest")
BACKTEST_CACHE_TTL = 300  # 5 minutes


async def _run_backtest_cached(symbol: str, trader_type: str, periods: int) -> dict:
    """Run backtest with caching."""
    cache_key = f"bt:{symbol}:{trader_type}:{periods}"
    entry = _backtest_cache.get(cache_key, BACKTEST_CACHE_TTL)
    if entry:
        return entry.data

    engine = get_backtest_engine()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, engine.run_backtest, symbol, trader_type, periods)
    _backtest_cache.set(cache_key, result, source="LIVE")
    return result


@router.get("/run/{symbol}")
async def run_backtest(
    symbol: str,
    trader_type: str = Query("swing", description="Trading style"),
    periods: int = Query(150, ge=50, le=500),
):
    """
    Run a backtest for a symbol.

    Replays signals over historical data and tracks accuracy.
    Returns win rate, average return, Sharpe ratio, and per-signal breakdown.
    """
    result = await _run_backtest_cached(symbol, trader_type, periods)
    return {"success": True, **result}


@router.get("/compare")
async def compare_strategies(
    symbol: str = Query(..., description="Stock symbol"),
    periods: int = Query(150, ge=50, le=500),
):
    """
    Compare all trader types for a symbol.

    Returns backtest results for day, swing, position, and scalp strategies
    side by side so users can pick the best approach.
    """
    styles = ["scalp", "day", "swing", "position"]

    # Run all 4 backtests in parallel
    tasks = [_run_backtest_cached(symbol, style, periods) for style in styles]
    bt_results = await asyncio.gather(*tasks)

    results = {}
    for style, bt in zip(styles, bt_results):
        results[style] = {
            "win_rate": bt["win_rate"],
            "avg_return": bt["avg_return"],
            "sharpe_ratio": bt["sharpe_ratio"],
            "total_signals": bt["total_signals"],
            "signal_breakdown": bt["signal_breakdown"],
        }

    # Determine best strategy
    best = max(results.items(), key=lambda x: x[1]["sharpe_ratio"])

    return {
        "success": True,
        "symbol": symbol.upper(),
        "strategies": results,
        "recommended": best[0],
        "reason": f"Highest Sharpe ratio ({best[1]['sharpe_ratio']}) with {best[1]['win_rate']}% win rate",
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/leaderboard")
async def signal_leaderboard(
    trader_type: str = Query("swing"),
):
    """
    Leaderboard: which symbols have the best signal accuracy?

    Tests a set of popular symbols and ranks them by win rate.
    """
    symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
        "SPY", "QQQ", "BTC-USD", "ETH-USD",
    ]

    # Run all backtests in parallel
    tasks = [_run_backtest_cached(sym, trader_type, 100) for sym in symbols]
    bt_results = await asyncio.gather(*tasks)

    leaderboard = []
    for sym, bt in zip(symbols, bt_results):
        leaderboard.append({
            "symbol": sym,
            "win_rate": bt["win_rate"],
            "avg_return": bt["avg_return"],
            "sharpe_ratio": bt["sharpe_ratio"],
            "total_signals": bt["total_signals"],
        })

    leaderboard.sort(key=lambda x: x["sharpe_ratio"], reverse=True)

    return {
        "success": True,
        "trader_type": trader_type,
        "leaderboard": leaderboard,
        "generated_at": datetime.now().isoformat(),
    }
