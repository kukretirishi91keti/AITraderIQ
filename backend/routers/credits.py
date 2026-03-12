"""
Credits Router
===============
REST API for credit balance, usage history, pricing, and top-ups.

Endpoints:
  GET  /api/credits/balance    - Current balance + tier info
  GET  /api/credits/history    - Transaction history
  GET  /api/credits/pricing    - Credit packs and tier plans
  GET  /api/credits/costs      - Per-feature credit costs
  POST /api/credits/topup      - Add credits (simulated payment)
  POST /api/credits/upgrade    - Change tier
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import get_db
from database.models import User
from auth.security import get_current_user, require_auth
from services.credits_service import (
    get_user_credits_summary,
    get_transaction_history,
    add_credits,
    CREDIT_PACKS,
    TIER_PLANS,
    AI_CREDIT_COSTS,
    FEATURE_COSTS,
    DAILY_GRANTS,
    ensure_daily_grant,
)

router = APIRouter(prefix="/api/credits", tags=["Credits"])


class TopupRequest(BaseModel):
    pack_id: str  # e.g. "pack_100"


class UpgradeRequest(BaseModel):
    tier: str  # free, starter, pro, unlimited


# ---- Public endpoints (no auth required, return defaults for anonymous) ----

@router.get("/pricing")
async def get_pricing():
    """Get credit packs and subscription tiers. Public endpoint."""
    return {
        "credit_packs": CREDIT_PACKS,
        "tiers": TIER_PLANS,
        "ai_costs": {k: v for k, v in AI_CREDIT_COSTS.items()},
        "feature_costs": FEATURE_COSTS,
    }


@router.get("/costs")
async def get_costs():
    """Get per-action credit costs. Public endpoint."""
    return {
        "ai_models": AI_CREDIT_COSTS,
        "features": FEATURE_COSTS,
        "free_features": [
            "Real-time charts & candles",
            "Market quotes (15 markets)",
            "Technical signals (RSI, MACD, VWAP)",
            "News feed",
            "Watchlist management",
            "Portfolio tracking",
            "Price alerts",
            "WebSocket streaming",
        ],
    }


# ---- Auth-required endpoints ----

@router.get("/balance")
async def get_balance(
    user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current credit balance and tier info.

    Returns default free-tier info for anonymous users.
    """
    if not user:
        return {
            "balance": DAILY_GRANTS["free"],
            "tier": "free",
            "daily_grant": DAILY_GRANTS["free"],
            "authenticated": False,
            "message": "Sign in to track your credits across sessions",
        }

    summary = await get_user_credits_summary(user, db)
    return {**summary, "authenticated": True}


@router.get("/history")
async def get_history(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get credit transaction history with pagination. Requires auth."""
    txns = await get_transaction_history(user.id, db, limit, offset)
    return {"transactions": txns, "count": len(txns), "offset": offset, "limit": limit}


@router.post("/topup")
async def topup_credits(
    req: TopupRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Buy a credit pack. Simulated payment for demo.

    In production, this would integrate with Stripe/Razorpay.
    For now, credits are granted immediately.
    """
    pack = next((p for p in CREDIT_PACKS if p["id"] == req.pack_id), None)
    if not pack:
        raise HTTPException(status_code=400, detail=f"Unknown pack: {req.pack_id}")

    new_balance = await add_credits(
        user, db,
        amount=pack["credits"],
        tx_type="topup",
        description=f"Purchased {pack['label']} (${pack['price_usd']})",
    )

    return {
        "success": True,
        "pack": pack["label"],
        "credits_added": pack["credits"],
        "new_balance": new_balance,
        "message": f"Added {pack['credits']} credits! New balance: {new_balance}",
    }


@router.post("/upgrade")
async def upgrade_tier(
    req: UpgradeRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade/downgrade tier. Simulated for demo."""
    valid_tiers = {"free", "starter", "pro", "unlimited"}
    if req.tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}")

    plan = next((p for p in TIER_PLANS if p["id"] == req.tier), None)

    user.tier = req.tier
    # Grant daily credits for new tier immediately
    user.credits_grant_date = ""  # Force re-grant
    await db.commit()
    await ensure_daily_grant(user, db)

    return {
        "success": True,
        "tier": req.tier,
        "plan": plan,
        "new_balance": user.credits_balance,
        "message": f"Upgraded to {plan['name']}! Daily credits: {plan['daily_credits']}",
    }
