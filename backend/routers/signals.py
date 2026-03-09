"""
Signals Router - Trading Signals with Bollinger Bands
======================================================
Location: backend/routers/signals.py

Features:
- RSI calculation
- MACD calculation  
- Bollinger Bands calculation
- Risk scoring
- Signal generation with explanations
"""

from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import random
import hashlib
import math
from datetime import datetime

router = APIRouter(prefix="/api/signals", tags=["signals"])


def generate_price_series(symbol: str, periods: int = 50) -> List[float]:
    """Generate realistic price series for calculations."""
    # Get base price from symbol
    base_prices = {
        'AAPL': 250, 'MSFT': 430, 'GOOGL': 175, 'AMZN': 225, 'NVDA': 140,
        'TSLA': 250, 'META': 580, 'RELIANCE.NS': 2500, 'TCS.NS': 4200,
        'BTC-USD': 105000, 'ETH-USD': 3900,
    }
    base = base_prices.get(symbol.upper(), 100)
    
    # Generate deterministic series
    seed = f"{symbol}:{datetime.now().strftime('%Y%m%d')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    prices = []
    current = base * 0.95
    for i in range(periods):
        change = (rng.random() - 0.48) * 0.02  # Slight upward bias
        current = current * (1 + change)
        prices.append(current)
    
    return prices


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)."""
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 1)


def calculate_macd(prices: List[float]) -> Dict[str, float]:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    # EMA calculations
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]
        for price in data[1:]:
            ema_values.append((price * multiplier) + (ema_values[-1] * (1 - multiplier)))
        return ema_values
    
    ema_12 = ema(prices, 12)
    ema_26 = ema(prices, 26)
    
    macd_line = [a - b for a, b in zip(ema_12, ema_26)]
    signal_line = ema(macd_line[-9:], 9) if len(macd_line) >= 9 else [0]
    
    macd_value = macd_line[-1]
    signal_value = signal_line[-1]
    histogram = macd_value - signal_value
    
    return {
        "macd": round(macd_value, 2),
        "signal": round(signal_value, 2),
        "histogram": round(histogram, 2)
    }


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: int = 2) -> Dict[str, Any]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return {
            "sma_20": prices[-1] if prices else 0,
            "upper_band": prices[-1] * 1.02 if prices else 0,
            "lower_band": prices[-1] * 0.98 if prices else 0,
            "bandwidth": 0.04,
            "percent_b": 0.5,
            "position": "MIDDLE",
            "squeeze": False
        }
    
    # Calculate SMA
    sma = sum(prices[-period:]) / period
    
    # Calculate Standard Deviation
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std = math.sqrt(variance)
    
    # Calculate bands
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    # Bandwidth (volatility indicator)
    bandwidth = (upper_band - lower_band) / sma
    
    # %B (where price is relative to bands)
    current_price = prices[-1]
    if upper_band != lower_band:
        percent_b = (current_price - lower_band) / (upper_band - lower_band)
    else:
        percent_b = 0.5
    
    # Position relative to bands
    if current_price > upper_band:
        position = "ABOVE_UPPER"
    elif current_price > sma + (std * 1):
        position = "UPPER_ZONE"
    elif current_price < lower_band:
        position = "BELOW_LOWER"
    elif current_price < sma - (std * 1):
        position = "LOWER_ZONE"
    else:
        position = "MIDDLE"
    
    # Squeeze detection (low volatility)
    squeeze = bandwidth < 0.04
    
    return {
        "sma_20": round(sma, 2),
        "upper_band": round(upper_band, 2),
        "lower_band": round(lower_band, 2),
        "bandwidth": round(bandwidth, 4),
        "percent_b": round(percent_b, 2),
        "position": position,
        "squeeze": squeeze,
        "current_price": round(current_price, 2)
    }


def calculate_risk_score(rsi: float, macd: Dict, bollinger: Dict, volatility: float = 0.02) -> Dict[str, Any]:
    """Calculate risk score based on technical indicators."""
    risk_points = 0
    reasons = []
    
    # RSI risk
    if rsi < 25 or rsi > 75:
        risk_points += 3
        reasons.append("Extreme RSI levels")
    elif rsi < 35 or rsi > 65:
        risk_points += 1
        reasons.append("RSI approaching extremes")
    
    # Volatility risk (from Bollinger bandwidth)
    if bollinger["bandwidth"] > 0.06:
        risk_points += 2
        reasons.append("High volatility")
    elif bollinger["bandwidth"] > 0.04:
        risk_points += 1
        reasons.append("Elevated volatility")
    
    # Position risk
    if bollinger["position"] in ["ABOVE_UPPER", "BELOW_LOWER"]:
        risk_points += 2
        reasons.append("Price outside Bollinger Bands")
    
    # MACD divergence risk
    if abs(macd["histogram"]) > 2:
        risk_points += 1
        reasons.append("Strong MACD divergence")
    
    # Determine level
    if risk_points >= 5:
        level = "HIGH"
        color = "red"
    elif risk_points >= 3:
        level = "MEDIUM"
        color = "yellow"
    else:
        level = "LOW"
        color = "green"
    
    return {
        "level": level,
        "score": risk_points,
        "max_score": 8,
        "color": color,
        "reasons": reasons if reasons else ["Normal market conditions"]
    }


def generate_technical_reasons(rsi: float, macd: Dict, bollinger: Dict) -> Dict[str, Any]:
    """Generate human-readable explanations for each indicator."""
    
    # RSI interpretation
    if rsi < 30:
        rsi_status = "OVERSOLD"
        rsi_explanation = "RSI below 30 indicates oversold conditions. Price may bounce."
        rsi_action = "Potential buying opportunity"
    elif rsi > 70:
        rsi_status = "OVERBOUGHT"
        rsi_explanation = "RSI above 70 indicates overbought conditions. Price may pull back."
        rsi_action = "Consider taking profits"
    elif rsi > 50:
        rsi_status = "BULLISH"
        rsi_explanation = "RSI above 50 shows bullish momentum."
        rsi_action = "Trend favors buyers"
    else:
        rsi_status = "BEARISH"
        rsi_explanation = "RSI below 50 shows bearish momentum."
        rsi_action = "Trend favors sellers"
    
    # MACD interpretation
    if macd["macd"] > macd["signal"] and macd["histogram"] > 0:
        macd_status = "BULLISH"
        macd_explanation = "MACD above signal line with positive histogram."
        macd_action = "Bullish momentum confirmed"
    elif macd["macd"] < macd["signal"] and macd["histogram"] < 0:
        macd_status = "BEARISH"
        macd_explanation = "MACD below signal line with negative histogram."
        macd_action = "Bearish momentum confirmed"
    elif macd["histogram"] > 0:
        macd_status = "TURNING_BULLISH"
        macd_explanation = "Histogram turning positive, potential crossover."
        macd_action = "Watch for bullish confirmation"
    else:
        macd_status = "TURNING_BEARISH"
        macd_explanation = "Histogram turning negative, potential crossover."
        macd_action = "Watch for bearish confirmation"
    
    # Bollinger interpretation
    if bollinger["position"] == "ABOVE_UPPER":
        bb_status = "EXTENDED_HIGH"
        bb_explanation = "Price above upper band - extremely overbought."
        bb_action = "High probability of pullback"
    elif bollinger["position"] == "BELOW_LOWER":
        bb_status = "EXTENDED_LOW"
        bb_explanation = "Price below lower band - extremely oversold."
        bb_action = "High probability of bounce"
    elif bollinger["position"] == "UPPER_ZONE":
        bb_status = "BULLISH_TREND"
        bb_explanation = "Price in upper zone - strong uptrend."
        bb_action = "Trend is bullish"
    elif bollinger["position"] == "LOWER_ZONE":
        bb_status = "BEARISH_TREND"
        bb_explanation = "Price in lower zone - strong downtrend."
        bb_action = "Trend is bearish"
    else:
        bb_status = "NEUTRAL"
        bb_explanation = "Price near middle band - no strong trend."
        bb_action = "Wait for breakout direction"
    
    # Squeeze interpretation
    if bollinger["squeeze"]:
        squeeze_note = "⚠️ Bollinger Squeeze detected - expect big move soon!"
    else:
        squeeze_note = None
    
    return {
        "rsi": {
            "value": rsi,
            "status": rsi_status,
            "explanation": rsi_explanation,
            "action": rsi_action
        },
        "macd": {
            "value": macd["macd"],
            "signal": macd["signal"],
            "histogram": macd["histogram"],
            "status": macd_status,
            "explanation": macd_explanation,
            "action": macd_action
        },
        "bollinger": {
            "upper": bollinger["upper_band"],
            "middle": bollinger["sma_20"],
            "lower": bollinger["lower_band"],
            "position": bollinger["position"],
            "status": bb_status,
            "explanation": bb_explanation,
            "action": bb_action,
            "bandwidth": bollinger["bandwidth"],
            "percent_b": bollinger["percent_b"]
        },
        "squeeze_alert": squeeze_note
    }


def determine_signal(rsi: float, macd: Dict, bollinger: Dict, trader_type: str) -> Dict[str, Any]:
    """Determine trading signal based on all indicators."""
    
    score = 0  # Positive = bullish, Negative = bearish
    
    # RSI contribution
    if rsi < 30:
        score += 2
    elif rsi < 40:
        score += 1
    elif rsi > 70:
        score -= 2
    elif rsi > 60:
        score -= 1
    
    # MACD contribution
    if macd["histogram"] > 0.5:
        score += 2
    elif macd["histogram"] > 0:
        score += 1
    elif macd["histogram"] < -0.5:
        score -= 2
    elif macd["histogram"] < 0:
        score -= 1
    
    # Bollinger contribution
    if bollinger["position"] == "BELOW_LOWER":
        score += 2
    elif bollinger["position"] == "LOWER_ZONE":
        score += 1
    elif bollinger["position"] == "ABOVE_UPPER":
        score -= 2
    elif bollinger["position"] == "UPPER_ZONE":
        score -= 1
    
    # Adjust for trader type
    if trader_type == "scalp":
        # Scalpers react to small signals
        if score >= 2:
            signal = "BUY"
        elif score <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"
    elif trader_type == "day":
        # Day traders need clearer signals
        if score >= 3:
            signal = "STRONG_BUY"
        elif score >= 1:
            signal = "BUY"
        elif score <= -3:
            signal = "STRONG_SELL"
        elif score <= -1:
            signal = "SELL"
        else:
            signal = "HOLD"
    elif trader_type == "position":
        # Position traders only act on strong signals
        if score >= 4:
            signal = "STRONG_BUY"
        elif score <= -4:
            signal = "STRONG_SELL"
        else:
            signal = "HOLD"
    else:  # swing
        if score >= 3:
            signal = "STRONG_BUY"
        elif score >= 1:
            signal = "BUY_THE_DIP"
        elif score <= -3:
            signal = "STRONG_SELL"
        elif score <= -1:
            signal = "SELL"
        else:
            signal = "HOLD"
    
    # Confidence based on agreement
    confidence = min(95, 50 + abs(score) * 10)
    
    return {
        "signal": signal,
        "score": score,
        "confidence": confidence
    }


def generate_full_analysis(symbol: str, trader_type: str = "swing") -> Dict[str, Any]:
    """Generate complete technical analysis."""
    
    # Generate price data
    prices = generate_price_series(symbol, 50)
    current_price = prices[-1]
    
    # Calculate all indicators
    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    bollinger = calculate_bollinger_bands(prices)
    
    # Generate interpretations
    technical_reasons = generate_technical_reasons(rsi, macd, bollinger)
    risk = calculate_risk_score(rsi, macd, bollinger)
    signal_data = determine_signal(rsi, macd, bollinger, trader_type)
    
    return {
        "symbol": symbol.upper(),
        "trader_type": trader_type,
        "current_price": round(current_price, 2),
        
        # Signal
        "signal": signal_data["signal"],
        "confidence": signal_data["confidence"],
        "win_probability": signal_data["confidence"],
        
        # Raw indicators
        "rsi": rsi,
        "macd": macd["macd"],
        "macd_signal": macd["signal"],
        "macd_histogram": macd["histogram"],
        
        # Bollinger Bands
        "bollinger": bollinger,
        
        # Risk assessment
        "risk": risk,
        
        # Detailed explanations
        "technical_reasons": technical_reasons,
        
        # For backward compatibility
        "technical_indicators": {
            "rsi": rsi,
            "macd": macd["macd"],
            "macd_signal": macd["signal"],
            "macd_histogram": macd["histogram"],
            "sma_20": bollinger["sma_20"],
            "bollinger_upper": bollinger["upper_band"],
            "bollinger_lower": bollinger["lower_band"],
        },
        "technical_score": signal_data["score"],
        "sentiment_score": 50 + signal_data["score"] * 5,
        
        "generated_at": datetime.now().isoformat(),
    }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/generate")
async def generate_signal(
    symbol: str = Query(..., description="Stock symbol"),
    trader_type: str = Query(default="swing", description="Trader type: day, swing, position, scalp"),
):
    """Generate complete trading signal with technical analysis."""
    return generate_full_analysis(symbol, trader_type)


@router.post("/generate")
async def generate_signal_post(
    symbol: str = Query(..., description="Stock symbol"),
    trader_type: str = Query(default="swing", description="Trader type"),
):
    """Generate trading signal (POST method)."""
    return generate_full_analysis(symbol, trader_type)


@router.get("/analyze/{symbol}")
async def analyze_symbol(
    symbol: str,
    trader_type: str = Query(default="swing"),
):
    """Full analysis for a symbol."""
    return generate_full_analysis(symbol, trader_type)


@router.get("/bollinger/{symbol}")
async def get_bollinger(symbol: str):
    """Get just Bollinger Bands data."""
    prices = generate_price_series(symbol, 50)
    return calculate_bollinger_bands(prices)


@router.get("/risk/{symbol}")
async def get_risk_score(symbol: str):
    """Get risk assessment for a symbol."""
    analysis = generate_full_analysis(symbol, "swing")
    return analysis["risk"]
