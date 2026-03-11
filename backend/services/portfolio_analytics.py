"""
Portfolio Analytics Service
===========================
Calculates P&L, allocation percentages, sector exposure,
risk metrics, and performance attribution for user portfolios.
"""

import hashlib
import random
from datetime import datetime
from typing import Dict, Any, List


# Sector mapping for common symbols
SYMBOL_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Cyclical", "NVDA": "Technology", "TSLA": "Consumer Cyclical",
    "META": "Technology", "AMD": "Technology", "NFLX": "Communication Services",
    "INTC": "Technology", "JPM": "Financial Services", "V": "Financial Services",
    "JNJ": "Healthcare", "WMT": "Consumer Defensive", "PG": "Consumer Defensive",
    "SPY": "Index ETF", "QQQ": "Index ETF", "IWM": "Index ETF",
    "BTC-USD": "Crypto", "ETH-USD": "Crypto", "SOL-USD": "Crypto",
    "RELIANCE.NS": "Energy", "TCS.NS": "Technology", "INFY.NS": "Technology",
}


def _get_current_price(symbol: str) -> float:
    """Get simulated current price."""
    base_prices = {
        'AAPL': 238, 'MSFT': 430, 'GOOGL': 175, 'AMZN': 220, 'NVDA': 933,
        'TSLA': 420, 'META': 580, 'AMD': 145, 'NFLX': 850, 'INTC': 22,
        'SPY': 590, 'QQQ': 510, 'BTC-USD': 95000, 'ETH-USD': 3400,
        'RELIANCE.NS': 1250, 'TCS.NS': 4100, 'INFY.NS': 1850,
    }
    base = base_prices.get(symbol.upper(), 100)
    # Add slight daily variation
    seed = f"{symbol}:{datetime.now().strftime('%Y%m%d')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    return round(base * rng.uniform(0.97, 1.03), 2)


def calculate_portfolio_analytics(holdings: List[Dict]) -> Dict[str, Any]:
    """
    Calculate full portfolio analytics.

    Args:
        holdings: List of {symbol, shares, avg_price, currency, market}

    Returns:
        Total value, P&L, allocation %, sector breakdown, risk metrics
    """
    if not holdings:
        return {
            "total_value": 0, "total_cost": 0, "total_pnl": 0,
            "total_pnl_pct": 0, "holdings": [], "sector_allocation": {},
            "top_gainers": [], "top_losers": [], "risk_metrics": {},
        }

    enriched = []
    total_value = 0
    total_cost = 0

    for h in holdings:
        symbol = h["symbol"].upper()
        shares = h["shares"]
        avg_price = h["avg_price"]
        current_price = _get_current_price(symbol)
        cost = shares * avg_price
        value = shares * current_price
        pnl = value - cost
        pnl_pct = ((current_price / avg_price) - 1) * 100 if avg_price > 0 else 0

        total_value += value
        total_cost += cost

        enriched.append({
            "symbol": symbol,
            "shares": shares,
            "avg_price": avg_price,
            "current_price": current_price,
            "cost_basis": round(cost, 2),
            "market_value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "sector": SYMBOL_SECTORS.get(symbol, "Other"),
            "currency": h.get("currency", "$"),
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = ((total_value / total_cost) - 1) * 100 if total_cost > 0 else 0

    # Calculate allocation percentages
    for h in enriched:
        h["allocation_pct"] = round((h["market_value"] / total_value * 100) if total_value > 0 else 0, 1)

    # Sector allocation
    sector_alloc = {}
    for h in enriched:
        sector = h["sector"]
        if sector not in sector_alloc:
            sector_alloc[sector] = {"value": 0, "pct": 0, "symbols": []}
        sector_alloc[sector]["value"] += h["market_value"]
        sector_alloc[sector]["symbols"].append(h["symbol"])

    for sector in sector_alloc:
        sector_alloc[sector]["pct"] = round(
            sector_alloc[sector]["value"] / total_value * 100 if total_value > 0 else 0, 1
        )
        sector_alloc[sector]["value"] = round(sector_alloc[sector]["value"], 2)

    # Top gainers/losers
    sorted_by_pnl = sorted(enriched, key=lambda x: x["pnl_pct"], reverse=True)
    top_gainers = [h for h in sorted_by_pnl if h["pnl_pct"] > 0][:3]
    top_losers = [h for h in reversed(sorted_by_pnl) if h["pnl_pct"] < 0][:3]

    # Risk metrics
    concentration = max(h["allocation_pct"] for h in enriched) if enriched else 0
    num_positions = len(enriched)
    diversification = "LOW" if num_positions <= 2 else "MEDIUM" if num_positions <= 5 else "HIGH"
    concentration_risk = "HIGH" if concentration > 50 else "MEDIUM" if concentration > 30 else "LOW"

    # Sector concentration
    max_sector_pct = max(s["pct"] for s in sector_alloc.values()) if sector_alloc else 0
    sector_risk = "HIGH" if max_sector_pct > 60 else "MEDIUM" if max_sector_pct > 40 else "LOW"

    risk_metrics = {
        "diversification": diversification,
        "num_positions": num_positions,
        "concentration_risk": concentration_risk,
        "largest_position_pct": concentration,
        "sector_concentration_risk": sector_risk,
        "max_sector_pct": max_sector_pct,
        "num_sectors": len(sector_alloc),
    }

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "holdings": enriched,
        "sector_allocation": sector_alloc,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "risk_metrics": risk_metrics,
        "generated_at": datetime.now().isoformat(),
    }
