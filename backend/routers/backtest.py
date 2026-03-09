"""
Backtest Router - Signal accuracy tracking and backtesting endpoints.
"""

from fastapi import APIRouter, Query
from datetime import datetime

from services.backtest_engine import get_backtest_engine

router = APIRouter(prefix="/api/backtest", tags=["Backtesting"])


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
    engine = get_backtest_engine()
    result = engine.run_backtest(symbol, trader_type, periods)
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
    engine = get_backtest_engine()
    results = {}

    for style in ["scalp", "day", "swing", "position"]:
        bt = engine.run_backtest(symbol, style, periods)
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
    engine = get_backtest_engine()
    symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
        "SPY", "QQQ", "BTC-USD", "ETH-USD",
    ]

    leaderboard = []
    for sym in symbols:
        bt = engine.run_backtest(sym, trader_type, 100)
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
