"""
Market Data Service v4.9
========================
Location: backend/services/market_data_service.py

PRODUCTION-GRADE DATA PIPELINE:
    1. yfinance (LIVE) - Primary source, uses fast_info
    2. LKG Cache (CACHED) - Last Known Good fallback
    3. MME Simulator (SIMULATED) - Final fallback

Features:
- Uses fast_info instead of info (avoids scraping)
- File-based caching with locking
- SingleFlight pattern to prevent thundering herd
- Circuit breaker for rate limit protection
- Proper async/sync bridging via run_in_threadpool
"""

import os
import random
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
import asyncio
import httpx

FINNHUB_KEY     = os.getenv("FINNHUB_API_KEY", "")
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# Third-party imports with fallbacks
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

try:
    from starlette.concurrency import run_in_threadpool
except ImportError:
    # Fallback for testing outside FastAPI
    async def run_in_threadpool(func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

# Local imports
try:
    from services.cache_manager import (
        get_cache_manager, get_singleflight, CacheEntry,
        DEFAULT_TTL_SECONDS, STALE_THRESHOLD_SECONDS
    )
except ImportError:
    # Running standalone
    from cache_manager import (
        get_cache_manager, get_singleflight, CacheEntry,
        DEFAULT_TTL_SECONDS, STALE_THRESHOLD_SECONDS
    )

logger = logging.getLogger(__name__)

# =============================================================================
# MARKET CONFIGURATIONS WITH CORRECT CURRENCIES
# =============================================================================

MARKET_CONFIG = {
    'US': {'currency': '$', 'name': 'United States', 'suffix': ''},
    'INDIA': {'currency': '₹', 'name': 'India (NSE)', 'suffix': '.NS'},
    'BSE': {'currency': '₹', 'name': 'India (BSE)', 'suffix': '.BO'},
    'UK': {'currency': '£', 'name': 'United Kingdom', 'suffix': '.L'},
    'GERMANY': {'currency': '€', 'name': 'Germany', 'suffix': '.DE'},
    'FRANCE': {'currency': '€', 'name': 'France', 'suffix': '.PA'},
    'JAPAN': {'currency': '¥', 'name': 'Japan', 'suffix': '.T'},
    'CHINA': {'currency': '¥', 'name': 'China', 'suffix': '.SS'},
    'HONGKONG': {'currency': 'HK$', 'name': 'Hong Kong', 'suffix': '.HK'},
    'AUSTRALIA': {'currency': 'A$', 'name': 'Australia', 'suffix': '.AX'},
    'CANADA': {'currency': 'C$', 'name': 'Canada', 'suffix': '.TO'},
    'BRAZIL': {'currency': 'R$', 'name': 'Brazil', 'suffix': '.SA'},
    'KOREA': {'currency': '₩', 'name': 'South Korea', 'suffix': '.KS'},
    'SINGAPORE': {'currency': 'S$', 'name': 'Singapore', 'suffix': '.SI'},
    'SWITZERLAND': {'currency': 'CHF', 'name': 'Switzerland', 'suffix': '.SW'},
    'NETHERLANDS': {'currency': '€', 'name': 'Netherlands', 'suffix': '.AS'},
    'SPAIN': {'currency': '€', 'name': 'Spain', 'suffix': '.MC'},
    'ITALY': {'currency': '€', 'name': 'Italy', 'suffix': '.MI'},
    'SWEDEN': {'currency': 'kr', 'name': 'Sweden', 'suffix': '.ST'},
    'CRYPTO': {'currency': '$', 'name': 'Cryptocurrency', 'suffix': ''},
    'ETF': {'currency': '$', 'name': 'ETFs', 'suffix': ''},
    'FOREX': {'currency': '$', 'name': 'Forex', 'suffix': ''},
    'COMMODITIES': {'currency': '$', 'name': 'Commodities', 'suffix': ''},
}

# =============================================================================
# GLOBAL STOCKS DATABASE
# All NSE tickers verified against NSE official symbol list (nseindia.com/market-data/securities-available-for-trading).
# To verify a new ticker: https://www.nseindia.com/get-quotes/equity?symbol=<TICKER>
# yfinance appends .NS; Twelve Data uses :NSE suffix (handled by _to_twelvedata_symbol).
# Index symbols (NIFTY50.NS, BANKNIFTY.NS) are MME-only reference data — live APIs
# use ^NSEI / ^NSEBANK for indices, which are not fetchable through the stock endpoint.
# =============================================================================

GLOBAL_STOCKS = {
    # US STOCKS
    'AAPL': {'name': 'Apple Inc.', 'market': 'US', 'basePrice': 250},
    'MSFT': {'name': 'Microsoft', 'market': 'US', 'basePrice': 430},
    'GOOGL': {'name': 'Alphabet Inc.', 'market': 'US', 'basePrice': 175},
    'AMZN': {'name': 'Amazon', 'market': 'US', 'basePrice': 225},
    'NVDA': {'name': 'NVIDIA Corp.', 'market': 'US', 'basePrice': 140},
    'TSLA': {'name': 'Tesla Inc.', 'market': 'US', 'basePrice': 250},
    'META': {'name': 'Meta Platforms', 'market': 'US', 'basePrice': 580},
    'NFLX': {'name': 'Netflix Inc.', 'market': 'US', 'basePrice': 900},
    'AMD': {'name': 'AMD Inc.', 'market': 'US', 'basePrice': 140},
    'CRM': {'name': 'Salesforce Inc.', 'market': 'US', 'basePrice': 350},
    'JPM': {'name': 'JPMorgan Chase', 'market': 'US', 'basePrice': 200},
    'V': {'name': 'Visa Inc.', 'market': 'US', 'basePrice': 315},
    'MA': {'name': 'Mastercard Inc.', 'market': 'US', 'basePrice': 530},
    'DIS': {'name': 'Walt Disney Co.', 'market': 'US', 'basePrice': 115},
    
    # INDIA — NIFTY 50 (NSE)
    'RELIANCE.NS':   {'name': 'Reliance Industries',    'market': 'INDIA', 'basePrice': 1280,  'sector': 'Energy'},
    'TCS.NS':        {'name': 'Tata Consultancy Svcs',  'market': 'INDIA', 'basePrice': 4100,  'sector': 'IT'},
    'HDFCBANK.NS':   {'name': 'HDFC Bank',              'market': 'INDIA', 'basePrice': 1750,  'sector': 'Banking'},
    'INFY.NS':       {'name': 'Infosys Ltd.',            'market': 'INDIA', 'basePrice': 1900,  'sector': 'IT'},
    'ICICIBANK.NS':  {'name': 'ICICI Bank',              'market': 'INDIA', 'basePrice': 1250,  'sector': 'Banking'},
    'HINDUNILVR.NS': {'name': 'Hindustan Unilever',      'market': 'INDIA', 'basePrice': 2400,  'sector': 'FMCG'},
    'ITC.NS':        {'name': 'ITC Ltd.',                'market': 'INDIA', 'basePrice': 490,   'sector': 'FMCG'},
    'SBIN.NS':       {'name': 'State Bank of India',     'market': 'INDIA', 'basePrice': 850,   'sector': 'Banking'},
    'BHARTIARTL.NS': {'name': 'Bharti Airtel',           'market': 'INDIA', 'basePrice': 1650,  'sector': 'Telecom'},
    'BAJFINANCE.NS': {'name': 'Bajaj Finance',           'market': 'INDIA', 'basePrice': 7200,  'sector': 'NBFC'},
    'KOTAKBANK.NS':  {'name': 'Kotak Mahindra Bank',     'market': 'INDIA', 'basePrice': 1900,  'sector': 'Banking'},
    'LT.NS':         {'name': 'Larsen & Toubro',         'market': 'INDIA', 'basePrice': 3500,  'sector': 'Infra'},
    'ASIANPAINT.NS': {'name': 'Asian Paints',            'market': 'INDIA', 'basePrice': 2800,  'sector': 'Paints'},
    'AXISBANK.NS':   {'name': 'Axis Bank',               'market': 'INDIA', 'basePrice': 1100,  'sector': 'Banking'},
    'MARUTI.NS':     {'name': 'Maruti Suzuki',           'market': 'INDIA', 'basePrice': 12000, 'sector': 'Auto'},
    'SUNPHARMA.NS':  {'name': 'Sun Pharma',              'market': 'INDIA', 'basePrice': 1700,  'sector': 'Pharma'},
    'TITAN.NS':      {'name': 'Titan Company',           'market': 'INDIA', 'basePrice': 3400,  'sector': 'Consumer'},
    'WIPRO.NS':      {'name': 'Wipro Ltd.',              'market': 'INDIA', 'basePrice': 450,   'sector': 'IT'},
    'NTPC.NS':       {'name': 'NTPC Ltd.',               'market': 'INDIA', 'basePrice': 375,   'sector': 'Power'},
    'POWERGRID.NS':  {'name': 'Power Grid Corp.',        'market': 'INDIA', 'basePrice': 330,   'sector': 'Power'},
    'ULTRACEMCO.NS': {'name': 'UltraTech Cement',        'market': 'INDIA', 'basePrice': 10500, 'sector': 'Cement'},
    'NESTLEIND.NS':  {'name': 'Nestle India',            'market': 'INDIA', 'basePrice': 2300,  'sector': 'FMCG'},
    'TATAMOTORS.NS': {'name': 'Tata Motors',             'market': 'INDIA', 'basePrice': 820,   'sector': 'Auto'},
    'TECHM.NS':      {'name': 'Tech Mahindra',           'market': 'INDIA', 'basePrice': 1650,  'sector': 'IT'},
    'HCLTECH.NS':    {'name': 'HCL Technologies',        'market': 'INDIA', 'basePrice': 1800,  'sector': 'IT'},
    'TATASTEEL.NS':  {'name': 'Tata Steel',              'market': 'INDIA', 'basePrice': 160,   'sector': 'Metals'},
    'JSWSTEEL.NS':   {'name': 'JSW Steel',               'market': 'INDIA', 'basePrice': 920,   'sector': 'Metals'},
    'ONGC.NS':       {'name': 'ONGC Ltd.',               'market': 'INDIA', 'basePrice': 270,   'sector': 'Energy'},
    'DRREDDY.NS':    {'name': "Dr. Reddy's Labs",        'market': 'INDIA', 'basePrice': 6500,  'sector': 'Pharma'},
    'CIPLA.NS':      {'name': 'Cipla Ltd.',              'market': 'INDIA', 'basePrice': 1550,  'sector': 'Pharma'},
    'ADANIPORTS.NS': {'name': 'Adani Ports',             'market': 'INDIA', 'basePrice': 1300,  'sector': 'Logistics'},
    'GRASIM.NS':     {'name': 'Grasim Industries',       'market': 'INDIA', 'basePrice': 2700,  'sector': 'Cement'},
    'HEROMOTOCO.NS': {'name': 'Hero MotoCorp',           'market': 'INDIA', 'basePrice': 4800,  'sector': 'Auto'},
    'EICHERMOT.NS':  {'name': 'Eicher Motors',           'market': 'INDIA', 'basePrice': 5100,  'sector': 'Auto'},
    'BAJAJFINSV.NS': {'name': 'Bajaj Finserv',           'market': 'INDIA', 'basePrice': 1900,  'sector': 'NBFC'},
    'TATACONSUM.NS': {'name': 'Tata Consumer Products',  'market': 'INDIA', 'basePrice': 1100,  'sector': 'FMCG'},
    'APOLLOHOSP.NS': {'name': 'Apollo Hospitals',        'market': 'INDIA', 'basePrice': 7200,  'sector': 'Healthcare'},
    'INDUSINDBK.NS': {'name': 'IndusInd Bank',           'market': 'INDIA', 'basePrice': 950,   'sector': 'Banking'},
    'BPCL.NS':       {'name': 'BPCL',                   'market': 'INDIA', 'basePrice': 340,   'sector': 'Energy'},
    'COALINDIA.NS':  {'name': 'Coal India',              'market': 'INDIA', 'basePrice': 490,   'sector': 'Mining'},
    'SHRIRAMFIN.NS': {'name': 'Shriram Finance',         'market': 'INDIA', 'basePrice': 3100,  'sector': 'NBFC'},
    'BRITANNIA.NS':  {'name': 'Britannia Industries',    'market': 'INDIA', 'basePrice': 5500,  'sector': 'FMCG'},
    'DIVISLAB.NS':   {'name': "Divi's Laboratories",     'market': 'INDIA', 'basePrice': 5800,  'sector': 'Pharma'},
    'HDFCLIFE.NS':   {'name': 'HDFC Life Insurance',     'market': 'INDIA', 'basePrice': 700,   'sector': 'Insurance'},
    'SBILIFE.NS':    {'name': 'SBI Life Insurance',      'market': 'INDIA', 'basePrice': 1600,  'sector': 'Insurance'},
    'M&M.NS':        {'name': 'Mahindra & Mahindra',     'market': 'INDIA', 'basePrice': 2900,  'sector': 'Auto'},
    'HINDALCO.NS':   {'name': 'Hindalco Industries',     'market': 'INDIA', 'basePrice': 680,   'sector': 'Metals'},
    # INDIA INDICES — yfinance uses ^NSEI / ^NSEBANK but these keys are MME-only reference data
    'NIFTY50.NS':    {'name': 'Nifty 50 Index',          'market': 'INDIA', 'basePrice': 24500, 'sector': 'Index'},
    'BANKNIFTY.NS':  {'name': 'Bank Nifty Index',        'market': 'INDIA', 'basePrice': 53000, 'sector': 'Index'},
    # ADDITIONAL NSE — Defence, PSU, Mid-cap popular stocks
    'BEL.NS':        {'name': 'Bharat Electronics',       'market': 'INDIA', 'basePrice': 280,   'sector': 'Defence'},
    'HAL.NS':        {'name': 'Hindustan Aeronautics',    'market': 'INDIA', 'basePrice': 4300,  'sector': 'Defence'},
    'IRFC.NS':       {'name': 'Indian Railway Finance',   'market': 'INDIA', 'basePrice': 175,   'sector': 'Finance'},
    'PFC.NS':        {'name': 'Power Finance Corp.',      'market': 'INDIA', 'basePrice': 450,   'sector': 'Finance'},
    'RECLTD.NS':     {'name': 'REC Limited',              'market': 'INDIA', 'basePrice': 530,   'sector': 'Finance'},
    'IRCTC.NS':      {'name': 'IRCTC',                   'market': 'INDIA', 'basePrice': 900,   'sector': 'Travel'},
    'PIDILITIND.NS': {'name': 'Pidilite Industries',      'market': 'INDIA', 'basePrice': 3000,  'sector': 'Chemical'},
    'DMART.NS':      {'name': 'Avenue Supermarts (D-Mart)','market': 'INDIA', 'basePrice': 4200,  'sector': 'Retail'},
    'AMBUJACEM.NS':  {'name': 'Ambuja Cements',           'market': 'INDIA', 'basePrice': 620,   'sector': 'Cement'},
    'BANKBARODA.NS': {'name': 'Bank of Baroda',           'market': 'INDIA', 'basePrice': 235,   'sector': 'Banking'},
    'CANBK.NS':      {'name': 'Canara Bank',              'market': 'INDIA', 'basePrice': 105,   'sector': 'Banking'},
    'PNB.NS':        {'name': 'Punjab National Bank',     'market': 'INDIA', 'basePrice': 105,   'sector': 'Banking'},
    'ZOMATO.NS':     {'name': 'Zomato Ltd.',              'market': 'INDIA', 'basePrice': 230,   'sector': 'Tech'},
    'PAYTM.NS':      {'name': 'Paytm (One 97 Comm.)',    'market': 'INDIA', 'basePrice': 750,   'sector': 'Tech'},
    'NYKAA.NS':      {'name': 'FSN E-Commerce (Nykaa)',  'market': 'INDIA', 'basePrice': 165,   'sector': 'Tech'},
    'TRENT.NS':      {'name': 'Trent Ltd.',               'market': 'INDIA', 'basePrice': 6100,  'sector': 'Retail'},
    'MUTHOOTFIN.NS': {'name': 'Muthoot Finance',          'market': 'INDIA', 'basePrice': 1950,  'sector': 'Finance'},
    'BAJAJ-AUTO.NS': {'name': 'Bajaj Auto',               'market': 'INDIA', 'basePrice': 9800,  'sector': 'Auto'},
    'SOLARINDS.NS':  {'name': 'Solar Industries India',   'market': 'INDIA', 'basePrice': 10200, 'sector': 'Defence'},
    'BHEL.NS':       {'name': 'Bharat Heavy Electricals', 'market': 'INDIA', 'basePrice': 245,   'sector': 'Engineering'},
    'NHPC.NS':       {'name': 'NHPC Ltd.',                'market': 'INDIA', 'basePrice': 85,    'sector': 'Power'},
    'SJVN.NS':       {'name': 'SJVN Ltd.',                'market': 'INDIA', 'basePrice': 112,   'sector': 'Power'},

    # INDIA — BSE Sensex 30 (.BO suffix)
    'RELIANCE.BO':   {'name': 'Reliance Industries',    'market': 'BSE', 'basePrice': 1280,  'sector': 'Energy'},
    'TCS.BO':        {'name': 'Tata Consultancy Svcs',  'market': 'BSE', 'basePrice': 4100,  'sector': 'IT'},
    'HDFCBANK.BO':   {'name': 'HDFC Bank',              'market': 'BSE', 'basePrice': 1750,  'sector': 'Banking'},
    'INFY.BO':       {'name': 'Infosys Ltd.',            'market': 'BSE', 'basePrice': 1900,  'sector': 'IT'},
    'ICICIBANK.BO':  {'name': 'ICICI Bank',              'market': 'BSE', 'basePrice': 1250,  'sector': 'Banking'},
    'HINDUNILVR.BO': {'name': 'Hindustan Unilever',      'market': 'BSE', 'basePrice': 2400,  'sector': 'FMCG'},
    'ITC.BO':        {'name': 'ITC Ltd.',                'market': 'BSE', 'basePrice': 490,   'sector': 'FMCG'},
    'SBIN.BO':       {'name': 'State Bank of India',     'market': 'BSE', 'basePrice': 850,   'sector': 'Banking'},
    'BHARTIARTL.BO': {'name': 'Bharti Airtel',           'market': 'BSE', 'basePrice': 1650,  'sector': 'Telecom'},
    'BAJFINANCE.BO': {'name': 'Bajaj Finance',           'market': 'BSE', 'basePrice': 7200,  'sector': 'NBFC'},
    'KOTAKBANK.BO':  {'name': 'Kotak Mahindra Bank',     'market': 'BSE', 'basePrice': 1900,  'sector': 'Banking'},
    'LT.BO':         {'name': 'Larsen & Toubro',         'market': 'BSE', 'basePrice': 3500,  'sector': 'Infra'},
    'ASIANPAINT.BO': {'name': 'Asian Paints',            'market': 'BSE', 'basePrice': 2800,  'sector': 'Paints'},
    'AXISBANK.BO':   {'name': 'Axis Bank',               'market': 'BSE', 'basePrice': 1100,  'sector': 'Banking'},
    'MARUTI.BO':     {'name': 'Maruti Suzuki',           'market': 'BSE', 'basePrice': 12000, 'sector': 'Auto'},
    'SUNPHARMA.BO':  {'name': 'Sun Pharma',              'market': 'BSE', 'basePrice': 1700,  'sector': 'Pharma'},
    'TITAN.BO':      {'name': 'Titan Company',           'market': 'BSE', 'basePrice': 3400,  'sector': 'Consumer'},
    'WIPRO.BO':      {'name': 'Wipro Ltd.',              'market': 'BSE', 'basePrice': 450,   'sector': 'IT'},
    'NTPC.BO':       {'name': 'NTPC Ltd.',               'market': 'BSE', 'basePrice': 375,   'sector': 'Power'},
    'POWERGRID.BO':  {'name': 'Power Grid Corp.',        'market': 'BSE', 'basePrice': 330,   'sector': 'Power'},
    'ULTRACEMCO.BO': {'name': 'UltraTech Cement',        'market': 'BSE', 'basePrice': 10500, 'sector': 'Cement'},
    'NESTLEIND.BO':  {'name': 'Nestle India',            'market': 'BSE', 'basePrice': 2300,  'sector': 'FMCG'},
    'TATAMOTORS.BO': {'name': 'Tata Motors',             'market': 'BSE', 'basePrice': 820,   'sector': 'Auto'},
    'HCLTECH.BO':    {'name': 'HCL Technologies',        'market': 'BSE', 'basePrice': 1800,  'sector': 'IT'},
    'TATASTEEL.BO':  {'name': 'Tata Steel',              'market': 'BSE', 'basePrice': 160,   'sector': 'Metals'},
    'ONGC.BO':       {'name': 'ONGC Ltd.',               'market': 'BSE', 'basePrice': 270,   'sector': 'Energy'},
    'BAJAJFINSV.BO': {'name': 'Bajaj Finserv',           'market': 'BSE', 'basePrice': 1900,  'sector': 'NBFC'},
    'TATACONSUM.BO': {'name': 'Tata Consumer Products',  'market': 'BSE', 'basePrice': 1100,  'sector': 'FMCG'},
    'INDUSINDBK.BO': {'name': 'IndusInd Bank',           'market': 'BSE', 'basePrice': 950,   'sector': 'Banking'},
    'M&M.BO':        {'name': 'Mahindra & Mahindra',     'market': 'BSE', 'basePrice': 2900,  'sector': 'Auto'},
    'ADANIPORTS.BO': {'name': 'Adani Ports',             'market': 'BSE', 'basePrice': 1300,  'sector': 'Logistics'},
    'DRREDDY.BO':    {'name': "Dr. Reddy's Labs",        'market': 'BSE', 'basePrice': 6500,  'sector': 'Pharma'},
    'CIPLA.BO':      {'name': 'Cipla Ltd.',              'market': 'BSE', 'basePrice': 1550,  'sector': 'Pharma'},
    'DIVISLAB.BO':   {'name': "Divi's Laboratories",     'market': 'BSE', 'basePrice': 5800,  'sector': 'Pharma'},
    'HDFCLIFE.BO':   {'name': 'HDFC Life Insurance',     'market': 'BSE', 'basePrice': 700,   'sector': 'Insurance'},
    'SBILIFE.BO':    {'name': 'SBI Life Insurance',      'market': 'BSE', 'basePrice': 1600,  'sector': 'Insurance'},
    'HINDALCO.BO':   {'name': 'Hindalco Industries',     'market': 'BSE', 'basePrice': 680,   'sector': 'Metals'},
    'JSWSTEEL.BO':   {'name': 'JSW Steel',               'market': 'BSE', 'basePrice': 920,   'sector': 'Metals'},
    'HEROMOTOCO.BO': {'name': 'Hero MotoCorp',           'market': 'BSE', 'basePrice': 4800,  'sector': 'Auto'},
    'EICHERMOT.BO':  {'name': 'Eicher Motors',           'market': 'BSE', 'basePrice': 5100,  'sector': 'Auto'},
    'GRASIM.BO':     {'name': 'Grasim Industries',       'market': 'BSE', 'basePrice': 2700,  'sector': 'Cement'},
    'ZOMATO.BO':     {'name': 'Zomato Ltd.',              'market': 'BSE', 'basePrice': 230,   'sector': 'Tech'},
    'BEL.BO':        {'name': 'Bharat Electronics',      'market': 'BSE', 'basePrice': 280,   'sector': 'Defence'},
    'HAL.BO':        {'name': 'Hindustan Aeronautics',   'market': 'BSE', 'basePrice': 4300,  'sector': 'Defence'},

    # UK STOCKS
    'HSBA.L': {'name': 'HSBC Holdings', 'market': 'UK', 'basePrice': 750},
    'BP.L': {'name': 'BP plc', 'market': 'UK', 'basePrice': 480},
    'AZN.L': {'name': 'AstraZeneca', 'market': 'UK', 'basePrice': 11500},
    'SHEL.L': {'name': 'Shell plc', 'market': 'UK', 'basePrice': 2800},
    
    # GERMANY STOCKS
    'SAP.DE': {'name': 'SAP SE', 'market': 'GERMANY', 'basePrice': 220},
    'SIE.DE': {'name': 'Siemens AG', 'market': 'GERMANY', 'basePrice': 185},
    'BMW.DE': {'name': 'BMW AG', 'market': 'GERMANY', 'basePrice': 85},
    
    # CRYPTO
    'BTC-USD': {'name': 'Bitcoin', 'market': 'CRYPTO', 'basePrice': 105000},
    'ETH-USD': {'name': 'Ethereum', 'market': 'CRYPTO', 'basePrice': 4000},
    'SOL-USD': {'name': 'Solana', 'market': 'CRYPTO', 'basePrice': 220},
    
    # ETFs
    'SPY': {'name': 'S&P 500 ETF', 'market': 'ETF', 'basePrice': 600},
    'QQQ': {'name': 'Nasdaq 100 ETF', 'market': 'ETF', 'basePrice': 530},
    'IWM': {'name': 'Russell 2000 ETF', 'market': 'ETF', 'basePrice': 230},
}


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for rate limit protection.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, block requests
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, max_failures: int = 10, reset_timeout: int = 120):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
        self.total_429_errors = 0
    
    def record_success(self):
        """Record successful API call."""
        self.failures = 0
        self.is_open = False
    
    def record_failure(self, is_rate_limit: bool = False):
        """Record failed API call."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if is_rate_limit:
            self.total_429_errors += 1
        
        if self.failures >= self.max_failures:
            self.is_open = True
            logger.warning(f"Circuit breaker OPENED after {self.failures} failures")
    
    def can_proceed(self) -> bool:
        """Check if we can make an API call."""
        if not self.is_open:
            return True
        
        # Check if reset timeout has passed
        if self.last_failure_time:
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed >= self.reset_timeout:
                logger.info("Circuit breaker HALF-OPEN, testing...")
                self.is_open = False
                self.failures = 0
                return True
        
        return False
    
    def get_status(self) -> dict:
        return {
            "state": "OPEN" if self.is_open else "CLOSED",
            "failures": self.failures,
            "total_429_errors": self.total_429_errors,
            "can_proceed": self.can_proceed()
        }


# Global circuit breaker
_circuit_breaker = CircuitBreaker()


# =============================================================================
# FINNHUB REST QUOTE (primary real-time source)
# =============================================================================

async def _fetch_finnhub_quote_async(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch real-time quote from Finnhub REST API.
    Finnhub uses plain tickers (no exchange suffix) for US stocks.
    For non-US symbols (e.g. RELIANCE.NS), strip the suffix — Finnhub
    will return null and we fall through to yfinance naturally.
    """
    if not FINNHUB_KEY:
        return None
    fh_symbol = symbol.split(".")[0] if "." in symbol else symbol
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": fh_symbol, "token": FINNHUB_KEY},
            )
            d = r.json()
        price = d.get("c")      # current price
        prev  = d.get("pc") or price
        if not price:
            return None
        return {
            "price":         round(price, 4),
            "change":        round(price - prev, 4),
            "changePercent": round((price - prev) / prev * 100, 4) if prev else 0,
            "high":          d.get("h"),
            "low":           d.get("l"),
            "open":          d.get("o"),
            "prevClose":     prev,
            "volume":        d.get("v", 0),
            "dataQuality":   "LIVE",
            "source":        "FINNHUB",
        }
    except Exception as e:
        logger.warning(f"Finnhub quote error for {symbol}: {e}")
        return None


