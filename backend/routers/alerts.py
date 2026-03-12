"""
Price Alerts Router
====================
REST API for managing price alerts.

Endpoints:
  POST   /api/alerts          - Create a new alert
  GET    /api/alerts           - List alerts for a user
  DELETE /api/alerts/{id}      - Remove an alert
  GET    /api/alerts/history   - Get triggered alert history
  GET    /api/alerts/stats     - Alert engine stats
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from services.alerts_engine import get_alerts_engine

router = APIRouter(prefix="/api/alerts", tags=["Price Alerts"])


class CreateAlertRequest(BaseModel):
    symbol: str
    condition: str = "above"  # above, below, crosses_above, crosses_below
    target_price: float
    user_id: str = "default"


@router.post("")
async def create_alert(req: CreateAlertRequest):
    """Create a new price alert."""
    engine = get_alerts_engine()
    alert = engine.add_alert(
        user_id=req.user_id,
        symbol=req.symbol,
        condition=req.condition,
        target_price=req.target_price,
    )
    return {
        "success": True,
        "alert": {
            "id": alert.id,
            "symbol": alert.symbol,
            "condition": alert.condition,
            "target_price": alert.target_price,
            "created_at": alert.created_at,
        },
    }


@router.get("")
async def list_alerts(user_id: str = Query("default")):
    """List all alerts for a user."""
    engine = get_alerts_engine()
    alerts = engine.get_user_alerts(user_id)
    return {"success": True, "count": len(alerts), "alerts": alerts}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert."""
    engine = get_alerts_engine()
    removed = engine.remove_alert(alert_id)
    return {"success": removed, "alert_id": alert_id}


@router.get("/history")
async def alert_history(user_id: Optional[str] = None, limit: int = 50):
    """Get alert trigger history."""
    engine = get_alerts_engine()
    history = engine.get_history(user_id, limit)
    return {"success": True, "count": len(history), "history": history}


@router.get("/stats")
async def alert_stats():
    """Get alert engine statistics."""
    engine = get_alerts_engine()
    return {"success": True, **engine.get_stats()}
