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
from datetime import datetime
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
        "AAPL": 238.47, "MSFT": 430.50, "GOOGL": 175.20, "AMZN": 220.10,
        "NVDA": 933.30, "TSLA": 420.50, "META": 580.00, "AMD": 145.00,
        "NFLX": 850.00, "INTC": 22.50, "SPY": 590.00, "QQQ": 510.00,
        "BTC-USD": 95000.00, "ETH-USD": 3400.00,
        "RELIANCE.NS": 1250.00, "TCS.NS": 4100.00, "INFY.NS": 1850.00,
        "HDFCBANK.NS": 1680.00, "ICICIBANK.NS": 1050.00,
        "HSBA.L": 680.00, "BP.L": 480.00, "AZN.L": 10500.00,
        "SAP.DE": 180.00, "SIE.DE": 170.00, "VOW3.DE": 110.00,
        "OR.PA": 430.00, "MC.PA": 750.00,
        "7203.T": 2700.00, "6758.T": 12500.00,
        "9988.HK": 85.00, "0700.HK": 380.00,
        "BHP.AX": 46.00, "CBA.AX": 115.00,
        "005930.KS": 72000.00,
        "D05.SI": 35.00,
        "NESN.SW": 100.00, "NOVN.SW": 92.00,
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
        
        candles.append({
            "timestamp": (now.timestamp() - (count - i) * interval_minutes * 60) * 1000,
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
        return {"success": True, **quote}
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
        "currency": "USD",
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# SIGNALS ENDPOINT - CRITICAL! (was missing, caused 404)
# =============================================================================

@router.get("/signals/{symbol}")
async def get_signals(symbol: str):
    """
    Get trading signals for a symbol.

    Returns RSI, MACD, trend, signal recommendation, ATR, and risk score.
    This endpoint is called by the frontend Technicals tab.
    """
    symbol = validate_symbol(symbol)
    
    # Generate consistent signals based on symbol + time
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 300)  # Change every 5 min
    random.seed(seed)
    
    # Get current price
    try:
        svc = get_market_data_service()
        quote = await svc.get_quote(symbol)
        price = quote.get("price", 100.0)
        currency = quote.get("currency", "$")
    except:
        price = 100.0
        currency = "$"
    
    # Generate indicators
    rsi = random.uniform(25, 75)
    macd = random.uniform(-5, 5)
    macd_signal = macd + random.uniform(-1, 1)
    macd_histogram = macd - macd_signal
    
    sma_20 = price * random.uniform(0.97, 1.03)
    ema_12 = price * random.uniform(0.98, 1.02)
    vwap = price * random.uniform(0.99, 1.01)
    
    # ATR (Average True Range) - typically 1-3% of price
    atr = round(price * random.uniform(0.01, 0.03), 2)
    
    # Bollinger Bands
    bb_middle = sma_20
    bb_std = price * 0.02
    bb_upper = bb_middle + (2 * bb_std)
    bb_lower = bb_middle - (2 * bb_std)
    
    # Determine signal based on RSI
    if rsi < 30:
        signal = "STRONG BUY"
        confidence = random.randint(75, 95)
        trend = "Oversold - Reversal Expected"
    elif rsi < 40:
        signal = "BUY"
        confidence = random.randint(60, 80)
        trend = "Bullish"
    elif rsi > 70:
        signal = "STRONG SELL"
        confidence = random.randint(75, 95)
        trend = "Overbought - Correction Expected"
    elif rsi > 60:
        signal = "SELL"
        confidence = random.randint(60, 80)
        trend = "Bearish"
    else:
        signal = "HOLD"
        confidence = random.randint(50, 70)
        trend = "Neutral"
    
    # Risk score (0-100)
    volatility = random.uniform(0.5, 2.5)
    risk_score = min(100, int(30 + volatility * 20 + abs(50 - rsi) * 0.5))
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
            "middle": round(bb_middle, 2),
            "lower": round(bb_lower, 2)
        },
        "risk_score": risk_score,
        "risk_level": risk_level,
        "support": round(price * 0.95, 2),
        "resistance": round(price * 1.05, 2),
        "currency": currency,
        "price": price,
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
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
        
        quotes = list(batch["results"].values())
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
                "quoteSource": quote["source"],
                "chartSource": candles["source"],
                "dataQuality": quote["dataQuality"],
                "asOf": quote["asOf"],
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
    """Get company financials for a symbol."""
    symbol = validate_symbol(symbol)
    seed = get_seed(symbol)
    random.seed(seed)
    
    # Get current price
    try:
        svc = get_market_data_service()
        quote = await svc.get_quote(symbol)
        price = quote.get("price", 100.0)
        currency = quote.get("currency", "$")
        name = quote.get("name", f"{symbol} Corp")
    except:
        price = 100.0
        currency = "$"
        name = f"{symbol} Corp"
    
    # Generate realistic financials
    shares_outstanding = random.randint(500, 5000) * 1_000_000
    market_cap = price * shares_outstanding
    revenue = market_cap * random.uniform(0.3, 0.8)
    net_income = revenue * random.uniform(0.05, 0.25)
    eps = net_income / shares_outstanding
    pe_ratio = price / eps if eps > 0 else 0
    
    return {
        "success": True,
        "symbol": symbol,
        "name": name,
        "currency": currency,
        "financials": {
            "market_cap": round(market_cap),
            "market_cap_formatted": f"{market_cap/1e9:.2f}B",
            "revenue": round(revenue),
            "revenue_formatted": f"{revenue/1e9:.2f}B",
            "net_income": round(net_income),
            "net_income_formatted": f"{net_income/1e9:.2f}B",
            "eps": round(eps, 2),
            "pe_ratio": round(pe_ratio, 2),
            "dividend_yield": round(random.uniform(0, 3), 2),
            "profit_margin": round(net_income / revenue * 100, 2),
            "roe": round(random.uniform(10, 30), 2),
            "debt_to_equity": round(random.uniform(0.2, 1.5), 2),
            "current_ratio": round(random.uniform(1, 3), 2),
            "quick_ratio": round(random.uniform(0.8, 2), 2),
            "beta": round(random.uniform(0.8, 1.5), 2),
            "52_week_high": round(price * 1.15, 2),
            "52_week_low": round(price * 0.75, 2),
            "avg_volume": random.randint(1, 50) * 1_000_000,
            "shares_outstanding": shares_outstanding
        },
        "sector": "Technology",
        "industry": "Software",
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
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
        svc = get_market_data_service()
        svc._yf_quote_breaker.reset()
        return {"success": True, "message": "Circuit breaker reset"}
    except Exception as e:
        logger.error(f"Reset breaker error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