# =============================================================================
# TWELVE DATA REST QUOTE (primary source for Indian NSE/BSE stocks)
# Free tier: 800 req/day, 8 req/min — enough for 50 stocks × 16 polls/day
# =============================================================================

def _to_twelvedata_symbol(symbol: str) -> Optional[str]:
    """
    Convert internal symbol to Twelve Data format.
      RELIANCE.NS  →  RELIANCE:NSE
      HDFCBANK.NS  →  HDFCBANK:NSE
      RELIANCE.BO  →  RELIANCE:BSE
      AAPL         →  AAPL  (unchanged — Finnhub handles US)
    Returns None for non-Indian symbols so caller falls through.
    """
    if symbol.endswith(".NS"):
        return f"{symbol[:-3]}:NSE"
    if symbol.endswith(".BO"):
        return f"{symbol[:-3]}:BSE"
    return None


_TD_INTERVAL_MAP = {
    # yfinance/internal → Twelve Data interval
    "1m": "1min", "2m": "2min", "5m": "5min", "15m": "15min",
    "30m": "30min", "60m": "1h", "1h": "1h", "90m": "90min",
    "1d": "1day", "5d": "1day", "1wk": "1week", "1mo": "1month",
    "3mo": "1month",
}

_TD_OUTPUTSIZE_MAP = {
    # period → number of candles
    "1d": 390, "5d": 390, "1mo": 30, "3mo": 66,
    "6mo": 130, "1y": 252, "2y": 504, "5y": 1000,
}


