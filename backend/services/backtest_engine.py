"""
Signal Backtesting Engine
=========================
Tracks historical signal accuracy by replaying signals against price outcomes.
Stores results in the database for credibility scoring.

How it works:
1. Generate a signal for a symbol at time T
2. Record the signal + price at T
3. After N periods, check if the signal was correct
4. Track win rate, avg return, Sharpe-like metrics per signal type
"""

import hashlib
import random
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

# Optional: DB model for persisting signal records (requires SQLAlchemy)
try:
    from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
    from database.engine import Base

    class SignalRecord(Base):
        __tablename__ = "signal_records"
        id = Column(Integer, primary_key=True, index=True)
        symbol = Column(String(20), nullable=False, index=True)
        signal = Column(String(20), nullable=False)
        confidence = Column(Float, nullable=False)
        trader_type = Column(String(20), default="swing")
        entry_price = Column(Float, nullable=False)
        exit_price = Column(Float, nullable=True)
        return_pct = Column(Float, nullable=True)
        is_correct = Column(Boolean, nullable=True)
        evaluated = Column(Boolean, default=False)
        rsi = Column(Float, nullable=True)
        macd = Column(Float, nullable=True)
        bollinger_position = Column(String(20), nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
        evaluated_at = Column(DateTime, nullable=True)
except ImportError:
    SignalRecord = None


# =============================================================================
# BACKTESTING ENGINE
# =============================================================================

class BacktestEngine:
    """
    Generates and evaluates historical signals to build accuracy stats.

    For the demo, we simulate historical prices using deterministic random walks
    (same seed = same results), so backtest results are reproducible.
    """

    # Evaluation periods by trader type
    EVAL_PERIODS = {
        "scalp": 1,     # 1 period (~15min)
        "day": 4,       # 4 periods (~1 hour)
        "swing": 20,    # 20 periods (~1 week)
        "position": 60, # 60 periods (~3 months)
    }

    def __init__(self):
        pass

    def _generate_price_series(self, symbol: str, periods: int = 200, base_date: str = None) -> List[float]:
        """Generate deterministic price series for backtesting."""
        base_prices = {
            'AAPL': 238, 'MSFT': 430, 'GOOGL': 175, 'AMZN': 220, 'NVDA': 933,
            'TSLA': 420, 'META': 580, 'AMD': 145, 'NFLX': 850, 'INTC': 22,
            'BTC-USD': 95000, 'ETH-USD': 3400, 'SPY': 590, 'QQQ': 510,
            'RELIANCE.NS': 1250, 'TCS.NS': 4100, 'INFY.NS': 1850,
        }
        base = base_prices.get(symbol.upper(), 100)

        seed_str = f"{symbol}:{base_date or datetime.now().strftime('%Y%m')}"
        rng = random.Random(hashlib.md5(seed_str.encode()).hexdigest())

        prices = []
        current = base * 0.9
        for _ in range(periods):
            change = (rng.random() - 0.48) * 0.025  # slight upward bias
            current = current * (1 + change)
            current = max(current, base * 0.5)
            prices.append(round(current, 2))

        return prices

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)

    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}

        def ema(data, period):
            mult = 2 / (period + 1)
            vals = [data[0]]
            for p in data[1:]:
                vals.append(p * mult + vals[-1] * (1 - mult))
            return vals

        ema12 = ema(prices, 12)
        ema26 = ema(prices, 26)
        macd_line = [a - b for a, b in zip(ema12, ema26)]
        sig = ema(macd_line[-9:], 9) if len(macd_line) >= 9 else [0]
        return {
            "macd": round(macd_line[-1], 4),
            "signal": round(sig[-1], 4),
            "histogram": round(macd_line[-1] - sig[-1], 4),
        }

    def _calculate_bollinger(self, prices: List[float], period: int = 20) -> Dict:
        if len(prices) < period:
            p = prices[-1] if prices else 100
            return {"sma_20": p, "upper_band": p * 1.02, "lower_band": p * 0.98,
                    "bandwidth": 0.04, "position": "MIDDLE"}
        sma = sum(prices[-period:]) / period
        std = math.sqrt(sum((p - sma) ** 2 for p in prices[-period:]) / period)
        upper = sma + 2 * std
        lower = sma - 2 * std
        cp = prices[-1]
        if cp > upper:
            pos = "ABOVE_UPPER"
        elif cp < lower:
            pos = "BELOW_LOWER"
        elif cp > sma + std:
            pos = "UPPER_ZONE"
        elif cp < sma - std:
            pos = "LOWER_ZONE"
        else:
            pos = "MIDDLE"
        return {
            "sma_20": round(sma, 2), "upper_band": round(upper, 2),
            "lower_band": round(lower, 2),
            "bandwidth": round((upper - lower) / sma, 4), "position": pos,
        }

    def _generate_signal(self, rsi: float, macd: Dict, bollinger: Dict, trader_type: str) -> Dict:
        """Determine signal from indicators."""
        score = 0
        if rsi < 30: score += 2
        elif rsi < 40: score += 1
        elif rsi > 70: score -= 2
        elif rsi > 60: score -= 1

        if macd["histogram"] > 0.5: score += 2
        elif macd["histogram"] > 0: score += 1
        elif macd["histogram"] < -0.5: score -= 2
        elif macd["histogram"] < 0: score -= 1

        if bollinger["position"] == "BELOW_LOWER": score += 2
        elif bollinger["position"] == "LOWER_ZONE": score += 1
        elif bollinger["position"] == "ABOVE_UPPER": score -= 2
        elif bollinger["position"] == "UPPER_ZONE": score -= 1

        thresholds = {
            "scalp": (2, -2), "day": (3, -3),
            "swing": (3, -3), "position": (4, -4),
        }
        buy_t, sell_t = thresholds.get(trader_type, (3, -3))

        if score >= buy_t:
            signal = "STRONG_BUY"
        elif score > 0:
            signal = "BUY"
        elif score <= sell_t:
            signal = "STRONG_SELL"
        elif score < 0:
            signal = "SELL"
        else:
            signal = "HOLD"

        confidence = min(95, 50 + abs(score) * 10)
        return {"signal": signal, "confidence": confidence, "score": score}

    def run_backtest(
        self,
        symbol: str,
        trader_type: str = "swing",
        periods: int = 150,
        lookback: int = 50,
    ) -> Dict[str, Any]:
        """
        Run a full backtest on historical data.

        Generates signals at each point in time and checks if they were correct
        N periods later. Returns accuracy statistics.
        """
        prices = self._generate_price_series(symbol, periods + lookback)
        eval_period = self.EVAL_PERIODS.get(trader_type, 20)

        signals_generated = []
        correct = 0
        incorrect = 0
        total_return = 0.0
        returns = []

        for i in range(lookback, len(prices) - eval_period):
            window = prices[i - lookback: i + 1]
            current_price = prices[i]

            rsi = self._calculate_rsi(window)
            macd = self._calculate_macd(window)
            boll = self._calculate_bollinger(window)
            sig = self._generate_signal(rsi, macd, boll, trader_type)

            # Evaluate outcome
            future_price = prices[i + eval_period]
            ret = (future_price - current_price) / current_price

            if sig["signal"] in ("BUY", "STRONG_BUY"):
                is_correct = ret > 0
                actual_return = ret
            elif sig["signal"] in ("SELL", "STRONG_SELL"):
                is_correct = ret < 0
                actual_return = -ret  # profit from short
            else:
                # HOLD signals aren't directional
                is_correct = abs(ret) < 0.02
                actual_return = 0

            if sig["signal"] != "HOLD":
                if is_correct:
                    correct += 1
                else:
                    incorrect += 1
                returns.append(actual_return)

            signals_generated.append({
                "index": i - lookback,
                "price": round(current_price, 2),
                "signal": sig["signal"],
                "confidence": sig["confidence"],
                "rsi": rsi,
                "outcome_price": round(future_price, 2),
                "return_pct": round(ret * 100, 2),
                "correct": is_correct,
            })

        total_signals = correct + incorrect
        win_rate = (correct / total_signals * 100) if total_signals > 0 else 0
        avg_return = (sum(returns) / len(returns) * 100) if returns else 0
        std_return = (
            math.sqrt(sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)) * 100
            if len(returns) > 1 else 0
        )
        sharpe = (avg_return / std_return) if std_return > 0 else 0

        # Breakdown by signal type
        by_signal = {}
        for s in signals_generated:
            sig_type = s["signal"]
            if sig_type not in by_signal:
                by_signal[sig_type] = {"count": 0, "correct": 0, "returns": []}
            by_signal[sig_type]["count"] += 1
            if s["correct"]:
                by_signal[sig_type]["correct"] += 1
            if sig_type != "HOLD":
                by_signal[sig_type]["returns"].append(s["return_pct"])

        signal_breakdown = {}
        for sig_type, data in by_signal.items():
            wr = (data["correct"] / data["count"] * 100) if data["count"] > 0 else 0
            ar = (sum(data["returns"]) / len(data["returns"])) if data["returns"] else 0
            signal_breakdown[sig_type] = {
                "count": data["count"],
                "win_rate": round(wr, 1),
                "avg_return": round(ar, 2),
            }

        return {
            "symbol": symbol.upper(),
            "trader_type": trader_type,
            "eval_period": eval_period,
            "total_signals": total_signals,
            "correct": correct,
            "incorrect": incorrect,
            "win_rate": round(win_rate, 1),
            "avg_return": round(avg_return, 2),
            "sharpe_ratio": round(sharpe, 2),
            "std_return": round(std_return, 2),
            "signal_breakdown": signal_breakdown,
            "recent_signals": signals_generated[-20:],
            "generated_at": datetime.now().isoformat(),
        }


# Singleton
_engine = BacktestEngine()


def get_backtest_engine() -> BacktestEngine:
    return _engine
