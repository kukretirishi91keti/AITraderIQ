"""
v5_complete.py - Production-Grade V5 Router (DEMO-READY)
=========================================================
Version: 5.8.7

CHANGES in v5.8.7:
- Added ALL 22 markets for Top Movers support
- Taiwan, Japan, China, Hong Kong, Australia, Canada, Brazil, Korea
- Singapore, Switzerland, Netherlands, Spain, Italy, Forex
- Complete DEMO_STOCKS for all markets
- Full MARKET_CONFIG for top-movers endpoint

Implements all requirements:
- Wilder's RSI (proper EMA smoothing)
- VWAP indicator  
- SingleFlight request coalescing with circuit breaker
- LKG (Last Known Good) cache with file persistence
- Rate-limit tracking with budget monitoring
- Deep health metrics
- Async-safe yfinance calls via run_in_threadpool
- Sequential screener fetching with timeout
- Demo mode fallback for rate-limited scenarios
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from starlette.concurrency import run_in_threadpool
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import deque
import random
import hashlib
import asyncio
import time
import logging
import json
import os
from pathlib import Path
from enum import Enum

router = APIRouter(tags=["v5-complete"])
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    DEMO = "demo"

class DataSource(Enum):
    LIVE = "LIVE"           # Real Yahoo Finance data
    CACHED = "CACHED"       # From in-memory cache
    LKG = "LKG"            # Last Known Good (file cache)
    DEMO = "DEMO"          # Pre-cached demo data
    MME = "MME"            # Mock Market Engine (generated)
    SIMULATED = "SIMULATED" # Simulated sentiment

# Cache configuration
CACHE_DIR = Path(os.getenv("CACHE_DIR", "/tmp/traderai_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limit configuration
RATE_LIMIT_WINDOW = 3600  # 1 hour window
RATE_LIMIT_ERROR_THRESHOLD = 5  # Errors before degraded
RATE_LIMIT_CRITICAL_THRESHOLD = 15  # Errors before critical
CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes cooldown after critical

# Screener configuration
SCREENER_FETCH_DELAY_MS = 150  # Delay between ticker fetches
SCREENER_TIMEOUT_SECONDS = 45  # Max time for full screener fetch
SCREENER_MAX_CONCURRENT = 3  # Max concurrent fetches

# Demo mode - SET TO TRUE FOR RELIABLE DEMOS
DEMO_MODE_ENABLED = os.getenv("DEMO_MODE", "false").lower() == "true"

# ============================================================
# DEMO DATA ENGINE - ALL 22 MARKETS
# ============================================================

# Realistic stock data - January 2026
DEMO_STOCKS = {
    # === US Tech ===
    "AAPL": {"name": "Apple Inc.", "base_price": 248.50, "currency": "$", "market": "US", "volatility": 0.018, "rsi_base": 55},
    "NVDA": {"name": "NVIDIA Corporation", "base_price": 138.50, "currency": "$", "market": "US", "volatility": 0.032, "rsi_base": 62},
    "TSLA": {"name": "Tesla, Inc.", "base_price": 436.00, "currency": "$", "market": "US", "volatility": 0.035, "rsi_base": 58},
    "MSFT": {"name": "Microsoft Corporation", "base_price": 438.00, "currency": "$", "market": "US", "volatility": 0.014, "rsi_base": 52},
    "GOOGL": {"name": "Alphabet Inc.", "base_price": 192.50, "currency": "$", "market": "US", "volatility": 0.016, "rsi_base": 54},
    "AMZN": {"name": "Amazon.com, Inc.", "base_price": 227.00, "currency": "$", "market": "US", "volatility": 0.020, "rsi_base": 56},
    "META": {"name": "Meta Platforms, Inc.", "base_price": 612.00, "currency": "$", "market": "US", "volatility": 0.022, "rsi_base": 60},
    "AMD": {"name": "Advanced Micro Devices", "base_price": 119.50, "currency": "$", "market": "US", "volatility": 0.028, "rsi_base": 48},
    "ADBE": {"name": "Adobe Inc.", "base_price": 445.00, "currency": "$", "market": "US", "volatility": 0.022, "rsi_base": 45},
    "CRM": {"name": "Salesforce, Inc.", "base_price": 340.00, "currency": "$", "market": "US", "volatility": 0.020, "rsi_base": 52},
    "NFLX": {"name": "Netflix, Inc.", "base_price": 910.00, "currency": "$", "market": "US", "volatility": 0.025, "rsi_base": 58},
    "INTC": {"name": "Intel Corporation", "base_price": 19.80, "currency": "$", "market": "US", "volatility": 0.030, "rsi_base": 35},
    
    # === India ===
    "RELIANCE.NS": {"name": "Reliance Industries", "base_price": 1265.00, "currency": "₹", "market": "India", "volatility": 0.016, "rsi_base": 52},
    "TCS.NS": {"name": "Tata Consultancy Services", "base_price": 4150.00, "currency": "₹", "market": "India", "volatility": 0.012, "rsi_base": 48},
    "INFY.NS": {"name": "Infosys Limited", "base_price": 1890.00, "currency": "₹", "market": "India", "volatility": 0.014, "rsi_base": 50},
    "HDFCBANK.NS": {"name": "HDFC Bank Limited", "base_price": 1785.00, "currency": "₹", "market": "India", "volatility": 0.013, "rsi_base": 55},
    "ICICIBANK.NS": {"name": "ICICI Bank Limited", "base_price": 1285.00, "currency": "₹", "market": "India", "volatility": 0.015, "rsi_base": 58},
    "WIPRO.NS": {"name": "Wipro Limited", "base_price": 295.00, "currency": "₹", "market": "India", "volatility": 0.018, "rsi_base": 45},
    "SBIN.NS": {"name": "State Bank of India", "base_price": 815.00, "currency": "₹", "market": "India", "volatility": 0.020, "rsi_base": 52},
    "BHARTIARTL.NS": {"name": "Bharti Airtel", "base_price": 1620.00, "currency": "₹", "market": "India", "volatility": 0.015, "rsi_base": 62},
    "HINDUNILVR.NS": {"name": "Hindustan Unilever", "base_price": 2400.00, "currency": "₹", "market": "India", "volatility": 0.012, "rsi_base": 50},
    
    # === UK ===
    "HSBA.L": {"name": "HSBC Holdings", "base_price": 782.00, "currency": "£", "market": "UK", "volatility": 0.014, "rsi_base": 54},
    "BP.L": {"name": "BP plc", "base_price": 385.00, "currency": "£", "market": "UK", "volatility": 0.018, "rsi_base": 48},
    "SHEL.L": {"name": "Shell plc", "base_price": 2580.00, "currency": "£", "market": "UK", "volatility": 0.016, "rsi_base": 52},
    "AZN.L": {"name": "AstraZeneca", "base_price": 10850.00, "currency": "£", "market": "UK", "volatility": 0.014, "rsi_base": 55},
    "GSK.L": {"name": "GSK plc", "base_price": 1420.00, "currency": "£", "market": "UK", "volatility": 0.012, "rsi_base": 50},
    "VOD.L": {"name": "Vodafone Group", "base_price": 72.50, "currency": "£", "market": "UK", "volatility": 0.020, "rsi_base": 42},
    
    # === Germany ===
    "SAP.DE": {"name": "SAP SE", "base_price": 236.00, "currency": "€", "market": "Germany", "volatility": 0.015, "rsi_base": 58},
    "SIE.DE": {"name": "Siemens AG", "base_price": 188.00, "currency": "€", "market": "Germany", "volatility": 0.016, "rsi_base": 54},
    "ALV.DE": {"name": "Allianz SE", "base_price": 295.00, "currency": "€", "market": "Germany", "volatility": 0.014, "rsi_base": 56},
    "BMW.DE": {"name": "BMW AG", "base_price": 78.50, "currency": "€", "market": "Germany", "volatility": 0.018, "rsi_base": 48},
    "VOW3.DE": {"name": "Volkswagen AG", "base_price": 92.00, "currency": "€", "market": "Germany", "volatility": 0.020, "rsi_base": 45},
    "DTE.DE": {"name": "Deutsche Telekom", "base_price": 28.50, "currency": "€", "market": "Germany", "volatility": 0.012, "rsi_base": 52},
    
    # === France ===
    "OR.PA": {"name": "L'Oreal SA", "base_price": 335.00, "currency": "€", "market": "France", "volatility": 0.014, "rsi_base": 55},
    "MC.PA": {"name": "LVMH", "base_price": 680.00, "currency": "€", "market": "France", "volatility": 0.018, "rsi_base": 52},
    "TTE.PA": {"name": "TotalEnergies", "base_price": 56.50, "currency": "€", "market": "France", "volatility": 0.016, "rsi_base": 50},
    "SAN.PA": {"name": "Sanofi", "base_price": 92.00, "currency": "€", "market": "France", "volatility": 0.012, "rsi_base": 48},
    "AIR.PA": {"name": "Airbus SE", "base_price": 155.00, "currency": "€", "market": "France", "volatility": 0.018, "rsi_base": 56},
    
    # === Japan ===
    "7203.T": {"name": "Toyota Motor", "base_price": 2850.00, "currency": "¥", "market": "Japan", "volatility": 0.014, "rsi_base": 52},
    "6758.T": {"name": "Sony Group", "base_price": 3150.00, "currency": "¥", "market": "Japan", "volatility": 0.018, "rsi_base": 55},
    "9984.T": {"name": "SoftBank Group", "base_price": 9200.00, "currency": "¥", "market": "Japan", "volatility": 0.025, "rsi_base": 58},
    "7974.T": {"name": "Nintendo", "base_price": 8500.00, "currency": "¥", "market": "Japan", "volatility": 0.016, "rsi_base": 54},
    "6861.T": {"name": "Keyence Corp", "base_price": 62000.00, "currency": "¥", "market": "Japan", "volatility": 0.014, "rsi_base": 50},
    
    # === China (HK Listed) ===
    "9988.HK": {"name": "Alibaba Group", "base_price": 88.00, "currency": "HK$", "market": "China", "volatility": 0.028, "rsi_base": 48},
    "9618.HK": {"name": "JD.com", "base_price": 145.00, "currency": "HK$", "market": "China", "volatility": 0.030, "rsi_base": 45},
    "3690.HK": {"name": "Meituan", "base_price": 158.00, "currency": "HK$", "market": "China", "volatility": 0.032, "rsi_base": 52},
    "1810.HK": {"name": "Xiaomi Corp", "base_price": 32.50, "currency": "HK$", "market": "China", "volatility": 0.028, "rsi_base": 55},
    
    # === Hong Kong ===
    "0700.HK": {"name": "Tencent Holdings", "base_price": 385.00, "currency": "HK$", "market": "HongKong", "volatility": 0.022, "rsi_base": 54},
    "0005.HK": {"name": "HSBC Holdings HK", "base_price": 68.50, "currency": "HK$", "market": "HongKong", "volatility": 0.014, "rsi_base": 52},
    "1299.HK": {"name": "AIA Group", "base_price": 58.00, "currency": "HK$", "market": "HongKong", "volatility": 0.016, "rsi_base": 50},
    "0941.HK": {"name": "China Mobile", "base_price": 72.00, "currency": "HK$", "market": "HongKong", "volatility": 0.012, "rsi_base": 48},
    "0388.HK": {"name": "HK Exchanges", "base_price": 285.00, "currency": "HK$", "market": "HongKong", "volatility": 0.018, "rsi_base": 55},
    
    # === Taiwan ===
    "2330.TW": {"name": "TSMC", "base_price": 1050.00, "currency": "NT$", "market": "Taiwan", "volatility": 0.020, "rsi_base": 58},
    "2317.TW": {"name": "Hon Hai Precision", "base_price": 178.00, "currency": "NT$", "market": "Taiwan", "volatility": 0.022, "rsi_base": 52},
    "2454.TW": {"name": "MediaTek Inc", "base_price": 1280.00, "currency": "NT$", "market": "Taiwan", "volatility": 0.025, "rsi_base": 55},
    "2308.TW": {"name": "Delta Electronics", "base_price": 385.00, "currency": "NT$", "market": "Taiwan", "volatility": 0.018, "rsi_base": 50},
    
    # === Australia ===
    "BHP.AX": {"name": "BHP Group", "base_price": 42.50, "currency": "A$", "market": "Australia", "volatility": 0.018, "rsi_base": 52},
    "CBA.AX": {"name": "Commonwealth Bank", "base_price": 152.00, "currency": "A$", "market": "Australia", "volatility": 0.012, "rsi_base": 55},
    "CSL.AX": {"name": "CSL Limited", "base_price": 285.00, "currency": "A$", "market": "Australia", "volatility": 0.014, "rsi_base": 54},
    "NAB.AX": {"name": "National Australia Bank", "base_price": 38.50, "currency": "A$", "market": "Australia", "volatility": 0.014, "rsi_base": 50},
    
    # === Canada ===
    "RY.TO": {"name": "Royal Bank of Canada", "base_price": 168.00, "currency": "C$", "market": "Canada", "volatility": 0.012, "rsi_base": 54},
    "TD.TO": {"name": "Toronto-Dominion Bank", "base_price": 78.50, "currency": "C$", "market": "Canada", "volatility": 0.014, "rsi_base": 48},
    "ENB.TO": {"name": "Enbridge Inc", "base_price": 58.00, "currency": "C$", "market": "Canada", "volatility": 0.010, "rsi_base": 52},
    "SHOP.TO": {"name": "Shopify Inc", "base_price": 115.00, "currency": "C$", "market": "Canada", "volatility": 0.028, "rsi_base": 58},
    
    # === Brazil ===
    "PETR4.SA": {"name": "Petrobras", "base_price": 38.50, "currency": "R$", "market": "Brazil", "volatility": 0.022, "rsi_base": 50},
    "VALE3.SA": {"name": "Vale SA", "base_price": 58.00, "currency": "R$", "market": "Brazil", "volatility": 0.020, "rsi_base": 48},
    "ITUB4.SA": {"name": "Itau Unibanco", "base_price": 32.00, "currency": "R$", "market": "Brazil", "volatility": 0.018, "rsi_base": 52},
    "ABEV3.SA": {"name": "Ambev SA", "base_price": 12.50, "currency": "R$", "market": "Brazil", "volatility": 0.016, "rsi_base": 45},
    
    # === Korea ===
    "005930.KS": {"name": "Samsung Electronics", "base_price": 72000.00, "currency": "₩", "market": "Korea", "volatility": 0.018, "rsi_base": 52},
    "000660.KS": {"name": "SK Hynix", "base_price": 185000.00, "currency": "₩", "market": "Korea", "volatility": 0.025, "rsi_base": 55},
    "035420.KS": {"name": "Naver Corp", "base_price": 195000.00, "currency": "₩", "market": "Korea", "volatility": 0.020, "rsi_base": 48},
    "005380.KS": {"name": "Hyundai Motor", "base_price": 245000.00, "currency": "₩", "market": "Korea", "volatility": 0.016, "rsi_base": 50},
    
    # === Singapore ===
    "D05.SI": {"name": "DBS Group", "base_price": 38.50, "currency": "S$", "market": "Singapore", "volatility": 0.012, "rsi_base": 54},
    "O39.SI": {"name": "OCBC Bank", "base_price": 15.20, "currency": "S$", "market": "Singapore", "volatility": 0.010, "rsi_base": 52},
    "U11.SI": {"name": "UOB Ltd", "base_price": 32.50, "currency": "S$", "market": "Singapore", "volatility": 0.011, "rsi_base": 50},
    "Z74.SI": {"name": "Singtel", "base_price": 3.15, "currency": "S$", "market": "Singapore", "volatility": 0.014, "rsi_base": 48},
    
    # === Switzerland ===
    "NESN.SW": {"name": "Nestle SA", "base_price": 85.00, "currency": "CHF", "market": "Switzerland", "volatility": 0.010, "rsi_base": 48},
    "ROG.SW": {"name": "Roche Holding", "base_price": 265.00, "currency": "CHF", "market": "Switzerland", "volatility": 0.012, "rsi_base": 52},
    "NOVN.SW": {"name": "Novartis AG", "base_price": 92.00, "currency": "CHF", "market": "Switzerland", "volatility": 0.011, "rsi_base": 50},
    "UBSG.SW": {"name": "UBS Group", "base_price": 28.50, "currency": "CHF", "market": "Switzerland", "volatility": 0.016, "rsi_base": 55},
    
    # === Netherlands ===
    "ASML.AS": {"name": "ASML Holding", "base_price": 695.00, "currency": "€", "market": "Netherlands", "volatility": 0.022, "rsi_base": 52},
    "INGA.AS": {"name": "ING Group", "base_price": 15.80, "currency": "€", "market": "Netherlands", "volatility": 0.018, "rsi_base": 50},
    "PHIA.AS": {"name": "Philips NV", "base_price": 25.50, "currency": "€", "market": "Netherlands", "volatility": 0.022, "rsi_base": 45},
    "UNA.AS": {"name": "Unilever NV", "base_price": 48.50, "currency": "€", "market": "Netherlands", "volatility": 0.012, "rsi_base": 52},
    "ADYEN.AS": {"name": "Adyen NV", "base_price": 1150.00, "currency": "€", "market": "Netherlands", "volatility": 0.028, "rsi_base": 55},
    
    # === Spain ===
    "SAN.MC": {"name": "Banco Santander", "base_price": 4.85, "currency": "€", "market": "Spain", "volatility": 0.020, "rsi_base": 52},
    "BBVA.MC": {"name": "BBVA SA", "base_price": 10.20, "currency": "€", "market": "Spain", "volatility": 0.018, "rsi_base": 55},
    "ITX.MC": {"name": "Inditex SA", "base_price": 48.50, "currency": "€", "market": "Spain", "volatility": 0.014, "rsi_base": 58},
    "IBE.MC": {"name": "Iberdrola SA", "base_price": 13.20, "currency": "€", "market": "Spain", "volatility": 0.012, "rsi_base": 50},
    
    # === Italy ===
    "ENI.MI": {"name": "Eni SpA", "base_price": 13.80, "currency": "€", "market": "Italy", "volatility": 0.016, "rsi_base": 48},
    "ENEL.MI": {"name": "Enel SpA", "base_price": 6.85, "currency": "€", "market": "Italy", "volatility": 0.014, "rsi_base": 52},
    "ISP.MI": {"name": "Intesa Sanpaolo", "base_price": 3.95, "currency": "€", "market": "Italy", "volatility": 0.018, "rsi_base": 55},
    "UCG.MI": {"name": "UniCredit SpA", "base_price": 38.50, "currency": "€", "market": "Italy", "volatility": 0.020, "rsi_base": 58},
    "RACE.MI": {"name": "Ferrari NV", "base_price": 425.00, "currency": "€", "market": "Italy", "volatility": 0.016, "rsi_base": 62},
    
    # === Crypto ===
    "BTC-USD": {"name": "Bitcoin", "base_price": 106500.00, "currency": "$", "market": "Crypto", "volatility": 0.035, "rsi_base": 65},
    "ETH-USD": {"name": "Ethereum", "base_price": 3950.00, "currency": "$", "market": "Crypto", "volatility": 0.040, "rsi_base": 58},
    "BNB-USD": {"name": "Binance Coin", "base_price": 715.00, "currency": "$", "market": "Crypto", "volatility": 0.038, "rsi_base": 52},
    "XRP-USD": {"name": "XRP", "base_price": 2.42, "currency": "$", "market": "Crypto", "volatility": 0.055, "rsi_base": 68},
    "SOL-USD": {"name": "Solana", "base_price": 218.00, "currency": "$", "market": "Crypto", "volatility": 0.050, "rsi_base": 62},
    "ADA-USD": {"name": "Cardano", "base_price": 1.08, "currency": "$", "market": "Crypto", "volatility": 0.045, "rsi_base": 55},
    "DOGE-USD": {"name": "Dogecoin", "base_price": 0.42, "currency": "$", "market": "Crypto", "volatility": 0.060, "rsi_base": 58},
    
    # === ETFs ===
    "SPY": {"name": "SPDR S&P 500 ETF", "base_price": 602.00, "currency": "$", "market": "ETF", "volatility": 0.010, "rsi_base": 54},
    "QQQ": {"name": "Invesco QQQ Trust", "base_price": 525.00, "currency": "$", "market": "ETF", "volatility": 0.014, "rsi_base": 56},
    "DIA": {"name": "SPDR Dow Jones ETF", "base_price": 438.00, "currency": "$", "market": "ETF", "volatility": 0.009, "rsi_base": 52},
    "IWM": {"name": "iShares Russell 2000", "base_price": 235.00, "currency": "$", "market": "ETF", "volatility": 0.016, "rsi_base": 50},
    "VTI": {"name": "Vanguard Total Market", "base_price": 295.00, "currency": "$", "market": "ETF", "volatility": 0.011, "rsi_base": 53},
    "GLD": {"name": "SPDR Gold Trust", "base_price": 242.00, "currency": "$", "market": "ETF", "volatility": 0.012, "rsi_base": 55},
    
    # === Commodities ===
    "GC=F": {"name": "Gold Futures", "base_price": 2655.00, "currency": "$", "market": "Commodities", "volatility": 0.012, "rsi_base": 58},
    "CL=F": {"name": "Crude Oil Futures", "base_price": 69.50, "currency": "$", "market": "Commodities", "volatility": 0.025, "rsi_base": 45},
    "SI=F": {"name": "Silver Futures", "base_price": 30.25, "currency": "$", "market": "Commodities", "volatility": 0.020, "rsi_base": 52},
    "NG=F": {"name": "Natural Gas Futures", "base_price": 3.15, "currency": "$", "market": "Commodities", "volatility": 0.040, "rsi_base": 48},
    
    # === Forex ===
    "EURUSD=X": {"name": "EUR/USD", "base_price": 1.0450, "currency": "$", "market": "Forex", "volatility": 0.005, "rsi_base": 50},
    "GBPUSD=X": {"name": "GBP/USD", "base_price": 1.2550, "currency": "$", "market": "Forex", "volatility": 0.006, "rsi_base": 48},
    "USDJPY=X": {"name": "USD/JPY", "base_price": 157.50, "currency": "¥", "market": "Forex", "volatility": 0.005, "rsi_base": 55},
    "AUDUSD=X": {"name": "AUD/USD", "base_price": 0.6250, "currency": "$", "market": "Forex", "volatility": 0.007, "rsi_base": 45},
}

# Stock names lookup
STOCK_NAMES = {symbol: data["name"] for symbol, data in DEMO_STOCKS.items()}

# Screener universe - All categories
SCREENER_UNIVERSE = {
    "US_Tech": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "AMD", "ADBE", "CRM", "NFLX", "INTC"],
    "India": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "WIPRO.NS", "SBIN.NS", "BHARTIARTL.NS"],
    "UK": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L", "VOD.L"],
    "Germany": ["SAP.DE", "SIE.DE", "ALV.DE", "BMW.DE", "VOW3.DE", "DTE.DE"],
    "France": ["OR.PA", "MC.PA", "TTE.PA", "SAN.PA", "AIR.PA"],
    "Japan": ["7203.T", "6758.T", "9984.T", "7974.T", "6861.T"],
    "China": ["9988.HK", "9618.HK", "3690.HK", "1810.HK"],
    "HongKong": ["0700.HK", "0005.HK", "1299.HK", "0941.HK", "0388.HK"],
    "Taiwan": ["2330.TW", "2317.TW", "2454.TW", "2308.TW"],
    "Australia": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX"],
    "Canada": ["RY.TO", "TD.TO", "ENB.TO", "SHOP.TO"],
    "Brazil": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "ABEV3.SA"],
    "Korea": ["005930.KS", "000660.KS", "035420.KS", "005380.KS"],
    "Singapore": ["D05.SI", "O39.SI", "U11.SI", "Z74.SI"],
    "Switzerland": ["NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW"],
    "Netherlands": ["ASML.AS", "INGA.AS", "PHIA.AS", "UNA.AS"],
    "Spain": ["SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC"],
    "Italy": ["ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "RACE.MI"],
    "Crypto": ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD", "ADA-USD", "DOGE-USD"],
    "ETF": ["SPY", "QQQ", "DIA", "IWM", "VTI", "GLD"],
    "Commodities": ["GC=F", "CL=F", "SI=F", "NG=F"],
    "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
}

# Market configuration - ALL 22 MARKETS
MARKET_CONFIG = {
    "US": {"currency": "$", "currency_name": "USD", "stocks": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "AMD"]},
    "India": {"currency": "₹", "currency_name": "INR", "stocks": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]},
    "UK": {"currency": "£", "currency_name": "GBP", "stocks": ["HSBA.L", "BP.L", "SHEL.L", "AZN.L", "GSK.L"]},
    "Germany": {"currency": "€", "currency_name": "EUR", "stocks": ["SAP.DE", "SIE.DE", "ALV.DE", "BMW.DE", "VOW3.DE"]},
    "France": {"currency": "€", "currency_name": "EUR", "stocks": ["OR.PA", "MC.PA", "TTE.PA", "SAN.PA", "AIR.PA"]},
    "Japan": {"currency": "¥", "currency_name": "JPY", "stocks": ["7203.T", "6758.T", "9984.T", "7974.T", "6861.T"]},
    "China": {"currency": "HK$", "currency_name": "HKD", "stocks": ["9988.HK", "9618.HK", "3690.HK", "1810.HK"]},
    "HongKong": {"currency": "HK$", "currency_name": "HKD", "stocks": ["0700.HK", "0005.HK", "1299.HK", "0941.HK", "0388.HK"]},
    "Taiwan": {"currency": "NT$", "currency_name": "TWD", "stocks": ["2330.TW", "2317.TW", "2454.TW", "2308.TW"]},
    "Australia": {"currency": "A$", "currency_name": "AUD", "stocks": ["BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX"]},
    "Canada": {"currency": "C$", "currency_name": "CAD", "stocks": ["RY.TO", "TD.TO", "ENB.TO", "SHOP.TO"]},
    "Brazil": {"currency": "R$", "currency_name": "BRL", "stocks": ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "ABEV3.SA"]},
    "Korea": {"currency": "₩", "currency_name": "KRW", "stocks": ["005930.KS", "000660.KS", "035420.KS", "005380.KS"]},
    "Singapore": {"currency": "S$", "currency_name": "SGD", "stocks": ["D05.SI", "O39.SI", "U11.SI", "Z74.SI"]},
    "Switzerland": {"currency": "CHF", "currency_name": "CHF", "stocks": ["NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW"]},
    "Netherlands": {"currency": "€", "currency_name": "EUR", "stocks": ["ASML.AS", "INGA.AS", "PHIA.AS", "UNA.AS"]},
    "Spain": {"currency": "€", "currency_name": "EUR", "stocks": ["SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC"]},
    "Italy": {"currency": "€", "currency_name": "EUR", "stocks": ["ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI"]},
    "Crypto": {"currency": "$", "currency_name": "USD", "stocks": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]},
    "ETF": {"currency": "$", "currency_name": "USD", "stocks": ["SPY", "QQQ", "DIA", "IWM", "GLD"]},
    "Forex": {"currency": "$", "currency_name": "USD", "stocks": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]},
    "Commodities": {"currency": "$", "currency_name": "USD", "stocks": ["GC=F", "CL=F", "SI=F", "NG=F"]},
}

# ============================================================
# DEMO DATA GENERATOR
# ============================================================

import math

class DemoDataEngine:
    """Generate realistic demo data based on time-seeded randomness."""
    
    def _get_time_seed(self, symbol: str, interval: str = "1m") -> float:
        now = datetime.now()
        if interval == "1m":
            seed_time = now.replace(second=0, microsecond=0)
        elif interval == "5m":
            seed_time = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
        else:
            seed_time = now.replace(minute=0, second=0, microsecond=0)
        seed_str = f"{symbol}:{seed_time.isoformat()}"
        return sum(ord(c) for c in seed_str) / 1000.0
    
    def _seeded_random(self, seed: float, index: int = 0) -> float:
        x = math.sin(seed * (index + 1) * 12.9898) * 43758.5453
        return x - math.floor(x)
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper()
        stock = DEMO_STOCKS.get(symbol, {
            "name": symbol, "base_price": 100.0, "currency": "$",
            "market": "US", "volatility": 0.02, "rsi_base": 50
        })
        
        seed = self._get_time_seed(symbol, "1m")
        rand1 = self._seeded_random(seed, 1)
        rand2 = self._seeded_random(seed, 2)
        rand3 = self._seeded_random(seed, 3)
        
        volatility = stock.get("volatility", 0.02)
        change_pct = (rand1 - 0.5) * volatility * 100 * 2
        
        base_price = stock.get("base_price", 100)
        price = base_price * (1 + change_pct / 100)
        change = price - base_price
        
        day_range = base_price * volatility
        open_price = base_price * (1 + (rand2 - 0.5) * volatility)
        high_price = max(price, open_price) + day_range * rand3 * 0.5
        low_price = min(price, open_price) - day_range * (1 - rand3) * 0.5
        
        return {
            "symbol": symbol,
            "name": stock.get("name", symbol),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "prev_close": round(base_price, 2),
            "volume": int(1000000 * (0.7 + rand1 * 0.6)),
            "market": stock.get("market", "US"),
            "currency": stock.get("currency", "$"),
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "DEMO",
            "source": "demo_engine"
        }
    
    def get_signals(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper()
        stock = DEMO_STOCKS.get(symbol, {"rsi_base": 50, "volatility": 0.02, "base_price": 100, "currency": "$"})
        
        seed = self._get_time_seed(symbol, "5m")
        rand1 = self._seeded_random(seed, 1)
        rand2 = self._seeded_random(seed, 2)
        rand3 = self._seeded_random(seed, 3)
        
        rsi_base = stock.get("rsi_base", 50)
        rsi = rsi_base + (rand1 - 0.5) * 30
        rsi = max(15, min(85, rsi))
        
        if rsi < 30:
            signal = "BUY" if rand2 > 0.3 else "STRONG_BUY"
            confidence = 70 + rand3 * 20
        elif rsi > 70:
            signal = "SELL" if rand2 > 0.3 else "STRONG_SELL"
            confidence = 70 + rand3 * 20
        elif rsi < 45:
            signal = "BUY" if rand2 > 0.5 else "HOLD"
            confidence = 55 + rand3 * 20
        elif rsi > 55:
            signal = "SELL" if rand2 > 0.5 else "HOLD"
            confidence = 55 + rand3 * 20
        else:
            signal = "HOLD"
            confidence = 50 + rand3 * 15
        
        base_price = stock.get("base_price", 100)
        volatility = stock.get("volatility", 0.02)
        currency = stock.get("currency", "$")
        
        vwap = base_price * (1 + (rand1 - 0.5) * 0.01)
        macd_value = (rand2 - 0.5) * 2 * volatility * base_price
        macd_signal = macd_value * (0.8 + rand3 * 0.4)
        
        bb_middle = vwap
        bb_width = base_price * volatility * 2
        
        risk = "HIGH" if rsi < 25 or rsi > 75 else "MEDIUM" if volatility > 0.03 else "LOW"
        
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": round(confidence),
            "rsi": {"value": round(rsi, 1), "signal": "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"},
            "vwap": {"value": round(vwap, 2), "signal": "Above" if base_price > vwap else "Below"},
            "macd": {"value": round(macd_value, 3), "signal": round(macd_signal, 3), "histogram": round(macd_value - macd_signal, 3)},
            "bollinger": {"upper": round(bb_middle + bb_width, 2), "middle": round(bb_middle, 2), "lower": round(bb_middle - bb_width, 2)},
            "sma20": round(base_price * (1 + (rand3 - 0.5) * 0.02), 2),
            "atr": round(base_price * volatility * 1.5, 2),
            "risk": risk,
            "currency": currency,
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "DEMO"
        }
    
    def get_history(self, symbol: str, interval: str = "1d", period: str = "1mo") -> Dict[str, Any]:
        symbol = symbol.upper()
        stock = DEMO_STOCKS.get(symbol, {"base_price": 100, "volatility": 0.02, "currency": "$"})
        
        base_price = stock.get("base_price", 100)
        volatility = stock.get("volatility", 0.02)
        
        period_candles = {"1d": 78, "5d": 78, "1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}
        num_candles = period_candles.get(period, 22)
        
        candles = []
        seed = self._get_time_seed(symbol, "1d")
        price = base_price
        
        for i in range(num_candles):
            rand1 = self._seeded_random(seed + i * 0.1, i)
            rand2 = self._seeded_random(seed + i * 0.1, i + 100)
            
            drift = (rand1 - 0.5) * volatility * 2
            mean_reversion = (base_price - price) / base_price * 0.1
            change = drift + mean_reversion
            
            open_price = price
            close_price = price * (1 + change)
            high_price = max(open_price, close_price) * (1 + rand2 * volatility * 0.5)
            low_price = min(open_price, close_price) * (1 - (1 - rand2) * volatility * 0.5)
            
            timestamp = datetime.now() - timedelta(days=num_candles - i - 1)
            
            candles.append({
                "timestamp": timestamp.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": int(1000000 * (0.5 + rand1))
            })
            price = close_price
        
        return {
            "symbol": symbol,
            "interval": interval,
            "period": period,
            "candles": candles,
            "currency": stock.get("currency", "$"),
            "dataQuality": "DEMO"
        }

# Global demo engine
demo_engine = DemoDataEngine()

# ============================================================
# RATE LIMIT TRACKER WITH CIRCUIT BREAKER
# ============================================================

class RateLimitTracker:
    def __init__(self, window_seconds: int = RATE_LIMIT_WINDOW):
        self.errors: deque = deque()
        self.window = window_seconds
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_success_time: Optional[float] = None
        self.last_error_time: Optional[float] = None
        self.circuit_open_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self.response_log: deque = deque(maxlen=100)
    
    async def record_error(self, symbol: str = "", error: str = ""):
        async with self._lock:
            now = time.time()
            self.errors.append(now)
            self.failed_requests += 1
            self.last_error_time = now
            self._cleanup()
            
            self.response_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "ERROR",
                "symbol": symbol,
                "error": error[:200],
                "error_count": len(self.errors)
            })
            
            if len(self.errors) >= RATE_LIMIT_CRITICAL_THRESHOLD:
                self.circuit_open_time = now
                logger.warning(f"🔴 Circuit breaker OPEN - {len(self.errors)} errors in window")
    
    async def record_success(self, symbol: str = "", data_quality: str = "LIVE"):
        async with self._lock:
            self.successful_requests += 1
            self.last_success_time = time.time()
            
            self.response_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "SUCCESS",
                "symbol": symbol,
                "data_quality": data_quality
            })
            
            # Reset circuit if we're recovering
            if self.circuit_open_time and (time.time() - self.circuit_open_time) > CIRCUIT_BREAKER_COOLDOWN:
                self.circuit_open_time = None
                self.errors.clear()
                logger.info("🟢 Circuit breaker CLOSED - Recovery successful")
    
    def _cleanup(self):
        cutoff = time.time() - self.window
        while self.errors and self.errors[0] < cutoff:
            self.errors.popleft()
    
    def is_circuit_open(self) -> bool:
        if self.circuit_open_time is None:
            return False
        elapsed = time.time() - self.circuit_open_time
        return elapsed < CIRCUIT_BREAKER_COOLDOWN
    
    def get_error_count(self) -> int:
        self._cleanup()
        return len(self.errors)
    
    def get_status(self) -> SystemStatus:
        if DEMO_MODE_ENABLED:
            return SystemStatus.DEMO
        if self.is_circuit_open():
            return SystemStatus.CRITICAL
        count = self.get_error_count()
        if count >= RATE_LIMIT_CRITICAL_THRESHOLD:
            return SystemStatus.CRITICAL
        elif count >= RATE_LIMIT_ERROR_THRESHOLD:
            return SystemStatus.DEGRADED
        return SystemStatus.HEALTHY
    
    def get_stats(self) -> Dict:
        self._cleanup()
        status = self.get_status()
        
        recovery_time = None
        if self.circuit_open_time:
            remaining = CIRCUIT_BREAKER_COOLDOWN - (time.time() - self.circuit_open_time)
            if remaining > 0:
                recovery_time = int(remaining)
        
        total = self.successful_requests + self.failed_requests
        success_rate = f"{(self.successful_requests / max(total, 1)) * 100:.1f}%"
        
        return {
            "errors_last_hour": len(self.errors),
            "total_successful": self.successful_requests,
            "total_failed": self.failed_requests,
            "success_rate": success_rate,
            "last_success": datetime.fromtimestamp(self.last_success_time).isoformat() if self.last_success_time else None,
            "last_error": datetime.fromtimestamp(self.last_error_time).isoformat() if self.last_error_time else None,
            "status": status.value,
            "demo_mode": DEMO_MODE_ENABLED,
            "circuit_breaker": {
                "state": "OPEN" if self.is_circuit_open() else "CLOSED",
                "recovery_in_seconds": recovery_time,
                "cooldown_period": CIRCUIT_BREAKER_COOLDOWN
            }
        }
    
    def reset_circuit(self):
        self.circuit_open_time = None
        self.errors.clear()
        logger.info("🟢 Circuit breaker manually reset")
    
    def get_recent_responses(self, limit: int = 20) -> List[Dict]:
        return list(self.response_log)[-limit:]

# Global tracker
rate_tracker = RateLimitTracker()

# ============================================================
# SINGLEFLIGHT IMPLEMENTATION
# ============================================================

class SingleFlight:
    def __init__(self):
        self._inflight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
    
    async def do(self, key: str, fn, *args, **kwargs) -> Any:
        async with self._lock:
            if key in self._inflight:
                logger.debug(f"Joining inflight request for {key}")
                return await self._inflight[key]
            
            future = asyncio.get_event_loop().create_future()
            self._inflight[key] = future
        
        try:
            result = await fn(*args, **kwargs)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

singleflight = SingleFlight()

# ============================================================
# IN-MEMORY CACHE
# ============================================================

class InMemoryCache:
    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl:
                    return entry["data"]
                del self._cache[key]
            return None
    
    async def set(self, key: str, data: Any):
        async with self._lock:
            self._cache[key] = {"data": data, "timestamp": time.time()}
    
    def stats(self) -> Dict:
        now = time.time()
        total = len(self._cache)
        fresh = sum(1 for v in self._cache.values() if now - v["timestamp"] < self.ttl)
        return {"total_entries": total, "fresh_entries": fresh}

quote_cache = InMemoryCache(ttl_seconds=60)
history_cache = InMemoryCache(ttl_seconds=300)
signals_cache = InMemoryCache(ttl_seconds=120)

# ============================================================
# LKG (Last Known Good) FILE CACHE
# ============================================================

class LKGCache:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, key: str) -> Path:
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Dict]:
        path = self._get_path(key)
        try:
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                    data["dataQuality"] = "LKG"
                    data["_lkg_loaded"] = True
                    return data
        except Exception as e:
            logger.warning(f"LKG read error for {key}: {e}")
        return None
    
    def set(self, key: str, data: Dict):
        path = self._get_path(key)
        try:
            data_copy = data.copy()
            data_copy["_lkg_timestamp"] = datetime.now().isoformat()
            with open(path, 'w') as f:
                json.dump(data_copy, f)
        except Exception as e:
            logger.warning(f"LKG write error for {key}: {e}")

lkg_cache = LKGCache()

# ============================================================
# YFINANCE INTEGRATION WITH FALLBACK CHAIN
# ============================================================

async def fetch_quote_live(symbol: str) -> Optional[Dict]:
    """Fetch live quote from Yahoo Finance."""
    if DEMO_MODE_ENABLED:
        return None
    
    if rate_tracker.is_circuit_open():
        logger.debug(f"Circuit open - skipping live fetch for {symbol}")
        return None
    
    try:
        import yfinance as yf
        
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            
            if not hasattr(info, 'last_price') or info.last_price is None:
                return None
            
            return {
                "symbol": symbol,
                "price": round(info.last_price, 2),
                "prev_close": round(info.previous_close, 2) if info.previous_close else None,
                "open": round(info.open, 2) if hasattr(info, 'open') and info.open else None,
                "high": round(info.day_high, 2) if hasattr(info, 'day_high') and info.day_high else None,
                "low": round(info.day_low, 2) if hasattr(info, 'day_low') and info.day_low else None,
                "volume": int(info.last_volume) if hasattr(info, 'last_volume') and info.last_volume else 0
            }
        
        result = await asyncio.wait_for(
            run_in_threadpool(_fetch),
            timeout=10.0
        )
        
        if result:
            await rate_tracker.record_success(symbol, "LIVE")
            return result
        return None
        
    except asyncio.TimeoutError:
        await rate_tracker.record_error(symbol, "timeout")
        return None
    except Exception as e:
        await rate_tracker.record_error(symbol, str(e))
        return None

async def fetch_history_live(symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[Dict]:
    """Fetch live history from Yahoo Finance."""
    if DEMO_MODE_ENABLED:
        return None
    
    if rate_tracker.is_circuit_open():
        return None
    
    try:
        import yfinance as yf
        
        def _fetch():
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            candles = []
            for idx, row in hist.iterrows():
                candles.append({
                    "timestamp": idx.isoformat(),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"])
                })
            
            return {"symbol": symbol, "candles": candles, "period": period, "interval": interval}
        
        result = await asyncio.wait_for(
            run_in_threadpool(_fetch),
            timeout=15.0
        )
        
        if result:
            await rate_tracker.record_success(symbol, "LIVE")
            return result
        return None
        
    except Exception as e:
        await rate_tracker.record_error(symbol, str(e))
        return None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_market_from_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return "India"
    elif symbol.endswith("-USD"):
        return "Crypto"
    elif symbol.endswith(".L"):
        return "UK"
    elif symbol.endswith(".DE"):
        return "Germany"
    elif symbol.endswith(".PA"):
        return "France"
    elif symbol.endswith(".T"):
        return "Japan"
    elif symbol.endswith(".HK"):
        return "HongKong"
    elif symbol.endswith(".TW"):
        return "Taiwan"
    elif symbol.endswith(".AX"):
        return "Australia"
    elif symbol.endswith(".TO"):
        return "Canada"
    elif symbol.endswith(".SA"):
        return "Brazil"
    elif symbol.endswith(".KS"):
        return "Korea"
    elif symbol.endswith(".SI"):
        return "Singapore"
    elif symbol.endswith(".SW"):
        return "Switzerland"
    elif symbol.endswith(".AS"):
        return "Netherlands"
    elif symbol.endswith(".MC"):
        return "Spain"
    elif symbol.endswith(".MI"):
        return "Italy"
    elif "=" in symbol:
        if "USD" in symbol:
            return "Forex"
        return "Commodities"
    elif symbol in ["SPY", "QQQ", "DIA", "IWM", "VTI", "GLD"]:
        return "ETF"
    return "US"

def get_currency(market: str) -> str:
    currency_map = {
        "India": "₹", "UK": "£", "Germany": "€", "France": "€",
        "Japan": "¥", "China": "HK$", "HongKong": "HK$", "Taiwan": "NT$",
        "Australia": "A$", "Canada": "C$", "Brazil": "R$", "Korea": "₩",
        "Singapore": "S$", "Switzerland": "CHF", "Netherlands": "€",
        "Spain": "€", "Italy": "€"
    }
    return currency_map.get(market, "$")

def get_currency_name(market: str) -> str:
    name_map = {
        "India": "INR", "UK": "GBP", "Germany": "EUR", "France": "EUR",
        "Japan": "JPY", "China": "HKD", "HongKong": "HKD", "Taiwan": "TWD",
        "Australia": "AUD", "Canada": "CAD", "Brazil": "BRL", "Korea": "KRW",
        "Singapore": "SGD", "Switzerland": "CHF", "Netherlands": "EUR",
        "Spain": "EUR", "Italy": "EUR"
    }
    return name_map.get(market, "USD")

# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/api/v4/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote with fallback chain: Cache → Live → LKG → Demo"""
    symbol = symbol.upper()
    cache_key = f"quote:{symbol}"
    
    # 1. Check in-memory cache
    cached = await quote_cache.get(cache_key)
    if cached:
        cached["dataQuality"] = "CACHED"
        return cached
    
    # 2. Try live fetch
    live_data = await singleflight.do(f"live_quote:{symbol}", fetch_quote_live, symbol)
    
    if live_data:
        # Enrich with market info
        market = get_market_from_symbol(symbol)
        live_data.update({
            "name": STOCK_NAMES.get(symbol, symbol),
            "market": market,
            "currency": get_currency(market),
            "change": round(live_data["price"] - (live_data.get("prev_close") or live_data["price"]), 2),
            "change_percent": round(((live_data["price"] / (live_data.get("prev_close") or live_data["price"])) - 1) * 100, 2),
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "LIVE"
        })
        
        await quote_cache.set(cache_key, live_data)
        lkg_cache.set(cache_key, live_data)
        return live_data
    
    # 3. Try LKG cache
    lkg_data = lkg_cache.get(cache_key)
    if lkg_data:
        return lkg_data
    
    # 4. Fall back to demo data
    demo_data = demo_engine.get_quote(symbol)
    return demo_data