async def _fetch_twelvedata_history_async(
    symbol: str, period: str = "1mo", interval: str = "1d"
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch OHLCV history from Twelve Data for Indian NSE/BSE symbols.
    Returns a list of candle dicts matching the internal format.
    """
    if not TWELVE_DATA_KEY:
        return None
    td_symbol = _to_twelvedata_symbol(symbol)
    if not td_symbol:
        return None
    td_interval  = _TD_INTERVAL_MAP.get(interval, "1day")
    outputsize   = _TD_OUTPUTSIZE_MAP.get(period, 30)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.twelvedata.com/time_series",
                params={
                    "symbol": td_symbol,
                    "interval": td_interval,
                    "outputsize": outputsize,
                    "apikey": TWELVE_DATA_KEY,
                    "order": "ASC",
                },
            )
            d = r.json()
        if d.get("status") == "error" or "values" not in d:
            logger.warning(f"Twelve Data history error for {td_symbol}: {d.get('message','')}")
            return None
        candles = []
        for row in d["values"]:
            candles.append({
                "timestamp": row["datetime"],
                "date":      row["datetime"],
                "open":      float(row["open"]),
                "high":      float(row["high"]),
                "low":       float(row["low"]),
                "close":     float(row["close"]),
                "volume":    int(row.get("volume") or 0),
            })
        return candles if candles else None
    except Exception as e:
        logger.warning(f"Twelve Data history error for {symbol}: {e}")
        return None


# Twelve Data quota guard — when daily credits are exhausted (429), skip TD calls
# for 4 hours rather than hammering the API every 2 minutes.
_td_backoff_until: Optional[datetime] = None


async def _fetch_twelvedata_quote_async(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch real-time quote from Twelve Data for Indian NSE/BSE stocks.
    Only called when TWELVE_DATA_API_KEY is set.
    """
    global _td_backoff_until
    if not TWELVE_DATA_KEY:
        return None
    if _td_backoff_until and datetime.now() < _td_backoff_until:
        return None          # Quota exhausted — skip until backoff window expires
    td_symbol = _to_twelvedata_symbol(symbol)
    if not td_symbol:
        return None          # Not an Indian symbol; let Finnhub/yfinance handle it
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                "https://api.twelvedata.com/quote",
                params={"symbol": td_symbol, "apikey": TWELVE_DATA_KEY},
            )
            d = r.json()
        if d.get("status") == "error" or "close" not in d:
            msg = d.get("message", "")
            is_rate_limit = d.get("code") == 429 or "429" in str(d.get("code", "")) or "run out" in msg.lower() or "too many" in msg.lower()
            if is_rate_limit:
                # Back off for 4 hours — daily quota resets at midnight UTC
                _td_backoff_until = datetime.now() + timedelta(hours=4)
                logger.warning(
                    f"Twelve Data daily quota EXHAUSTED — backing off for 4h "
                    f"(resumes ~{_td_backoff_until.strftime('%H:%M')}). "
                    f"Falling through to Yahoo Direct for Indian stocks."
                )
            else:
                logger.warning(f"Twelve Data no data for {td_symbol}: {msg}")
            return None
        price      = float(d["close"])
        prev_close = float(d.get("previous_close") or price)
        change     = float(d.get("change") or (price - prev_close))
        change_pct = float(d.get("percent_change") or ((change / prev_close * 100) if prev_close else 0))
        return {
            "price":         round(price, 2),
            "change":        round(change, 2),
            "changePercent": round(change_pct, 2),
            "high":          float(d["high"])   if d.get("high")   else None,
            "low":           float(d["low"])    if d.get("low")    else None,
            "open":          float(d["open"])   if d.get("open")   else None,
            "prevClose":     round(prev_close, 2),
            "volume":        int(d.get("volume") or 0),
            "dataQuality":   "LIVE",
            "source":        "TWELVE_DATA",
        }
    except Exception as e:
        logger.warning(f"Twelve Data quote error for {symbol}: {e}")
        return None


