"""
Commentary Router - AI-generated market insights.
Optimized: caching for commentary and digest endpoints.
"""

from fastapi import APIRouter, Query

from services.market_commentary import generate_commentary, generate_market_digest
from services.cache_manager import get_cache_manager

router = APIRouter(prefix="/api/commentary", tags=["Market Commentary"])

# Cache for commentary (5-minute TTL)
_commentary_cache = get_cache_manager("commentary")
COMMENTARY_CACHE_TTL = 300  # 5 minutes


@router.get("/{symbol}")
async def get_commentary(symbol: str):
    """
    Get AI-generated commentary for a symbol.

    Detects significant moves and generates context-aware commentary
    using Groq LLM (falls back to rule-based if unavailable).
    """
    cache_key = f"commentary:{symbol.upper()}"
    entry = _commentary_cache.get(cache_key, COMMENTARY_CACHE_TTL)
    if entry:
        return {"success": True, **entry.data}

    result = await generate_commentary(symbol)
    _commentary_cache.set(cache_key, result, source="LIVE")
    return {"success": True, **result}


@router.get("/market/digest")
async def get_market_digest(
    symbols: str = Query(
        None,
        description="Comma-separated symbols (default: major indices + tech)"
    ),
):
    """
    Get a market digest with commentary on all significant moves.

    Scans multiple symbols and generates commentary only for
    those with noteworthy activity (price moves, volume spikes, etc.).
    """
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

    cache_key = f"digest:{','.join(symbol_list) if symbol_list else 'default'}"
    entry = _commentary_cache.get(cache_key, COMMENTARY_CACHE_TTL)
    if entry:
        return {"success": True, **entry.data}

    result = await generate_market_digest(symbol_list)
    _commentary_cache.set(cache_key, result, source="LIVE")
    return {"success": True, **result}
