"""
Subscription & Payment Router v2.0
====================================
Location: backend/routers/subscription.py

Manages user subscription tiers and payment processing.
Supports both Stripe (international) and Razorpay (India) payment gateways.

Tiers:
  - Free:    5 AI queries/day, basic signals, 1 watchlist
  - Pro:     100 AI queries/day, strategy intelligence, unlimited watchlists ($9.99/mo | INR 799/mo)
  - Premium: Unlimited AI, real-time data, priority support ($29.99/mo | INR 2499/mo)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os
import json
import hmac
import hashlib

from database.engine import get_db
from database.models import User
from auth.security import get_current_user, require_auth

router = APIRouter(prefix="/api/subscription", tags=["subscription"])
logger = logging.getLogger(__name__)

# =============================================================================
# PAYMENT GATEWAY CONFIGURATION
# =============================================================================

# Stripe (international)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

try:
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    STRIPE_AVAILABLE = bool(STRIPE_SECRET_KEY)
except ImportError:
    STRIPE_AVAILABLE = False

# Razorpay (India)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

try:
    import razorpay
    _razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None
    RAZORPAY_AVAILABLE = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
except ImportError:
    _razorpay_client = None
    RAZORPAY_AVAILABLE = False


# =============================================================================
# PLAN DEFINITIONS
# =============================================================================

PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "price_inr": 0,
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
        "price_usd": 9.99,
        "price_inr": 799,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", ""),
        "razorpay_plan_id": os.getenv("RAZORPAY_PLAN_PRO", ""),
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
        "price_usd": 29.99,
        "price_inr": 2499,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PREMIUM", ""),
        "razorpay_plan_id": os.getenv("RAZORPAY_PLAN_PREMIUM", ""),
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
# HELPERS
# =============================================================================


def check_ai_query_limit(user: User) -> dict:
    """Check if user has remaining AI queries for today."""
    plan = PLANS.get(user.plan or "free", PLANS["free"])
    daily_limit = plan["ai_queries_per_day"]

    if daily_limit == -1:
        return {"allowed": True, "remaining": -1, "limit": -1}

    now = datetime.utcnow()
    if user.ai_queries_reset_at is None or user.ai_queries_reset_at.date() < now.date():
        user.ai_queries_today = 0
        user.ai_queries_reset_at = now

    used = user.ai_queries_today or 0
    remaining = max(0, daily_limit - used)

    return {"allowed": remaining > 0, "remaining": remaining, "limit": daily_limit, "used": used}


def get_plan_limits(user: User) -> dict:
    """Get current plan limits for a user."""
    plan_key = user.plan or "free"
    plan = PLANS.get(plan_key, PLANS["free"])
    return {
        "plan": plan_key,
        "plan_name": plan["name"],
        "limits": plan["limits"],
        "ai_queries_per_day": plan["ai_queries_per_day"],
        "price_usd": plan["price_usd"],
        "price_inr": plan["price_inr"],
    }


async def _activate_plan(user: User, plan_key: str, db: AsyncSession):
    """Activate a plan for a user."""
    user.plan = plan_key
    user.plan_expires_at = datetime.utcnow() + timedelta(days=30)
    user.ai_queries_today = 0
    await db.commit()
    await db.refresh(user)


# =============================================================================
# PLAN ENDPOINTS
# =============================================================================


@router.get("/plans")
async def list_plans():
    """List all subscription plans with pricing in USD and INR."""
    return {
        "plans": [
            {
                "key": key,
                "name": plan["name"],
                "price_usd": plan["price_usd"],
                "price_inr": plan["price_inr"],
                "ai_queries_per_day": plan["ai_queries_per_day"],
                "features": plan["features"],
                "limits": plan["limits"],
            }
            for key, plan in PLANS.items()
        ],
        "payment_gateways": {
            "stripe": {"available": STRIPE_AVAILABLE, "currencies": ["USD", "EUR", "GBP"]},
            "razorpay": {"available": RAZORPAY_AVAILABLE, "currencies": ["INR"]},
        },
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


# =============================================================================
# STRIPE CHECKOUT
# =============================================================================


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|premium)$")
    gateway: str = Field(default="stripe", pattern="^(stripe|razorpay)$")
    success_url: str = Field(default="")
    cancel_url: str = Field(default="")


@router.post("/checkout")
async def create_checkout(
    request: CheckoutRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment checkout session.

    Supports both Stripe (international) and Razorpay (India).
    If neither is configured, returns setup instructions.
    """
    plan = PLANS.get(request.plan)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    if request.gateway == "razorpay":
        return await _create_razorpay_order(request, plan, user, db)
    else:
        return await _create_stripe_checkout(request, plan, user, db)