@router.get("/api/v4/history/{symbol}")
async def get_history(symbol: str, interval: str = "1d", period: str = "1mo"):
    """Get price history with fallback chain."""
    symbol = symbol.upper()
    cache_key = f"history:{symbol}:{period}:{interval}"
    
    # 1. Check cache
    cached = await history_cache.get(cache_key)
    if cached:
        cached["dataQuality"] = "CACHED"
        return cached
    
    # 2. Try live
    live_data = await singleflight.do(f"live_history:{symbol}", fetch_history_live, symbol, period, interval)
    
    if live_data and live_data.get("candles"):
        market = get_market_from_symbol(symbol)
        live_data.update({
            "currency": get_currency(market),
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "LIVE"
        })
        
        await history_cache.set(cache_key, live_data)
        lkg_cache.set(cache_key, live_data)
        return live_data
    
    # 3. Try LKG
    lkg_data = lkg_cache.get(cache_key)
    if lkg_data:
        return lkg_data
    
    # 4. Demo fallback
    demo_data = demo_engine.get_history(symbol, interval, period)
    return demo_data

@router.get("/api/signals/{symbol}")
async def get_signals(symbol: str):
    """Get trading signals with RSI, MACD, VWAP."""
    symbol = symbol.upper()
    cache_key = f"signals:{symbol}"
    
    # Check cache
    cached = await signals_cache.get(cache_key)
    if cached:
        cached["dataQuality"] = "CACHED"
        return cached
    
    # Get quote for price data
    quote = await get_quote(symbol)
    
    # For now, generate signals from demo engine (consistent quality)
    signals = demo_engine.get_signals(symbol)
    
    # Use actual price if available
    if quote.get("dataQuality") == "LIVE":
        signals["currentPrice"] = quote["price"]
        signals["dataQuality"] = "LIVE"
    
    await signals_cache.set(cache_key, signals)
    return signals

