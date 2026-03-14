"""
Strategy Builder Router
========================
No-code algo trading rules. Users define indicator conditions,
the system scans the universe and fires alerts when matched.

Rule format example:
  [
    {"indicator": "rsi", "operator": "<", "value": 30},
    {"indicator": "macd_crossover", "operator": "==", "value": "bullish"},
    {"indicator": "price_vs_vwap", "operator": ">", "value": 0}
  ]

Supported indicators:
  rsi, macd, macd_signal, macd_histogram, price, change_pct,
  volume, bb_upper, bb_lower, bb_bandwidth, vwap, atr,
  macd_crossover (bullish/bearish), rsi_zone (oversold/neutral/overbought),
  price_vs_vwap (above=1, below=-1)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_db
from database.models import User, Strategy
from auth.security import require_auth

try:
    from middleware.rate_limit import limiter, AI_RATE, DEFAULT_RATE

    def _scan_rate_limit(func):
        return limiter.limit(AI_RATE)(func)

    def _default_rate_limit(func):
        return limiter.limit(DEFAULT_RATE)(func)
except ImportError:
    def _scan_rate_limit(func):
        return func

    def _default_rate_limit(func):
        return func

router = APIRouter(prefix="/api/strategy", tags=["Strategy Builder"])
logger = logging.getLogger(__name__)

# Max strategies per tier
MAX_STRATEGIES = {"free": 2, "starter": 5, "pro": 20, "unlimited": 100}

VALID_INDICATORS = {
    "rsi", "macd", "macd_signal", "macd_histogram",
    "price", "change_pct", "volume",
    "bb_upper", "bb_lower", "bb_bandwidth",
    "vwap", "atr",
    "macd_crossover", "rsi_zone", "price_vs_vwap",
}

VALID_OPERATORS = {"<", "<=", ">", ">=", "==", "!="}

# Symbols to scan per universe category (subset for demo performance)
SCAN_UNIVERSES = {
    "US_TECH": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "INTC", "CRM"],
    "US_FINANCE": ["JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "SCHW", "AXP", "V"],
    "US_HEALTH": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "BMY", "AMGN"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "DOGE-USD"],
    "ETF": ["SPY", "QQQ", "IWM", "DIA", "VTI", "ARKK", "XLF", "XLK", "XLE", "GLD"],
    "INDIA": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
}


# =============================================================================
# REQUEST MODELS
# =============================================================================

class RuleCondition(BaseModel):
    indicator: str = Field(..., description="Indicator name")
    operator: str = Field(..., pattern=r"^(<|<=|>|>=|==|!=)$")
    value: float | str = Field(..., description="Threshold value")


class CreateStrategyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    conditions: List[RuleCondition] = Field(..., min_length=1, max_length=10)
    action: str = Field(default="BUY", pattern=r"^(BUY|SELL)$")
    universe: str = Field(default="US_TECH", max_length=200)


class UpdateStrategyRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    conditions: Optional[List[RuleCondition]] = None
    action: Optional[str] = Field(None, pattern=r"^(BUY|SELL)$")
    universe: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


# =============================================================================
# RULE EVALUATION ENGINE
# =============================================================================

def _evaluate_condition(condition: dict, data: dict) -> bool:
    """Evaluate a single condition against market data."""
    indicator = condition["indicator"]
    operator = condition["operator"]
    threshold = condition["value"]

    # Derived indicators
    if indicator == "macd_crossover":
        macd = data.get("macd", 0)
        signal = data.get("macd_signal", 0)
        actual = "bullish" if macd > signal else "bearish"
        return (actual == threshold) if operator == "==" else (actual != threshold)

    if indicator == "rsi_zone":
        rsi = data.get("rsi", 50)
        if rsi < 30:
            actual = "oversold"
        elif rsi > 70:
            actual = "overbought"
        else:
            actual = "neutral"
        return (actual == threshold) if operator == "==" else (actual != threshold)

    if indicator == "price_vs_vwap":
        price = data.get("price", 0)
        vwap = data.get("vwap", price)
        actual = 1 if price > vwap else -1
        threshold = float(threshold)
    else:
        actual = data.get(indicator)
        if actual is None:
            return False
        threshold = float(threshold)

    # Numeric comparison
    if operator == "<":
        return actual < threshold
    elif operator == "<=":
        return actual <= threshold
    elif operator == ">":
        return actual > threshold
    elif operator == ">=":
        return actual >= threshold
    elif operator == "==":
        return actual == threshold
    elif operator == "!=":
        return actual != threshold
    return False


def _evaluate_strategy(conditions: list, data: dict) -> dict:
    """Evaluate all conditions. Returns match result with details."""
    results = []
    for cond in conditions:
        passed = _evaluate_condition(cond, data)
        results.append({
            "indicator": cond["indicator"],
            "operator": cond["operator"],
            "threshold": cond["value"],
            "actual": data.get(cond["indicator"]),
            "passed": passed,
        })

    all_passed = all(r["passed"] for r in results)
    return {"match": all_passed, "conditions": results}


async def _fetch_symbol_data(symbol: str) -> dict:
    """Fetch current market data for a symbol using internal API."""
    try:
        from services.market_data_service import get_market_data_service
        svc = get_market_data_service()
        quote = await svc.get_quote(symbol)
        if not quote:
            return {}

        # Also try to get signals
        data = {
            "symbol": symbol,
            "price": quote.get("price", 0),
            "change_pct": quote.get("changePct", 0),
            "volume": quote.get("volume", 0),
            "rsi": quote.get("rsi", 50),
            "macd": quote.get("macd", 0),
            "macd_signal": quote.get("macdSignal", 0),
            "macd_histogram": (quote.get("macd", 0) or 0) - (quote.get("macdSignal", 0) or 0),
            "bb_upper": quote.get("bbUpper", 0),
            "bb_lower": quote.get("bbLower", 0),
            "vwap": quote.get("vwap", quote.get("price", 0)),
        }

        # Derived
        if data["bb_upper"] and data["bb_lower"] and data["bb_upper"] > 0:
            data["bb_bandwidth"] = round(
                (data["bb_upper"] - data["bb_lower"]) / data["price"] * 100, 2
            ) if data["price"] else 0

        return data
    except Exception as e:
        logger.warning(f"Failed to fetch data for {symbol}: {e}")
        return {}


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/create")
@_default_rate_limit
async def create_strategy(
    request_obj: Request,
    req: CreateStrategyRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new trading strategy with rule conditions."""
    # Validate indicator names
    for cond in req.conditions:
        if cond.indicator not in VALID_INDICATORS:
            raise HTTPException(400, f"Unknown indicator: {cond.indicator}. Valid: {sorted(VALID_INDICATORS)}")

    # Check strategy limit per tier
    tier = user.tier or "free"
    max_allowed = MAX_STRATEGIES.get(tier, 2)
    result = await db.execute(
        select(func.count()).where(Strategy.user_id == user.id)
    )
    current_count = result.scalar()
    if current_count >= max_allowed:
        raise HTTPException(400, f"{tier} tier allows max {max_allowed} strategies. Upgrade for more.")

    # Validate universe
    universes = [u.strip() for u in req.universe.split(",")]
    for u in universes:
        if u not in SCAN_UNIVERSES:
            raise HTTPException(400, f"Unknown universe: {u}. Valid: {sorted(SCAN_UNIVERSES.keys())}")

    rules = [c.model_dump() for c in req.conditions]

    strategy = Strategy(
        user_id=user.id,
        name=req.name,
        description=req.description,
        rules_json=json.dumps(rules),
        action=req.action,
        universe=req.universe,
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    logger.info(f"Strategy created: user={user.id} name='{req.name}' rules={len(rules)}")

    return {
        "success": True,
        "strategy": {
            "id": strategy.id,
            "name": strategy.name,
            "description": strategy.description,
            "conditions": rules,
            "action": strategy.action,
            "universe": strategy.universe,
            "is_active": strategy.is_active,
        },
    }


@router.get("/list")
async def list_strategies(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all user strategies."""
    result = await db.execute(
        select(Strategy)
        .where(Strategy.user_id == user.id)
        .order_by(desc(Strategy.created_at))
    )
    strategies = result.scalars().all()

    tier = user.tier or "free"

    return {
        "success": True,
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "conditions": json.loads(s.rules_json),
                "action": s.action,
                "universe": s.universe,
                "is_active": s.is_active,
                "matches_count": s.matches_count,
                "last_scan_at": s.last_scan_at.isoformat() if s.last_scan_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in strategies
        ],
        "count": len(strategies),
        "max_allowed": MAX_STRATEGIES.get(tier, 2),
        "tier": tier,
    }


@router.put("/{strategy_id}")
@_default_rate_limit
async def update_strategy(
    request_obj: Request,
    strategy_id: int,
    req: UpdateStrategyRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing strategy."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    if req.name is not None:
        strategy.name = req.name
    if req.description is not None:
        strategy.description = req.description
    if req.action is not None:
        strategy.action = req.action
    if req.universe is not None:
        strategy.universe = req.universe
    if req.is_active is not None:
        strategy.is_active = req.is_active
    if req.conditions is not None:
        for cond in req.conditions:
            if cond.indicator not in VALID_INDICATORS:
                raise HTTPException(400, f"Unknown indicator: {cond.indicator}")
        strategy.rules_json = json.dumps([c.model_dump() for c in req.conditions])

    strategy.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True, "message": "Strategy updated"}


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a strategy."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    await db.delete(strategy)
    await db.commit()

    return {"success": True, "message": "Strategy deleted"}


@router.post("/{strategy_id}/scan")
@_scan_rate_limit
async def scan_strategy(
    request_obj: Request,
    strategy_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Run a strategy scan against its universe. Returns matching symbols."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    conditions = json.loads(strategy.rules_json)
    universes = [u.strip() for u in strategy.universe.split(",")]

    # Collect symbols to scan
    symbols = []
    for u in universes:
        symbols.extend(SCAN_UNIVERSES.get(u, []))
    symbols = list(set(symbols))  # deduplicate

    # Scan each symbol
    matches = []
    scanned = 0
    for symbol in symbols:
        data = await _fetch_symbol_data(symbol)
        if not data:
            continue
        scanned += 1
        eval_result = _evaluate_strategy(conditions, data)
        if eval_result["match"]:
            matches.append({
                "symbol": symbol,
                "price": data.get("price"),
                "rsi": data.get("rsi"),
                "macd": data.get("macd"),
                "change_pct": data.get("change_pct"),
                "conditions": eval_result["conditions"],
            })

    # Update strategy metadata
    strategy.last_scan_at = datetime.now(timezone.utc)
    strategy.matches_count = len(matches)
    await db.commit()

    logger.info(f"Strategy scan: id={strategy_id} scanned={scanned} matches={len(matches)}")

    return {
        "success": True,
        "strategy_name": strategy.name,
        "action": strategy.action,
        "scanned": scanned,
        "matches": matches,
        "match_count": len(matches),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{strategy_id}/backtest")
@_scan_rate_limit
async def backtest_strategy(
    request_obj: Request,
    strategy_id: int,
    symbol: str = "AAPL",
    days: int = 30,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Backtest a strategy on historical data for a single symbol.

    Uses the existing signals/backtest infrastructure to evaluate
    how the strategy's conditions would have performed historically.
    """
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Strategy not found")

    conditions = json.loads(strategy.rules_json)
    days = min(days, 90)  # cap at 90 days

    # Simulate by evaluating current snapshot (simplified backtest)
    # In production this would iterate over historical candles
    data = await _fetch_symbol_data(symbol)
    if not data:
        raise HTTPException(400, f"No data available for {symbol}")

    eval_result = _evaluate_strategy(conditions, data)

    return {
        "success": True,
        "strategy_name": strategy.name,
        "symbol": symbol,
        "current_match": eval_result["match"],
        "conditions": eval_result["conditions"],
        "recommendation": f"{strategy.action} {symbol}" if eval_result["match"] else f"No {strategy.action} signal",
        "note": "Full historical backtest coming soon. Current evaluation uses live snapshot.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/indicators")
async def list_indicators():
    """List all supported indicators and operators for building rules."""
    return {
        "indicators": [
            {"id": "rsi", "name": "RSI (14)", "type": "numeric", "range": "0-100", "description": "Relative Strength Index"},
            {"id": "macd", "name": "MACD", "type": "numeric", "description": "MACD line value"},
            {"id": "macd_signal", "name": "MACD Signal", "type": "numeric", "description": "MACD signal line"},
            {"id": "macd_histogram", "name": "MACD Histogram", "type": "numeric", "description": "MACD - Signal difference"},
            {"id": "macd_crossover", "name": "MACD Crossover", "type": "enum", "values": ["bullish", "bearish"], "description": "MACD crosses signal line"},
            {"id": "rsi_zone", "name": "RSI Zone", "type": "enum", "values": ["oversold", "neutral", "overbought"], "description": "RSI zone classification"},
            {"id": "price", "name": "Price", "type": "numeric", "description": "Current stock price"},
            {"id": "change_pct", "name": "Change %", "type": "numeric", "description": "Intraday price change percentage"},
            {"id": "volume", "name": "Volume", "type": "numeric", "description": "Trading volume"},
            {"id": "bb_upper", "name": "Bollinger Upper", "type": "numeric", "description": "Upper Bollinger Band"},
            {"id": "bb_lower", "name": "Bollinger Lower", "type": "numeric", "description": "Lower Bollinger Band"},
            {"id": "bb_bandwidth", "name": "Bollinger Width %", "type": "numeric", "description": "Bollinger Band width as % of price"},
            {"id": "vwap", "name": "VWAP", "type": "numeric", "description": "Volume Weighted Average Price"},
            {"id": "price_vs_vwap", "name": "Price vs VWAP", "type": "enum", "values": ["1", "-1"], "description": "1 = above VWAP, -1 = below"},
        ],
        "operators": ["<", "<=", ">", ">=", "==", "!="],
        "universes": [
            {"id": k, "name": k.replace("_", " ").title(), "symbols": len(v)}
            for k, v in sorted(SCAN_UNIVERSES.items())
        ],
    }
