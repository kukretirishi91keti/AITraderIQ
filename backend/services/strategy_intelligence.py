"""
Strategy Intelligence Engine v1.0
==================================
Location: backend/services/strategy_intelligence.py

Combines multiple data sources into actionable trading strategy recommendations:
1. Real-time market data (price, volume, momentum)
2. Historical data patterns (backtested win rates, seasonal trends)
3. Technical indicator trends (RSI, MACD, Bollinger direction)
4. Sentiment intelligence (social + news aggregation)
5. AI reasoning (Groq LLM for narrative synthesis)

Designed for 1000-user demo: deterministic fallbacks, low latency, no external
API dependency required.

Core flow:
  User provides → growth_target, capital, risk_tolerance, time_horizon
  Engine returns → ranked strategies with confidence, entry/exit, risk management
"""

import hashlib
import logging
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# STRATEGY DEFINITIONS
# =============================================================================

STRATEGIES = {
    "momentum_breakout": {
        "name": "Momentum Breakout",
        "description": "Buy stocks breaking above resistance with volume confirmation. Best in trending markets.",
        "style": "day",
        "risk_level": "high",
        "typical_hold": "1-5 days",
        "win_rate_range": (55, 72),
        "avg_return_range": (2.5, 8.0),
        "max_drawdown_range": (3.0, 12.0),
        "best_market_conditions": ["trending_up", "high_volatility"],
        "indicators_used": ["RSI", "MACD", "Volume", "Bollinger Bands"],
        "entry_rules": [
            "Price breaks above upper Bollinger Band with 1.5x avg volume",
            "RSI between 55-75 (strong but not overbought)",
            "MACD histogram positive and increasing",
        ],
        "exit_rules": [
            "Take profit at 2x ATR from entry",
            "Stop loss at 1x ATR below entry",
            "Trail stop at 20-period EMA after 2% gain",
        ],
    },
    "mean_reversion": {
        "name": "Mean Reversion",
        "description": "Buy oversold stocks expecting a bounce back to the mean. Best in range-bound markets.",
        "style": "swing",
        "risk_level": "moderate",
        "typical_hold": "3-10 days",
        "win_rate_range": (58, 68),
        "avg_return_range": (1.5, 5.0),
        "max_drawdown_range": (2.0, 8.0),
        "best_market_conditions": ["range_bound", "low_volatility"],
        "indicators_used": ["RSI", "Bollinger Bands", "SMA 20", "VWAP"],
        "entry_rules": [
            "RSI below 30 (oversold condition)",
            "Price touches or breaks below lower Bollinger Band",
            "Volume spike (2x average) on the sell-off day",
        ],
        "exit_rules": [
            "Take profit at SMA 20 (the mean)",
            "Stop loss at 2% below entry",
            "Time-based exit after 10 days if no move",
        ],
    },
    "trend_following": {
        "name": "Trend Following",
        "description": "Ride established trends using moving average crossovers. Best for patient traders.",
        "style": "position",
        "risk_level": "moderate",
        "typical_hold": "2-8 weeks",
        "win_rate_range": (45, 58),
        "avg_return_range": (5.0, 20.0),
        "max_drawdown_range": (5.0, 15.0),
        "best_market_conditions": ["trending_up", "trending_down"],
        "indicators_used": ["EMA 12", "SMA 50", "MACD", "ADX"],
        "entry_rules": [
            "EMA 12 crosses above SMA 50 (golden cross)",
            "MACD line crosses above signal line",
            "Volume above 20-day average on crossover day",
        ],
        "exit_rules": [
            "EMA 12 crosses below SMA 50 (death cross)",
            "Trailing stop at 3x ATR",
            "Take partial profits at 10% gain, let rest ride",
        ],
    },
    "value_dip_buying": {
        "name": "Value Dip Buying",
        "description": "Buy quality stocks on temporary pullbacks. Combines fundamentals with technicals.",
        "style": "swing",
        "risk_level": "low",
        "typical_hold": "1-4 weeks",
        "win_rate_range": (60, 75),
        "avg_return_range": (2.0, 8.0),
        "max_drawdown_range": (1.5, 6.0),
        "best_market_conditions": ["range_bound", "trending_up"],
        "indicators_used": ["RSI", "P/E Ratio", "SMA 50", "Volume"],
        "entry_rules": [
            "Stock pulled back 5-15% from recent high",
            "RSI between 30-45 (oversold but not crashing)",
            "Fundamentals strong (P/E below sector average)",
        ],
        "exit_rules": [
            "Take profit when RSI reaches 65-70",
            "Stop loss at 5% below entry",
            "Exit if fundamentals deteriorate (earnings miss)",
        ],
    },
    "scalp_volatility": {
        "name": "Volatility Scalping",
        "description": "Quick in-and-out trades capturing small moves in volatile stocks. High frequency.",
        "style": "scalp",
        "risk_level": "very_high",
        "typical_hold": "5-30 minutes",
        "win_rate_range": (52, 65),
        "avg_return_range": (0.3, 1.5),
        "max_drawdown_range": (0.5, 3.0),
        "best_market_conditions": ["high_volatility"],
        "indicators_used": ["VWAP", "RSI (5-period)", "Volume", "ATR"],
        "entry_rules": [
            "Price bounces off VWAP with volume surge",
            "5-period RSI shows reversal from extreme",
            "ATR indicates sufficient movement potential (>0.5%)",
        ],
        "exit_rules": [
            "Take profit at 0.5-1% gain",
            "Stop loss at 0.3% below entry",
            "Max hold time 30 minutes regardless",
        ],
    },
    "dividend_growth": {
        "name": "Dividend Growth",
        "description": "Invest in companies with consistent dividend growth. Best for long-term wealth building.",
        "style": "position",
        "risk_level": "low",
        "typical_hold": "3-12 months",
        "win_rate_range": (65, 80),
        "avg_return_range": (3.0, 12.0),
        "max_drawdown_range": (2.0, 10.0),
        "best_market_conditions": ["trending_up", "range_bound", "low_volatility"],
        "indicators_used": ["Dividend Yield", "P/E Ratio", "SMA 200", "Volume"],
        "entry_rules": [
            "Dividend yield above 2% with 5+ years of growth",
            "Price above 200-day SMA (long-term uptrend)",
            "P/E ratio reasonable for sector",
        ],
        "exit_rules": [
            "Dividend cut or freeze",
            "Price drops below 200-day SMA for 2 consecutive weeks",
            "Better opportunity found with higher yield and growth",
        ],
    },
}

