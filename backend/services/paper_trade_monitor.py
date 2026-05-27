"""
Paper Trade Monitor - Background service for automated stop-loss / take-profit execution.

Runs every 60 seconds. For each open paper trade with stop_loss_price or
take_profit_price set, fetches the current market price and auto-closes the
trade if the level has been triggered.
"""

import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _calc_pnl(side: str, entry: float, exit_p: float, qty: float):
    if side == "buy":
        pnl = (exit_p - entry) * qty
    else:
        pnl = (entry - exit_p) * qty
    pnl_pct = (pnl / (entry * qty)) * 100 if entry else 0.0
    return round(pnl, 2), round(pnl_pct, 2)


async def _check_and_close(trade, svc, db: AsyncSession) -> bool:
    """Fetch current price for trade.symbol and close if levels are hit. Returns True if closed."""
    try:
        quote = await svc.get_quote(trade.symbol)
        current_price = quote.get("price")
        if current_price is None:
            return False
    except Exception as e:
        logger.debug(f"Monitor: could not fetch quote for {trade.symbol}: {e}")
        return False

    triggered_note = None

    if trade.side == "buy":
        if trade.stop_loss_price is not None and current_price <= trade.stop_loss_price:
            triggered_note = "Auto-closed: stop-loss hit"
        elif trade.take_profit_price is not None and current_price >= trade.take_profit_price:
            triggered_note = "Auto-closed: take-profit hit"
    else:  # short / sell
        if trade.stop_loss_price is not None and current_price >= trade.stop_loss_price:
            triggered_note = "Auto-closed: stop-loss hit"
        elif trade.take_profit_price is not None and current_price <= trade.take_profit_price:
            triggered_note = "Auto-closed: take-profit hit"

    if triggered_note is None:
        return False

    pnl, pnl_pct = _calc_pnl(trade.side, trade.entry_price, current_price, trade.quantity)
    trade.exit_price = current_price
    trade.pnl = pnl
    trade.pnl_percent = pnl_pct
    trade.status = "closed"
    trade.closed_at = datetime.now(timezone.utc)
    trade.notes = f"{trade.notes}\n{triggered_note}".strip()
    await db.commit()

    logger.info(
        f"Monitor: auto-closed trade #{trade.id} ({trade.symbol} {trade.side}) "
        f"— {triggered_note} @ {current_price:.2f}, P&L={pnl:+.2f}"
    )
    return True


async def monitor_paper_trades(session_factory, interval_seconds: int = 60):
    """Continuously monitor open paper trades and auto-close on triggered levels."""
    from database.models import PaperTrade
    from services.market_data_service import get_market_data_service

    logger.info("Paper trade monitor started (interval=%ds)", interval_seconds)

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async with session_factory() as db:
                result = await db.execute(
                    select(PaperTrade).where(
                        PaperTrade.status == "open",
                        (PaperTrade.stop_loss_price.isnot(None))
                        | (PaperTrade.take_profit_price.isnot(None)),
                    )
                )
                trades = result.scalars().all()
                if not trades:
                    continue

                svc = get_market_data_service()
                for trade in trades:
                    await _check_and_close(trade, svc, db)

        except asyncio.CancelledError:
            logger.info("Paper trade monitor cancelled — shutting down")
            return
        except Exception as e:
            logger.error(f"Paper trade monitor error: {e}", exc_info=True)
