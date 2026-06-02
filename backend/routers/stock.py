"""
stock.py - Stock Router v5.7.1
==============================
Location: backend/routers/stock.py

FIXES in v5.7.1:
- Added /api/v4/signals/{symbol} endpoint (was returning 404)
- Expanded top-movers to ALL 15 markets
- Added ATR to signals response

All endpoints:
  /api/v4/quote/{symbol}
  /api/v4/quotes
  /api/v4/candles/{symbol}
  /api/v4/history/{symbol}
  /api/v4/signals/{symbol}     <- ADDED!
  /api/v4/watchlist
  /api/v4/market-overview
  /api/v4/top-movers/{market}
  /api/v4/stock/{symbol}
  /api/v4/health
  /api/v4/roadmap
  /api/v4/financials/{symbol}
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
import random
import hashlib

from services.market_data_service import get_market_data_service
from utils.validation import validate_symbol, validate_symbols, validate_market, validate_interval, validate_period

logger = logging.getLogger(__name__)

# MATCHES frontend config.js: /api/v4/
router = APIRouter(prefix="/api/v4", tags=["Market Data v4"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class BatchQuotesRequest(BaseModel):
    symbols: List[str]
    include_candles: bool = False


class WatchlistRequest(BaseModel):
    symbols: List[str]


# =============================================================================
# MARKET SYMBOLS BY REGION (for top-movers)
# =============================================================================

MARKET_SYMBOLS = {
    "US": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD", "NFLX", "INTC", "JPM", "V", "JNJ", "WMT", "PG"],
    "INDIA": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "WIPRO.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS"],
    "INDIA_BSE": ["RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO", "ICICIBANK.BO", "SBIN.BO", "BHARTIARTL.BO", "ITC.BO", "KOTAKBANK.BO", "LT.BO"],
    "UK": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L", "ULVR.L", "RIO.L", "LLOY.L", "BARC.L", "VOD.L"],
    "GERMANY": ["SAP.DE", "SIE.DE", "VOW3.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BMW.DE", "MBG.DE", "DTE.DE", "ADS.DE"],
    "FRANCE": ["OR.PA", "MC.PA", "SAN.PA", "AIR.PA", "TTE.PA", "BNP.PA", "SU.PA", "AI.PA", "KER.PA", "DG.PA"],
    "JAPAN": ["7203.T", "6758.T", "9984.T", "6861.T", "7267.T", "8306.T", "9432.T", "6902.T", "4502.T", "8035.T"],
    "CHINA": ["9988.HK", "0700.HK", "3690.HK", "1810.HK", "2318.HK", "0939.HK", "1398.HK", "2020.HK", "9618.HK", "9999.HK"],
    "HONGKONG": ["0005.HK", "0011.HK", "0388.HK", "0016.HK", "0001.HK", "0002.HK", "0003.HK", "0006.HK", "0012.HK", "0017.HK"],
    "AUSTRALIA": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX", "MQG.AX", "FMG.AX", "TLS.AX"],
    "CANADA": ["RY.TO", "TD.TO", "ENB.TO", "CNR.TO", "BNS.TO", "BMO.TO", "CP.TO", "SU.TO", "TRP.TO", "BCE.TO"],
    "BRAZIL": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA", "B3SA3.SA", "WEGE3.SA", "RENT3.SA", "GGBR4.SA", "RAIL3.SA"],
    "KOREA": ["005930.KS", "000660.KS", "035420.KS", "005380.KS", "051910.KS", "006400.KS", "035720.KS", "028260.KS", "003550.KS", "034730.KS"],
    "SINGAPORE": ["D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C38U.SI", "F34.SI", "BN4.SI", "C52.SI", "N2IU.SI", "A17U.SI"],
    "SWITZERLAND": ["NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW", "ABBN.SW", "CSGN.SW", "ZURN.SW", "SREN.SW", "GIVN.SW", "LONN.SW"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "MATIC-USD", "LINK-USD"],
    "ETF": ["SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "EEM", "GLD", "SLV", "XLF"],
    "COMMODITIES": ["GC=F", "CL=F", "SI=F", "NG=F", "HG=F", "PL=F", "PA=F", "ZC=F", "ZW=F", "KC=F"],
    "FOREX": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X"],
}

# Aliases for market names
MARKET_ALIASES = {
    "EUROPE": "GERMANY",
    "EU": "GERMANY",
    "DE": "GERMANY",
    "FR": "FRANCE",
    "JP": "JAPAN",
    "CN": "CHINA",
    "HK": "HONGKONG",
    "AU": "AUSTRALIA",
    "CA": "CANADA",
    "BR": "BRAZIL",
    "KR": "KOREA",
    "SG": "SINGAPORE",
    "CH": "SWITZERLAND",
    "BSE": "INDIA_BSE",
}


# =============================================================================
# DEMO DATA GENERATOR (for fallback)
# =============================================================================

def get_seed(symbol: str) -> int:
    """Generate consistent seed from symbol."""
    return int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)


def generate_demo_candles(symbol: str, interval: str = "15m", count: int = 100):
    """Generate realistic demo candles for chart."""
    base_prices = {
        # US
        "AAPL": 238.47, "MSFT": 430.50, "GOOGL": 175.20, "AMZN": 220.10,
        "NVDA": 933.30, "TSLA": 420.50, "META": 580.00, "AMD": 145.00,
        "NFLX": 850.00, "INTC": 22.50, "SPY": 590.00, "QQQ": 510.00,
        "BTC-USD": 95000.00, "ETH-USD": 3400.00,
        # NSE — Nifty 50 (all 47 constituents with realistic prices)
        "RELIANCE.NS": 1280.00, "TCS.NS": 4100.00, "HDFCBANK.NS": 1750.00,
        "INFY.NS": 1900.00, "ICICIBANK.NS": 1250.00, "HINDUNILVR.NS": 2400.00,
        "ITC.NS": 490.00, "SBIN.NS": 850.00, "BHARTIARTL.NS": 1650.00,
        "BAJFINANCE.NS": 7200.00, "KOTAKBANK.NS": 1900.00, "LT.NS": 3500.00,
        "ASIANPAINT.NS": 2605.00, "AXISBANK.NS": 1100.00, "MARUTI.NS": 12000.00,
        "SUNPHARMA.NS": 1700.00, "TITAN.NS": 3400.00, "WIPRO.NS": 450.00,
        "NTPC.NS": 375.00, "POWERGRID.NS": 330.00, "ULTRACEMCO.NS": 10500.00,
        "NESTLEIND.NS": 2300.00, "TATAMOTORS.NS": 820.00, "TECHM.NS": 1650.00,
        "HCLTECH.NS": 1800.00, "TATASTEEL.NS": 160.00, "JSWSTEEL.NS": 920.00,
        "ONGC.NS": 270.00, "DRREDDY.NS": 6500.00, "CIPLA.NS": 1550.00,
        "ADANIPORTS.NS": 1300.00, "GRASIM.NS": 2700.00, "HEROMOTOCO.NS": 4800.00,
        "EICHERMOT.NS": 5100.00, "BAJAJFINSV.NS": 1900.00, "TATACONSUM.NS": 1100.00,
        "APOLLOHOSP.NS": 7200.00, "INDUSINDBK.NS": 950.00, "BPCL.NS": 340.00,
        "COALINDIA.NS": 490.00, "SHRIRAMFIN.NS": 3100.00, "BRITANNIA.NS": 5500.00,
        "DIVISLAB.NS": 5800.00, "HDFCLIFE.NS": 700.00, "SBILIFE.NS": 1600.00,
        "M&M.NS": 2900.00, "HINDALCO.NS": 680.00,
        # NSE — Additional popular stocks
        "BEL.NS": 280.00, "HAL.NS": 4300.00, "BHEL.NS": 245.00,
        "IRFC.NS": 175.00, "PFC.NS": 450.00, "RECLTD.NS": 530.00,
        "IRCTC.NS": 900.00, "ZOMATO.NS": 230.00, "DMART.NS": 4200.00,
        "AMBUJACEM.NS": 620.00, "BANKBARODA.NS": 235.00, "PNB.NS": 105.00,
        "CANBK.NS": 105.00, "TRENT.NS": 6100.00, "BAJAJ-AUTO.NS": 9800.00,
        # UK
        "HSBA.L": 680.00, "BP.L": 480.00, "AZN.L": 10500.00,
        # Europe
        "SAP.DE": 180.00, "SIE.DE": 170.00,
        "OR.PA": 430.00, "MC.PA": 750.00,
        # Asia
        "7203.T": 2700.00, "6758.T": 12500.00,
        "9988.HK": 85.00, "0700.HK": 380.00,
        "BHP.AX": 46.00, "CBA.AX": 115.00,
        "005930.KS": 72000.00,
        "D05.SI": 35.00,
        "NESN.SW": 100.00,
    }
    
    base_price = base_prices.get(symbol.upper(), 100.0)
    candles = []
    
    # Generate timestamps
    now = datetime.now()
    interval_minutes = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240, "1d": 1440, "1w": 10080, "1wk": 10080
    }.get(interval, 15)
    
    current_price = base_price
    seed = get_seed(symbol)
    random.seed(seed)
    
    for i in range(count):
        # Random walk
        change = random.uniform(-0.005, 0.005) * current_price
        current_price = max(current_price + change, base_price * 0.8)
        current_price = min(current_price, base_price * 1.2)
        
        open_price = current_price * random.uniform(0.998, 1.002)
        close_price = current_price * random.uniform(0.998, 1.002)
        high_price = max(open_price, close_price) * random.uniform(1.001, 1.01)
        low_price = min(open_price, close_price) * random.uniform(0.99, 0.999)
        volume = random.randint(100000, 5000000)
        
        candle_time = now - timedelta(minutes=(count - i) * interval_minutes)
        candles.append({
            "timestamp": candle_time.isoformat(),
            "date": candle_time.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
    
    return candles


# =============================================================================
# QUOTE ENDPOINTS
# =============================================================================

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote for a single symbol."""
    symbol = validate_symbol(symbol)
    try:
        svc = get_market_data_service()
        quote = await svc.get_quote(symbol)
        result = {"success": True, **quote}
        result.setdefault("symbol", symbol)
        result.setdefault("timestamp", datetime.now().isoformat())
        return result
    except Exception as e:
        logger.error(f"Quote error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quote")


