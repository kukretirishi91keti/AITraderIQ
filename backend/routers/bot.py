"""
Bot Router — CRUD for per-user auto-bot configuration, status, decisions.
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timezone

from database.engine import get_db
from database.models import User, BotConfig, BotDecisionLog, PaperTrade
from auth.security import require_auth

router = APIRouter(prefix="/api/bot", tags=["Auto Bot"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BotConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    strategy: Optional[str] = Field(default=None, pattern=r"^(day|swing|position|scalp)$")
    symbols: Optional[List[str]] = None
    max_position_usd: Optional[float] = Field(default=None, gt=0)
    max_daily_trades: Optional[int] = Field(default=None, ge=1, le=50)
    max_daily_loss_pct: Optional[float] = Field(default=None, gt=0, le=100)
    min_confidence: Optional[float] = Field(default=None, ge=0, le=100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_config(user_id: int, db: AsyncSession) -> BotConfig:
    result = await db.execute(select(BotConfig).where(BotConfig.user_id == user_id))
    config = result.scalar_one_or_none()
    if config is None:
        config = BotConfig(user_id=user_id)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


def _config_to_dict(config: BotConfig) -> dict:
    return {
        "enabled": config.enabled,
        "strategy": config.strategy,
        "symbols": config.symbols or [],
        "max_position_usd": config.max_position_usd,
        "max_daily_trades": config.max_daily_trades,
        "max_daily_loss_pct": config.max_daily_loss_pct,
        "min_confidence": config.min_confidence,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_bot_config(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return the current bot configuration for the authenticated user."""
    config = await _get_or_create_config(user.id, db)
    return _config_to_dict(config)


@router.put("/config")
async def update_bot_config(
    body: BotConfigUpdate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update bot configuration. Only provided fields are changed."""
    config = await _get_or_create_config(user.id, db)

    if body.enabled is not None:
        config.enabled = body.enabled
    if body.strategy is not None:
        config.strategy = body.strategy
    if body.symbols is not None:
        # normalise to uppercase, deduplicate, max 20 symbols
        config.symbols = list(dict.fromkeys(s.upper() for s in body.symbols))[:20]
    if body.max_position_usd is not None:
        config.max_position_usd = body.max_position_usd
    if body.max_daily_trades is not None:
        config.max_daily_trades = body.max_daily_trades
    if body.max_daily_loss_pct is not None:
        config.max_daily_loss_pct = body.max_daily_loss_pct
    if body.min_confidence is not None:
        config.min_confidence = body.min_confidence

    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config)

    return {
        "message": "Bot configuration updated",
        "config": _config_to_dict(config),
    }


@router.get("/status")
async def get_bot_status(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Current bot status: enabled state, trades today, P&L today, last decision time."""
    config = await _get_or_create_config(user.id, db)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    trades_today_result = await db.execute(
        select(func.count(BotDecisionLog.id)).where(
            BotDecisionLog.user_id == user.id,
            BotDecisionLog.action.in_(["BUY", "SELL"]),
            BotDecisionLog.created_at >= today_start,
        )
    )
    trades_today = trades_today_result.scalar() or 0

    pnl_today_result = await db.execute(
        select(func.coalesce(func.sum(PaperTrade.pnl), 0.0)).where(
            PaperTrade.user_id == user.id,
            PaperTrade.status == "closed",
            PaperTrade.strategy == "auto-bot",
            PaperTrade.closed_at >= today_start,
        )
    )
    pnl_today = round(float(pnl_today_result.scalar() or 0.0), 2)

    last_decision_result = await db.execute(
        select(BotDecisionLog.created_at)
        .where(BotDecisionLog.user_id == user.id)
        .order_by(BotDecisionLog.created_at.desc())
        .limit(1)
    )
    last_decision = last_decision_result.scalar_one_or_none()

    return {
        "enabled": config.enabled,
        "strategy": config.strategy,
        "symbols": config.symbols or [],
        "trades_today": trades_today,
        "max_daily_trades": config.max_daily_trades,
        "pnl_today": pnl_today,
        "last_decision_at": last_decision.isoformat() if last_decision else None,
    }


@router.get("/decisions")
async def get_bot_decisions(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent bot decisions (audit log)."""
    result = await db.execute(
        select(BotDecisionLog)
        .where(BotDecisionLog.user_id == user.id)
        .order_by(BotDecisionLog.created_at.desc())
        .limit(limit)
    )
    decisions = result.scalars().all()

    return {
        "count": len(decisions),
        "decisions": [
            {
                "id": d.id,
                "symbol": d.symbol,
                "action": d.action,
                "confidence": d.confidence,
                "score": d.score,
                "reason": d.reason,
                "indicators": d.indicators,
                "trade_id": d.trade_id,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ],
    }


@router.post("/run-now")
async def trigger_bot_run(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger one bot execution cycle for the current user.
    Useful for testing — bypasses the market-hours guard.
    """
    from services.bot_executor import _run_for_user
    from services.market_data_service import get_market_data_service

    config = await _get_or_create_config(user.id, db)
    if not config.symbols:
        raise HTTPException(status_code=400, detail="No symbols configured. Add symbols to your bot config first.")

    svc = get_market_data_service()
    acted = await _run_for_user(config, svc, db)

    return {
        "message": f"Bot cycle complete: {acted} trade(s) placed or closed",
        "actions_taken": acted,
    }
