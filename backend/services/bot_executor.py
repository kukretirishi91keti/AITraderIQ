"""
Bot Executor — autonomous paper-trading background loop.

Runs every 60 s. For each user with bot_config.enabled = True:
  1. Check daily trade count and daily loss guard.
  2. For each symbol in the user's bot symbols list:
     a. Run signal aggregator.
     b. If BUY + confidence >= threshold + no existing open position → open paper trade.
     c. If SELL + open position exists → close paper trade.
  3. Log every decision (action taken OR skipped) to BotDecisionLog.

Market hours guard: only runs during 09:35–15:55 ET on weekdays.
When DEMO_MODE=true the guard is bypassed so you can test any time.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta, UTC
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Market hours helpers
# ---------------------------------------------------------------------------

def _is_market_hours() -> bool:
    """Return True if current UTC time falls within US market hours (ET 9:35–15:55 Mon–Fri)."""
    if DEMO_MODE:
        return True  # always run in demo/test mode

    now_utc = datetime.now(timezone.utc)
    if now_utc.weekday() >= 5:  # Sat=5, Sun=6
        return False

    # ET = UTC-5 (EST) / UTC-4 (EDT). Approximate with UTC-4 for daylight saving.
    now_et = now_utc - timedelta(hours=4)
    market_open = now_et.replace(hour=9, minute=35, second=0, microsecond=0)
    market_close = now_et.replace(hour=15, minute=55, second=0, microsecond=0)
    return market_open <= now_et <= market_close


# ---------------------------------------------------------------------------
# Daily guard helpers
# ---------------------------------------------------------------------------

async def _daily_trade_count(user_id: int, db: AsyncSession) -> int:
    from database.models import BotDecisionLog
    today_start = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(BotDecisionLog.id)).where(
            BotDecisionLog.user_id == user_id,
            BotDecisionLog.action.in_(["BUY", "SELL"]),
            BotDecisionLog.created_at >= today_start,
        )
    )
    return result.scalar() or 0


async def _daily_pnl(user_id: int, db: AsyncSession) -> float:
    """Return sum of P&L from paper trades closed by the bot today."""
    from database.models import PaperTrade
    today_start = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(PaperTrade.pnl), 0.0)).where(
            PaperTrade.user_id == user_id,
            PaperTrade.status == "closed",
            PaperTrade.closed_at >= today_start,
            PaperTrade.strategy == "auto-bot",
        )
    )
    return float(result.scalar() or 0.0)


async def _open_position(user_id: int, symbol: str, db: AsyncSession) -> Optional[object]:
    from database.models import PaperTrade
    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.user_id == user_id,
            PaperTrade.symbol == symbol,
            PaperTrade.status == "open",
            PaperTrade.strategy == "auto-bot",
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Core execution for one user
# ---------------------------------------------------------------------------

async def _run_for_user(config, svc, db: AsyncSession) -> int:
    """Process one user's bot config. Returns number of trades placed/closed."""
    from database.models import PaperTrade, BotDecisionLog
    from services.signal_aggregator import aggregate

    user_id = config.user_id
    symbols = config.symbols or []
    if not symbols:
        return 0

    trades_today = await _daily_trade_count(user_id, db)
    if trades_today >= config.max_daily_trades:
        logger.info("Bot: user %d hit daily trade limit (%d)", user_id, config.max_daily_trades)
        return 0

    daily_pnl = await _daily_pnl(user_id, db)
    # Estimate portfolio value as max_position_usd * max_daily_trades (simple proxy)
    portfolio_proxy = config.max_position_usd * config.max_daily_trades
    if portfolio_proxy > 0:
        loss_pct = abs(min(daily_pnl, 0)) / portfolio_proxy * 100
        if loss_pct >= config.max_daily_loss_pct:
            logger.info(
                "Bot: user %d circuit breaker — daily loss %.2f%% >= %.2f%%",
                user_id, loss_pct, config.max_daily_loss_pct,
            )
            return 0

    acted = 0
    for symbol in symbols:
        if trades_today + acted >= config.max_daily_trades:
            break

        signal = aggregate(symbol, config.strategy)
        current_price = signal.current_price

        # Fetch real price when market data service is available
        try:
            quote = await svc.get_quote(symbol)
            if quote.get("price"):
                current_price = float(quote["price"])
        except Exception as exc:
            logger.debug("Bot: price fetch failed for %s: %s", symbol, exc)

        log_entry = BotDecisionLog(
            user_id=user_id,
            symbol=symbol,
            action=signal.action,
            confidence=signal.confidence,
            score=signal.score,
            reason=signal.reason,
            indicators=signal.indicators,
        )

        existing = await _open_position(user_id, symbol, db)

        if signal.action == "BUY" and signal.confidence >= config.min_confidence and not existing:
            qty = round(config.max_position_usd / current_price, 4) if current_price else 1.0
            trade = PaperTrade(
                user_id=user_id,
                symbol=symbol,
                side="buy",
                quantity=qty,
                entry_price=current_price,
                status="open",
                strategy="auto-bot",
                notes=signal.reason,
            )
            db.add(trade)
            await db.flush()  # populate trade.id before logging
            log_entry.trade_id = trade.id
            acted += 1
            logger.info(
                "Bot: BUY %s for user %d — qty=%.4f @ %.2f (conf=%.0f%%)",
                symbol, user_id, qty, current_price, signal.confidence,
            )

        elif signal.action == "SELL" and signal.confidence >= config.min_confidence and existing:
            # Auto-close the existing bot-opened position
            exit_price = current_price
            if existing.side == "buy":
                pnl = (exit_price - existing.entry_price) * existing.quantity
            else:
                pnl = (existing.entry_price - exit_price) * existing.quantity
            pnl_pct = pnl / (existing.entry_price * existing.quantity) * 100 if existing.entry_price else 0
            existing.exit_price = exit_price
            existing.pnl = round(pnl, 2)
            existing.pnl_percent = round(pnl_pct, 2)
            existing.status = "closed"
            existing.closed_at = datetime.now(timezone.utc)
            existing.notes = f"{existing.notes}\nAuto-closed by bot: {signal.reason}".strip()
            log_entry.trade_id = existing.id
            acted += 1
            logger.info(
                "Bot: SELL %s for user %d — P&L=%.2f (conf=%.0f%%)",
                symbol, user_id, pnl, signal.confidence,
            )

        else:
            # SELL with no open position, or any unactioned signal
            log_entry.action = "SKIP"
            if signal.confidence < config.min_confidence:
                log_entry.reason = f"SKIP — confidence {signal.confidence:.0f}% < {config.min_confidence:.0f}% threshold"
            elif signal.action == "SELL" and not existing:
                log_entry.reason = f"SKIP — SELL signal but no open position to close"
            else:
                log_entry.reason = signal.reason

        db.add(log_entry)

    if acted:
        await db.commit()
    else:
        await db.commit()  # commit SKIP logs too

    return acted


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

async def run_bot_executor(session_factory, interval_seconds: int = 60):
    """Main background loop — called once at startup, runs until app shuts down."""
    from database.models import BotConfig
    from services.market_data_service import get_market_data_service

    logger.info("Bot executor started (interval=%ds)", interval_seconds)

    while True:
        await asyncio.sleep(interval_seconds)
        if not _is_market_hours():
            continue  # silent skip outside market hours

        try:
            async with session_factory() as db:
                result = await db.execute(
                    select(BotConfig).where(BotConfig.enabled == True)
                )
                configs = result.scalars().all()
                if not configs:
                    continue

                svc = get_market_data_service()
                total_acted = 0
                for cfg in configs:
                    try:
                        total_acted += await _run_for_user(cfg, svc, db)
                    except Exception as exc:
                        logger.error("Bot: error processing user %d: %s", cfg.user_id, exc, exc_info=True)

                if total_acted:
                    logger.info("Bot executor cycle: %d action(s) taken", total_acted)

        except asyncio.CancelledError:
            logger.info("Bot executor cancelled — shutting down")
            return
        except Exception as exc:
            logger.error("Bot executor outer error: %s", exc, exc_info=True)