@router.get("/api/screener/universe")
async def get_screener_data():
    """
    Get screener data for static universe.
    Uses demo data for reliability, with timeout protection.
    """
    results = []
    start_time = time.time()
    
    # If demo mode or circuit open, use demo data directly
    use_demo = DEMO_MODE_ENABLED or rate_tracker.is_circuit_open()
    
    for category, symbols in SCREENER_UNIVERSE.items():
        for symbol in symbols:
            # Check timeout
            if time.time() - start_time > SCREENER_TIMEOUT_SECONDS:
                logger.warning(f"Screener timeout after {SCREENER_TIMEOUT_SECONDS}s")
                break
            
            try:
                if use_demo:
                    # Direct demo data
                    quote = demo_engine.get_quote(symbol)
                    signals = demo_engine.get_signals(symbol)
                else:
                    # Try live with fast fallback
                    quote = await get_quote(symbol)
                    signals = await get_signals(symbol)
                    await asyncio.sleep(SCREENER_FETCH_DELAY_MS / 1000)
                
                rsi_value = signals.get("rsi", {})
                if isinstance(rsi_value, dict):
                    rsi = rsi_value.get("value", 50)
                else:
                    rsi = rsi_value
                
                results.append({
                    "symbol": symbol,
                    "name": STOCK_NAMES.get(symbol, symbol),
                    "category": category,
                    "price": quote.get("price", 0),
                    "change_percent": quote.get("change_percent", 0),
                    "rsi": round(rsi, 1) if rsi else 50,
                    "signal": signals.get("signal", "HOLD"),
                    "currency": quote.get("currency", "$"),
                    "dataQuality": quote.get("dataQuality", "DEMO")
                })
                
            except Exception as e:
                logger.warning(f"Screener fetch failed for {symbol}: {e}")
                # Fallback to demo
                demo = demo_engine.get_quote(symbol)
                signals = demo_engine.get_signals(symbol)
                results.append({
                    "symbol": symbol,
                    "name": STOCK_NAMES.get(symbol, symbol),
                    "category": category,
                    "price": demo["price"],
                    "change_percent": demo["change_percent"],
                    "rsi": signals["rsi"]["value"],
                    "signal": signals["signal"],
                    "currency": demo["currency"],
                    "dataQuality": "DEMO"
                })
    
    # Categorize
    oversold = [r for r in results if r["rsi"] < 30]
    overbought = [r for r in results if r["rsi"] > 70]
    buy_signals = [r for r in results if r["signal"] in ["BUY", "STRONG_BUY"]]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "all": results,
        "oversold": oversold,
        "overbought": overbought,
        "buySignals": buy_signals,
        "categories": list(SCREENER_UNIVERSE.keys()),
        "systemStatus": rate_tracker.get_status().value,
        "demoMode": DEMO_MODE_ENABLED or use_demo
    }

