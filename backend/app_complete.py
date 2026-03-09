"""
TraderAI Pro - SINGLE FILE BACKEND v5.8.6
==========================================
FIXES in v5.8.6:
- FIXED: Top Movers now includes ALL 21 markets
- Added: Korea, Singapore, Switzerland, Netherlands, Spain, Italy to top-movers
- Charts now change when switching intervals (1M/5M/1H/1D/1WK)
- Expanded SECTOR_MAP with all symbols from all markets

Just run: python app_complete.py
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import random
import hashlib
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="TraderAI Pro API",
    version="5.8.6",
    description="AI-Powered Trading Dashboard - All Markets Top Movers Fixed"
)

# CORS - Allow all
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# CONFIGURATION
# ============================================================

VERSION = "5.8.6"

# Base prices for demo data
BASE_PRICES = {
    # US
    "AAPL": 246.50, "MSFT": 430.00, "GOOGL": 175.00, "NVDA": 933.00,
    "TSLA": 420.00, "META": 580.00, "AMZN": 220.00, "AMD": 145.00,
    "NFLX": 850.00, "INTC": 22.50, "JPM": 195.00, "V": 278.00,
    "WMT": 162.00, "DIS": 112.00, "JNJ": 156.00, "PG": 158.00,
    # India
    "RELIANCE.NS": 1250.00, "TCS.NS": 4100.00, "INFY.NS": 1850.00,
    "HDFCBANK.NS": 1680.00, "ICICIBANK.NS": 1050.00, "HINDUNILVR.NS": 2400.00,
    "WIPRO.NS": 480.00, "BHARTIARTL.NS": 1650.00, "ITC.NS": 450.00,
    "KOTAKBANK.NS": 1780.00, "LT.NS": 3500.00, "SBIN.NS": 820.00,
    # UK
    "HSBA.L": 680.00, "BP.L": 480.00, "SHEL.L": 2600.00, "AZN.L": 10500.00,
    "GSK.L": 1450.00, "ULVR.L": 4200.00, "RIO.L": 5100.00, "LLOY.L": 55.00,
    "BARC.L": 210.00, "VOD.L": 72.00,
    # Germany
    "SAP.DE": 180.00, "SIE.DE": 170.00, "VOW3.DE": 110.00, "ALV.DE": 250.00,
    "BAS.DE": 45.00, "BAYN.DE": 28.00, "BMW.DE": 95.00, "MBG.DE": 58.00,
    # France
    "OR.PA": 430.00, "MC.PA": 750.00, "SAN.PA": 90.00, "AIR.PA": 145.00,
    "TTE.PA": 58.00, "BNP.PA": 62.00,
    # Japan
    "7203.T": 2700.00, "6758.T": 12500.00, "9984.T": 8200.00, "6861.T": 48000.00,
    "7267.T": 1450.00, "8306.T": 1250.00, "7974.T": 7500.00,
    # Australia
    "BHP.AX": 46.00, "CBA.AX": 115.00, "CSL.AX": 280.00, "NAB.AX": 35.00,
    "WBC.AX": 28.00, "ANZ.AX": 29.00,
    # China/HK
    "9988.HK": 85.00, "0700.HK": 380.00, "3690.HK": 130.00, "1810.HK": 18.00,
    "2318.HK": 42.00, "0005.HK": 58.00, "0011.HK": 145.00, "0388.HK": 280.00,
    "9618.HK": 145.00, "1299.HK": 65.00,
    # Korea
    "005930.KS": 72000.00, "000660.KS": 135000.00, "035420.KS": 185000.00,
    "005380.KS": 180000.00,
    # Singapore
    "D05.SI": 35.00, "O39.SI": 11.50, "U11.SI": 28.00, "Z74.SI": 3.20,
    # Switzerland
    "NESN.SW": 100.00, "NOVN.SW": 92.00, "ROG.SW": 245.00, "UBSG.SW": 26.00,
    # Canada
    "RY.TO": 135.00, "TD.TO": 85.00, "ENB.TO": 52.00, "SHOP.TO": 125.00,
    "CNR.TO": 165.00, "BCE.TO": 48.00, "BMO.TO": 128.00, "BNS.TO": 72.00,
    # Brazil
    "PETR4.SA": 38.00, "VALE3.SA": 62.00, "ITUB4.SA": 32.00, "ABEV3.SA": 12.50,
    "BBDC4.SA": 14.00, "B3SA3.SA": 11.00, "WEGE3.SA": 35.00, "RENT3.SA": 42.00,
    # Netherlands
    "ASML.AS": 680.00, "INGA.AS": 14.50, "PHIA.AS": 25.00, "ABN.AS": 15.50,
    "ADYEN.AS": 1450.00, "HEIA.AS": 85.00,
    # Spain
    "SAN.MC": 4.50, "BBVA.MC": 9.50, "ITX.MC": 42.00, "IBE.MC": 12.50,
    "TEF.MC": 4.20, "REP.MC": 13.50,
    # Italy
    "ENI.MI": 14.00, "ENEL.MI": 6.80, "ISP.MI": 3.50, "UCG.MI": 38.00,
    "STM.MI": 28.00, "G.MI": 35.00,
    # Crypto
    "BTC-USD": 94500.00, "ETH-USD": 3350.00, "SOL-USD": 185.00, "XRP-USD": 2.15,
    "BNB-USD": 680.00, "ADA-USD": 0.95, "DOGE-USD": 0.32, "AVAX-USD": 42.00,
    # Forex
    "EURUSD=X": 1.04, "GBPUSD=X": 1.25, "USDJPY=X": 157.5, "AUDUSD=X": 0.62,
    "USDCAD=X": 1.44, "USDCHF=X": 0.90,
    # Commodities
    "GC=F": 2650.00, "CL=F": 70.50, "SI=F": 29.50, "NG=F": 3.45, "HG=F": 4.15,
    # ETF
    "SPY": 595.00, "QQQ": 520.00, "DIA": 425.00, "IWM": 225.00,
    "VTI": 290.00, "GLD": 245.00, "SLV": 28.00, "VOO": 545.00,
}

# Currency mapping
CURRENCY_MAP = {
    ".NS": "₹", ".BO": "₹",  # India
    ".L": "£",  # UK
    ".DE": "€", ".PA": "€", ".AS": "€", ".MC": "€", ".MI": "€",  # Europe
    ".T": "¥",  # Japan
    ".HK": "HK$",  # Hong Kong
    ".AX": "A$",  # Australia
    ".KS": "₩",  # Korea
    ".SI": "S$",  # Singapore
    ".SW": "CHF",  # Switzerland
    ".TO": "C$",  # Canada
    ".SA": "R$",  # Brazil
}

# Stock names
STOCK_NAMES = {
    "AAPL": "Apple Inc", "MSFT": "Microsoft", "GOOGL": "Alphabet", "NVDA": "NVIDIA",
    "TSLA": "Tesla", "META": "Meta Platforms", "AMZN": "Amazon", "AMD": "AMD",
    "RELIANCE.NS": "Reliance Industries", "TCS.NS": "Tata Consultancy",
    "INFY.NS": "Infosys", "HDFCBANK.NS": "HDFC Bank", "ICICIBANK.NS": "ICICI Bank",
    "HSBA.L": "HSBC Holdings", "BP.L": "BP plc", "SHEL.L": "Shell",
    "SAP.DE": "SAP SE", "SIE.DE": "Siemens", "OR.PA": "L'Oreal",
    "7203.T": "Toyota Motor", "6758.T": "Sony Group", "9984.T": "SoftBank",
    "BHP.AX": "BHP Group", "CBA.AX": "Commonwealth Bank", "CSL.AX": "CSL Limited",
    "0700.HK": "Tencent", "9988.HK": "Alibaba", "3690.HK": "Meituan",
    "005930.KS": "Samsung Electronics", "D05.SI": "DBS Group", "NESN.SW": "Nestle",
    "RY.TO": "Royal Bank of Canada", "TD.TO": "Toronto-Dominion",
    "PETR4.SA": "Petrobras", "VALE3.SA": "Vale", "ASML.AS": "ASML Holding",
    "SAN.MC": "Banco Santander", "ENI.MI": "Eni SpA",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "SPY": "SPDR S&P 500", "QQQ": "Invesco QQQ", "GLD": "SPDR Gold",
    "EURUSD=X": "EUR/USD", "GC=F": "Gold Futures", "CL=F": "Crude Oil",
}

# Expanded Sector Map - v5.8.4
SECTOR_MAP = {
    # US Tech
    "AAPL": ("Technology", "Consumer Electronics"),
    "MSFT": ("Technology", "Software - Infrastructure"),
    "GOOGL": ("Technology", "Internet Content & Information"),
    "NVDA": ("Technology", "Semiconductors"),
    "TSLA": ("Consumer Cyclical", "Auto Manufacturers"),
    "META": ("Technology", "Internet Content & Information"),
    "AMZN": ("Consumer Cyclical", "Internet Retail"),
    "AMD": ("Technology", "Semiconductors"),
    "NFLX": ("Communication Services", "Entertainment"),
    "INTC": ("Technology", "Semiconductors"),
    # US Finance
    "JPM": ("Financial Services", "Banks - Diversified"),
    "V": ("Financial Services", "Credit Services"),
    "WMT": ("Consumer Defensive", "Discount Stores"),
    "JNJ": ("Healthcare", "Drug Manufacturers"),
    "PG": ("Consumer Defensive", "Household Products"),
    "DIS": ("Communication Services", "Entertainment"),
    # India
    "RELIANCE.NS": ("Energy", "Oil & Gas"),
    "TCS.NS": ("Technology", "IT Services"),
    "INFY.NS": ("Technology", "IT Services"),
    "HDFCBANK.NS": ("Financial Services", "Banks - Regional"),
    "ICICIBANK.NS": ("Financial Services", "Banks - Regional"),
    "HINDUNILVR.NS": ("Consumer Defensive", "Household Products"),
    "WIPRO.NS": ("Technology", "IT Services"),
    "BHARTIARTL.NS": ("Communication Services", "Telecom"),
    "ITC.NS": ("Consumer Defensive", "Tobacco"),
    "SBIN.NS": ("Financial Services", "Banks - Regional"),
    "LT.NS": ("Industrials", "Engineering & Construction"),
    # UK
    "HSBA.L": ("Financial Services", "Banks - Diversified"),
    "BP.L": ("Energy", "Oil & Gas"),
    "SHEL.L": ("Energy", "Oil & Gas"),
    "AZN.L": ("Healthcare", "Drug Manufacturers"),
    "GSK.L": ("Healthcare", "Drug Manufacturers"),
    "VOD.L": ("Communication Services", "Telecom"),
    # Germany
    "SAP.DE": ("Technology", "Software - Application"),
    "SIE.DE": ("Industrials", "Specialty Industrial Machinery"),
    "VOW3.DE": ("Consumer Cyclical", "Auto Manufacturers"),
    "ALV.DE": ("Financial Services", "Insurance"),
    "BMW.DE": ("Consumer Cyclical", "Auto Manufacturers"),
    # France
    "OR.PA": ("Consumer Defensive", "Household Products"),
    "MC.PA": ("Consumer Cyclical", "Luxury Goods"),
    "AIR.PA": ("Industrials", "Aerospace & Defense"),
    "TTE.PA": ("Energy", "Oil & Gas"),
    # Japan
    "7203.T": ("Consumer Cyclical", "Auto Manufacturers"),
    "6758.T": ("Technology", "Consumer Electronics"),
    "9984.T": ("Technology", "Internet Content & Information"),
    "7974.T": ("Communication Services", "Electronic Gaming"),
    # Hong Kong
    "0700.HK": ("Technology", "Internet Content & Information"),
    "9988.HK": ("Consumer Cyclical", "Internet Retail"),
    "3690.HK": ("Consumer Cyclical", "Internet Retail"),
    # Australia
    "BHP.AX": ("Basic Materials", "Mining"),
    "CBA.AX": ("Financial Services", "Banks - Diversified"),
    "CSL.AX": ("Healthcare", "Biotechnology"),
    # Brazil
    "PETR4.SA": ("Energy", "Oil & Gas"),
    "VALE3.SA": ("Basic Materials", "Mining"),
    "ITUB4.SA": ("Financial Services", "Banks - Regional"),
    "B3SA3.SA": ("Financial Services", "Capital Markets"),
    # Canada
    "RY.TO": ("Financial Services", "Banks - Diversified"),
    "TD.TO": ("Financial Services", "Banks - Diversified"),
    "BMO.TO": ("Financial Services", "Banks - Diversified"),
    "BNS.TO": ("Financial Services", "Banks - Diversified"),
    "SHOP.TO": ("Technology", "E-Commerce"),
    "ENB.TO": ("Energy", "Oil & Gas Pipelines"),
    "CNR.TO": ("Industrials", "Railroads"),
    "BCE.TO": ("Communication Services", "Telecom"),
    # ETF
    "SPY": ("ETF", "S&P 500 Index"),
    "QQQ": ("ETF", "Nasdaq 100 Index"),
    "GLD": ("ETF", "Gold"),
    "DIA": ("ETF", "Dow Jones Index"),
    # Crypto
    "BTC-USD": ("Cryptocurrency", "Digital Currency"),
    "ETH-USD": ("Cryptocurrency", "Smart Contracts"),
    "SOL-USD": ("Cryptocurrency", "Smart Contracts"),
    # Forex
    "EURUSD=X": ("Forex", "Major Pair"),
    "GBPUSD=X": ("Forex", "Major Pair"),
    # Commodities
    "GC=F": ("Commodities", "Precious Metals"),
    "CL=F": ("Commodities", "Energy"),
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_seed(text: str) -> int:
    """Generate a deterministic seed from text."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)

