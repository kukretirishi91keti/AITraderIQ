"""
Credits Service
================
Manages user credit balances, daily grants, and usage tracking.

Pricing Philosophy:
- Free tier: 50 credits/day (enough to explore everything)
- Credits are cheap: AI queries cost 1-5 credits depending on model
- Market data, charts, signals: FREE (no credits needed)
- Only AI queries and premium analytics consume credits
- Way cheaper than $20/mo ChatGPT or $200/mo Bloomberg

Credit Costs:
  Groq Llama 3.1 8B (fast)    → 1 credit
  Groq Llama 3.3 70B          → 2 credits
  OpenAI GPT-4o-mini           → 3 credits
  OpenAI GPT-4o                → 5 credits
  Anthropic Claude Haiku       → 2 credits
  Anthropic Claude Sonnet      → 4 credits
  Fallback (rule-based)        → 0 credits (always free)
  Advanced backtest            → 3 credits
  AI Scanner                   → 2 credits

Tiers:
  free       → 50 credits/day (auto-granted)
  starter    → 200 credits/day + rollover up to 500
  pro        → 1000 credits/day + rollover up to 3000
  unlimited  → no limits
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, CreditTransaction

logger = logging.getLogger(__name__)

# ---- Pricing Tables ----

DAILY_GRANTS = {
    "free": 50,
    "starter": 200,
    "pro": 1000,
    "unlimited": 999999,
}

MAX_ROLLOVER = {
    "free": 50,       # no rollover — resets daily
    "starter": 500,
    "pro": 3000,
    "unlimited": 999999,
}

AI_CREDIT_COSTS = {
    # provider:model → cost
    "groq:llama-3.1-8b-instant": 1,
    "groq:llama-3.3-70b-versatile": 2,
    "openai:gpt-3.5-turbo": 2,
    "openai:gpt-4o-mini": 3,
    "openai:gpt-4o": 5,
    "anthropic:claude-haiku-4-20250414": 2,
    "anthropic:claude-sonnet-4-20250514": 4,
}

# Default cost if model not in table
DEFAULT_AI_COST = 3

FEATURE_COSTS = {
    "ai_query": None,        # varies by model (see AI_CREDIT_COSTS)
    "backtest": 3,
    "ai_scanner": 2,
    "export_report": 1,
}

CREDIT_PACKS = [
    {"id": "pack_100", "credits": 100, "price_usd": 0.99, "label": "100 Credits", "popular": False},
    {"id": "pack_500", "credits": 500, "price_usd": 3.99, "label": "500 Credits", "popular": True, "savings": "20%"},
    {"id": "pack_2000", "credits": 2000, "price_usd": 12.99, "label": "2,000 Credits", "popular": False, "savings": "35%"},
    {"id": "pack_10000", "credits": 10000, "price_usd": 49.99, "label": "10,000 Credits", "popular": False, "savings": "50%"},
]

TIER_PLANS = [
    {"id": "free", "name": "Free", "price_usd": 0, "daily_credits": 50, "features": ["50 AI queries/day", "All markets", "Real-time charts", "Basic signals"]},
    {"id": "starter", "name": "Starter", "price_usd": 4.99, "daily_credits": 200, "features": ["200 AI queries/day", "Credit rollover (500 max)", "Advanced signals", "Backtesting"]},
    {"id": "pro", "name": "Pro", "price_usd": 14.99, "daily_credits": 1000, "features": ["1000 AI queries/day", "Credit rollover (3000 max)", "AI Scanner", "Export reports", "Priority support"]},
    {"id": "unlimited", "name": "Unlimited", "price_usd": 29.99, "daily_credits": 999999, "features": ["Unlimited AI queries", "All features", "API access", "White-label ready"]},
]


# ---- Service Functions ----

def get_ai_cost(provider: str, model: str) -> int:
    """Get credit cost for an AI query based on provider and model."""
    key = f"{provider}:{model}"
    return AI_CREDIT_COSTS.get(key, DEFAULT_AI_COST)


async def ensure_daily_grant(user: User, db: AsyncSession) -> int:
    """Grant daily free credits if not already granted today.

    Returns the number of credits granted (0 if already granted).
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if user.credits_grant_date == today:
        return 0  # Already granted today

    tier = user.tier or "free"
    daily = DAILY_GRANTS.get(tier, 50)
    max_roll = MAX_ROLLOVER.get(tier, 50)

    # For free tier: reset to daily grant (no rollover)
    # For paid tiers: add daily grant, cap at max rollover
    if tier == "free":
        new_balance = daily
    else:
        new_balance = min((user.credits_balance or 0) + daily, max_roll)

    granted = new_balance - (user.credits_balance or 0)

    user.credits_balance = new_balance
    user.credits_granted_today = daily
    user.credits_grant_date = today

    # Record transaction
    tx = CreditTransaction(
        user_id=user.id,
        amount=granted,
        balance_after=new_balance,
        tx_type="daily_grant",
        description=f"Daily {tier} grant: +{granted} credits",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Daily grant for user {user.id} ({tier}): +{granted} → {new_balance}")
    return granted


async def check_and_debit(
    user: User,
    db: AsyncSession,
    cost: int,
    tx_type: str = "ai_query",
    description: str = "",
    metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Check if user has enough credits and debit them.

    Returns {"allowed": True/False, "balance": int, "cost": int, ...}
    """
    # Ensure daily grant first
    await ensure_daily_grant(user, db)

    tier = user.tier or "free"

    # Unlimited tier skips balance check
    if tier == "unlimited":
        user.lifetime_credits_used = (user.lifetime_credits_used or 0) + cost
        await db.commit()
        return {"allowed": True, "balance": user.credits_balance, "cost": cost, "tier": tier}

    balance = user.credits_balance or 0

    if balance < cost:
        return {
            "allowed": False,
            "balance": balance,
            "cost": cost,
            "tier": tier,
            "message": f"Insufficient credits. Need {cost}, have {balance}. Buy more or wait for daily reset.",
        }

    # Debit
    user.credits_balance = balance - cost
    user.lifetime_credits_used = (user.lifetime_credits_used or 0) + cost

    tx = CreditTransaction(
        user_id=user.id,
        amount=-cost,
        balance_after=user.credits_balance,
        tx_type=tx_type,
        description=description or f"{tx_type}: -{cost} credits",
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)

    return {"allowed": True, "balance": user.credits_balance, "cost": cost, "tier": tier}


async def add_credits(
    user: User,
    db: AsyncSession,
    amount: int,
    tx_type: str = "topup",
    description: str = "",
) -> int:
    """Add credits to user's balance. Returns new balance."""
    user.credits_balance = (user.credits_balance or 0) + amount

    tx = CreditTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=user.credits_balance,
        tx_type=tx_type,
        description=description or f"Added {amount} credits",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    return user.credits_balance


async def get_transaction_history(
    user_id: int,
    db: AsyncSession,
    limit: int = 50,
) -> List[Dict]:
    """Get recent credit transactions for a user."""
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user_id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(limit)
    )
    txns = result.scalars().all()
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "type": t.tx_type,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]


async def get_user_credits_summary(user: User, db: AsyncSession) -> Dict[str, Any]:
    """Get full credits summary for a user (for the UI)."""
    await ensure_daily_grant(user, db)

    tier = user.tier or "free"
    daily = DAILY_GRANTS.get(tier, 50)

    return {
        "balance": user.credits_balance or 0,
        "tier": tier,
        "daily_grant": daily,
        "daily_remaining": (user.credits_balance or 0),
        "lifetime_used": user.lifetime_credits_used or 0,
        "max_rollover": MAX_ROLLOVER.get(tier, 50),
        "grant_date": user.credits_grant_date or "",
    }