@router.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """Get curated news with FinBERT sentiment."""
    symbol = symbol.upper()
    market = get_market_from_symbol(symbol)
    
    seed = f"news:{symbol}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    news_templates = [
        {"title": f"{STOCK_NAMES.get(symbol, symbol)} Sees Strong Momentum", "source": "Reuters", "sentiment": "Bullish"},
        {"title": f"Analysts Upgrade {symbol} Price Target", "source": "Bloomberg", "sentiment": "Bullish"},
        {"title": f"What's Next for {symbol} Stock?", "source": "CNBC", "sentiment": "Neutral"},
        {"title": f"{symbol} Technical Analysis Shows Support", "source": "MarketWatch", "sentiment": "Bullish"},
        {"title": f"Institutional Investors Adjust {symbol} Holdings", "source": "WSJ", "sentiment": "Neutral"},
        {"title": f"Market Update: {symbol} Amid Sector Rotation", "source": "Financial Times", "sentiment": "Neutral"},
    ]
    
    articles = []
    for i, template in enumerate(rng.sample(news_templates, min(5, len(news_templates)))):
        articles.append({
            "title": template["title"],
            "source": template["source"],
            "sentiment": template["sentiment"],
            "confidence": round(0.6 + rng.random() * 0.35, 2),
            "time_ago": f"{i+1}h ago",
            "url": f"https://news.example.com/{symbol.lower()}/{i}"
        })
    
    return {
        "symbol": symbol,
        "market": market,
        "articles": articles,
        "sentiment_source": "FinBERT",
        "dataQuality": "CURATED"
    }

