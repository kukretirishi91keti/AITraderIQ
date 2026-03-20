"""
Strategy Intelligence Router v1.0
==================================
Location: backend/routers/strategy.py

Endpoints for the Trading Strategy Intelligence system.
Provides strategy recommendations, growth projections, and market intelligence.
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["strategy-intelligence"])


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================


class StrategyRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock/crypto ticker")
    capital: float = Field(10000, ge=100, le=100_000_000, description="Investment capital")
    growth_target_pct: float = Field(10, ge=1, le=500, description="Target growth %")
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")
    time_horizon: str = Field("medium", pattern="^(short|medium|long)$")
    trader_style: str = Field("swing", pattern="^(scalp|day|swing|position)$")


class MarketOverviewRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=1, max_length=20)
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/intelligence")
async def get_intelligence(request: StrategyRequest):
    """Get comprehensive strategy intelligence for a symbol.

    Combines real-time data, historical patterns, technical trends, sentiment,
    and AI reasoning into ranked strategy recommendations with growth projections.

    Used by the Strategy Intelligence wizard on the frontend.
    """
    try:
        from services.strategy_intelligence import get_strategy_intelligence

        result = await get_strategy_intelligence(
            symbol=request.symbol.upper().strip(),
            capital=request.capital,
            growth_target_pct=request.growth_target_pct,
            risk_tolerance=request.risk_tolerance,
            time_horizon=request.time_horizon,
            trader_style=request.trader_style,
        )
        return result
    except Exception as e:
        logger.error(f"Strategy intelligence error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Strategy analysis failed")


@router.get("/intelligence/{symbol}")
async def get_intelligence_quick(
    symbol: str,
    capital: float = Query(10000, ge=100, le=100_000_000),
    growth_target_pct: float = Query(10, ge=1, le=500),
    risk_tolerance: str = Query("moderate"),
    time_horizon: str = Query("medium"),
    trader_style: str = Query("swing"),
):
    """Quick GET endpoint for strategy intelligence.

    Same as POST but via query parameters — useful for direct linking and demos.
    """
    try:
        from services.strategy_intelligence import get_strategy_intelligence

        result = await get_strategy_intelligence(
            symbol=symbol.upper().strip(),
            capital=capital,
            growth_target_pct=growth_target_pct,
            risk_tolerance=risk_tolerance,
            time_horizon=time_horizon,
            trader_style=trader_style,
        )
        return result
    except Exception as e:
        logger.error(f"Strategy intelligence error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Strategy analysis failed")


@router.post("/market-overview")
async def get_market_overview(request: MarketOverviewRequest):
    """Get market intelligence overview across multiple symbols.

    Returns market mood, per-symbol trend/momentum analysis,
    and top opportunities ranked by condition.
    """
    try:
        from services.strategy_intelligence import get_market_intelligence_overview

        result = await get_market_intelligence_overview(
            symbols=[s.upper().strip() for s in request.symbols],
            risk_tolerance=request.risk_tolerance,
        )
        return result
    except Exception as e:
        logger.error(f"Market overview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Market analysis failed")


@router.get("/strategies")
async def list_strategies():
    """List all available trading strategies with their details.

    No user context needed — returns the full strategy catalog.
    """
    from services.strategy_intelligence import STRATEGIES

    return {
        "count": len(STRATEGIES),
        "strategies": [
            {
                "key": key,
                "name": s["name"],
                "description": s["description"],
                "style": s["style"],
                "risk_level": s["risk_level"],
                "typical_hold": s["typical_hold"],
                "indicators_used": s["indicators_used"],
                "entry_rules": s["entry_rules"],
                "exit_rules": s["exit_rules"],
                "best_market_conditions": s["best_market_conditions"],
            }
            for key, s in STRATEGIES.items()
        ],
    }
