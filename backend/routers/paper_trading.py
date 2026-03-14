"""
Paper Trading Router
=====================
Virtual trading with $100K starting balance.
Users can place BUY/SELL/SHORT orders, track P&L, and view stats.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_db
from database.models import User, PaperTrade
from auth.security import require_auth

try:
    from middleware.rate_limit import limiter, DEFAULT_RATE

    def _default_rate_limit(func):
        return limiter.limit(DEFAULT_RATE)(func)
except ImportError:
    def _default_rate_limit(func):
        return func

router = APIRouter(prefix="/api/paper", tags=["Paper Trading"])
logger = logging.getLogger(__name__)

STARTING_BALANCE = 100_000.00
MAX_OPEN_POSITIONS = 20


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern=r"^(BUY|SELL|SHORT)$")
    quantity: float = Field(..., gt=0, le=100000)
    price: float = Field(..., gt=0)
    currency: str = Field(default="$", max_length=5)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    notes: str = Field(default="", max_length=500)


class CloseOrderRequest(BaseModel):
    price: float = Field(..., gt=0)
    notes: str = Field(default="", max_length=500)


# =============================================================================
# HELPERS
# =============================================================================

async def _get_paper_balance(user_id: int, db: AsyncSession) -> dict:
    """Calculate available cash and unrealized P&L from open positions."""
    # Sum capital locked in open positions
    result = await db.execute(
        select(
            func.coalesce(func.sum(PaperTrade.entry_price * PaperTrade.quantity), 0)
        ).where(PaperTrade.user_id == user_id, PaperTrade.status == "open")
    )
    locked_capital = float(result.scalar())

    # Sum realized P&L from closed trades
    result = await db.execute(
        select(
            func.coalesce(func.sum(PaperTrade.pnl), 0)
        ).where(PaperTrade.user_id == user_id, PaperTrade.status == "closed")
    )
    realized_pnl = float(result.scalar())

    available_cash = STARTING_BALANCE + realized_pnl - locked_capital
    return {
        "starting_balance": STARTING_BALANCE,
        "available_cash": round(available_cash, 2),
        "locked_in_positions": round(locked_capital, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_equity": round(available_cash + locked_capital, 2),
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/order")
@_default_rate_limit
async def place_order(
    request_obj: Request,
    order: PlaceOrderRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Place a paper trade order (BUY, SELL, or SHORT)."""
    # Check open position limit
    result = await db.execute(
        select(func.count()).where(
            PaperTrade.user_id == user.id, PaperTrade.status == "open"
        )
    )
    open_count = result.scalar()
    if open_count >= MAX_OPEN_POSITIONS:
        raise HTTPException(400, f"Maximum {MAX_OPEN_POSITIONS} open positions allowed")

    # Check available cash
    balance = await _get_paper_balance(user.id, db)
    order_cost = order.price * order.quantity
    if order_cost > balance["available_cash"]:
        raise HTTPException(400, f"Insufficient funds. Need ${order_cost:,.2f}, have ${balance['available_cash']:,.2f}")

    trade = PaperTrade(
        user_id=user.id,
        symbol=order.symbol.upper(),
        side=order.side,
        quantity=order.quantity,
        entry_price=order.price,
        currency=order.currency,
        stop_loss=order.stop_loss,
        take_profit=order.take_profit,
        notes=order.notes,
        status="open",
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    logger.info(f"Paper trade opened: user={user.id} {order.side} {order.quantity} {order.symbol} @ {order.price}")

    return {
        "success": True,
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "balance": await _get_paper_balance(user.id, db),
    }


@router.post("/order/{trade_id}/close")
@_default_rate_limit
async def close_order(
    request_obj: Request,
    trade_id: int,
    close: CloseOrderRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Close an open paper trade at a given price."""
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == user.id,
            PaperTrade.status == "open",
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(404, "Trade not found or already closed")

    # Calculate P&L
    if trade.side == "SHORT":
        pnl = (trade.entry_price - close.price) * trade.quantity
    else:  # BUY or SELL
        pnl = (close.price - trade.entry_price) * trade.quantity

    pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100

    trade.exit_price = close.price
    trade.pnl = round(pnl, 2)
    trade.pnl_pct = round(pnl_pct, 2)
    trade.status = "closed"
    trade.closed_at = datetime.now(timezone.utc)
    if close.notes:
        trade.notes = (trade.notes or "") + f" | Close: {close.notes}"

    await db.commit()

    logger.info(f"Paper trade closed: id={trade_id} pnl={pnl:.2f} ({pnl_pct:.1f}%)")

    return {
        "success": True,
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "pnl": trade.pnl,
        "pnl_pct": trade.pnl_pct,
        "balance": await _get_paper_balance(user.id, db),
    }


@router.get("/positions")
async def get_positions(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get all open paper positions."""
    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.user_id == user.id, PaperTrade.status == "open")
        .order_by(desc(PaperTrade.opened_at))
    )
    trades = result.scalars().all()

    return {
        "success": True,
        "positions": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "currency": t.currency,
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
                "notes": t.notes,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            }
            for t in trades
        ],
        "count": len(trades),
        "balance": await _get_paper_balance(user.id, db),
    }