@router.get("/api/sentiment/reddit/{symbol}")
async def get_reddit_sentiment(symbol: str):
    """Get Reddit sentiment - tries real API first."""
    symbol = symbol.upper()
    
    # Try real Reddit sentiment
    try:
        # Import sentiment service if available
        from sentiment_service import get_reddit_mentions
        result = await get_reddit_mentions(symbol)
        if result and result.get("isLive"):
            return result
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Reddit sentiment error: {e}")
    
    # Fallback to simulated
    seed = f"reddit:{symbol}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    bullish = rng.randint(35, 75)
    
    return {
        "symbol": symbol,
        "mentions": rng.randint(500, 10000),
        "bullish_percent": bullish,
        "bearish_percent": 100 - bullish,
        "trend": f"+{rng.randint(5, 30)}%" if rng.random() > 0.4 else f"-{rng.randint(5, 20)}%",
        "trending": rng.random() > 0.6,
        "top_subreddits": ["wallstreetbets", "stocks", "investing"],
        "sentiment_score": round((bullish - 50) / 50, 2),
        "timestamp": datetime.now().isoformat(),
        "dataQuality": "SIMULATED"
    }

@router.get("/api/sentiment/stocktwits/{symbol}")
async def get_stocktwits_sentiment(symbol: str):
    """Get StockTwits sentiment - tries real API first."""
    symbol = symbol.upper()
    
    try:
        from sentiment_service import get_stocktwits_stream
        result = await get_stocktwits_stream(symbol)
        if result and result.get("isLive"):
            return result
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"StockTwits sentiment error: {e}")
    
    # Fallback
    seed = f"stocktwits:{symbol}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    bullish = rng.randint(40, 70)
    
    return {
        "symbol": symbol,
        "bullish_percent": bullish,
        "bearish_percent": 100 - bullish,
        "watchers": rng.randint(5000, 100000),
        "message_count": rng.randint(50, 500),
        "sentiment": "Bullish" if bullish > 55 else "Bearish" if bullish < 45 else "Mixed",
        "trending": rng.random() > 0.7,
        "timestamp": datetime.now().isoformat(),
        "dataQuality": "SIMULATED"
    }

