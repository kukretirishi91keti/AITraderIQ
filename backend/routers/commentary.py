"""
Commentary Router - AI-generated market insights.
"""

from fastapi import APIRouter, Query

from services.market_commentary import generate_commentary, generate_market_digest

router = APIRouter(prefix="/api/commentary", tags=["Market Commentary"])


@router.get("/{symbol}")
async def get_commentary(symbol: str):
    """
    Get AI-generated commentary for a symbol.

    Detects significant moves and generates context-aware commentary
    using Groq LLM (falls back to rule-based if unavailable).
    """
    result = await generate_commentary(symbol)
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

    result = await generate_market_digest(symbol_list)
    return {"success": True, **result}