def get_currency(symbol: str) -> str:
    symbol_upper = symbol.upper()
    for suffix, currency in CURRENCY_MAP.items():
        if suffix in symbol_upper:
            return currency
    return "$"

def get_name(symbol: str) -> str:
    return STOCK_NAMES.get(symbol.upper(), symbol.split('.')[0].upper())

def get_base_price(symbol: str) -> float:
    return BASE_PRICES.get(symbol.upper(), 100.0)

def get_sector_industry(symbol: str) -> tuple:
    """Get sector and industry for a symbol - v5.8.4 expanded mapping"""
    symbol_upper = symbol.upper()
    
    # Check explicit mapping first
    if symbol_upper in SECTOR_MAP:
        return SECTOR_MAP[symbol_upper]
    
    # Infer from symbol suffix/pattern
    if '-USD' in symbol_upper:
        return ("Cryptocurrency", "Digital Currency")
    if '=F' in symbol_upper:
        return ("Commodities", "Futures")
    if '=X' in symbol_upper:
        return ("Forex", "Currency Pair")
    if symbol_upper in ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'GLD', 'SLV']:
        return ("ETF", "Index Fund")
    
    # Default by suffix
    suffix_sectors = {
        '.NS': ("Technology", "Indian IT"),
        '.BO': ("Financial Services", "Indian Markets"),
        '.L': ("Financial Services", "UK Markets"),
        '.DE': ("Industrials", "German Industry"),
        '.PA': ("Consumer Goods", "French Markets"),
        '.T': ("Consumer Cyclical", "Japanese Markets"),
        '.HK': ("Technology", "Chinese Tech"),
        '.AX': ("Basic Materials", "Australian Mining"),
        '.SA': ("Energy", "Brazilian Energy"),
        '.TO': ("Financial Services", "Canadian Banks"),
        '.KS': ("Technology", "Korean Tech"),
        '.SI': ("Financial Services", "Singapore Finance"),
        '.SW': ("Consumer Defensive", "Swiss Markets"),
        '.AS': ("Technology", "Dutch Tech"),
        '.MC': ("Financial Services", "Spanish Banks"),
        '.MI': ("Energy", "Italian Markets"),
    }
    
    for suffix, sector_tuple in suffix_sectors.items():
        if suffix in symbol_upper:
            return sector_tuple
    
    return ("Technology", "General")