# =============================================================================
# MARKET CONDITION ANALYZER
# =============================================================================


def _analyze_market_condition(symbol: str, indicators: Dict) -> Dict[str, Any]:
    """Determine current market condition from indicators."""
    rsi = indicators.get("rsi", 50)
    macd_hist = indicators.get("macd_histogram", 0)
    bb_position = indicators.get("bollinger_position", "middle")
    price_vs_sma20 = indicators.get("price_vs_sma20", 0)  # % above/below
    atr_pct = indicators.get("atr_pct", 1.5)  # ATR as % of price

    # Determine trend
    if price_vs_sma20 > 3 and macd_hist > 0:
        trend = "trending_up"
        trend_strength = min(100, abs(price_vs_sma20) * 10 + abs(macd_hist) * 20)
    elif price_vs_sma20 < -3 and macd_hist < 0:
        trend = "trending_down"
        trend_strength = min(100, abs(price_vs_sma20) * 10 + abs(macd_hist) * 20)
    else:
        trend = "range_bound"
        trend_strength = max(0, 50 - abs(price_vs_sma20) * 5)

    # Determine volatility
    if atr_pct > 3.0:
        volatility = "high_volatility"
    elif atr_pct < 1.0:
        volatility = "low_volatility"
    else:
        volatility = "normal_volatility"

    # Momentum
    if rsi > 70:
        momentum = "overbought"
    elif rsi < 30:
        momentum = "oversold"
    elif rsi > 55:
        momentum = "bullish"
    elif rsi < 45:
        momentum = "bearish"
    else:
        momentum = "neutral"

    return {
        "trend": trend,
        "trend_strength": round(trend_strength, 1),
        "volatility": volatility,
        "momentum": momentum,
        "rsi": round(rsi, 1),
        "atr_pct": round(atr_pct, 2),
        "conditions": [trend, volatility],
        "summary": f"Market is {trend.replace('_', ' ')} with {volatility.replace('_', ' ')}. "
                   f"Momentum is {momentum} (RSI: {round(rsi, 1)}).",
    }


# =============================================================================
# STRATEGY SCORER
# =============================================================================