# =============================================================================
# YAHOO FINANCE DIRECT (browser headers — bypasses yfinance rate limit)
# =============================================================================

_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
}

async def _fetch_yahoo_quote_async(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Direct Yahoo Finance v8 API call with browser User-Agent.
    Avoids the yfinance library which Yahoo actively rate-limits on shared IPs.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_YF_HEADERS, follow_redirects=True) as client:
            r = await client.get(url, params={"interval": "1d", "range": "2d"})
            if r.status_code == 429:
                logger.warning(f"Yahoo direct: rate limited for {symbol}")
                return None
            d = r.json()
        result = d.get("chart", {}).get("result")
        if not result:
            return None
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if not price:
            return None
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose") or price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        market = _get_market_from_symbol(symbol)
        currency = get_currency_symbol(market)
        name = GLOBAL_STOCKS.get(symbol, {}).get("name", symbol)
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change": round(change, 2),
            "changePercent": round(change_pct, 2),
            "high": meta.get("regularMarketDayHigh"),
            "low": meta.get("regularMarketDayLow"),
            "open": meta.get("regularMarketOpen"),
            "prevClose": round(prev_close, 2),
            "volume": meta.get("regularMarketVolume", 0),
            "currency": currency,
            "market": market,
            "dataQuality": "LIVE",
            "source": "YAHOO_DIRECT",
        }
    except Exception as e:
        logger.warning(f"Yahoo direct quote error for {symbol}: {e}")
        return None