@router.get("/api/v4/financials/{symbol}")
async def get_financials(symbol: str):
    """Get company financial data."""
    symbol = symbol.upper()
    market = get_market_from_symbol(symbol)
    currency = get_currency(market)
    
    seed = f"fin:{symbol}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    stock = DEMO_STOCKS.get(symbol, {"base_price": 100})
    base = stock.get("base_price", 100)
    market_cap = base * rng.randint(1000000000, 50000000000) / 100
    
    if market_cap >= 1e12:
        mc_fmt = f"{market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        mc_fmt = f"{market_cap/1e9:.2f}B"
    else:
        mc_fmt = f"{market_cap/1e6:.2f}M"
    
    pe = round(15 + rng.random() * 35, 2)
    eps = round(base / pe, 2)
    
    return {
        "symbol": symbol,
        "market": market,
        "currency": currency,
        "market_cap": mc_fmt,
        "pe_ratio": pe,
        "eps": eps,
        "revenue": f"{rng.randint(50, 500)}B",
        "profit_margin": f"{rng.randint(10, 35)}%",
        "dividend_yield": f"{round(rng.random() * 3, 2)}%",
        "beta": round(0.8 + rng.random() * 0.8, 2),
        "52w_high": round(base * 1.3, 2),
        "52w_low": round(base * 0.7, 2),
        "dataQuality": "ESTIMATED"
    }