async def _create_stripe_checkout(request, plan, user, db):
    """Create Stripe Checkout session."""
    if not STRIPE_AVAILABLE:
        return {
            "status": "not_configured",
            "gateway": "stripe",
            "message": "Stripe not configured. Set STRIPE_SECRET_KEY in .env",
            "setup_url": "https://dashboard.stripe.com/apikeys",
            "demo_action": f"POST /api/subscription/demo-upgrade?plan={request.plan}",
        }

    if not plan.get("stripe_price_id"):
        raise HTTPException(status_code=400, detail="Stripe price not configured for this plan")

    try:
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

        return {"gateway": "stripe", "checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail="Stripe payment processing failed")


# =============================================================================
# RAZORPAY CHECKOUT
# =============================================================================


async def _create_razorpay_order(request, plan, user, db):
    """Create Razorpay order for payment."""
    if not RAZORPAY_AVAILABLE or not _razorpay_client:
        return {
            "status": "not_configured",
            "gateway": "razorpay",
            "message": "Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env",
            "setup_url": "https://dashboard.razorpay.com/app/keys",
            "demo_action": f"POST /api/subscription/demo-upgrade?plan={request.plan}",
        }

    try:
        # Create Razorpay order (amount in paise = INR * 100)
        amount_paise = int(plan["price_inr"] * 100)

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"order_{user.id}_{request.plan}_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "user_id": str(user.id),
                "plan": request.plan,
                "username": user.username,
            },
        }

        order = _razorpay_client.order.create(data=order_data)

        return {
            "gateway": "razorpay",
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "plan": request.plan,
            "plan_name": plan["name"],
            "price_display": f"INR {plan['price_inr']}/month",
            "user_email": user.email,
            "user_name": user.full_name or user.username,
            "description": f"TraderAI Pro - {plan['name']} Plan (Monthly)",
            "notes": {
                "Frontend integration": "Use razorpay_key_id and order_id with Razorpay Checkout.js",
                "docs": "https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/",
            },
        }
    except Exception as e:
        logger.error(f"Razorpay order error: {e}")
        raise HTTPException(status_code=500, detail="Razorpay payment processing failed")


@router.post("/razorpay/verify")
async def verify_razorpay_payment(
    request: Request,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Verify Razorpay payment signature and activate plan.

    Called by frontend after successful Razorpay Checkout.
    Expects: razorpay_order_id, razorpay_payment_id, razorpay_signature, plan
    """
    if not RAZORPAY_AVAILABLE:
        raise HTTPException(status_code=400, detail="Razorpay not configured")

    body = await request.json()
    order_id = body.get("razorpay_order_id", "")
    payment_id = body.get("razorpay_payment_id", "")
    signature = body.get("razorpay_signature", "")
    plan_key = body.get("plan", "pro")

    if not all([order_id, payment_id, signature]):
        raise HTTPException(status_code=400, detail="Missing payment verification fields")

    # Verify signature
    message = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Payment verified — activate plan
    if plan_key not in ("pro", "premium"):
        plan_key = "pro"

    await _activate_plan(user, plan_key, db)

    return {
        "status": "verified",
        "payment_id": payment_id,
        "plan": plan_key,
        "plan_name": PLANS[plan_key]["name"],
        "expires_at": user.plan_expires_at.isoformat(),
        "message": f"Payment verified! {PLANS[plan_key]['name']} plan activated for 30 days.",
    }


# =============================================================================
# RAZORPAY WEBHOOK
# =============================================================================


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Razorpay webhook for server-to-server payment notifications."""
    if not RAZORPAY_AVAILABLE or not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Razorpay webhooks not configured")

    payload = await request.body()
    sig_header = request.headers.get("x-razorpay-signature", "")

    # Verify webhook signature
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(payload)
    event_type = event.get("event", "")

    if event_type == "payment.captured":
        payment = event.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment.get("notes", {})
        user_id = int(notes.get("user_id", 0))
        plan_key = notes.get("plan", "pro")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await _activate_plan(user, plan_key, db)
                logger.info(f"Razorpay: User {user_id} upgraded to {plan_key}")

    elif event_type == "subscription.cancelled":
        subscription = event.get("payload", {}).get("subscription", {}).get("entity", {})
        notes = subscription.get("notes", {})
        user_id = int(notes.get("user_id", 0))

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = "free"
                user.plan_expires_at = None
                await db.commit()
                logger.info(f"Razorpay: User {user_id} downgraded to free")

    return {"received": True}


# =============================================================================
# STRIPE WEBHOOK
# =============================================================================


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Stripe webhook handler for payment events."""
    if not STRIPE_AVAILABLE or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Stripe webhooks not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"].get("user_id", 0))
        plan_key = session["metadata"].get("plan", "pro")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await _activate_plan(user, plan_key, db)
                logger.info(f"Stripe: User {user_id} upgraded to {plan_key}")

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        if customer_id:
            result = await db.execute(
                select(User).where(User.stripe_customer_id == customer_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.plan = "free"
                user.plan_expires_at = None
                await db.commit()
                logger.info(f"Stripe: User {user.id} downgraded to free")

    return {"received": True}


# =============================================================================
# DEMO UPGRADE (for testing without payment gateway)
# =============================================================================


@router.post("/demo-upgrade")
async def demo_upgrade(
    plan: str = "pro",
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Simulate plan upgrade without payment (development/demo only)."""
    if plan not in ("pro", "premium"):
        raise HTTPException(status_code=400, detail="Plan must be 'pro' or 'premium'")

    await _activate_plan(user, plan, db)

    return {
        "status": "upgraded",
        "plan": plan,
        "plan_name": PLANS[plan]["name"],
        "expires_at": user.plan_expires_at.isoformat(),
        "message": f"Demo upgrade to {PLANS[plan]['name']} plan. Expires in 30 days.",
    }