async def _fetch_yahoo_history_async(symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[List[Dict]]:
    """Direct Yahoo Finance history with browser headers."""
    _period_map = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y"}
    # Yahoo Finance has no native 4h interval; use 1h candles and return more of them
    _interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "4h": "60m", "1d": "1d", "1w": "1wk", "1wk": "1wk"}
    yf_period = _period_map.get(period, "1mo")
    yf_interval = _interval_map.get(interval, "1d")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_YF_HEADERS, follow_redirects=True) as client:
            r = await client.get(url, params={"interval": yf_interval, "range": yf_period})
            if r.status_code == 429:
                logger.warning(f"Yahoo direct history: rate limited for {symbol}")
                return None
            d = r.json()
        result = d.get("chart", {}).get("result")
        if not result:
            return None
        timestamps = result[0].get("timestamp", [])
        ohlcv = result[0].get("indicators", {}).get("quote", [{}])[0]
        opens   = ohlcv.get("open", [])
        highs   = ohlcv.get("high", [])
        lows    = ohlcv.get("low", [])
        closes  = ohlcv.get("close", [])
        volumes = ohlcv.get("volume", [])
        candles = []
        for i, ts in enumerate(timestamps):
            c = closes[i] if i < len(closes) and closes[i] else None
            if c is None:
                continue
            from datetime import timezone
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            candles.append({
                "timestamp": dt.isoformat(),
                "date": dt.isoformat(),
                "open":   round(opens[i]   if i < len(opens)   and opens[i]   else c, 2),
                "high":   round(highs[i]   if i < len(highs)   and highs[i]   else c, 2),
                "low":    round(lows[i]    if i < len(lows)    and lows[i]    else c, 2),
                "close":  round(c, 2),
                "volume": int(volumes[i]) if i < len(volumes) and volumes[i] else 0,
            })
        return candles if candles else None
    except Exception as e:
        logger.warning(f"Yahoo direct history error for {symbol}: {e}")
        return None