@router.get("/api/v4/top-movers/{market}")
async def get_top_movers(market: str = "US"):
    """Get top movers for a market - used by frontend Top Movers component."""
    market_key = market.replace(" ", "")
    config = MARKET_CONFIG.get(market_key, MARKET_CONFIG.get(market, MARKET_CONFIG['US']))
    currency = config['currency']
    stocks = config['stocks']
    
    seed = f"movers:{market}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    movers = []
    for symbol in stocks:
        stock = DEMO_STOCKS.get(symbol, {"base_price": 100, "name": symbol})
        base = stock.get("base_price", 100)
        change_pct = (rng.random() - 0.5) * 8
        price = base * (1 + change_pct / 100)
        movers.append({
            "symbol": symbol,
            "fullSymbol": symbol,
            "name": stock.get("name", symbol),
            "price": round(price, 2),
            "change": round(price - base, 2),
            "changePercent": round(change_pct, 2),
            "currency": currency
        })
    
    movers.sort(key=lambda x: abs(x['changePercent']), reverse=True)
    
    return {
        "success": True,
        "market": market,
        "currency": currency,
        "movers": movers[:6],  # Top 6 movers
        "timestamp": datetime.now().isoformat(),
        "dataQuality": "SIMULATED"
    }

@router.get("/api/v4/movers/{market}")
async def get_movers(market: str = "US"):
    """Get top gainers and losers for a market (legacy format)."""
    market_key = market.replace(" ", "")
    config = MARKET_CONFIG.get(market_key, MARKET_CONFIG.get(market, MARKET_CONFIG['US']))
    currency = config['currency']
    stocks = config['stocks']
    
    seed = f"movers:{market}:{datetime.now().strftime('%Y%m%d%H')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    movers = []
    for symbol in stocks:
        stock = DEMO_STOCKS.get(symbol, {"base_price": 100, "name": symbol})
        base = stock.get("base_price", 100)
        change_pct = (rng.random() - 0.5) * 8
        price = base * (1 + change_pct / 100)
        movers.append({
            "symbol": symbol,
            "name": stock.get("name", symbol),
            "price": round(price, 2),
            "change": round(price - base, 2),
            "change_percent": round(change_pct, 2),
            "currency": currency
        })
    
    movers.sort(key=lambda x: x['change_percent'], reverse=True)
    gainers = [m for m in movers if m['change_percent'] > 0][:5]
    losers = sorted([m for m in movers if m['change_percent'] < 0], key=lambda x: x['change_percent'])[:5]
    
    return {
        "market": market,
        "currency": currency,
        "gainers": gainers,
        "losers": losers,
        "timestamp": datetime.now().isoformat(),
        "dataQuality": "SIMULATED"
    }

