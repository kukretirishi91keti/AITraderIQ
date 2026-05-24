"""
Strategy Intelligence Router v1.0
==================================
Location: backend/routers/strategy.py

Endpoints for the Trading Strategy Intelligence system.
Provides strategy recommendations, growth projections, and market intelligence.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import logging

from auth.security import require_auth
from database.engine import get_db
from database.models import User, PortfolioItem, PaperTrade
from utils.validation import validate_symbol
from services.market_data_service import get_market_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["strategy-intelligence"])


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================


class StrategyRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock/crypto ticker")
    market: str = Field(default="", description="Market context (US, INDIA, UK, etc.)")
    capital: float = Field(10000, ge=100, le=100_000_000, description="Investment capital")
    growth_target_pct: float = Field(10, ge=1, le=500, description="Target growth %")
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")
    time_horizon: str = Field("medium", pattern="^(short|medium|long)$")
    trader_style: str = Field("swing", pattern="^(scalp|day|swing|position)$")


class MarketOverviewRequest(BaseModel):
    symbols: List[str] = Field(default=[], description="Symbols to analyze (empty = use market default)")
    market: str = Field(default="US", description="Market to analyze")
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")


class ApplyStrategyRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    strategy_name: str = Field(..., description="Strategy name from intelligence results")
    capital: float = Field(..., ge=100)
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")


class ApplyPortfolioStrategyRequest(BaseModel):
    strategy_name: str = Field(default="auto", description="Strategy to apply or 'auto' for AI selection")
    risk_tolerance: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")
    market: str = Field(default="", description="Filter portfolio by market (empty = all)")


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

    If symbols is empty, defaults to the market's standard symbol list.
    """
    try:
        from services.strategy_intelligence import get_market_intelligence_overview

        symbols = [s.upper().strip() for s in request.symbols] if request.symbols else []

        # If no symbols provided, pull defaults from MARKET_SYMBOLS
        if not symbols:
            from routers.stock import MARKET_SYMBOLS
            market_key = request.market.upper() if request.market else "US"
            symbols = MARKET_SYMBOLS.get(market_key, MARKET_SYMBOLS["US"])

        result = await get_market_intelligence_overview(
            symbols=symbols,
            risk_tolerance=request.risk_tolerance,
        )
        return result
    except Exception as e:
        logger.error(f"Market overview error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Market analysis failed")


