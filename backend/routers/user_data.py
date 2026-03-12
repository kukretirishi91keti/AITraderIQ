"""
User Data Router - Watchlists, Portfolio, Alerts (persisted in DB).
All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional
from datetime import datetime, timezone

from database.engine import get_db
from database.models import User, WatchlistItem, PortfolioItem, Alert
from auth.security import require_auth
from utils.validation import validate_symbol

router = APIRouter(prefix="/api/user", tags=["User Data"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class AddWatchlistItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    market: str = Field(default="US", max_length=20)
    notes: str = Field(default="", max_length=500)


class AddPortfolioItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    shares: float = Field(..., gt=0)
    avg_price: float = Field(..., gt=0)
    currency: str = Field(default="$", max_length=10)
    market: str = Field(default="US", max_length=20)
    notes: str = Field(default="", max_length=500)


class UpdatePortfolioItem(BaseModel):
    shares: float | None = Field(default=None, gt=0)
    avg_price: float | None = Field(default=None, gt=0)
    notes: str | None = None


class AddAlert(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    condition: str = Field(..., pattern=r"^(above|below|rsi_above|rsi_below)$")
    target_value: float


# =============================================================================
# WATCHLIST ENDPOINTS
# =============================================================================

@router.get("/watchlist")
async def get_watchlist(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user's watchlist with pagination."""
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.sort_order, WatchlistItem.added_at)
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()

    return {
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "watchlist": [
            {
                "id": item.id,
                "symbol": item.symbol,
                "market": item.market,
                "notes": item.notes,
                "added_at": item.added_at.isoformat() if item.added_at else None,
            }
            for item in items
        ],
    }


@router.post("/watchlist", status_code=201)
async def add_to_watchlist(
    request: AddWatchlistItem,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a symbol to the watchlist."""
    symbol = validate_symbol(request.symbol)

    # Check for duplicate
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.symbol == symbol,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{symbol} already in watchlist")

    item = WatchlistItem(
        user_id=user.id,
        symbol=symbol,
        market=request.market,
        notes=request.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {"id": item.id, "symbol": item.symbol, "message": "Added to watchlist"}


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(
    symbol: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a symbol from the watchlist."""
    symbol = validate_symbol(symbol)
    result = await db.execute(
        delete(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.symbol == symbol,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Symbol not in watchlist")

    return {"message": f"{symbol} removed from watchlist"}


# =============================================================================
# PORTFOLIO ENDPOINTS
# =============================================================================

@router.get("/portfolio")
async def get_portfolio(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user's portfolio holdings with pagination."""
    result = await db.execute(
        select(PortfolioItem)
        .where(PortfolioItem.user_id == user.id)
        .order_by(PortfolioItem.added_at)
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()

    return {
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "holdings": [
            {
                "id": item.id,
                "symbol": item.symbol,
                "shares": item.shares,
                "avg_price": item.avg_price,
                "currency": item.currency,
                "market": item.market,
                "notes": item.notes,
                "added_at": item.added_at.isoformat() if item.added_at else None,
            }
            for item in items
        ],
    }


@router.post("/portfolio", status_code=201)
async def add_to_portfolio(
    request: AddPortfolioItem,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a holding to the portfolio."""
    symbol = validate_symbol(request.symbol)

    item = PortfolioItem(
        user_id=user.id,
        symbol=symbol,
        shares=request.shares,
        avg_price=request.avg_price,
        currency=request.currency,
        market=request.market,
        notes=request.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {"id": item.id, "symbol": item.symbol, "message": "Added to portfolio"}


@router.put("/portfolio/{item_id}")
async def update_portfolio_item(
    item_id: int,
    update: UpdatePortfolioItem,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a portfolio holding."""
    result = await db.execute(
        select(PortfolioItem).where(
            PortfolioItem.id == item_id,
            PortfolioItem.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Holding not found")

    if update.shares is not None:
        item.shares = update.shares
    if update.avg_price is not None:
        item.avg_price = update.avg_price
    if update.notes is not None:
        item.notes = update.notes

    item.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Holding updated"}


@router.delete("/portfolio/{item_id}")
async def remove_from_portfolio(
    item_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a holding from the portfolio."""
    result = await db.execute(
        delete(PortfolioItem).where(
            PortfolioItem.id == item_id,
            PortfolioItem.user_id == user.id,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Holding not found")

    return {"message": "Holding removed"}


# =============================================================================
# PORTFOLIO ANALYTICS
# =============================================================================

@router.get("/portfolio/analytics")
async def get_portfolio_analytics(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full portfolio analytics: P&L, allocation, sector breakdown, risk metrics.

    Requires at least one holding in the portfolio.
    """
    from services.portfolio_analytics import calculate_portfolio_analytics

    result = await db.execute(
        select(PortfolioItem)
        .where(PortfolioItem.user_id == user.id)
    )
    items = result.scalars().all()

    holdings = [
        {
            "symbol": item.symbol,
            "shares": item.shares,
            "avg_price": item.avg_price,
            "currency": item.currency,
            "market": item.market,
        }
        for item in items
    ]

    analytics = calculate_portfolio_analytics(holdings)
    return {"success": True, **analytics}


# =============================================================================
# ALERTS ENDPOINTS
# =============================================================================

@router.get("/alerts")
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get user's alerts with pagination."""
    result = await db.execute(
        select(Alert)
        .where(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = result.scalars().all()

    return {
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "alerts": [
            {
                "id": item.id,
                "symbol": item.symbol,
                "condition": item.condition,
                "target_value": item.target_value,
                "is_triggered": item.is_triggered,
                "is_active": item.is_active,
                "triggered_at": item.triggered_at.isoformat() if item.triggered_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/alerts", status_code=201)
async def create_alert(
    request: AddAlert,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a price alert."""
    symbol = validate_symbol(request.symbol)

    alert = Alert(
        user_id=user.id,
        symbol=symbol,
        condition=request.condition,
        target_value=request.target_value,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return {"id": alert.id, "symbol": alert.symbol, "message": "Alert created"}


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert."""
    result = await db.execute(
        delete(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == user.id,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert deleted"}