@router.get("/history")
async def get_trade_history(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get closed paper trade history with pagination."""
    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.user_id == user.id, PaperTrade.status == "closed")
        .order_by(desc(PaperTrade.closed_at))
        .offset(offset)
        .limit(limit)
    )
    trades = result.scalars().all()

    return {
        "success": True,
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "currency": t.currency,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "notes": t.notes,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in trades
        ],
        "count": len(trades),
        "offset": offset,
        "limit": limit,
    }


@router.get("/stats")
async def get_stats(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get paper trading performance statistics."""
    # Aggregate stats from closed trades
    result = await db.execute(
        select(
            func.count().label("total_trades"),
            func.coalesce(func.sum(case((PaperTrade.pnl > 0, 1), else_=0)), 0).label("wins"),
            func.coalesce(func.sum(case((PaperTrade.pnl <= 0, 1), else_=0)), 0).label("losses"),
            func.coalesce(func.sum(PaperTrade.pnl), 0).label("total_pnl"),
            func.coalesce(func.avg(PaperTrade.pnl), 0).label("avg_pnl"),
            func.coalesce(func.avg(PaperTrade.pnl_pct), 0).label("avg_pnl_pct"),
            func.coalesce(func.max(PaperTrade.pnl), 0).label("best_trade"),
            func.coalesce(func.min(PaperTrade.pnl), 0).label("worst_trade"),
        ).where(PaperTrade.user_id == user.id, PaperTrade.status == "closed")
    )
    row = result.one()

    total = row.total_trades
    wins = row.wins
    win_rate = round((wins / total) * 100, 1) if total > 0 else 0

    # Profit factor: gross profit / gross loss
    profit_result = await db.execute(
        select(
            func.coalesce(func.sum(case((PaperTrade.pnl > 0, PaperTrade.pnl), else_=0)), 0),
            func.coalesce(func.abs(func.sum(case((PaperTrade.pnl < 0, PaperTrade.pnl), else_=0))), 0),
        ).where(PaperTrade.user_id == user.id, PaperTrade.status == "closed")
    )
    gross_profit, gross_loss = profit_result.one()
    profit_factor = round(float(gross_profit) / max(float(gross_loss), 0.01), 2)

    balance = await _get_paper_balance(user.id, db)

    return {
        "success": True,
        "stats": {
            "total_trades": total,
            "wins": wins,
            "losses": row.losses,
            "win_rate": win_rate,
            "total_pnl": round(float(row.total_pnl), 2),
            "avg_pnl": round(float(row.avg_pnl), 2),
            "avg_pnl_pct": round(float(row.avg_pnl_pct), 2),
            "best_trade": round(float(row.best_trade), 2),
            "worst_trade": round(float(row.worst_trade), 2),
            "profit_factor": profit_factor,
        },
        "balance": balance,
    }


@router.post("/reset")
async def reset_paper_account(
    request_obj: Request,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Reset paper trading account — deletes all trades and starts fresh."""
    await db.execute(
        PaperTrade.__table__.delete().where(PaperTrade.user_id == user.id)
    )
    await db.commit()

    logger.info(f"Paper account reset for user {user.id}")

    return {
        "success": True,
        "message": "Paper trading account reset to $100,000",
        "balance": await _get_paper_balance(user.id, db),
    }
