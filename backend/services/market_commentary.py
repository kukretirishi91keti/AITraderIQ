"""
Auto-Generated Market Commentary
=================================
Generates AI commentary on significant market moves using Groq LLM
with fallback to rule-based generation.

Triggers commentary when:
- Price moves > 3% in a session
- RSI crosses extreme thresholds (30/70)
- Bollinger Band breakouts
- Volume spikes > 2x average
"""

import os
import hashlib
import random
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def _detect_significant_moves(symbol: str) -> Dict[str, Any]:
    """Detect if a symbol has had significant moves worth commenting on."""
    # Deterministic simulation for demo
    seed = f"{symbol}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())

    price_change = rng.gauss(0, 3.5)
    volume_ratio = max(0.3, rng.gauss(1.2, 0.6))
    rsi = rng.uniform(20, 80)
    bb_position = rng.choice(["MIDDLE", "UPPER_ZONE", "LOWER_ZONE", "ABOVE_UPPER", "BELOW_LOWER"])

    triggers = []
    severity = "normal"

    if abs(price_change) > 5:
        triggers.append(f"{'surged' if price_change > 0 else 'plunged'} {abs(price_change):.1f}%")
        severity = "high"
    elif abs(price_change) > 3:
        triggers.append(f"moved {'+' if price_change > 0 else ''}{price_change:.1f}%")
        severity = "medium"

    if volume_ratio > 2.0:
        triggers.append(f"volume spike ({volume_ratio:.1f}x average)")
        severity = max(severity, "medium")

    if rsi < 25:
        triggers.append(f"deeply oversold (RSI {rsi:.0f})")
        severity = max(severity, "medium")
    elif rsi > 75:
        triggers.append(f"extremely overbought (RSI {rsi:.0f})")
        severity = max(severity, "medium")

    if bb_position in ("ABOVE_UPPER", "BELOW_LOWER"):
        triggers.append(f"Bollinger Band breakout ({bb_position.replace('_', ' ').lower()})")

    return {
        "symbol": symbol,
        "price_change_pct": round(price_change, 2),
        "volume_ratio": round(volume_ratio, 2),
        "rsi": round(rsi, 1),
        "bb_position": bb_position,
        "triggers": triggers,
        "severity": severity,
        "has_significant_move": len(triggers) > 0,
    }


def _generate_rule_based_commentary(move: Dict) -> str:
    """Generate commentary from rules when LLM unavailable."""
    symbol = move["symbol"]
    pct = move["price_change_pct"]
    rsi = move["rsi"]
    triggers = move["triggers"]

    if not triggers:
        return f"{symbol} trading within normal range. No significant moves detected."

    trigger_text = ", ".join(triggers)

    if pct > 5:
        return (
            f"ALERT: {symbol} {trigger_text}. This strong momentum suggests institutional buying pressure. "
            f"RSI at {rsi:.0f} - {'approaching overbought territory, watch for pullback' if rsi > 60 else 'still has room to run'}. "
            f"Key question: is this breakout sustainable or a blow-off top?"
        )
    elif pct < -5:
        return (
            f"ALERT: {symbol} {trigger_text}. Sharp decline may indicate capitulation selling. "
            f"RSI at {rsi:.0f} - {'approaching oversold, potential bounce candidate' if rsi < 40 else 'more downside possible'}. "
            f"Watch for volume climax as a sign of potential reversal."
        )
    elif pct > 3:
        return (
            f"{symbol} {trigger_text}. Bullish momentum building with RSI at {rsi:.0f}. "
            f"Swing traders may look for continuation; day traders watch for intraday pullback entry."
        )
    elif pct < -3:
        return (
            f"{symbol} {trigger_text}. Bearish pressure increasing with RSI at {rsi:.0f}. "
            f"Consider tightening stops on long positions. Short-term support levels being tested."
        )
    elif move["volume_ratio"] > 2:
        return (
            f"{symbol} seeing unusual volume ({move['volume_ratio']:.1f}x average) with {trigger_text}. "
            f"Volume spikes often precede major moves - stay alert for breakout direction."
        )
    else:
        return f"{symbol} showing activity: {trigger_text}. Monitor for follow-through."


async def _generate_llm_commentary(move: Dict) -> Optional[str]:
    """Generate commentary using Groq LLM."""
    if not GROQ_API_KEY:
        return None

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""You are a professional market commentator. Write a brief (2-3 sentence)
trading commentary about this move:

Symbol: {move['symbol']}
Price Change: {move['price_change_pct']:+.1f}%
Volume: {move['volume_ratio']:.1f}x average
RSI: {move['rsi']:.0f}
Bollinger Position: {move['bb_position']}
Triggers: {', '.join(move['triggers']) or 'None'}

Be specific, actionable, and mention risk levels. Use trader language."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.warning(f"LLM commentary failed: {e}")
        return None


async def generate_commentary(symbol: str) -> Dict[str, Any]:
    """Generate market commentary for a symbol."""
    move = _detect_significant_moves(symbol)

    # Try LLM first, fallback to rules
    llm_text = await _generate_llm_commentary(move) if move["has_significant_move"] else None
    commentary = llm_text or _generate_rule_based_commentary(move)

    return {
        "symbol": symbol.upper(),
        "commentary": commentary,
        "source": "groq" if llm_text else "rule-based",
        "severity": move["severity"],
        "triggers": move["triggers"],
        "metrics": {
            "price_change_pct": move["price_change_pct"],
            "volume_ratio": move["volume_ratio"],
            "rsi": move["rsi"],
        },
        "generated_at": datetime.now().isoformat(),
    }


async def generate_market_digest(symbols: List[str] = None) -> Dict[str, Any]:
    """Generate a market digest covering multiple symbols."""
    if not symbols:
        symbols = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "BTC-USD", "MSFT", "META"]

    items = []
    significant_count = 0

    for sym in symbols[:15]:
        move = _detect_significant_moves(sym)
        if move["has_significant_move"]:
            significant_count += 1
            commentary = _generate_rule_based_commentary(move)
            items.append({
                "symbol": sym,
                "severity": move["severity"],
                "commentary": commentary,
                "price_change_pct": move["price_change_pct"],
                "triggers": move["triggers"],
            })

    # Sort by severity and abs price change
    severity_order = {"high": 0, "medium": 1, "normal": 2}
    items.sort(key=lambda x: (severity_order.get(x["severity"], 2), -abs(x["price_change_pct"])))

    # Generate summary
    if significant_count == 0:
        summary = "Markets trading in a quiet range. No significant moves detected across monitored symbols."
    elif significant_count <= 2:
        movers = [f"{i['symbol']} ({i['price_change_pct']:+.1f}%)" for i in items[:2]]
        summary = f"Mixed session with notable moves in {', '.join(movers)}."
    else:
        avg_change = sum(i["price_change_pct"] for i in items) / len(items) if items else 0
        direction = "bullish" if avg_change > 0 else "bearish" if avg_change < 0 else "mixed"
        summary = f"Active session with {significant_count} significant moves. Overall tone: {direction}."

    return {
        "summary": summary,
        "significant_moves": significant_count,
        "total_monitored": len(symbols),
        "items": items,
        "generated_at": datetime.now().isoformat(),
    }