# ============================================================
# DATA GENERATORS
# ============================================================

def generate_quote(symbol: str) -> dict:
    """Generate quote data."""
    symbol = symbol.upper()
    base_price = get_base_price(symbol)
    
    # v5.8.4: Include time bucket for evolving prices
    time_bucket = int(datetime.now().timestamp() / 300)  # 5-minute buckets
    seed = get_seed(symbol) + time_bucket
    random.seed(seed)
    
    price = base_price * random.uniform(0.97, 1.03)
    change = price - base_price
    change_pct = (change / base_price) * 100
    
    return {
        "symbol": symbol,
        "name": get_name(symbol),
        "price": round(price, 2),
        "change": round(change, 2),
        "changePercent": round(change_pct, 2),
        "volume": random.randint(1000000, 50000000),
        "high": round(price * 1.02, 2),
        "low": round(price * 0.98, 2),
        "open": round(base_price, 2),
        "previousClose": round(base_price, 2),
        "currency": get_currency(symbol),
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


def generate_signals(symbol: str) -> dict:
    """Generate technical signals."""
    symbol = symbol.upper()
    price = get_base_price(symbol)
    
    time_bucket = int(datetime.now().timestamp() / 300)
    seed = get_seed(symbol) + time_bucket
    random.seed(seed)
    
    rsi = random.uniform(25, 75)
    macd = random.uniform(-2, 2)
    macd_signal = macd + random.uniform(-0.5, 0.5)
    sma_20 = price * random.uniform(0.97, 1.03)
    ema_12 = price * random.uniform(0.98, 1.02)
    vwap = price * random.uniform(0.99, 1.01)
    atr = price * random.uniform(0.01, 0.03)
    
    # Generate signal based on RSI
    if rsi < 30:
        signal = "STRONG BUY"
        confidence = random.randint(75, 95)
    elif rsi < 45:
        signal = "BUY"
        confidence = random.randint(60, 80)
    elif rsi > 70:
        signal = "STRONG SELL"
        confidence = random.randint(75, 95)
    elif rsi > 55:
        signal = "SELL"
        confidence = random.randint(60, 80)
    else:
        signal = "HOLD"
        confidence = random.randint(50, 70)
    
    risk_score = random.randint(20, 80)
    
    return {
        "symbol": symbol,
        "signal": signal,
        "overall_signal": signal,
        "confidence": confidence,
        "trend": "Bullish" if rsi < 45 else "Bearish" if rsi > 55 else "Neutral",
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "macd_signal": round(macd_signal, 4),
        "macd_histogram": round(macd - macd_signal, 4),
        "sma_20": round(sma_20, 2),
        "ema_12": round(ema_12, 2),
        "vwap": round(vwap, 2),
        "atr": round(atr, 2),
        "bollinger": {
            "upper": round(sma_20 + price * 0.04, 2),
            "middle": round(sma_20, 2),
            "lower": round(sma_20 - price * 0.04, 2)
        },
        "risk_score": risk_score,
        "risk_level": "Low" if risk_score < 40 else "Medium" if risk_score < 70 else "High",
        "support": round(price * 0.95, 2),
        "resistance": round(price * 1.05, 2),
        "currency": get_currency(symbol),
        "price": round(price, 2),
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


def generate_candles(symbol: str, interval: str = "15m", count: int = 100) -> list:
    """
    Generate candle data - v5.8.4 FIX
    Now includes INTERVAL in the seed so different timeframes produce different charts!
    Also includes time_bucket for charts that evolve over time.
    """
    symbol = symbol.upper()
    base_price = get_base_price(symbol)
    
    interval_minutes = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30, 
        "1h": 60, "4h": 240, "1d": 1440, "1wk": 10080
    }.get(interval, 15)
    
    candles = []
    now = datetime.now()
    
    # v5.8.4 FIX: Include INTERVAL in the seed!
    # This ensures different timeframes produce different chart patterns
    time_bucket = int(now.timestamp() / 300)  # 5-minute buckets for time evolution
    seed_string = f"{symbol}_{interval}_{time_bucket}"
    seed = get_seed(seed_string)
    random.seed(seed)
    
    logger.info(f"[Candles] Generating {count} candles for {symbol} @ {interval} (seed: {seed})")
    
    # Start with a varied initial price
    current_price = base_price * (1 + random.uniform(-0.05, 0.05))
    
    # Generate unique volatility per symbol+interval combination
    symbol_volatility = 0.003 + (seed % 100) / 10000  # 0.003 to 0.013
    
    for i in range(count):
        timestamp = now - timedelta(minutes=(count - i) * interval_minutes)
        
        # Varied price movement with slight trend
        trend_bias = random.uniform(-0.001, 0.001)
        change = (random.uniform(-symbol_volatility, symbol_volatility) + trend_bias) * current_price
        current_price = max(current_price + change, base_price * 0.7)
        current_price = min(current_price, base_price * 1.3)
        
        # Generate OHLC with variation
        open_p = current_price * random.uniform(0.997, 1.003)
        close_p = current_price * random.uniform(0.997, 1.003)
        high_p = max(open_p, close_p) * random.uniform(1.002, 1.015)
        low_p = min(open_p, close_p) * random.uniform(0.985, 0.998)
        
        candles.append({
            "timestamp": int(timestamp.timestamp() * 1000),  # Milliseconds for JS
            "date": timestamp.isoformat(),  # ISO string for frontend fallback
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": random.randint(100000, 5000000)
        })
    
    return candles


def generate_financials(symbol: str) -> dict:
    """Generate financial data."""
    symbol = symbol.upper()
    price = get_base_price(symbol)
    currency = get_currency(symbol)
    sector, industry = get_sector_industry(symbol)
    
    seed = get_seed(symbol)
    random.seed(seed)
    
    market_cap = price * random.randint(1000000, 10000000000)
    revenue = market_cap * random.uniform(0.1, 0.5)
    net_income = revenue * random.uniform(0.05, 0.25)
    
    return {
        "symbol": symbol,
        "name": get_name(symbol),
        "currency": currency,
        "sector": sector,
        "industry": industry,
        "market_cap": market_cap,
        "market_cap_formatted": f"{market_cap/1e9:.2f}B" if market_cap > 1e9 else f"{market_cap/1e6:.2f}M",
        "pe_ratio": round(price / (net_income / market_cap * price) if net_income > 0 else 0, 2),
        "eps": round(net_income / (market_cap / price), 2),
        "revenue": revenue,
        "revenue_formatted": f"{revenue/1e9:.2f}B" if revenue > 1e9 else f"{revenue/1e6:.2f}M",
        "net_income": net_income,
        "profit_margin": round(net_income / revenue * 100, 2) if revenue > 0 else 0,
        "dividend_yield": round(random.uniform(0, 3), 2),
        "beta": round(random.uniform(0.5, 2.0), 2),
        "52_week_high": round(price * 1.15, 2),
        "52_week_low": round(price * 0.85, 2),
        "source": "DEMO"
    }


# ============================================================
# REQUEST MODELS
# ============================================================

class GenAIRequest(BaseModel):
    question: str
    symbol: Optional[str] = "AAPL"
    price: Optional[float] = None
    currency: Optional[str] = "$"
    rsi: Optional[float] = None
    signal: Optional[str] = "HOLD"
    trader_style: Optional[str] = "swing"
    trader_type: Optional[str] = None
    market: Optional[str] = None


# ============================================================
# QUOTE ENDPOINTS
# ============================================================

@app.get("/api/v4/quote/{symbol}")
async def get_quote(symbol: str):
    quote = generate_quote(symbol)
    return {"success": True, **quote}

@app.get("/api/v4/quotes")
async def get_quotes(symbols: str = Query(...)):
    symbol_list = [s.strip() for s in symbols.split(",")]
    results = {}
    for sym in symbol_list:
        results[sym.upper()] = generate_quote(sym)
    return {"success": True, "results": results, "asOf": datetime.now().isoformat()}

@app.get("/api/v4/signals/{symbol}")
async def get_signals(symbol: str):
    signals = generate_signals(symbol)
    return {"success": True, **signals}


# ============================================================
# HISTORY / CANDLES ENDPOINTS
# ============================================================

@app.get("/api/v4/history/{symbol}")
async def get_history(symbol: str, period: str = "5d", interval: str = "15m"):
    period_map = {"1d": 100, "5d": 100, "1mo": 200, "3mo": 300, "1y": 365}
    count = period_map.get(period, 100)
    candles = generate_candles(symbol, interval, count)
    logger.info(f"[History] {symbol} @ {interval}: Generated {len(candles)} candles")
    return {
        "success": True,
        "candles": candles,
        "interval": interval,
        "count": len(candles),
        "source": "DEMO"
    }

@app.get("/api/v4/candles/{symbol}")
async def get_candles(symbol: str, interval: str = "15m", lookback: int = 100):
    candles = generate_candles(symbol, interval, lookback)
    return {
        "success": True,
        "candles": candles,
        "interval": interval,
        "count": len(candles)
    }


# ============================================================
# FINANCIALS
# ============================================================

@app.get("/api/v4/financials/{symbol}")
async def get_financials(symbol: str):
    fin = generate_financials(symbol)
    return {
        "success": True,
        "symbol": symbol.upper(),
        "name": fin["name"],
        "currency": fin["currency"],
        "financials": fin,
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# TOP MOVERS
# ============================================================

@app.get("/api/v4/top-movers/{market}")
async def get_top_movers(market: str):
    # All 21 markets matching frontend MARKETS list
    market_symbols = {
        "US": ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"],
        "India": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS"],
        "UK": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L", "VOD.L"],
        "Germany": ["SAP.DE", "SIE.DE", "ALV.DE", "BMW.DE", "VOW3.DE"],
        "France": ["OR.PA", "MC.PA", "AIR.PA", "TTE.PA"],
        "Japan": ["7203.T", "6758.T", "9984.T", "7974.T"],
        "China": ["9988.HK", "0700.HK", "9618.HK", "1810.HK"],
        "HongKong": ["0005.HK", "0011.HK", "0388.HK", "2318.HK", "1299.HK"],
        "Australia": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX"],
        "Canada": ["RY.TO", "TD.TO", "SHOP.TO", "ENB.TO", "CNR.TO"],
        "Brazil": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "B3SA3.SA", "WEGE3.SA"],
        "Korea": ["005930.KS", "000660.KS", "035420.KS", "005380.KS"],
        "Singapore": ["D05.SI", "O39.SI", "U11.SI", "Z74.SI"],
        "Switzerland": ["NESN.SW", "NOVN.SW", "ROG.SW", "UBSG.SW"],
        "Netherlands": ["ASML.AS", "INGA.AS", "PHIA.AS", "ADYEN.AS"],
        "Spain": ["SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC"],
        "Italy": ["ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI"],
        "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD"],
        "ETF": ["SPY", "QQQ", "DIA", "IWM", "GLD", "VOO"],
        "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"],
        "Commodities": ["GC=F", "CL=F", "SI=F", "NG=F"],
    }
    
    symbols = market_symbols.get(market, market_symbols["US"])
    
    movers = []
    for sym in symbols:
        seed = get_seed(sym) + int(datetime.now().timestamp() / 300)
        random.seed(seed)
        change = round(random.uniform(-5, 5), 2)
        movers.append({
            "symbol": sym,
            "fullSymbol": sym,
            "name": get_name(sym),
            "change": change,
            "changePercent": change,
            "price": get_base_price(sym),
            "currency": get_currency(sym)
        })
    
    # Sort by absolute change
    movers.sort(key=lambda x: abs(x["change"]), reverse=True)
    
    return {
        "success": True,
        "market": market,
        "movers": movers[:8],
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# SENTIMENT ENDPOINTS
# ============================================================

@app.get("/api/sentiment/reddit/{symbol}")
async def get_reddit_sentiment(symbol: str):
    seed = get_seed(symbol.upper()) + int(datetime.now().timestamp() / 3600)
    random.seed(seed)
    
    bullish = random.randint(30, 70)
    bearish = 100 - bullish
    
    return {
        "success": True,
        "symbol": symbol.upper(),
        "mentions": random.randint(50, 500),
        "bullish_percent": bullish,
        "bearish_percent": bearish,
        "sentiment": {
            "bullish": bullish,
            "bearish": bearish,
            "label": "Bullish" if bullish > 55 else "Bearish" if bullish < 45 else "Neutral"
        },
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/sentiment/twitter/{symbol}")
async def get_twitter_sentiment(symbol: str):
    seed = get_seed(symbol.upper()) + int(datetime.now().timestamp() / 3600)
    random.seed(seed)
    
    bullish = random.randint(35, 65)
    
    return {
        "success": True,
        "symbol": symbol.upper(),
        "bullish_percent": bullish,
        "bearish_percent": 100 - bullish,
        "mentions": random.randint(100, 1000),
        "source": "DEMO"
    }


# ============================================================
# NEWS ENDPOINT
# ============================================================

@app.get("/api/news/{symbol}")
async def get_news(symbol: str):
    symbol = symbol.upper()
    name = get_name(symbol)
    
    headlines = [
        f"{name} reports strong quarterly earnings, beats expectations",
        f"Analysts upgrade {name} stock to 'Outperform'",
        f"{name} announces new product line, shares rise",
        f"Market volatility impacts {name} trading volume",
        f"{name} expands into new markets, analysts bullish",
        f"Institutional investors increase {name} holdings",
    ]
    
    articles = []
    for i, headline in enumerate(headlines[:4]):
        articles.append({
            "title": headline,
            "source": random.choice(["Reuters", "Bloomberg", "CNBC", "WSJ"]),
            "url": f"https://news.example.com/{symbol.lower()}/{i}",
            "publishedAt": (datetime.now() - timedelta(hours=i*2)).isoformat(),
            "sentiment": random.choice(["positive", "neutral", "negative"])
        })
    
    return {
        "success": True,
        "symbol": symbol,
        "articles": articles,
        "source": "DEMO"
    }


# ============================================================
# SCREENER ENDPOINT
# ============================================================

@app.get("/api/screener/universe")
async def get_screener_universe():
    categories = {
        "US Tech": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN", "AMD"],
        "India": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS"],
        "UK": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L", "VOD.L"],
        "Germany": ["SAP.DE", "SIE.DE", "VOW3.DE", "ALV.DE", "BMW.DE"],
        "France": ["OR.PA", "MC.PA", "AIR.PA", "TTE.PA"],
        "Japan": ["7203.T", "6758.T", "9984.T", "7974.T"],
        "Australia": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX"],
        "Hong Kong": ["0700.HK", "9988.HK", "3690.HK"],
        "Brazil": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "B3SA3.SA"],
        "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
        "ETF": ["SPY", "QQQ", "DIA", "GLD"],
    }
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "categories": list(categories.keys()),
        "total_stocks": sum(len(v) for v in categories.values()),
        "source": "DEMO"
    }
    
    for category, symbols in categories.items():
        stocks = []
        for sym in symbols:
            signals = generate_signals(sym)
            quote = generate_quote(sym)
            stocks.append({
                "symbol": sym,
                "name": get_name(sym),
                "price": quote["price"],
                "change_percent": quote["changePercent"],
                "rsi": signals["rsi"],
                "signal": signals["signal"],
                "currency": get_currency(sym),
                "dataQuality": "DEMO"
            })
        result[category] = stocks
    
    return result