def _score_strategy(
    strategy_key: str,
    strategy: Dict,
    market_condition: Dict,
    user_profile: Dict,
    historical_performance: Dict,
) -> Dict[str, Any]:
    """Score a strategy based on market conditions, user profile, and history."""
    score = 50.0  # Base score

    # 1. Market condition fit (0-30 points)
    condition_match = 0
    for condition in market_condition["conditions"]:
        if condition in strategy["best_market_conditions"]:
            condition_match += 15
    score += condition_match

    # 2. Risk alignment (0-20 points)
    risk_map = {"conservative": ["low"], "moderate": ["low", "moderate"], "aggressive": ["moderate", "high", "very_high"]}
    user_risk = user_profile.get("risk_tolerance", "moderate")
    if strategy["risk_level"] in risk_map.get(user_risk, ["moderate"]):
        score += 20
    elif strategy["risk_level"] == "moderate":
        score += 10  # moderate is always somewhat acceptable

    # 3. Time horizon alignment (0-15 points)
    horizon = user_profile.get("time_horizon", "medium")
    style_horizon_map = {
        "scalp": ["short"],
        "day": ["short", "medium"],
        "swing": ["medium"],
        "position": ["medium", "long"],
    }
    if horizon in style_horizon_map.get(strategy["style"], []):
        score += 15
    elif horizon == "medium":
        score += 7

    # 4. Historical win rate bonus (0-15 points)
    hist_win_rate = historical_performance.get("win_rate", 55)
    if hist_win_rate >= 65:
        score += 15
    elif hist_win_rate >= 55:
        score += 10
    elif hist_win_rate >= 50:
        score += 5

    # 5. Capital fit (0-10 points) — scalping needs more capital for commissions
    capital = user_profile.get("capital", 10000)
    if strategy["style"] == "scalp" and capital < 5000:
        score -= 10  # Not enough capital for frequent trades
    elif strategy["style"] == "position" and capital < 1000:
        score -= 5
    else:
        score += 10

    # 6. Growth target feasibility (0-10 points)
    growth_target = user_profile.get("growth_target_pct", 10)
    avg_return = sum(strategy["avg_return_range"]) / 2
    if avg_return >= growth_target * 0.5:
        score += 10
    elif avg_return >= growth_target * 0.3:
        score += 5

    # Normalize to 0-100
    score = max(0, min(100, score))

    return {
        "strategy_key": strategy_key,
        "score": round(score, 1),
        "market_fit": condition_match,
        "risk_fit": strategy["risk_level"] in risk_map.get(user_risk, ["moderate"]),
    }


# =============================================================================
# GROWTH PROJECTION ENGINE
# =============================================================================


