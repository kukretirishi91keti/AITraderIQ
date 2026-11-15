"""
Signal Aggregator — combines RSI, MACD, and Bollinger Bands into one decision.

Returns a single AggregateSignal with action (BUY/SELL/HOLD), confidence (0-100),
a numeric score, and a plain-English reason. The existing signals router has the
raw maths; this service uses them directly without HTTP calls.
"""

from dataclasses import dataclass, field
from typing import Optional
from routers.signals import (
    generate_price_series,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    determine_signal,
)


@dataclass
class AggregateSignal:
    symbol: str
    action: str           # BUY | SELL | HOLD
    confidence: float     # 0-100
    score: int            # raw composite score (positive=bullish, negative=bearish)
    reason: str           # human-readable explanation
    indicators: dict = field(default_factory=dict)
    current_price: float = 0.0


def aggregate(symbol: str, strategy: str = "swing") -> AggregateSignal:
    """
    Run all three indicators and return a single consolidated signal.

    Strategy maps to trader_type in the existing determine_signal function:
      swing → score >= 1 triggers BUY/SELL
      day   → score >= 1 triggers BUY/SELL
      scalp → score >= 2 triggers BUY/SELL
      position → score >= 4 triggers BUY/SELL
    """
    prices = generate_price_series(symbol, periods=50)
    current_price = prices[-1]

    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    bb = calculate_bollinger_bands(prices)
    signal_data = determine_signal(rsi, macd, bb, strategy)

    raw_signal = signal_data["signal"]
    score = signal_data["score"]
    confidence = signal_data["confidence"]

    # Normalise to BUY / SELL / HOLD
    if raw_signal in ("BUY", "STRONG_BUY", "BUY_THE_DIP"):
        action = "BUY"
    elif raw_signal in ("SELL", "STRONG_SELL"):
        action = "SELL"
    else:
        action = "HOLD"

    reason = _build_reason(action, rsi, macd, bb, score)

    indicators = {
        "rsi": rsi,
        "macd": macd["macd"],
        "macd_signal": macd["signal"],
        "macd_histogram": macd["histogram"],
        "bb_position": bb["position"],
        "bb_bandwidth": bb["bandwidth"],
        "percent_b": bb["percent_b"],
    }

    return AggregateSignal(
        symbol=symbol.upper(),
        action=action,
        confidence=confidence,
        score=score,
        reason=reason,
        indicators=indicators,
        current_price=round(current_price, 2),
    )


def _build_reason(action: str, rsi: float, macd: dict, bb: dict, score: int) -> str:
    parts = []

    if rsi < 30:
        parts.append(f"RSI {rsi:.0f} oversold")
    elif rsi > 70:
        parts.append(f"RSI {rsi:.0f} overbought")
    else:
        parts.append(f"RSI {rsi:.0f} neutral")

    hist = macd["histogram"]
    if hist > 0.5:
        parts.append("MACD strongly bullish")
    elif hist > 0:
        parts.append("MACD mildly bullish")
    elif hist < -0.5:
        parts.append("MACD strongly bearish")
    elif hist < 0:
        parts.append("MACD mildly bearish")

    pos = bb["position"]
    if pos == "BELOW_LOWER":
        parts.append("price below BB lower (bounce zone)")
    elif pos == "ABOVE_UPPER":
        parts.append("price above BB upper (overextended)")
    elif pos == "LOWER_ZONE":
        parts.append("price in BB lower zone")
    elif pos == "UPPER_ZONE":
        parts.append("price in BB upper zone")

    summary = f"{action} (score={score:+d}): " + "; ".join(parts)
    return summary
