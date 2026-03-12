"""
WebSocket Router - Real-time price streaming.

Clients connect and subscribe to symbols. A background task
broadcasts price updates to all connected subscribers.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and symbol subscriptions."""

    def __init__(self):
        # websocket -> set of subscribed symbols
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        # symbol -> set of websockets subscribed to it
        self.symbol_subscribers: Dict[str, Set[WebSocket]] = {}
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = set()
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        # Remove from all symbol subscriptions
        subscriptions = self.active_connections.pop(websocket, set())
        for symbol in subscriptions:
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(websocket)
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    def subscribe(self, websocket: WebSocket, symbols: list[str]):
        """Subscribe a connection to symbols."""
        for symbol in symbols:
            sym = symbol.upper().strip()
            if not sym:
                continue
            self.active_connections.setdefault(websocket, set()).add(sym)
            self.symbol_subscribers.setdefault(sym, set()).add(websocket)

    def unsubscribe(self, websocket: WebSocket, symbols: list[str]):
        """Unsubscribe from symbols."""
        for symbol in symbols:
            sym = symbol.upper().strip()
            if websocket in self.active_connections:
                self.active_connections[websocket].discard(sym)
            if sym in self.symbol_subscribers:
                self.symbol_subscribers[sym].discard(websocket)

    async def broadcast_to_symbol(self, symbol: str, data: dict):
        """Send data to all subscribers of a symbol."""
        subscribers = self.symbol_subscribers.get(symbol, set())
        dead = []
        for ws in subscribers:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def get_all_subscribed_symbols(self) -> set[str]:
        """Get all symbols that have at least one subscriber."""
        return set(self.symbol_subscribers.keys())

    def get_stats(self) -> dict:
        return {
            "connections": len(self.active_connections),
            "symbols_tracked": len(self.symbol_subscribers),
            "subscriptions": sum(len(s) for s in self.active_connections.values()),
        }


# Global connection manager
manager = ConnectionManager()

# Background price broadcaster
_broadcast_running = False


async def price_broadcast_loop():
    """Background loop that reads from batch service and broadcasts to all subscribers.

    This is O(symbols) per cycle, NOT O(symbols * connections).
    Each symbol's data is fetched once and broadcast to all subscribers.
    Supports 1000+ concurrent WebSocket connections.
    """
    global _broadcast_running
    if _broadcast_running:
        return
    _broadcast_running = True

    logger.info("Price broadcast loop started")

    try:
        while True:
            symbols = manager.get_all_subscribed_symbols()
            if not symbols:
                await asyncio.sleep(2)
                continue

            try:
                # Try batch service first (O(1) reads, no API calls)
                try:
                    from services.batch_data_service import get_batch_data_service
                    batch_svc = get_batch_data_service()
                    # Tell batch service to also track WebSocket symbols
                    batch_svc.track(list(symbols))
                    use_batch = True
                except Exception:
                    use_batch = False

                from services.market_data_service import get_market_data_service
                svc = get_market_data_service()

                for symbol in list(symbols)[:100]:  # Increased cap with batch service
                    try:
                        # Prefer batch cache (instant), fallback to live fetch
                        quote = None
                        if use_batch:
                            quote = batch_svc.get_quote(symbol)
                        if not quote:
                            quote = await svc.get_quote(symbol)

                        if quote:
                            await manager.broadcast_to_symbol(symbol, {
                                "type": "quote",
                                "symbol": symbol,
                                "price": quote.get("price"),
                                "change": quote.get("change"),
                                "changePercent": quote.get("changePercent"),
                                "volume": quote.get("volume"),
                                "dataQuality": quote.get("dataQuality"),
                                "timestamp": datetime.now().isoformat(),
                            })
                    except Exception as e:
                        logger.warning(f"Broadcast error for {symbol}: {e}")

            except Exception as e:
                logger.error(f"Broadcast loop error: {e}")

            await asyncio.sleep(5)  # Broadcast every 5 seconds

    except asyncio.CancelledError:
        logger.info("Price broadcast loop stopped")
    finally:
        _broadcast_running = False


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price streaming.

    Protocol:
    - Client sends: {"action": "subscribe", "symbols": ["AAPL", "MSFT"]}
    - Client sends: {"action": "unsubscribe", "symbols": ["AAPL"]}
    - Server sends: {"type": "quote", "symbol": "AAPL", "price": 150.50, ...}
    - Server sends: {"type": "status", "connections": 5, ...}
    """
    await manager.connect(websocket)

    # Ensure broadcast loop is running
    global _broadcast_running
    if not _broadcast_running:
        asyncio.create_task(price_broadcast_loop())

    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to TraderAI Pro price stream",
            **manager.get_stats(),
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action", "")

                if action == "subscribe":
                    symbols = msg.get("symbols", [])
                    if isinstance(symbols, list) and len(symbols) <= 20:
                        manager.subscribe(websocket, symbols)
                        await websocket.send_json({
                            "type": "subscribed",
                            "symbols": symbols,
                        })

                elif action == "unsubscribe":
                    symbols = msg.get("symbols", [])
                    manager.unsubscribe(websocket, symbols)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "symbols": symbols,
                    })

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

                elif action == "status":
                    await websocket.send_json({
                        "type": "status",
                        **manager.get_stats(),
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