@router.post("/apply")
async def apply_strategy(
    request: ApplyStrategyRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Apply a strategy by creating a paper trade based on the strategy recommendation."""
    from services.strategy_intelligence import STRATEGIES

    # Validate symbol
    symbol = validate_symbol(request.symbol)

    # Validate strategy name exists
    if request.strategy_name not in STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{request.strategy_name}'. "
                   f"Valid strategies: {', '.join(STRATEGIES.keys())}",
        )

    # 1. Get current price from market data service
    svc = get_market_data_service()
    try:
        quote = await svc.get_quote(symbol)
        current_price = quote.get("price")
        currency_sym = quote.get("currency", "$")
        if not current_price or current_price <= 0:
            raise ValueError("Invalid price")
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch current price for {symbol}",
        )

    # 2. Calculate position size based on capital and risk tolerance
    risk_pct_map = {
        "conservative": 0.02,
        "moderate": 0.05,
        "aggressive": 0.10,
    }
    risk_pct = risk_pct_map[request.risk_tolerance]
    position_capital = request.capital * risk_pct
    quantity = round(position_capital / current_price, 6)

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Capital too low to buy even a fractional share of {symbol} at {currency_sym}{current_price:.2f}",
        )

    # 3. Create a PaperTrade record
    trade = PaperTrade(
        user_id=user.id,
        symbol=symbol,
        side="buy",
        quantity=quantity,
        entry_price=current_price,
        status="open",
        strategy=request.strategy_name,
        notes=f"Auto-created via strategy apply. "
              f"Risk tolerance: {request.risk_tolerance}, "
              f"Capital allocated: {currency_sym}{position_capital:.2f} of {currency_sym}{request.capital:.2f}",
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    strategy_info = STRATEGIES[request.strategy_name]

    # 4. Return the created trade details
    return {
        "trade_id": trade.id,
        "symbol": symbol,
        "side": "buy",
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "position_value": round(trade.quantity * trade.entry_price, 2),
        "strategy": request.strategy_name,
        "strategy_name": strategy_info["name"],
        "risk_tolerance": request.risk_tolerance,
        "capital_allocated": round(position_capital, 2),
        "capital_total": request.capital,
        "risk_pct": risk_pct * 100,
        "status": "open",
        "exit_rules": strategy_info["exit_rules"],
        "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
    }


@router.post("/apply-portfolio")
async def apply_portfolio_strategy(
    request: ApplyPortfolioStrategyRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Analyze portfolio and apply strategy across holdings.

    Returns per-holding analysis with strategy recommendations and suggested
    actions. Does NOT auto-execute trades -- the user should review and confirm
    via the /apply endpoint for each holding they want to act on.
    """
    from services.strategy_intelligence import (
        STRATEGIES,
        _generate_indicators,
        _analyze_market_condition,
        _simulate_historical_performance,
        _score_strategy,
    )

    # 1. Get user's portfolio holdings from DB
    query = select(PortfolioItem).where(PortfolioItem.user_id == user.id)
    if request.market:
        query = query.where(PortfolioItem.market == request.market.upper())
    result = await db.execute(query)
    holdings = result.scalars().all()

    if not holdings:
        raise HTTPException(
            status_code=404,
            detail="No portfolio holdings found"
                   + (f" for market '{request.market.upper()}'" if request.market else ""),
        )

    svc = get_market_data_service()

    user_profile = {
        "risk_tolerance": request.risk_tolerance,
        "time_horizon": "medium",
        "capital": 10000,  # per-holding default for scoring
        "growth_target_pct": 10,
    }

    holding_analyses = []

    for holding in holdings:
        symbol = holding.symbol

        # 2. Get current signals / indicators
        indicators = _generate_indicators(symbol)
        market_condition = _analyze_market_condition(symbol, indicators)

        # 3. Get current price
        try:
            quote = await svc.get_quote(symbol)
            current_price = quote.get("price", holding.avg_price)
        except Exception:
            current_price = holding.avg_price  # fallback

        unrealized_pnl = (current_price - holding.avg_price) * holding.shares
        unrealized_pnl_pct = (
            ((current_price - holding.avg_price) / holding.avg_price) * 100
            if holding.avg_price > 0
            else 0
        )

        # 3. Generate strategy recommendations per holding
        if request.strategy_name == "auto":
            # Score all strategies, pick best
            best_score = -1
            best_key = "mean_reversion"
            for key, strategy in STRATEGIES.items():
                historical = _simulate_historical_performance(symbol, key)
                score_result = _score_strategy(
                    key, strategy, market_condition, user_profile, historical,
                )
                if score_result["score"] > best_score:
                    best_score = score_result["score"]
                    best_key = key
            recommended_strategy = best_key
            confidence = best_score
        else:
            if request.strategy_name not in STRATEGIES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown strategy '{request.strategy_name}'",
                )
            recommended_strategy = request.strategy_name
            historical = _simulate_historical_performance(symbol, recommended_strategy)
            score_result = _score_strategy(
                recommended_strategy,
                STRATEGIES[recommended_strategy],
                market_condition,
                user_profile,
                historical,
            )
            confidence = score_result["score"]

        strategy_info = STRATEGIES[recommended_strategy]

        # Determine suggested action based on market condition + strategy
        if market_condition["momentum"] in ("oversold", "bearish") and unrealized_pnl_pct < -5:
            suggested_action = "hold_or_add"
            action_reason = "Oversold conditions may present a buying opportunity"
        elif market_condition["momentum"] in ("overbought",) and unrealized_pnl_pct > 10:
            suggested_action = "consider_taking_profit"
            action_reason = "Overbought with significant gains -- consider partial exit"
        elif market_condition["momentum"] == "bullish":
            suggested_action = "hold"
            action_reason = "Bullish momentum supports continued holding"
        else:
            suggested_action = "monitor"
            action_reason = "Neutral conditions -- watch for entry/exit signals"

        holding_analyses.append({
            "symbol": symbol,
            "market": holding.market,
            "shares": holding.shares,
            "avg_price": holding.avg_price,
            "current_price": round(current_price, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "market_condition": {
                "trend": market_condition["trend"],
                "momentum": market_condition["momentum"],
                "volatility": market_condition["volatility"],
                "rsi": market_condition["rsi"],
            },
            "recommended_strategy": recommended_strategy,
            "strategy_name": strategy_info["name"],
            "confidence": round(confidence, 1),
            "suggested_action": suggested_action,
            "action_reason": action_reason,
            "entry_rules": strategy_info["entry_rules"],
            "exit_rules": strategy_info["exit_rules"],
        })

    # Sort by confidence descending
    holding_analyses.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "portfolio_size": len(holding_analyses),
        "market_filter": request.market.upper() if request.market else "ALL",
        "strategy_mode": request.strategy_name,
        "risk_tolerance": request.risk_tolerance,
        "holdings": holding_analyses,
        "summary": {
            "total_holdings": len(holding_analyses),
            "bullish_count": sum(1 for h in holding_analyses if h["market_condition"]["momentum"] in ("bullish", "overbought")),
            "bearish_count": sum(1 for h in holding_analyses if h["market_condition"]["momentum"] in ("bearish", "oversold")),
            "avg_confidence": round(sum(h["confidence"] for h in holding_analyses) / len(holding_analyses), 1) if holding_analyses else 0,
            "actions": {
                "hold": sum(1 for h in holding_analyses if h["suggested_action"] == "hold"),
                "hold_or_add": sum(1 for h in holding_analyses if h["suggested_action"] == "hold_or_add"),
                "consider_taking_profit": sum(1 for h in holding_analyses if h["suggested_action"] == "consider_taking_profit"),
                "monitor": sum(1 for h in holding_analyses if h["suggested_action"] == "monitor"),
            },
        },
    }


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
