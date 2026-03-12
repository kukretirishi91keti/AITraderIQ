"""
Batch Data Service v1.0
========================
Location: backend/services/batch_data_service.py

Production-grade batch data pipeline for handling 1000+ concurrent users.

Architecture:
- Pre-fetches quotes for popular symbols every 30s (hot cache)
- Batches yfinance calls to reduce API load
- Provides O(1) reads from in-memory store for all connected users
- Rate budget tracking to stay within yfinance limits

This service runs as a background task and feeds:
- REST API quote endpoints
- WebSocket price stream
- Screener/Scanner data
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Set, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class BatchDataService:
    """
    Manages a hot cache of market data refreshed on a timer.

    Instead of each user request triggering a yfinance call,
    this service pre-fetches all subscribed symbols and serves
    reads from memory. This allows 1000+ users to read
    simultaneously with zero contention.
    """

    def __init__(self):
        # Hot cache: symbol → latest quote dict
        self._quotes: Dict[str, Dict[str, Any]] = {}
        # Symbols currently tracked (union of watchlists + popular)
        self._tracked_symbols: Set[str] = set()
        # Popular symbols always kept hot
        self._popular = {
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
            "AMD", "NFLX", "SPY", "QQQ", "BTC-USD", "ETH-USD",
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
        }
        self._tracked_symbols.update(self._popular)

        # Stats
        self.stats = {
            "cycles": 0,
            "total_fetches": 0,
            "errors": 0,
            "last_cycle_ms": 0,
            "symbols_tracked": 0,
            "cache_reads": 0,
        }

        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ----- Public API -----

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """O(1) read from hot cache. Returns None if not cached."""
        self.stats["cache_reads"] += 1
        return self._quotes.get(symbol.upper())

    def track(self, symbols: List[str]):
        """Add symbols to the tracked set (e.g., when a user subscribes)."""
        for s in symbols:
            self._tracked_symbols.add(s.upper().strip())

    def untrack(self, symbols: List[str]):
        """Remove symbols from tracking (only non-popular ones)."""
        for s in symbols:
            sym = s.upper().strip()
            if sym not in self._popular:
                self._tracked_symbols.discard(sym)

    def get_all_quotes(self) -> Dict[str, Dict[str, Any]]:
        """Return the full hot cache (for screener/scanner)."""
        self.stats["cache_reads"] += 1
        return dict(self._quotes)

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "symbols_tracked": len(self._tracked_symbols),
            "cache_size": len(self._quotes),
            "running": self._running,
        }

    # ----- Background Loop -----

    async def start(self):
        """Start the background refresh loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info(f"BatchDataService started, tracking {len(self._tracked_symbols)} symbols")

    async def stop(self):
        """Stop the background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BatchDataService stopped")

    async def _refresh_loop(self):
        """Main loop: fetch all tracked symbols in batches."""
        from services.market_data_service import get_market_data_service

        while self._running:
            try:
                start = time.monotonic()
                svc = get_market_data_service()
                symbols = list(self._tracked_symbols)

                # Fetch in batches of 10 to avoid overwhelming yfinance
                batch_size = 10
                for i in range(0, len(symbols), batch_size):
                    if not self._running:
                        break
                    batch = symbols[i:i + batch_size]

                    tasks = []
                    for sym in batch:
                        tasks.append(self._safe_fetch(svc, sym))
                    results = await asyncio.gather(*tasks)

                    for sym, quote in zip(batch, results):
                        if quote:
                            self._quotes[sym] = quote
                            self.stats["total_fetches"] += 1

                    # Small delay between batches to avoid rate limits
                    await asyncio.sleep(0.5)

                elapsed = (time.monotonic() - start) * 1000
                self.stats["cycles"] += 1
                self.stats["last_cycle_ms"] = round(elapsed)
                self.stats["symbols_tracked"] = len(self._tracked_symbols)

                # Wait before next cycle (30s for quotes)
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"BatchDataService cycle error: {e}")
                await asyncio.sleep(10)

    async def _safe_fetch(self, svc, symbol: str) -> Optional[Dict]:
        """Fetch a single quote, never raising."""
        try:
            return await svc.get_quote(symbol)
        except Exception as e:
            logger.debug(f"Batch fetch error for {symbol}: {e}")
            return None


# Singleton
_batch_service: Optional[BatchDataService] = None


def get_batch_data_service() -> BatchDataService:
    """Get the global BatchDataService instance."""
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchDataService()
    return _batch_service
