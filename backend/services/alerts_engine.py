"""
Price Alerts Engine v1.0
=========================
Location: backend/services/alerts_engine.py

In-memory price alert system that checks against live/cached quotes
and fires via WebSocket when triggered.

Features:
- Configurable conditions: above, below, crosses_above, crosses_below, pct_change
- Per-user alert storage (in-memory, DB-backed in future)
- Batched evaluation against batch_data_service for efficiency
- Alert history with timestamps
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PriceAlert:
    """A single price alert."""
    id: str
    user_id: str
    symbol: str
    condition: str  # above, below, pct_change_up, pct_change_down
    target_price: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    triggered: bool = False
    triggered_at: Optional[str] = None
    triggered_price: Optional[float] = None


class AlertsEngine:
    """
    Evaluates price alerts against current market data.

    Usage:
        engine = get_alerts_engine()
        engine.add_alert("user1", "AAPL", "above", 250.0)
        triggered = engine.evaluate({"AAPL": {"price": 251.0}})
    """

    def __init__(self):
        # alert_id → PriceAlert
        self._alerts: Dict[str, PriceAlert] = {}
        self._alert_counter = 0
        self._history: List[Dict[str, Any]] = []
        self._previous_prices: Dict[str, float] = {}

    def add_alert(
        self, user_id: str, symbol: str, condition: str, target_price: float
    ) -> PriceAlert:
        """Create a new price alert."""
        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter}"
        alert = PriceAlert(
            id=alert_id,
            user_id=user_id,
            symbol=symbol.upper(),
            condition=condition,
            target_price=target_price,
        )
        self._alerts[alert_id] = alert
        logger.info(f"Alert created: {alert_id} - {symbol} {condition} {target_price}")
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert."""
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            return True
        return False

    def get_user_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all alerts for a user."""
        return [
            {
                "id": a.id,
                "symbol": a.symbol,
                "condition": a.condition,
                "target_price": a.target_price,
                "triggered": a.triggered,
                "triggered_at": a.triggered_at,
                "created_at": a.created_at,
            }
            for a in self._alerts.values()
            if a.user_id == user_id
        ]

    def evaluate(self, quotes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate all pending alerts against current quotes.

        Returns list of newly triggered alerts.
        """
        triggered = []

        for alert_id, alert in list(self._alerts.items()):
            if alert.triggered:
                continue

            quote = quotes.get(alert.symbol)
            if not quote:
                continue

            price = quote.get("price", 0)
            prev_price = self._previous_prices.get(alert.symbol, price)
            fired = False

            if alert.condition == "above" and price >= alert.target_price:
                fired = True
            elif alert.condition == "below" and price <= alert.target_price:
                fired = True
            elif alert.condition == "crosses_above":
                if prev_price < alert.target_price <= price:
                    fired = True
            elif alert.condition == "crosses_below":
                if prev_price > alert.target_price >= price:
                    fired = True

            if fired:
                alert.triggered = True
                alert.triggered_at = datetime.now().isoformat()
                alert.triggered_price = price
                entry = {
                    "alert_id": alert.id,
                    "user_id": alert.user_id,
                    "symbol": alert.symbol,
                    "condition": alert.condition,
                    "target_price": alert.target_price,
                    "triggered_price": price,
                    "triggered_at": alert.triggered_at,
                }
                triggered.append(entry)
                self._history.append(entry)
                logger.info(f"Alert triggered: {alert_id} - {alert.symbol} {alert.condition} {alert.target_price} (actual: {price})")

        # Update previous prices for cross detection
        for sym, quote in quotes.items():
            self._previous_prices[sym] = quote.get("price", 0)

        return triggered

    def get_history(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get alert trigger history."""
        history = self._history
        if user_id:
            history = [h for h in history if h["user_id"] == user_id]
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for a in self._alerts.values() if not a.triggered)
        triggered = sum(1 for a in self._alerts.values() if a.triggered)
        return {
            "total_alerts": len(self._alerts),
            "active": active,
            "triggered": triggered,
            "history_count": len(self._history),
        }


# Singleton
_alerts_engine: Optional[AlertsEngine] = None


def get_alerts_engine() -> AlertsEngine:
    global _alerts_engine
    if _alerts_engine is None:
        _alerts_engine = AlertsEngine()
    return _alerts_engine