# =============================================================================
# YFINANCE WRAPPER (fast_info)
# =============================================================================

def _fetch_yfinance_quote_sync(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Synchronous yfinance fetch using fast_info (not info!).
    
    fast_info uses JSON API endpoints instead of HTML scraping.
    This is the ONLY method that should be used in production.
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available")
        return None
    
    if not _circuit_breaker.can_proceed():
        logger.warning(f"Circuit breaker OPEN, skipping yfinance for {symbol}")
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Use fast_info - NOT info!
        # fast_info uses JSON API, info uses HTML scraping
        fi = ticker.fast_info
        
        if fi is None or not hasattr(fi, 'last_price'):
            logger.warning(f"fast_info empty for {symbol}")
            return None
        
        # Get price data from fast_info
        price = fi.last_price if hasattr(fi, 'last_price') else None
        prev_close = fi.previous_close if hasattr(fi, 'previous_close') else None
        
        if price is None:
            return None
        
        # Calculate change
        change = 0
        change_pct = 0
        if prev_close and prev_close > 0:
            change = price - prev_close
            change_pct = (change / prev_close) * 100
        
        # Get additional data
        day_high = fi.day_high if hasattr(fi, 'day_high') else price * 1.01
        day_low = fi.day_low if hasattr(fi, 'day_low') else price * 0.99
        open_price = fi.open if hasattr(fi, 'open') else prev_close
        volume = fi.last_volume if hasattr(fi, 'last_volume') else 0
        market_cap = fi.market_cap if hasattr(fi, 'market_cap') else None
        
        # Determine market from symbol
        market = _get_market_from_symbol(symbol)
        currency = MARKET_CONFIG.get(market, {}).get('currency', '$')
        
        # Get company name (fallback to GLOBAL_STOCKS or symbol)
        name = GLOBAL_STOCKS.get(symbol, {}).get('name', symbol)
        
        _circuit_breaker.record_success()
        
        return {
            'symbol': symbol,
            'price': round(price, 2),
            'change': round(change, 2),
            'changePercent': round(change_pct, 2),
            'previousClose': round(prev_close, 2) if prev_close else None,
            'prevClose': round(prev_close, 2) if prev_close else None,
            'open': round(open_price, 2) if open_price else None,
            'dayOpen': round(open_price, 2) if open_price else None,
            'high': round(day_high, 2) if day_high else None,
            'dayHigh': round(day_high, 2) if day_high else None,
            'low': round(day_low, 2) if day_low else None,
            'dayLow': round(day_low, 2) if day_low else None,
            'volume': int(volume) if volume else 0,
            'marketCap': market_cap,
            'market': market,
            'currency': currency,
            'name': name,
            'companyName': name,
            'shortName': name,
            'dataQuality': 'LIVE',
            'source': 'YFINANCE',
            'timestamp': datetime.now().isoformat(),
        }
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = '429' in error_str or 'rate' in error_str or 'too many' in error_str
        
        _circuit_breaker.record_failure(is_rate_limit=is_rate_limit)
        logger.warning(f"yfinance error for {symbol}: {e}")
        
        return None


def _fetch_yfinance_history_sync(
    symbol: str, 
    period: str = "1mo",
    interval: str = "1d"
) -> Optional[List[Dict]]:
    """
    Fetch historical OHLCV data from yfinance.
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    if not _circuit_breaker.can_proceed():
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return None
        
        candles = []
        for idx, row in hist.iterrows():
            candles.append({
                'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
        
        _circuit_breaker.record_success()
        return candles
        
    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = '429' in error_str or 'rate' in error_str
        _circuit_breaker.record_failure(is_rate_limit=is_rate_limit)
        logger.warning(f"yfinance history error for {symbol}: {e}")
        return None


# =============================================================================
# MME SIMULATOR (FALLBACK)
# =============================================================================

def _generate_mme_quote(symbol: str) -> Dict[str, Any]:
    """
    Market Model Engine - Simulated fallback.
    
    Generates deterministic but realistic-looking price data
    when yfinance is unavailable.
    """
    # Get stock info
    stock_info = GLOBAL_STOCKS.get(symbol, {})
    market = stock_info.get('market') or _get_market_from_symbol(symbol)
    base_price = stock_info.get('basePrice', 100)
    name = stock_info.get('name', symbol)
    currency = MARKET_CONFIG.get(market, {}).get('currency', '$')
    
    # Generate deterministic but varying price
    seed = f"{symbol}:{datetime.now().strftime('%Y%m%d%H%M')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    price = base_price * (0.95 + rng.random() * 0.10)
    prev_close = base_price * (0.96 + rng.random() * 0.08)
    change = price - prev_close
    change_pct = (change / prev_close) * 100 if prev_close else 0
    
    return {
        'symbol': symbol,
        'price': round(price, 2),
        'change': round(change, 2),
        'changePercent': round(change_pct, 2),
        'previousClose': round(prev_close, 2),
        'prevClose': round(prev_close, 2),
        'open': round(prev_close * (1 + (rng.random() - 0.5) * 0.01), 2),
        'dayOpen': round(prev_close * (1 + (rng.random() - 0.5) * 0.01), 2),
        'high': round(max(price, prev_close) * (1 + rng.random() * 0.02), 2),
        'dayHigh': round(max(price, prev_close) * (1 + rng.random() * 0.02), 2),
        'low': round(min(price, prev_close) * (1 - rng.random() * 0.02), 2),
        'dayLow': round(min(price, prev_close) * (1 - rng.random() * 0.02), 2),
        'volume': int(rng.random() * 50000000),
        'market': market,
        'currency': currency,
        'name': name,
        'companyName': name,
        'shortName': name,
        'dataQuality': 'SIMULATED',
        'source': 'MME',
        'timestamp': datetime.now().isoformat(),
    }


def _generate_mme_history(
    symbol: str, 
    period: str = "1mo",
    interval: str = "1d"
) -> List[Dict]:
    """Generate simulated historical data."""
    stock_info = GLOBAL_STOCKS.get(symbol, {})
    base_price = stock_info.get('basePrice', 100)
    
    # Determine number of candles
    period_days = {'1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365}
    days = period_days.get(period, 30)
    
    interval_map = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '1d': 1440}
    
    seed = f"history:{symbol}:{period}:{interval}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    candles = []
    current_price = base_price
    
    for i in range(min(days * 2, 200)):  # Cap at 200 candles
        timestamp = datetime.now() - timedelta(days=days - i)
        
        # Random walk
        change_pct = (rng.random() - 0.48) * 3  # Slight upward bias
        current_price *= (1 + change_pct / 100)
        
        open_price = current_price * (1 + (rng.random() - 0.5) * 0.01)
        close_price = current_price
        high = max(open_price, close_price) * (1 + rng.random() * 0.015)
        low = min(open_price, close_price) * (1 - rng.random() * 0.015)
        
        candles.append({
            'timestamp': timestamp.isoformat(),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close_price, 2),
            'volume': int(rng.random() * 20000000)
        })
    
    return candles


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_market_from_symbol(symbol: str) -> str:
    """Determine market from symbol suffix."""
    symbol = symbol.upper()
    
    if symbol in GLOBAL_STOCKS:
        return GLOBAL_STOCKS[symbol].get('market', 'US')
    
    if '.NS' in symbol:
        return 'INDIA'
    elif '.BO' in symbol:
        return 'BSE'
    elif '.L' in symbol:
        return 'UK'
    elif '.DE' in symbol:
        return 'GERMANY'
    elif '.PA' in symbol:
        return 'FRANCE'
    elif '.T' in symbol:
        return 'JAPAN'
    elif '.SS' in symbol or '.SZ' in symbol:
        return 'CHINA'
    elif '.HK' in symbol:
        return 'HONGKONG'
    elif '.AX' in symbol:
        return 'AUSTRALIA'
    elif '.TO' in symbol:
        return 'CANADA'
    elif '.SA' in symbol:
        return 'BRAZIL'
    elif '.KS' in symbol:
        return 'KOREA'
    elif '-USD' in symbol:
        return 'CRYPTO'
    elif '=X' in symbol:
        return 'FOREX'
    elif '=F' in symbol:
        return 'COMMODITIES'
    
    return 'US'


def get_currency_symbol(market: str) -> str:
    """Get currency symbol for a market."""
    return MARKET_CONFIG.get(market.upper(), {}).get('currency', '$')


def get_stocks_for_market(market: str) -> List[Dict]:
    """Get all stocks for a specific market."""
    market = market.upper()
    return [
        {'symbol': sym, **info}
        for sym, info in GLOBAL_STOCKS.items()
        if info.get('market', '').upper() == market
    ]


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class MarketDataService:
    """
    Production-grade market data service.
    
    Data flow:
        1. yfinance (LIVE) → Primary source
        2. LKG Cache (CACHED) → Fallback when live fails
        3. MME (SIMULATED) → Final fallback
    """
    
    def __init__(self):
        self.cache = get_cache_manager("market_data")
        self.singleflight = get_singleflight()
        self.stocks = GLOBAL_STOCKS
        self.markets = MARKET_CONFIG
        
        # Stats
        self.stats = {
            "live_fetches": 0,
            "cache_hits": 0,
            "lkg_fallbacks": 0,
            "mme_fallbacks": 0,
            "last_live_fetch": None
        }
    
    async def get_quote(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get quote with full fallback chain.

        Flow: Finnhub (real-time) → yfinance → LKG Cache → MME Simulator
        """
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"
        is_indian = bool(_to_twelvedata_symbol(symbol))

        # 1. Check fresh cache (unless force refresh)
        # Use 5-minute TTL for Indian stocks (Twelve Data free tier = 8 req/min).
        # yfinance/Finnhub US stocks can stay at 90s.
        quote_ttl = 300 if is_indian else 90
        if not force_refresh:
            entry = self.cache.get(cache_key, ttl_seconds=quote_ttl)
            if entry:
                self.stats["cache_hits"] += 1
                data = entry.data
                data['dataQuality'] = 'CACHED'
                data['cacheAge'] = entry.age_human()
                return data

        # 2a. Twelve Data — primary for Indian stocks IF plan supports it
        if TWELVE_DATA_KEY and is_indian:
            td_data = await _fetch_twelvedata_quote_async(symbol)
            if td_data:
                self.cache.set(cache_key, td_data, source="TWELVE_DATA")
                self.stats["live_fetches"] += 1
                self.stats["last_live_fetch"] = datetime.now().isoformat()
                return td_data

        # 2b. Yahoo Finance direct HTTP (browser headers) — works for all symbols
        # Used as primary for Indian stocks when Twelve Data plan doesn't cover NSE
        if is_indian:
            yahoo_data = await _fetch_yahoo_quote_async(symbol)
            if yahoo_data:
                self.cache.set(cache_key, yahoo_data, source="YAHOO_DIRECT")
                self.stats["live_fetches"] += 1
                self.stats["last_live_fetch"] = datetime.now().isoformat()
                return yahoo_data

        # 2c. Finnhub REST — primary for US stocks
        if FINNHUB_KEY and not is_indian:
            fh_data = await _fetch_finnhub_quote_async(symbol)
            if fh_data:
                self.cache.set(cache_key, fh_data, source="FINNHUB")
                self.stats["live_fetches"] += 1
                self.stats["last_live_fetch"] = datetime.now().isoformat()
                return fh_data

        # 3. Try yfinance via SingleFlight (prevents thundering herd)
        async def fetch_live():
            return await asyncio.wait_for(
                run_in_threadpool(_fetch_yfinance_quote_sync, symbol),
                timeout=8.0,  # 8s — fast fallback to LKG/MME rather than blocking UI
            )

        try:
            live_data = await self.singleflight.do(f"quote:{symbol}", fetch_live)

            if live_data:
                self.cache.set(cache_key, live_data, source="LIVE")
                self.stats["live_fetches"] += 1
                self.stats["last_live_fetch"] = datetime.now().isoformat()
                return live_data

        except asyncio.TimeoutError:
            logger.warning(f"Live fetch timed out for {symbol} (15s)")
        except Exception as e:
            logger.warning(f"Live fetch failed for {symbol}: {e}")

        # 4. LKG cache (any age)
        lkg = self.cache.get_lkg(cache_key)
        if lkg:
            self.stats["lkg_fallbacks"] += 1
            data = dict(lkg.data)
            data['dataQuality'] = 'LKG'
            data['cacheAge'] = lkg.age_human()
            data['source'] = 'LKG_CACHE'
            logger.info(f"Using LKG for {symbol} ({lkg.age_human()})")
            return data

        # 5. Final fallback: MME simulator
        self.stats["mme_fallbacks"] += 1
        logger.info(f"Using MME simulator for {symbol}")
        return _generate_mme_quote(symbol)
    
    async def get_history(
        self, 
        symbol: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Tuple[List[Dict], str]:
        """
        Get historical data with fallback.
        
        Returns: (candles, source)
        """
        symbol = symbol.upper()
        cache_key = f"history:{symbol}:{period}:{interval}"
        
        # Check cache first
        entry = self.cache.get(cache_key, ttl_seconds=300)  # 5 min TTL for history
        if entry:
            return entry.data, "CACHED"
        
        # 1a. Twelve Data — primary for Indian (NSE/BSE) history
        if TWELVE_DATA_KEY and _to_twelvedata_symbol(symbol):
            td_hist = await _fetch_twelvedata_history_async(symbol, period, interval)
            if td_hist:
                self.cache.set(cache_key, td_hist, source="TWELVE_DATA")
                return td_hist, "TWELVE_DATA"

        # 1b. Yahoo Finance direct HTTP — browser headers bypass yfinance rate limit
        yahoo_hist = await _fetch_yahoo_history_async(symbol, period, interval)
        if yahoo_hist:
            self.cache.set(cache_key, yahoo_hist, source="YAHOO_DIRECT")
            return yahoo_hist, "YAHOO_DIRECT"

        # 1c. yfinance library fallback
        async def fetch_live():
            return await asyncio.wait_for(
                run_in_threadpool(
                    _fetch_yfinance_history_sync, symbol, period, interval
                ),
                timeout=8.0,
            )

        try:
            live_data = await self.singleflight.do(cache_key, fetch_live)

            if live_data:
                self.cache.set(cache_key, live_data, source="LIVE")
                return live_data, "LIVE"

        except asyncio.TimeoutError:
            logger.warning(f"History fetch timed out for {symbol} (8s)")
        except Exception as e:
            logger.warning(f"History fetch failed for {symbol}: {e}")
        
        # LKG fallback
        lkg = self.cache.get_lkg(cache_key)
        if lkg:
            return lkg.data, "LKG"
        
        # MME fallback
        return _generate_mme_history(symbol, period, interval), "SIMULATED"
    
    async def get_top_movers(self, market: str, limit: int = 5) -> Dict[str, Any]:
        """Get top gainers and losers for a market."""
        market = market.upper()
        currency = get_currency_symbol(market)
        
        # Get stocks for this market
        market_stocks = get_stocks_for_market(market)
        
        if not market_stocks:
            market_stocks = get_stocks_for_market('US')
        
        # Fetch quotes for all stocks
        movers = []
        for stock in market_stocks[:20]:  # Limit to prevent rate limiting
            try:
                quote = await self.get_quote(stock['symbol'])
                movers.append({
                    'symbol': quote['symbol'],
                    'name': quote.get('name', quote['symbol']),
                    'shortName': quote.get('shortName', quote['symbol']),
                    'price': quote['price'],
                    'change': quote['change'],
                    'changePercent': quote['changePercent'],
                    'currency': currency,
                    'market': market,
                    'dataQuality': quote.get('dataQuality', 'UNKNOWN')
                })
            except Exception as e:
                logger.warning(f"Failed to get quote for {stock['symbol']}: {e}")
        
        # Sort by change percent
        movers.sort(key=lambda x: x['changePercent'], reverse=True)
        gainers = [m for m in movers if m['changePercent'] > 0][:limit]
        losers = [m for m in movers if m['changePercent'] < 0]
        losers.sort(key=lambda x: x['changePercent'])
        losers = losers[:limit]
        
        return {
            'market': market,
            'currency': currency,
            'gainers': gainers,
            'losers': losers,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch quotes for multiple symbols at once.

        Returns: {results: {SYMBOL: quote_data, ...}, asOf: timestamp}
        """
        results = {}
        for symbol in symbols:
            sym = symbol.upper().strip()
            if not sym:
                continue
            try:
                quote = await self.get_quote(sym)
                # Add asOf field that some callers expect
                quote['asOf'] = quote.get('timestamp', datetime.now().isoformat())
                results[sym] = quote
            except Exception as e:
                logger.warning(f"Batch quote failed for {sym}: {e}")

        return {
            "results": results,
            "count": len(results),
            "asOf": datetime.now().isoformat()
        }

    async def get_candles(
        self,
        symbol: str,
        interval: str = "1d",
        lookback: int = 100
    ) -> Dict[str, Any]:
        """
        Get OHLCV candles for a symbol.

        Maps interval/lookback to period for get_history().
        Returns: {symbol, interval, count, candles, source, dataQuality}
        """
        symbol = symbol.upper()

        # Map lookback + interval to a yfinance-compatible period
        if interval in ("1m", "5m", "15m", "30m"):
            period = "5d"
        elif interval in ("1h", "4h"):
            period = "1mo"
        elif interval == "1d":
            if lookback <= 30:
                period = "1mo"
            elif lookback <= 90:
                period = "3mo"
            elif lookback <= 180:
                period = "6mo"
            else:
                period = "1y"
        elif interval in ("1w", "1wk"):
            period = "1y"
        else:
            period = "1mo"

        candles, source = await self.get_history(symbol, period=period, interval=interval)

        # Trim to lookback
        candles = candles[-lookback:] if len(candles) > lookback else candles

        market = _get_market_from_symbol(symbol)
        currency = get_currency_symbol(market)

        return {
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "candles": candles,
            "source": source,
            "dataQuality": source,
            "currency": currency,
        }

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get a broad market overview across key indices and sectors."""
        overview_symbols = ["SPY", "QQQ", "DIA", "IWM", "BTC-USD", "GC=F"]

        results = {}
        for sym in overview_symbols:
            try:
                quote = await self.get_quote(sym)
                results[sym] = {
                    "symbol": sym,
                    "name": quote.get("name", sym),
                    "price": quote["price"],
                    "change": quote["change"],
                    "changePercent": quote["changePercent"],
                    "dataQuality": quote.get("dataQuality", "UNKNOWN"),
                }
            except Exception as e:
                logger.warning(f"Overview fetch failed for {sym}: {e}")

        return {
            "overview": results,
            "timestamp": datetime.now().isoformat()
        }

    async def get_health(self) -> Dict[str, Any]:
        """Get detailed service health including circuit breaker state."""
        status = self.get_service_status()

        return {
            "status": status["health"],
            "yfinance": {
                "available": status["yfinance_available"],
                "breaker": status["circuit_breaker"],
            },
            "cache": status["cache"],
            "stats": status["stats"],
            "timestamp": status["timestamp"]
        }

    def get_roadmap(self) -> Dict[str, Any]:
        """Get product roadmap / feature status."""
        return {
            "version": "4.9",
            "features": {
                "live_quotes": {"status": "GA", "description": "Real-time quotes via yfinance"},
                "historical_data": {"status": "GA", "description": "OHLCV history with caching"},
                "top_movers": {"status": "GA", "description": "18 global markets"},
                "signals": {"status": "GA", "description": "RSI, MACD, Bollinger, ATR"},
                "strategy_intelligence": {"status": "GA", "description": "AI-powered strategy ranking"},
                "sentiment": {"status": "GA", "description": "Multi-source sentiment aggregation"},
                "ai_chatbot": {"status": "GA", "description": "Groq Llama 3.3 70B with fallback"},
                "payments_stripe": {"status": "GA", "description": "Stripe checkout integration"},
                "payments_razorpay": {"status": "GA", "description": "Razorpay for India/INR"},
                "websockets": {"status": "BETA", "description": "Real-time price streaming"},
                "portfolio_tracking": {"status": "PLANNED", "description": "Track user portfolios"},
                "alerts": {"status": "PLANNED", "description": "Price and signal alerts"},
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_service_status(self) -> Dict[str, Any]:
        """Get service health status."""
        cache_stats = self.cache.get_stats()
        circuit_status = _circuit_breaker.get_status()
        
        # Determine overall health
        health = "HEALTHY"
        if circuit_status["state"] == "OPEN":
            health = "DEGRADED"
        if self.stats["mme_fallbacks"] > self.stats["live_fetches"]:
            health = "DEGRADED"
        
        return {
            "health": health,
            "yfinance_available": YFINANCE_AVAILABLE,
            "circuit_breaker": circuit_status,
            "cache": cache_stats,
            "stats": self.stats,
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get singleton market data service instance."""
    global _service
    if _service is None:
        _service = MarketDataService()
    return _service


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = get_market_data_service()
        
        print("\n" + "="*60)
        print("MARKET DATA SERVICE TEST")
        print("="*60)
        
        # Test quote
        print("\n📊 Testing AAPL quote...")
        quote = await service.get_quote("AAPL")
        print(f"   Price: ${quote['price']}")
        print(f"   Change: {quote['changePercent']:.2f}%")
        print(f"   Source: {quote['dataQuality']} ({quote.get('source', 'N/A')})")
        
        # Test history
        print("\n📈 Testing AAPL history...")
        history, source = await service.get_history("AAPL", "5d", "1d")
        print(f"   Candles: {len(history)}")
        print(f"   Source: {source}")
        
        # Service status
        print("\n⚙️ Service Status:")
        status = service.get_service_status()
        print(f"   Health: {status['health']}")
        print(f"   yfinance: {status['yfinance_available']}")
        print(f"   Circuit: {status['circuit_breaker']['state']}")
        
    asyncio.run(test())