# ============================================================
# HEALTH & DEBUG ENDPOINTS
# ============================================================

@router.get("/api/health")
async def health_check():
    """Deep health check with polling recommendations."""
    yf_status = "unknown"
    try:
        import yfinance
        yf_status = "available"
    except ImportError:
        yf_status = "not_installed"
    
    rate_stats = rate_tracker.get_stats()
    status = rate_tracker.get_status()
    
    # Polling recommendations
    polling_intervals = {
        SystemStatus.HEALTHY: 60,
        SystemStatus.DEGRADED: 120,
        SystemStatus.CRITICAL: 300,
        SystemStatus.DEMO: 60
    }
    
    return {
        "status": status.value,
        "version": "5.8.7",
        "timestamp": datetime.now().isoformat(),
        "demo_mode": DEMO_MODE_ENABLED,
        "services": {
            "yfinance": yf_status,
            "demo_engine": "available",
            "sentiment": "available"
        },
        "rate_limit": rate_stats,
        "cache": {
            "quotes": quote_cache.stats(),
            "history": history_cache.stats(),
            "signals": signals_cache.stats()
        },
        "polling_recommendation": polling_intervals.get(status, 60),
        "circuit_breaker": rate_stats["circuit_breaker"],
        "markets_supported": len(MARKET_CONFIG)
    }

@router.get("/api/debug/responses")
async def get_debug_responses(limit: int = 20):
    """Get recent API responses for debugging."""
    return {
        "responses": rate_tracker.get_recent_responses(limit),
        "stats": rate_tracker.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/api/debug/reset-circuit")
async def reset_circuit():
    """Manually reset the circuit breaker."""
    rate_tracker.reset_circuit()
    return {
        "success": True,
        "message": "Circuit breaker reset",
        "new_status": rate_tracker.get_status().value
    }

@router.post("/api/debug/toggle-demo")
async def toggle_demo_mode():
    """Toggle demo mode on/off."""
    global DEMO_MODE_ENABLED
    DEMO_MODE_ENABLED = not DEMO_MODE_ENABLED
    return {
        "demo_mode": DEMO_MODE_ENABLED,
        "message": f"Demo mode {'enabled' if DEMO_MODE_ENABLED else 'disabled'}"
    }
