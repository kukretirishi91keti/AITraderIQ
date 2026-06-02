"""
WebSocket Router - Real-time price streaming.

Clients connect and subscribe to symbols. A background task
broadcasts price updates to all connected subscribers.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


async def _authenticate_ws(token: Optional[str]) -> Optional[int]:
    """Validate JWT token and return user_id, or None for anonymous."""
    if not token:
        return None
    try:
        from jose import jwt as jose_jwt, JWTError
        from auth.security import SECRET_KEY, ALGORITHM
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        raw_id = payload.get("sub")
        return int(raw_id) if raw_id else None
    except Exception:
        return None


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
    """
    Hybrid broadcast loop:
      - Finnhub WebSocket for US stocks (real-time ticks)
      - REST polling every 5s for Indian stocks (.NS/.BO) via Twelve Data
      - Pure polling fallback when no Finnhub key is set
    """
    global _broadcast_running
    if _broadcast_running:
        return
    _broadcast_running = True
    logger.info("Price broadcast loop started")

    finnhub_key = os.getenv("FINNHUB_API_KEY", "")

    if finnhub_key:
        # Run Finnhub WS (US) and India polling concurrently
        await asyncio.gather(
            _finnhub_ws_loop(finnhub_key),
            _india_polling_loop(),
            return_exceptions=True,
        )
    else:
        await _polling_fallback_loop()

    _broadcast_running = False


async def _india_polling_loop():
    """Poll Twelve Data every 5s for Indian stocks (.NS / .BO symbols)."""
    try:
        from services.market_data_service import get_market_data_service
        svc = get_market_data_service()
        while True:
            symbols = manager.get_all_subscribed_symbols()
            indian = [s for s in symbols if s.endswith(".NS") or s.endswith(".BO")]
            for symbol in indian:
                try:
                    quote = await svc.get_quote(symbol)
                    if quote and quote.get("price"):
                        await manager.broadcast_to_symbol(symbol, {
                            "type": "quote",
                            "symbol": symbol,
                            "price": quote.get("price"),
                            "change": quote.get("change"),
                            "changePercent": quote.get("changePercent"),
                            "volume": quote.get("volume"),
                            "dataQuality": quote.get("dataQuality", "LIVE"),
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"India poll error for {symbol}: {e}")
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("India polling loop stopped")


async def _finnhub_ws_loop(finnhub_key: str):
    """Real-time Finnhub WebSocket stream with auto-reconnect."""
    import websockets as _ws

    backoff = 1
    while True:
        try:
            uri = f"wss://ws.finnhub.io?token={finnhub_key}"
            async with _ws.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                logger.info("Finnhub WebSocket connected")
                backoff = 1  # reset on successful connect
                subscribed: set = set()

                while True:
                    # Sync Finnhub subscriptions with current manager state
                    current = manager.get_all_subscribed_symbols()
                    for sym in current - subscribed:
                        fh_sym = sym.split(".")[0] if "." in sym else sym
                        await ws.send(json.dumps({"type": "subscribe", "symbol": fh_sym}))
                        subscribed.add(sym)
                    for sym in subscribed - current:
                        fh_sym = sym.split(".")[0] if "." in sym else sym
                        await ws.send(json.dumps({"type": "unsubscribe", "symbol": fh_sym}))
                        subscribed.discard(sym)

                    # Receive next message (1s timeout so we re-check subscriptions)
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        msg = json.loads(raw)
                        if msg.get("type") == "trade":
                            for tick in msg.get("data", []):
                                sym = tick["s"]
                                await manager.broadcast_to_symbol(sym, {
                                    "type": "quote",
                                    "symbol": sym,
                                    "price": tick["p"],
                                    "change": None,
                                    "changePercent": None,
                                    "volume": tick.get("v"),
                                    "dataQuality": "LIVE",
                                    "timestamp": datetime.now().isoformat(),
                                })
                    except asyncio.TimeoutError:
                        pass  # normal — loop back to sync subscriptions

        except asyncio.CancelledError:
            logger.info("Finnhub WS loop cancelled")
            return
        except Exception as e:
            logger.warning(f"Finnhub WS disconnected: {e} — reconnecting in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)  # exponential backoff, cap 30s


async def _polling_fallback_loop():
    """5s REST polling fallback when no Finnhub key is configured."""
    try:
        while True:
            symbols = manager.get_all_subscribed_symbols()
            if not symbols:
                await asyncio.sleep(2)
                continue
            try:
                from services.market_data_service import get_market_data_service
                svc = get_market_data_service()
                for symbol in list(symbols)[:50]:
                    try:
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
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("Polling fallback loop stopped")


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time price streaming.

    Authentication: Optional. Pass ?token=<jwt> for authenticated access.
    Anonymous connections are allowed but may be rate-limited in the future.

    Protocol:
    - Client sends: {"action": "subscribe", "symbols": ["AAPL", "MSFT"]}
    - Client sends: {"action": "unsubscribe", "symbols": ["AAPL"]}
    - Server sends: {"type": "quote", "symbol": "AAPL", "price": 150.50, ...}
    - Server sends: {"type": "status", "connections": 5, ...}
    """
    user_id = await _authenticate_ws(token)
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
            "authenticated": user_id is not None,
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

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}",
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