# ============================================================
# GENAI ENDPOINT
# ============================================================

@app.post("/api/genai/query")
async def genai_query(request: GenAIRequest):
    symbol = (request.symbol or "AAPL").upper()
    price = request.price or get_base_price(symbol)
    currency = request.currency or get_currency(symbol)
    rsi = request.rsi or 50
    signal = request.signal or "HOLD"
    style = request.trader_type or request.trader_style or "swing"
    
    style_advice = {
        "day": "For day trading, focus on intraday momentum and volume spikes.",
        "swing": "For swing trading, look at multi-day trends and support/resistance levels.",
        "position": "For position trading, consider fundamental analysis and long-term trends.",
        "scalper": "For scalping, watch for micro-movements and tight spreads."
    }
    
    base_advice = style_advice.get(style.lower(), style_advice["swing"])
    
    if rsi < 30:
        rsi_advice = f"RSI at {rsi:.1f} indicates oversold conditions - potential buy opportunity."
    elif rsi > 70:
        rsi_advice = f"RSI at {rsi:.1f} indicates overbought conditions - consider taking profits."
    else:
        rsi_advice = f"RSI at {rsi:.1f} is neutral - wait for clearer signals."
    
    response = f"""**{symbol} Analysis** (Current: {currency}{price:.2f})

{base_advice}

**Technical View:**
{rsi_advice}
Current signal: {signal}

**Key Levels:**
• Support: {currency}{price * 0.95:.2f}
• Resistance: {currency}{price * 1.05:.2f}

*This is AI-generated analysis for educational purposes. Always do your own research.*"""
    
    return {
        "success": True,
        "answer": response,
        "response": response,
        "symbol": symbol,
        "source": "AI"
    }


# ============================================================
# HEALTH ENDPOINT
# ============================================================

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": VERSION,
        "timestamp": datetime.now().isoformat(),
        "polling_recommendation": 60,
        "endpoints": [
            "/api/v4/quote/{symbol}",
            "/api/v4/history/{symbol}",
            "/api/v4/signals/{symbol}",
            "/api/v4/financials/{symbol}",
            "/api/v4/top-movers/{market}",
            "/api/screener/universe",
            "/api/sentiment/reddit/{symbol}",
            "/api/news/{symbol}",
            "/api/genai/query",
        ],
        "demo_mode": True
    }


@app.get("/")
async def root():
    return {
        "name": "TraderAI Pro API",
        "version": VERSION,
        "status": "running",
        "docs": "/docs"
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting TraderAI Pro API v{VERSION} on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