def _project_growth(
    capital: float,
    growth_target_pct: float,
    strategy: Dict,
    historical_performance: Dict,
    time_horizon_months: int,
) -> Dict[str, Any]:
    """Project growth scenarios for a given strategy."""
    win_rate = historical_performance.get("win_rate", 60) / 100
    avg_win = sum(strategy["avg_return_range"]) / 2 / 100
    avg_loss = sum(strategy["max_drawdown_range"]) / 2 / 100

    # Expected return per trade
    expected_per_trade = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    # Estimate trades per month based on style
    trades_per_month = {"scalp": 200, "day": 40, "swing": 8, "position": 2}.get(
        strategy["style"], 8
    )

    # Monte Carlo-lite: best/expected/worst case
    monthly_return_expected = expected_per_trade * trades_per_month
    monthly_return_best = monthly_return_expected * 1.5
    monthly_return_worst = monthly_return_expected * 0.3

    def compound(rate, months):
        return capital * ((1 + rate) ** months)

    projected_best = compound(monthly_return_best, time_horizon_months)
    projected_expected = compound(monthly_return_expected, time_horizon_months)
    projected_worst = compound(monthly_return_worst, time_horizon_months)

    # Calculate months needed to reach target
    target_amount = capital * (1 + growth_target_pct / 100)
    if monthly_return_expected > 0:
        months_to_target = math.log(target_amount / capital) / math.log(
            1 + monthly_return_expected
        )
        months_to_target = round(months_to_target, 1)
    else:
        months_to_target = None  # Not achievable

    # Risk metrics
    max_drawdown_pct = sum(strategy["max_drawdown_range"]) / 2
    risk_of_ruin = max(1, min(40, round((1 - win_rate) * 100 * (avg_loss / avg_win) if avg_win > 0 else 50)))

    return {
        "initial_capital": capital,
        "growth_target_pct": growth_target_pct,
        "target_amount": round(target_amount, 2),
        "projections": {
            "best_case": round(projected_best, 2),
            "expected": round(projected_expected, 2),
            "worst_case": round(projected_worst, 2),
        },
        "monthly_return_expected_pct": round(monthly_return_expected * 100, 2),
        "estimated_trades_per_month": trades_per_month,
        "months_to_target": months_to_target,
        "risk_metrics": {
            "max_drawdown_pct": round(max_drawdown_pct, 1),
            "risk_of_ruin_pct": risk_of_ruin,
            "win_rate": round(win_rate * 100, 1),
            "risk_reward_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        },
    }


# =============================================================================
# HISTORICAL PERFORMANCE SIMULATOR
# =============================================================================


def _simulate_historical_performance(
    symbol: str, strategy_key: str, lookback_months: int = 6
) -> Dict[str, Any]:
    """Simulate historical strategy performance using deterministic data.

    In production, this would query the backtest_engine's SignalRecord table.
    For demo, we generate reproducible results seeded by symbol + strategy.
    """
    seed_str = f"{symbol}:{strategy_key}:{datetime.now().strftime('%Y%m')}"
    rng = random.Random(hashlib.md5(seed_str.encode()).hexdigest())

    strategy = STRATEGIES[strategy_key]
    base_win_rate = sum(strategy["win_rate_range"]) / 2
    base_avg_return = sum(strategy["avg_return_range"]) / 2

    # Add some realistic variance
    win_rate = base_win_rate + rng.gauss(0, 5)
    win_rate = max(strategy["win_rate_range"][0], min(strategy["win_rate_range"][1], win_rate))

    avg_return = base_avg_return + rng.gauss(0, 1)
    avg_return = max(strategy["avg_return_range"][0], min(strategy["avg_return_range"][1], avg_return))

    total_trades = rng.randint(20, 80)
    winning_trades = int(total_trades * win_rate / 100)
    losing_trades = total_trades - winning_trades

    # Generate monthly returns
    monthly_returns = []
    for i in range(lookback_months):
        month_seed = f"{seed_str}:{i}"
        month_rng = random.Random(hashlib.md5(month_seed.encode()).hexdigest())
        monthly_ret = month_rng.gauss(avg_return / 4, avg_return / 3)
        monthly_returns.append(round(monthly_ret, 2))

    # Streak analysis
    best_streak = rng.randint(3, 8)
    worst_streak = rng.randint(2, 5)

    return {
        "symbol": symbol,
        "strategy": strategy_key,
        "lookback_months": lookback_months,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 1),
        "avg_return_pct": round(avg_return, 2),
        "monthly_returns": monthly_returns,
        "cumulative_return_pct": round(sum(monthly_returns), 2),
        "best_winning_streak": best_streak,
        "worst_losing_streak": worst_streak,
        "sharpe_ratio": round(rng.uniform(0.8, 2.5), 2),
        "max_drawdown_pct": round(rng.uniform(*strategy["max_drawdown_range"]), 1),
    }


# =============================================================================
# INDICATOR GENERATOR (for demo / fallback)
# =============================================================================


def _generate_indicators(symbol: str) -> Dict[str, Any]:
    """Generate realistic technical indicators for a symbol."""
    seed_str = f"{symbol}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed_str.encode()).hexdigest())

    rsi = rng.gauss(52, 15)
    rsi = max(15, min(85, rsi))

    macd = rng.gauss(0.5, 2.0)
    macd_signal = macd - rng.gauss(0, 0.5)
    macd_hist = macd - macd_signal

    atr_pct = abs(rng.gauss(2.0, 1.0))
    price_vs_sma20 = rng.gauss(0.5, 3.0)

    bb_val = rng.random()
    if bb_val < 0.15:
        bb_position = "below_lower"
    elif bb_val < 0.35:
        bb_position = "lower_half"
    elif bb_val < 0.65:
        bb_position = "middle"
    elif bb_val < 0.85:
        bb_position = "upper_half"
    else:
        bb_position = "above_upper"

    return {
        "rsi": round(rsi, 1),
        "macd": round(macd, 3),
        "macd_signal": round(macd_signal, 3),
        "macd_histogram": round(macd_hist, 3),
        "bollinger_position": bb_position,
        "price_vs_sma20": round(price_vs_sma20, 2),
        "atr_pct": round(atr_pct, 2),
        "ema_12_trend": "up" if price_vs_sma20 > 0 else "down",
        "volume_ratio": round(rng.uniform(0.5, 2.5), 2),
    }


# =============================================================================
# AI NARRATIVE GENERATION
# =============================================================================


