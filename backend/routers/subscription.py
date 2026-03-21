"""
Subscription & Payment Router v1.0
====================================
Location: backend/routers/subscription.py

Manages user subscription tiers and payment processing.
Supports Stripe integration for Pro/Premium upgrades.

Tiers:
  - Free:    5 AI queries/day, basic signals, 1 watchlist
  - Pro:     100 AI queries/day, strategy intelligence, unlimited watchlists ($9.99/mo)
  - Premium: Unlimited AI, real-time data, priority support ($29.99/mo)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from database.engine import get_db
from database.models import User
from auth.security import get_current_user, require_auth

router = APIRouter(prefix="/api/subscription", tags=["subscription"])
logger = logging.getLogger(__name__)

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

try:
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    STRIPE_AVAILABLE = bool(STRIPE_SECRET_KEY)
except ImportError:
    STRIPE_AVAILABLE = False

# =============================================================================
# PLAN DEFINITIONS
# =============================================================================

PLANS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "ai_queries_per_day": 5,
        "features": [
            "Basic technical signals (RSI, MACD)",
            "5 AI queries per day",
            "1 watchlist (max 10 symbols)",
            "Daily market overview",
            "Community support",
        ],
        "limits": {
            "watchlists": 1,
            "watchlist_symbols": 10,
            "portfolio_items": 5,
            "alerts": 3,
            "backtest_runs_per_day": 2,
        },
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 9.99,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", ""),
        "ai_queries_per_day": 100,
        "features": [
            "All Free features",
            "100 AI queries per day",
            "Strategy Intelligence wizard",
            "Unlimited watchlists",
            "Advanced backtesting",
            "Sentiment analysis (StockTwits + Reddit + News)",
            "Email alerts",
        ],
        "limits": {
            "watchlists": 10,
            "watchlist_symbols": 50,
            "portfolio_items": 50,
            "alerts": 25,
            "backtest_runs_per_day": 20,
        },
    },
    "premium": {
        "name": "Premium",
        "price_monthly": 29.99,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PREMIUM", ""),
        "ai_queries_per_day": -1,  # unlimited
        "features": [
            "All Pro features",
            "Unlimited AI queries",
            "Real-time WebSocket data",
            "Priority AI model access",
            "Custom strategy builder",
            "API access for automation",
            "Priority support",
        ],
        "limits": {
            "watchlists": -1,
            "watchlist_symbols": -1,
            "portfolio_items": -1,
            "alerts": -1,
            "backtest_runs_per_day": -1,
        },
    },
}


# =============================================================================
# HELPER: CHECK PLAN LIMITS
# =============================================================================


def check_ai_query_limit(user: User) -> dict:
    """Check if user has remaining AI queries for today."""
    plan = PLANS.get(user.plan or "free", PLANS["free"])
    daily_limit = plan["ai_queries_per_day"]

    if daily_limit == -1:  # unlimited
        return {"allowed": True, "remaining": -1, "limit": -1}

    # Reset counter if new day
    now = datetime.utcnow()
    if user.ai_queries_reset_at is None or user.ai_queries_reset_at.date() < now.date():
        user.ai_queries_today = 0
        user.ai_queries_reset_at = now

    used = user.ai_queries_today or 0
    remaining = max(0, daily_limit - used)

    return {
        "allowed": remaining > 0,
        "remaining": remaining,
        "limit": daily_limit,
        "used": used,
    }


def get_plan_limits(user: User) -> dict:
    """Get current plan limits for a user."""
    plan_key = user.plan or "free"
    plan = PLANS.get(plan_key, PLANS["free"])
    return {
        "plan": plan_key,
        "plan_name": plan["name"],
        "limits": plan["limits"],
        "ai_queries_per_day": plan["ai_queries_per_day"],
        "price_monthly": plan["price_monthly"],
    }


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/plans")
async def list_plans():
    """List all available subscription plans with features and pricing."""
    return {
        "plans": [
            {
                "key": key,
                "name": plan["name"],
                "price_monthly": plan["price_monthly"],
                "ai_queries_per_day": plan["ai_queries_per_day"],
                "features": plan["features"],
                "limits": plan["limits"],
                "stripe_available": STRIPE_AVAILABLE and bool(plan.get("stripe_price_id")),
            }
            for key, plan in PLANS.items()
        ],
        "stripe_configured": STRIPE_AVAILABLE,
    }


@router.get("/my-plan")
async def get_my_plan(user: User = Depends(require_auth)):
    """Get current user's subscription details and usage."""
    ai_status = check_ai_query_limit(user)
    plan_info = get_plan_limits(user)

    return {
        **plan_info,
        "ai_usage": ai_status,
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "is_expired": (
            user.plan_expires_at is not None and user.plan_expires_at < datetime.utcnow()
        ) if user.plan != "free" else False,
    }


class CreateCheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|premium)$")
    success_url: str = Field(default="")
    cancel_url: str = Field(default="")


@router.post("/checkout")
async def create_checkout(
    request: CreateCheckoutRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for plan upgrade.

    Returns a checkout URL to redirect the user to Stripe's hosted payment page.
    If Stripe is not configured, returns instructions for manual setup.
    """
    if not STRIPE_AVAILABLE:
        return {
            "status": "stripe_not_configured",
            "message": "Payment processing requires Stripe configuration.",
            "setup_instructions": {
                "step_1": "Create account at https://stripe.com",
                "step_2": "Get API keys from https://dashboard.stripe.com/apikeys",
                "step_3": "Create products/prices in Stripe Dashboard",
                "step_4": "Set environment variables: STRIPE_SECRET_KEY, STRIPE_PRICE_PRO, STRIPE_PRICE_PREMIUM",
                "step_5": "Set STRIPE_WEBHOOK_SECRET for payment confirmations",
            },
            "demo_mode": True,
            "demo_action": f"In demo mode, use POST /api/subscription/demo-upgrade?plan={request.plan} to simulate upgrade",
        }

    plan = PLANS.get(request.plan)
    if not plan or not plan.get("stripe_price_id"):
        raise HTTPException(status_code=400, detail="Invalid plan or price not configured")

    try:
        # Create or reuse Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id), "username": user.username},
            )
            user.stripe_customer_id = customer.id
            await db.commit()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            mode="subscription",
            success_url=request.success_url or "http://localhost:5173?upgrade=success",
            cancel_url=request.cancel_url or "http://localhost:5173?upgrade=cancelled",
            metadata={"user_id": str(user.id), "plan": request.plan},
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


@router.post("/demo-upgrade")
async def demo_upgrade(
    plan: str = "pro",
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Demo/test endpoint to simulate plan upgrade (no real payment).

    For development and demo purposes only. In production, upgrades happen
    via Stripe webhook after successful payment.
    """
    if plan not in ("pro", "premium"):
        raise HTTPException(status_code=400, detail="Plan must be 'pro' or 'premium'")

    user.plan = plan
    user.plan_expires_at = datetime.utcnow() + timedelta(days=30)
    user.ai_queries_today = 0
    await db.commit()
    await db.refresh(user)

    return {
        "status": "upgraded",
        "plan": plan,
        "plan_name": PLANS[plan]["name"],
        "expires_at": user.plan_expires_at.isoformat(),
        "message": f"Demo upgrade to {PLANS[plan]['name']} plan successful. Expires in 30 days.",
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Stripe webhook handler for payment events.

    Handles: checkout.session.completed, invoice.paid, customer.subscription.deleted
    """
    if not STRIPE_AVAILABLE or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Webhooks not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"].get("user_id", 0))
        plan = session["metadata"].get("plan", "pro")

        if user_id:
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = plan
                user.plan_expires_at = datetime.utcnow() + timedelta(days=30)
                user.ai_queries_today = 0
                await db.commit()
                logger.info(f"User {user_id} upgraded to {plan}")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        if customer_id:
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.stripe_customer_id == customer_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.plan = "free"
                user.plan_expires_at = None
                await db.commit()
                logger.info(f"User {user.id} downgraded to free (subscription cancelled)")

    return {"received": True}
