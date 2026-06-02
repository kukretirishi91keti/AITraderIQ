"""
Alert Monitor — Background service that checks user price alerts every 60 s
and fires SendGrid emails when conditions are met.

Only processes alerts where is_active=True and is_triggered=False.
On trigger: marks is_triggered=True, is_active=False, sets triggered_at.
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _condition_met(condition: str, current: float, target: float) -> bool:
    if condition == "above":
        return current >= target
    if condition == "below":
        return current <= target
    return False


async def _process_alerts(db: AsyncSession, svc) -> int:
    from database.models import Alert, User

    result = await db.execute(
        select(Alert)
        .where(Alert.is_active == True, Alert.is_triggered == False)
        .join(User, Alert.user_id == User.id)
    )
    alerts = result.scalars().all()
    if not alerts:
        return 0

    # Deduplicate symbols so we only fetch each price once
    symbols = list({a.symbol for a in alerts})
    prices: dict[str, float] = {}
    for sym in symbols:
        try:
            quote = await svc.get_quote(sym)
            if quote.get("price") is not None:
                prices[sym] = float(quote["price"])
        except Exception as exc:
            logger.debug("Alert monitor: quote failed for %s: %s", sym, exc)

    fired = 0
    for alert in alerts:
        price = prices.get(alert.symbol)
        if price is None:
            continue
        if not _condition_met(alert.condition, price, alert.target_value):
            continue

        # Load user email
        user_result = await db.execute(
            select(__import__("database.models", fromlist=["User"]).User)
            .where(__import__("database.models", fromlist=["User"]).User.id == alert.user_id)
        )
        user = user_result.scalar_one_or_none()

        alert.is_triggered = True
        alert.is_active = False
        alert.triggered_at = datetime.now(timezone.utc)
        fired += 1

        if user:
            try:
                from services.email_service import send_price_alert_email
                await send_price_alert_email(
                    to_email=user.email,
                    symbol=alert.symbol,
                    condition=alert.condition,
                    target_value=alert.target_value,
                    current_price=price,
                )
            except Exception as exc:
                logger.warning("Email send error for alert #%d: %s", alert.id, exc)

    if fired:
        await db.commit()
        logger.info("Alert monitor: triggered %d alert(s)", fired)

    return fired


async def monitor_alerts(session_factory, interval_seconds: int = 60):
    """Continuously check active price alerts and send emails when triggered."""
    from services.market_data_service import get_market_data_service

    logger.info("Alert monitor started (interval=%ds)", interval_seconds)

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with session_factory() as db:
                svc = get_market_data_service()
                await _process_alerts(db, svc)
        except asyncio.CancelledError:
            logger.info("Alert monitor cancelled — shutting down")
            return
        except Exception as exc:
            logger.error("Alert monitor error: %s", exc, exc_info=True)