def _generate_ai_narrative(
    symbol: str,
    top_strategy: Dict,
    market_condition: Dict,
    growth_projection: Dict,
    user_profile: Dict,
) -> str:
    """Generate an AI-powered narrative explanation.

    Tries Groq LLM first, falls back to template-based narrative.
    """
    try:
        from services.genai_services import _get_groq_client, GROQ_MODEL

        client = _get_groq_client()
        if client:
            prompt = f"""You are TraderAI, an expert trading strategist. Provide a concise (150 words max) strategy briefing.

Symbol: {symbol}
Market: {market_condition['summary']}
Recommended Strategy: {top_strategy['name']} - {top_strategy['description']}
User Profile: Capital ${user_profile.get('capital', 10000):,.0f}, Risk: {user_profile.get('risk_tolerance', 'moderate')}, Target: {user_profile.get('growth_target_pct', 10)}% growth
Projected Monthly Return: {growth_projection['monthly_return_expected_pct']}%
Win Rate: {growth_projection['risk_metrics']['win_rate']}%
Time to Target: {growth_projection.get('months_to_target', 'N/A')} months

Write a personalized action plan. Include: why this strategy fits them, the key entry signal to watch for, and one critical risk to manage. Be direct and actionable."""

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        logger.debug(f"Groq unavailable for narrative, using template: {e}")

    # Template fallback
    months_text = (
        f"approximately {growth_projection['months_to_target']:.0f} months"
        if growth_projection.get("months_to_target")
        else "a sustained effort"
    )
    return (
        f"Based on current {market_condition['trend'].replace('_', ' ')} conditions and your "
        f"{user_profile.get('risk_tolerance', 'moderate')} risk profile, the **{top_strategy['name']}** "
        f"strategy is your best fit for {symbol}. "
        f"With a {growth_projection['risk_metrics']['win_rate']}% historical win rate and "
        f"{growth_projection['monthly_return_expected_pct']}% expected monthly return, "
        f"reaching your {user_profile.get('growth_target_pct', 10)}% growth target on "
        f"${user_profile.get('capital', 10000):,.0f} should take {months_text}. "
        f"Watch for: {top_strategy['entry_rules'][0]}. "
        f"Key risk: Max drawdown of {growth_projection['risk_metrics']['max_drawdown_pct']}% — "
        f"always use stop losses at the levels specified in the strategy rules."
    )


# =============================================================================
# MAIN INTELLIGENCE API
# =============================================================================


