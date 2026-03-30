"""
Paper Trade Router - Simulated trading for strategy testing.
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional
from datetime import datetime
import logging

from database.engine import get_db
from database.models import User, PaperTrade
from auth.security import require_auth
from utils.validation import validate_symbol, sanitize_text
from services.market_data_service import get_market_data_service

router = APIRouter(prefix="/api/paper-trade", tags=["Paper Trading"])
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST MODELS
# =============================================================================

class PlaceTrade(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern=r"^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    strategy: Optional[str] = Field(default=None, max_length=50)
    notes: str = Field(default="", max_length=500)


class SetLevels(BaseModel):
    stop_loss_price: Optional[float] = Field(default=None, gt=0)
    take_profit_price: Optional[float] = Field(default=None, gt=0)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("", status_code=201)
async def place_paper_trade(
    request: PlaceTrade,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Place a new paper trade (buy or sell)."""
    symbol = validate_symbol(request.symbol)

    # Fetch current market price
    try:
        svc = get_market_data_service()
        quote = await svc.get_quote(symbol)
        price = quote.get("price")
        currency = quote.get("currency", "$")
        market = quote.get("market", "US")
        if price is None:
            raise ValueError("No price returned")
    except Exception as e:
        logger.error(f"Failed to fetch quote for {symbol}: {e}")
        raise HTTPException(status_code=502, detail=f"Could not fetch current price for {symbol}")

    trade = PaperTrade(
        user_id=user.id,
        symbol=symbol,
        side=request.side,
        quantity=request.quantity,
        entry_price=price,
        status="open",
        strategy=request.strategy,
        market=market,
        currency=currency,
        notes=sanitize_text(request.notes),
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "quantity": trade.quantity,
        "entry_price": trade.entry_price,
        "currency": trade.currency,
        "status": trade.status,
        "message": f"Paper {trade.side} placed for {trade.quantity} shares of {symbol} at {currency}{price:.2f}",
    }


@router.get("/summary")
async def get_paper_trade_summary(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get paper trading P&L summary."""
    result = await db.execute(
        select(PaperTrade).where(PaperTrade.user_id == user.id)
    )
    trades = result.scalars().all()

    total_trades = len(trades)
    open_trades = [t for t in trades if t.status == "open"]
    closed_trades = [t for t in trades if t.status == "closed"]

    wins = [t for t in closed_trades if t.pnl is not None and t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl is not None and t.pnl <= 0]
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0

    total_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None)

    return {
        "total_trades": total_trades,
        "open_positions": len(open_trades),
        "closed_trades": len(closed_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
    }


@router.get("/journal")
async def get_trade_journal(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Return closed trades + risk metrics + equity-curve data points.
    Equity curve = cumulative P&L sorted by closed_at.
    """
    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.user_id == user.id, PaperTrade.status == "closed")
        .order_by(PaperTrade.closed_at)
    )
    closed = result.scalars().all()

    pnls = [t.pnl for t in closed if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Equity curve: cumulative sum over time
    equity_curve = []
    running = 0.0
    for t in closed:
        if t.pnl is not None:
            running += t.pnl
        equity_curve.append({
            "date": t.closed_at.isoformat() if t.closed_at else None,
            "symbol": t.symbol,
            "cumulative_pnl": round(running, 2),
        })

    total_pnl = sum(pnls)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0.0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else None

    # Max drawdown from equity curve
    peak = 0.0
    max_dd = 0.0
    running2 = 0.0
    for p in pnls:
        running2 += p
        if running2 > peak:
            peak = running2
        dd = peak - running2
        if dd > max_dd:
            max_dd = dd

    return {
        "metrics": {
            "total_closed": len(closed),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor else None,
            "max_drawdown": round(max_dd, 2),
            "best_trade": round(max(pnls), 2) if pnls else 0,
            "worst_trade": round(min(pnls), 2) if pnls else 0,
        },
        "equity_curve": equity_curve,
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "currency": t.currency,
                "strategy": t.strategy,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in reversed(closed)  # newest first
        ],
    }


@router.get("")
async def list_paper_trades(
    status: Optional[str] = Query(default=None, pattern=r"^(open|closed)$"),
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List user's paper trades. Optionally filter by status (open/closed)."""
    query = select(PaperTrade).where(PaperTrade.user_id == user.id)
    if status:
        query = query.where(PaperTrade.status == status)
    query = query.order_by(PaperTrade.opened_at.desc())

    result = await db.execute(query)
    trades = result.scalars().all()

    return {
        "count": len(trades),
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "status": t.status,
                "strategy": t.strategy,
                "market": t.market,
                "currency": t.currency,
                "stop_loss_price": t.stop_loss_price,
                "take_profit_price": t.take_profit_price,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "notes": t.notes,
                "opened_at": t.opened_at.isoformat() if t.opened_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in trades
        ],
    }


@router.post("/{trade_id}/close")
async def close_paper_trade(
    trade_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Close an open paper trade at the current market price."""
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == user.id,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    # Fetch current price for exit
    try:
        svc = get_market_data_service()
        quote = await svc.get_quote(trade.symbol)
        exit_price = quote.get("price")
        if exit_price is None:
            raise ValueError("No price returned")
    except Exception as e:
        logger.error(f"Failed to fetch exit price for {trade.symbol}: {e}")
        raise HTTPException(status_code=502, detail=f"Could not fetch current price for {trade.symbol}")

    # Calculate P&L
    if trade.side == "buy":
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:  # sell (short)
        pnl = (trade.entry_price - exit_price) * trade.quantity

    pnl_percent = ((pnl) / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price else 0.0

    trade.exit_price = exit_price
    trade.pnl = round(pnl, 2)
    trade.pnl_percent = round(pnl_percent, 2)
    trade.status = "closed"
    trade.closed_at = datetime.utcnow()

    await db.commit()

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "quantity": trade.quantity,
        "pnl": trade.pnl,
        "pnl_percent": trade.pnl_percent,
        "currency": trade.currency,
        "status": "closed",
        "message": f"Trade closed. P&L: {trade.currency}{trade.pnl:+.2f} ({trade.pnl_percent:+.2f}%)",
    }


@router.put("/{trade_id}/levels")
async def set_trade_levels(
    trade_id: int,
    levels: SetLevels,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Set stop-loss and/or take-profit price levels on an open paper trade."""
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == user.id,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Paper trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail="Cannot set levels on a closed trade")

    if levels.stop_loss_price is not None:
        trade.stop_loss_price = levels.stop_loss_price
    if levels.take_profit_price is not None:
        trade.take_profit_price = levels.take_profit_price

    await db.commit()

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "stop_loss_price": trade.stop_loss_price,
        "take_profit_price": trade.take_profit_price,
        "message": "Trade levels updated",
    }


@router.delete("/{trade_id}")
async def delete_paper_trade(
    trade_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/delete a paper trade."""
    result = await db.execute(
        delete(PaperTrade).where(
            PaperTrade.id == trade_id,
            PaperTrade.user_id == user.id,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Paper trade not found")

    return {"message": "Paper trade deleted"}