@router.get("/quotes")
async def get_quotes_query(
    symbols: List[str] = Query(..., description="List of symbols")
):
    """Get quotes for multiple symbols."""
    try:
        svc = get_market_data_service()
        result = await svc.get_quotes_batch(symbols)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Batch quotes error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/quotes")
async def get_quotes_body(request: BatchQuotesRequest):
    """Get quotes for multiple symbols (JSON body)."""
    try:
        svc = get_market_data_service()
        result = await svc.get_quotes_batch(request.symbols)
        
        if request.include_candles:
            for symbol in request.symbols:
                sym = symbol.upper()
                if sym in result["results"]:
                    candles = await svc.get_candles(sym, "1d", 20)
                    result["results"][sym]["miniChart"] = candles["candles"][-20:]
        
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Batch quotes error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# CANDLES ENDPOINT
# =============================================================================

@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    interval: str = Query("1d"),
    timeframe: str = Query(None),
    lookback: int = Query(100, ge=5, le=500)
):
    """Get historical OHLCV candles."""
    symbol = validate_symbol(symbol)
    tf = validate_interval(timeframe or interval)
    try:
        svc = get_market_data_service()
        result = await svc.get_candles(symbol, interval=tf, lookback=lookback)
        return {
            "success": True,
            "symbol": result["symbol"],
            "interval": result["interval"],
            "count": result["count"],
            "results": result["candles"],
            "candles": result["candles"],
            "source": result["source"],
            "dataQuality": result["dataQuality"],
        }
    except Exception as e:
        logger.error(f"Candles error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# HISTORY ENDPOINT (FOR CHART) - CRITICAL FOR UI!
# =============================================================================

@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    period: str = Query("5d"),
    interval: str = Query("15m")
):
    """
    Get price history for charting.
    
    This endpoint is called by the frontend chart component.
    Falls back to demo data if live data unavailable.
    """
    symbol = validate_symbol(symbol)
    period = validate_period(period)
    interval = validate_interval(interval)

    # Map period to lookback count
    period_to_count = {
        "1d": 100, "5d": 100, "1mo": 200, "3mo": 300,
        "6mo": 400, "1y": 500, "2y": 600
    }
    lookback = period_to_count.get(period, 100)

    try:
        svc = get_market_data_service()
        result = await svc.get_candles(symbol, interval=interval, lookback=lookback)
        
        if result and result.get("candles"):
            return {
                "success": True,
                "symbol": symbol,
                "interval": interval,
                "period": period,
                "count": result["count"],
                "candles": result["candles"],
                "history": result["candles"],  # Frontend expects 'history'
                "data": result["candles"],     # Frontend fallback expects 'data'
                "source": result["source"],
                "dataQuality": result["dataQuality"],
                "currency": result.get("currency", "USD"),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.warning(f"Live history failed for {symbol}: {e}")
    
    # Fallback to demo data
    logger.info(f"Using demo candles for {symbol}")
    demo_candles = generate_demo_candles(symbol, interval, lookback)
    demo_currency = "₹" if symbol.endswith(".NS") or symbol.endswith(".BO") else "USD"

    return {
        "success": True,
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "count": len(demo_candles),
        "candles": demo_candles,
        "history": demo_candles,
        "data": demo_candles,
        "source": "DEMO",
        "dataQuality": "DEMO",
        "currency": demo_currency,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# SIGNALS ENDPOINT - CRITICAL! (was missing, caused 404)
# =============================================================================

@router.get("/signals/{symbol}")
async def get_signals(symbol: str):
    """
    Get trading signals for a symbol using real technical indicators.

    Computes RSI(14), MACD(12,26,9), Bollinger Bands(20,2), ATR(14), VWAP,
    SMA(20), EMA(12) from actual OHLCV price history.
    Falls back to demo data if live history is unavailable.
    """
    import math

    symbol = validate_symbol(symbol)
    source = "LIVE"

    try:
        svc = get_market_data_service()
        candles_raw, hist_source = await svc.get_history(symbol, period="3mo", interval="1d")

        if not candles_raw or len(candles_raw) < 26:
            raise ValueError("Insufficient data")

        # Extract OHLCV
        candles = []
        for c in candles_raw:
            candles.append({
                "open": float(c.get("open", 0)),
                "high": float(c.get("high", 0)),
                "low": float(c.get("low", 0)),
                "close": float(c.get("close", 0)),
                "volume": float(c.get("volume", 0)),
            })

        closes = [c["close"] for c in candles]
        price = closes[-1]

        # Get currency from quote
        try:
            quote = await svc.get_quote(symbol)
            currency = quote.get("currency", "$")
        except Exception:
            currency = "$"

        # ── RSI(14) ──
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = sum(gains[:14]) / 14
        avg_loss = sum(losses[:14]) / 14
        for i in range(14, len(gains)):
            avg_gain = (avg_gain * 13 + gains[i]) / 14
            avg_loss = (avg_loss * 13 + losses[i]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # ── EMA helper ──
        def _ema(data, period):
            k = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                result.append(data[i] * k + result[-1] * (1 - k))
            return result

        # ── MACD(12,26,9) ──
        ema12_vals = _ema(closes, 12)
        ema26_vals = _ema(closes, 26)
        macd_line = [ema12_vals[i] - ema26_vals[i] for i in range(len(closes))]
        signal_line = _ema(macd_line[25:], 9)
        macd = macd_line[-1]
        macd_signal = signal_line[-1]
        macd_histogram = macd - macd_signal

        # ── Bollinger Bands(20,2) ──
        window = closes[-20:] if len(closes) >= 20 else closes
        sma_20 = sum(window) / len(window)
        std_20 = math.sqrt(sum((c - sma_20) ** 2 for c in window) / len(window))
        bb_upper = sma_20 + 2 * std_20
        bb_lower = sma_20 - 2 * std_20

        # ── ATR(14) ──
        trs = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i - 1]["close"]),
                abs(candles[i]["low"] - candles[i - 1]["close"]),
            )
            trs.append(tr)
        atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else (sum(trs) / len(trs) if trs else 0)

        # ── VWAP ──
        tp_vol = sum((c["high"] + c["low"] + c["close"]) / 3 * c["volume"] for c in candles)
        total_vol = sum(c["volume"] for c in candles)
        vwap = tp_vol / total_vol if total_vol > 0 else price

        # ── EMA(12) ──
        ema_12 = ema12_vals[-1]

        # ── Signal determination ──
        if rsi < 30 and macd_histogram > 0:
            signal = "STRONG BUY"
            confidence = round(80 + min(15, (30 - rsi) / 2), 1)
            trend = "Oversold + MACD crossover - Reversal Expected"
        elif rsi < 30:
            signal = "BUY"
            confidence = round(65 + min(15, (30 - rsi) / 2), 1)
            trend = "Oversold - Reversal Expected"
        elif rsi > 70 and macd_histogram < 0:
            signal = "STRONG SELL"
            confidence = round(80 + min(15, (rsi - 70) / 2), 1)
            trend = "Overbought + MACD bearish - Correction Expected"
        elif rsi > 70:
            signal = "SELL"
            confidence = round(65 + min(15, (rsi - 70) / 2), 1)
            trend = "Overbought - Correction Expected"
        elif macd_histogram > 0 and price > sma_20:
            signal = "BUY"
            confidence = round(55 + min(15, abs(macd_histogram) / price * 1000), 1)
            trend = "Bullish"
        elif macd_histogram < 0 and price < sma_20:
            signal = "SELL"
            confidence = round(55 + min(15, abs(macd_histogram) / price * 1000), 1)
            trend = "Bearish"
        else:
            signal = "HOLD"
            confidence = round(45 + min(15, (50 - abs(rsi - 50)) / 3), 1)
            trend = "Neutral"

        confidence = max(0, min(100, confidence))

        # Risk assessment
        volatility = (atr / price * 100) if price > 0 else 1.0
        risk_score = min(100, int(30 + volatility * 10 + abs(50 - rsi) * 0.5))
        risk_level = "Low" if risk_score < 40 else "Medium" if risk_score < 70 else "High"

        return {
            "success": True,
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "trend": trend,
            "rsi": round(rsi, 2),
            "macd": round(macd, 4),
            "macd_signal": round(macd_signal, 4),
            "macd_histogram": round(macd_histogram, 4),
            "sma_20": round(sma_20, 2),
            "ema_12": round(ema_12, 2),
            "vwap": round(vwap, 2),
            "atr": round(atr, 2),
            "bollinger": {
                "upper": round(bb_upper, 2),
                "middle": round(sma_20, 2),
                "lower": round(bb_lower, 2),
            },
            "risk_score": risk_score,
            "risk_level": risk_level,
            "support": round(bb_lower, 2),
            "resistance": round(bb_upper, 2),
            "currency": currency,
            "price": round(price, 2),
            "source": hist_source,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.warning(f"Live signals failed for {symbol}, using demo: {e}")
        # ── Fallback: demo signals ──
        seed = get_seed(symbol) + int(datetime.now().timestamp() / 300)
        random.seed(seed)

        try:
            svc = get_market_data_service()
            quote = await svc.get_quote(symbol)
            price = quote.get("price", 100.0)
            currency = quote.get("currency", "$")
        except Exception:
            price = 100.0
            currency = "$"

        rsi = random.uniform(25, 75)
        macd = random.uniform(-5, 5)
        macd_signal = macd + random.uniform(-1, 1)
        macd_histogram = macd - macd_signal
        sma_20 = price * random.uniform(0.97, 1.03)
        ema_12 = price * random.uniform(0.98, 1.02)
        vwap = price * random.uniform(0.99, 1.01)
        atr = round(price * random.uniform(0.01, 0.03), 2)
        bb_std = price * 0.02
        bb_upper = sma_20 + 2 * bb_std
        bb_lower = sma_20 - 2 * bb_std

        if rsi < 30:
            signal, confidence, trend = "STRONG BUY", random.randint(75, 95), "Oversold - Reversal Expected"
        elif rsi < 40:
            signal, confidence, trend = "BUY", random.randint(60, 80), "Bullish"
        elif rsi > 70:
            signal, confidence, trend = "STRONG SELL", random.randint(75, 95), "Overbought - Correction Expected"
        elif rsi > 60:
            signal, confidence, trend = "SELL", random.randint(60, 80), "Bearish"
        else:
            signal, confidence, trend = "HOLD", random.randint(50, 70), "Neutral"

        risk_score = min(100, int(30 + random.uniform(0.5, 2.5) * 20 + abs(50 - rsi) * 0.5))
        risk_level = "Low" if risk_score < 40 else "Medium" if risk_score < 70 else "High"

        return {
            "success": True,
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "trend": trend,
            "rsi": round(rsi, 2),
            "macd": round(macd, 4),
            "macd_signal": round(macd_signal, 4),
            "macd_histogram": round(macd_histogram, 4),
            "sma_20": round(sma_20, 2),
            "ema_12": round(ema_12, 2),
            "vwap": round(vwap, 2),
            "atr": atr,
            "bollinger": {
                "upper": round(bb_upper, 2),
                "middle": round(sma_20, 2),
                "lower": round(bb_lower, 2),
            },
            "risk_score": risk_score,
            "risk_level": risk_level,
            "support": round(price * 0.95, 2),
            "resistance": round(price * 1.05, 2),
            "currency": currency,
            "price": price,
            "source": "DEMO",
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# WATCHLIST ENDPOINT
# =============================================================================

@router.get("/watchlist")
async def get_watchlist(
    symbols: str = Query(None, description="Comma-separated symbols")
):
    """Get watchlist data with mini charts."""
    try:
        svc = get_market_data_service()
        
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        else:
            symbol_list = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                "TSLA", "META", "AMD", "NFLX",
                "RELIANCE.NS", "TCS.NS",
                "BTC-USD", "ETH-USD",
                "SPY", "QQQ",
            ]
        
        batch = await svc.get_quotes_batch(symbol_list)
        
        watchlist = []
        for symbol in symbol_list:
            sym = symbol.upper()
            if sym in batch["results"]:
                quote = batch["results"][sym]
                candles = await svc.get_candles(sym, "1d", 20)
                watchlist.append({
                    **quote,
                    "miniChart": candles["candles"][-20:],
                })
        
        watchlist.sort(key=lambda x: abs(x.get("changePercent") or 0), reverse=True)
        
        return {
            "success": True,
            "count": len(watchlist),
            "asOf": batch["asOf"],
            "watchlist": watchlist,
        }
    except Exception as e:
        logger.error(f"Watchlist error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/watchlist")
async def post_watchlist(request: WatchlistRequest):
    """Get watchlist data (JSON body)."""
    symbols_str = ",".join(request.symbols)
    return await get_watchlist(symbols=symbols_str)


# =============================================================================
# TOP MOVERS ENDPOINT - NOW SUPPORTS ALL MARKETS
# =============================================================================

@router.get("/top-movers/{market}")
async def get_top_movers(
    market: str = "US",
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get top gainers and losers for a market.
    
    Supports: US, INDIA, UK, GERMANY, FRANCE, JAPAN, CHINA, HONGKONG,
              AUSTRALIA, CANADA, BRAZIL, KOREA, SINGAPORE, SWITZERLAND,
              CRYPTO, ETF, COMMODITIES, FOREX
    """
    try:
        svc = get_market_data_service()
        
        # Normalize market name
        market_upper = market.upper()
        market_key = MARKET_ALIASES.get(market_upper, market_upper)
        
        # Get symbols for market
        symbols = MARKET_SYMBOLS.get(market_key, MARKET_SYMBOLS["US"])
        
        batch = await svc.get_quotes_batch(symbols)
        
        quotes = [{**q, "symbol": q.get("symbol") or sym} for sym, q in batch["results"].items()]
        quotes.sort(key=lambda x: x.get("changePercent") or 0, reverse=True)

        gainers = [
            {
                "ticker": q["symbol"],
                "name": q.get("name", q["symbol"]),
                "price": q["price"], 
                "changePercent": q.get("changePercent") or 0,
                "currency": q.get("currency", "$")
            }
            for q in quotes if (q.get("changePercent") or 0) > 0
        ][:limit]
        
        losers = [
            {
                "ticker": q["symbol"], 
                "name": q.get("name", q["symbol"]),
                "price": q["price"], 
                "changePercent": q.get("changePercent") or 0,
                "currency": q.get("currency", "$")
            }
            for q in quotes if (q.get("changePercent") or 0) < 0
        ][:limit]
        
        # If not enough movers, generate demo data
        if len(gainers) < 2 or len(losers) < 2:
            random.seed(get_seed(market_key) + int(datetime.now().timestamp() / 300))
            for sym in symbols[:limit]:
                if len(gainers) < limit:
                    gainers.append({
                        "ticker": sym,
                        "name": sym,
                        "price": 100.0,
                        "changePercent": round(random.uniform(0.5, 5.0), 2),
                        "currency": "$"
                    })
                if len(losers) < limit:
                    losers.append({
                        "ticker": symbols[-(symbols.index(sym)+1)] if sym in symbols else sym,
                        "name": symbols[-(symbols.index(sym)+1)] if sym in symbols else sym,
                        "price": 100.0,
                        "changePercent": round(random.uniform(-5.0, -0.5), 2),
                        "currency": "$"
                    })
        
        return {
            "success": True,
            "market": market_key,
            "gainers": gainers[:limit],
            "losers": losers[:limit],
            "asOf": batch.get("asOf", datetime.now().isoformat()),
        }
    except Exception as e:
        logger.error(f"Top movers error for {market}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# MARKET OVERVIEW
# =============================================================================

@router.get("/market-overview")
async def get_market_overview():
    """Get multi-market overview."""
    try:
        svc = get_market_data_service()
        result = await svc.get_market_overview()
        
        indices = [
            {"symbol": "SPY", "name": "S&P 500", "change": 0.5},
            {"symbol": "QQQ", "name": "NASDAQ", "change": 0.8},
            {"symbol": "DIA", "name": "DOW", "change": 0.3},
        ]
        
        try:
            idx_batch = await svc.get_quotes_batch(["SPY", "QQQ", "DIA"])
            for idx in indices:
                if idx["symbol"] in idx_batch["results"]:
                    q = idx_batch["results"][idx["symbol"]]
                    idx["change"] = q.get("changePercent") or 0
                    idx["price"] = q.get("price")
        except:
            pass
        
        return {
            "success": True,
            "indices": indices,
            **result
        }
    except Exception as e:
        logger.error(f"Market overview error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# COMBINED STOCK ENDPOINT
# =============================================================================

@router.get("/stock/{symbol}")
async def get_stock_data(
    symbol: str,
    timeframe: str = Query("1d")
):
    """Get complete stock data: quote + chart."""
    symbol = validate_symbol(symbol)
    timeframe = validate_interval(timeframe)
    try:
        svc = get_market_data_service()
        
        quote = await svc.get_quote(symbol)
        
        periods_map = {
            "1m": 60, "5m": 60, "15m": 60, "30m": 48,
            "1h": 48, "4h": 30, "1d": 90, "1w": 52, "1mo": 24
        }
        lookback = periods_map.get(timeframe, 90)
        candles = await svc.get_candles(symbol, interval=timeframe, lookback=lookback)
        
        return {
            "success": True,
            "ticker": symbol.upper(),
            "quote": quote,
            "chart": {
                "timeframe": timeframe,
                "count": candles["count"],
                "data": candles["candles"],
                "source": candles["source"],
            },
            "metadata": {
                "quoteSource": quote.get("source", "UNKNOWN"),
                "chartSource": candles["source"],
                "dataQuality": quote.get("dataQuality", "UNKNOWN"),
                "asOf": quote.get("asOf", quote.get("timestamp", datetime.now().isoformat())),
            }
        }
    except Exception as e:
        logger.error(f"Stock data error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# FINANCIALS ENDPOINT
# =============================================================================

@router.get("/financials/{symbol}")
async def get_financials(symbol: str):
    """Get company financials for a symbol using real yfinance data."""
    symbol = validate_symbol(symbol)

    try:
        try:
            from services.financials_service import get_financials_service
        except ImportError:
            from financials_service import get_financials_service

        fin_svc = get_financials_service()
        data = await fin_svc.get_financials(symbol, include_summary=False)

        profit_margin_raw = data.get("profitMargin")   # decimal: 0.25 → 25%
        div_yield_raw = data.get("dividendYield")       # decimal: 0.015 → 1.5%

        financials_obj = {
            "market_cap": data.get("marketCap"),
            "market_cap_formatted": data.get("marketCapFormatted"),
            "revenue": data.get("revenue"),
            "revenue_formatted": data.get("revenueFormatted"),
            "net_income": data.get("netIncome"),
            "net_income_formatted": data.get("netIncomeFormatted"),
            "eps": data.get("eps"),
            "pe_ratio": data.get("pe"),
            "dividend_yield": round(div_yield_raw * 100, 2) if div_yield_raw else 0,
            "profit_margin": round(profit_margin_raw * 100, 2) if profit_margin_raw else None,
            "debt_to_equity": data.get("debtToEquity"),
            "current_ratio": data.get("currentRatio"),
            "beta": data.get("beta"),
            "fiftyTwoWeekHigh": data.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": data.get("fiftyTwoWeekLow"),
            "sector": data.get("sector", "N/A"),
            "industry": data.get("industry", "N/A"),
        }

        return {
            "success": True,
            "symbol": symbol,
            "name": data.get("name", symbol),
            "currency": data.get("currency", "$"),
            "financials": financials_obj,
            "sector": data.get("sector", "N/A"),
            "industry": data.get("industry", "N/A"),
            "dataQuality": data.get("dataQuality", "LIVE"),
            "source": data.get("source", "YFINANCE"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Financials error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch financials")


# =============================================================================
# INDICES ENDPOINT — Nifty 50 + Bank Nifty live levels (India dashboard bar)
# =============================================================================

@router.get("/indices")
async def get_india_indices():
    """Return live Nifty 50 and Bank Nifty index levels via Twelve Data."""
    import asyncio as _asyncio
    svc = get_market_data_service()

    nifty_task = _asyncio.create_task(svc.get_quote("NIFTY50.NS"))
    banknifty_task = _asyncio.create_task(svc.get_quote("BANKNIFTY.NS"))
    nifty, banknifty = await _asyncio.gather(nifty_task, banknifty_task, return_exceptions=True)

    def _safe(q, name, symbol):
        if isinstance(q, Exception) or not q:
            return {"name": name, "symbol": symbol, "price": None, "change": None,
                    "changePercent": None, "dataQuality": "UNAVAILABLE"}
        return {"name": name, "symbol": symbol, "price": q.get("price"),
                "change": q.get("change"), "changePercent": q.get("changePercent"),
                "dataQuality": q.get("dataQuality", "LIVE")}

    return {
        "success": True,
        "indices": [
            _safe(nifty, "NIFTY 50", "NIFTY50.NS"),
            _safe(banknifty, "BANK NIFTY", "BANKNIFTY.NS"),
        ],
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# HEALTH ENDPOINT
# =============================================================================

@router.get("/health")
async def get_health():
    """Get service health and diagnostics."""
    try:
        svc = get_market_data_service()
        health = await svc.get_health()
        
        breaker_state = health.get("yfinance", {}).get("breaker", {}).get("state", "CLOSED")
        if breaker_state == "CLOSED":
            status_emoji = "🟢"
            status_text = "healthy"
        elif breaker_state == "HALF_OPEN":
            status_emoji = "🟡"
            status_text = "recovering"
        else:
            status_emoji = "🟠"
            status_text = "degraded (using fallback)"
        
        return {
            "success": True,
            "statusEmoji": status_emoji,
            "statusText": status_text,
            **health
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# ROADMAP ENDPOINT
# =============================================================================

@router.get("/roadmap")
async def get_roadmap():
    """Get full product roadmap."""
    try:
        svc = get_market_data_service()
        roadmap = svc.get_roadmap()
        return {"success": True, **roadmap}
    except Exception as e:
        logger.error(f"Roadmap error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# ADMIN ENDPOINT
# =============================================================================

@router.post("/admin/reset-breaker")
async def reset_circuit_breaker():
    """Reset circuit breaker (admin use)."""
    try:
        from services.market_data_service import _circuit_breaker
        _circuit_breaker.failures = 0
        _circuit_breaker.is_open = False
        return {"success": True, "message": "Circuit breaker reset"}
    except Exception as e:
        logger.error(f"Reset breaker error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