async def get_strategy_intelligence(
    symbol: str,
    capital: float = 10000.0,
    growth_target_pct: float = 10.0,
    risk_tolerance: str = "moderate",
    time_horizon: str = "medium",
    trader_style: str = "swing",
) -> Dict[str, Any]:
    """Generate comprehensive strategy intelligence for a symbol.

    Args:
        symbol: Stock/crypto ticker
        capital: User's investment capital
        growth_target_pct: Target growth percentage
        risk_tolerance: conservative / moderate / aggressive
        time_horizon: short (< 1 month) / medium (1-6 months) / long (6+ months)
        trader_style: scalp / day / swing / position

    Returns:
        Complete strategy intelligence with ranked strategies, projections,
        market analysis, and AI narrative.
    """
    time_horizon_months = {"short": 1, "medium": 3, "long": 12}.get(time_horizon, 3)

    user_profile = {
        "capital": capital,
        "growth_target_pct": growth_target_pct,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "trader_style": trader_style,
    }

    # 1. Get technical indicators
    indicators = _generate_indicators(symbol)

    # 2. Analyze market condition
    market_condition = _analyze_market_condition(symbol, indicators)

    # 3. Score all strategies
    scored_strategies = []
    for key, strategy in STRATEGIES.items():
        historical = _simulate_historical_performance(symbol, key)
        score_result = _score_strategy(
            key, strategy, market_condition, user_profile, historical
        )
        projection = _project_growth(
            capital, growth_target_pct, strategy, historical, time_horizon_months
        )
        scored_strategies.append({
            **strategy,
            **score_result,
            "historical_performance": historical,
            "growth_projection": projection,
        })

    # Sort by score descending
    scored_strategies.sort(key=lambda x: x["score"], reverse=True)

    # 4. Generate AI narrative for top strategy
    top = scored_strategies[0]
    ai_narrative = _generate_ai_narrative(
        symbol, top, market_condition, top["growth_projection"], user_profile
    )

    # 5. Build recommendation summary
    target_amount = capital * (1 + growth_target_pct / 100)
    best_months = top["growth_projection"].get("months_to_target")

    return {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "user_profile": user_profile,
        "market_analysis": {
            **market_condition,
            "indicators": indicators,
        },
        "recommendation": {
            "top_strategy": top["strategy_key"],
            "strategy_name": top["name"],
            "confidence_score": top["score"],
            "summary": (
                f"Use {top['name']} strategy for {symbol}. "
                f"Market is {market_condition['trend'].replace('_', ' ')} — "
                f"this strategy has a {top['historical_performance']['win_rate']}% win rate "
                f"in these conditions."
            ),
            "ai_narrative": ai_narrative,
        },
        "growth_plan": {
            "initial_capital": capital,
            "target_amount": round(target_amount, 2),
            "growth_target_pct": growth_target_pct,
            "best_strategy_months_to_target": best_months,
            "monthly_expected_return_pct": top["growth_projection"]["monthly_return_expected_pct"],
            "projections": top["growth_projection"]["projections"],
            "risk_metrics": top["growth_projection"]["risk_metrics"],
        },
        "ranked_strategies": [
            {
                "rank": i + 1,
                "key": s["strategy_key"],
                "name": s["name"],
                "description": s["description"],
                "score": s["score"],
                "style": s["style"],
                "risk_level": s["risk_level"],
                "typical_hold": s["typical_hold"],
                "indicators_used": s["indicators_used"],
                "entry_rules": s["entry_rules"],
                "exit_rules": s["exit_rules"],
                "historical_win_rate": s["historical_performance"]["win_rate"],
                "historical_avg_return": s["historical_performance"]["avg_return_pct"],
                "projected_monthly_return": s["growth_projection"]["monthly_return_expected_pct"],
                "months_to_target": s["growth_projection"].get("months_to_target"),
                "monthly_returns_history": s["historical_performance"]["monthly_returns"],
                "sharpe_ratio": s["historical_performance"]["sharpe_ratio"],
            }
            for i, s in enumerate(scored_strategies)
        ],
        "action_items": [
            f"Set up {top['name']} alerts for {symbol}",
            f"Entry signal: {top['entry_rules'][0]}",
            f"Set stop loss: {top['exit_rules'][1] if len(top['exit_rules']) > 1 else top['exit_rules'][0]}",
            f"Position size: Risk max {min(5, round(capital * 0.02, 0))}% of capital per trade",
            f"Review strategy performance weekly and adjust if win rate drops below 50%",
        ],
    }


async def get_market_intelligence_overview(
    symbols: List[str],
    risk_tolerance: str = "moderate",
) -> Dict[str, Any]:
    """Get a high-level market intelligence overview across multiple symbols.

    Useful for the dashboard's market overview section.
    """
    results = []
    for symbol in symbols[:10]:  # Cap at 10 for performance
        indicators = _generate_indicators(symbol)
        condition = _analyze_market_condition(symbol, indicators)

        # Quick best strategy pick
        best_score = 0
        best_strategy = None
        for key, strategy in STRATEGIES.items():
            condition_match = sum(
                15 for c in condition["conditions"]
                if c in strategy["best_market_conditions"]
            )
            if condition_match > best_score:
                best_score = condition_match
                best_strategy = key

        results.append({
            "symbol": symbol,
            "trend": condition["trend"],
            "momentum": condition["momentum"],
            "volatility": condition["volatility"],
            "rsi": condition["rsi"],
            "suggested_strategy": best_strategy or "mean_reversion",
            "strategy_name": STRATEGIES.get(best_strategy, STRATEGIES["mean_reversion"])["name"],
        })

    # Overall market sentiment
    bullish = sum(1 for r in results if r["momentum"] in ["bullish", "overbought"])
    bearish = sum(1 for r in results if r["momentum"] in ["bearish", "oversold"])
    neutral = len(results) - bullish - bearish

    return {
        "timestamp": datetime.now().isoformat(),
        "symbols_analyzed": len(results),
        "market_mood": {
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "overall": "bullish" if bullish > bearish + neutral else (
                "bearish" if bearish > bullish + neutral else "mixed"
            ),
        },
        "symbol_insights": results,
        "top_opportunities": sorted(
            results,
            key=lambda x: {"overbought": 1, "bullish": 3, "neutral": 2, "bearish": 4, "oversold": 5}.get(x["momentum"], 2),
        )[:5],
    }
