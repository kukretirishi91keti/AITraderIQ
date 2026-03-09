"""
screener_universe.py - Static Universe Screener Endpoint
=========================================================
Version: 5.8.5 - ALL 22 MARKETS

Add this file to: backend/routers/screener_universe.py

Provides the /api/screener/universe endpoint with all 22 market categories.
Supports demo mode with deterministic data generation.

CURRENCY ENCODING: Uses Unicode escapes for maximum compatibility
"""

from fastapi import APIRouter
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import os
import logging

router = APIRouter(prefix="/api/screener", tags=["screener-universe"])
logger = logging.getLogger(__name__)

# Check demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ============================================================
# COMPREHENSIVE STATIC UNIVERSE - ALL 22 MARKETS
# ============================================================

STATIC_UNIVERSE = {
    # === US Markets ===
    'US_Tech': [
        'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD',
        'ADBE', 'CRM', 'NFLX', 'INTC'
    ],
    
    # === India ===
    'India': [
        'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
        'WIPRO.NS', 'SBIN.NS', 'BHARTIARTL.NS'
    ],
    
    # === UK ===
    'UK': [
        'HSBA.L', 'BP.L', 'SHEL.L', 'AZN.L', 'GSK.L', 'VOD.L', 'LLOY.L'
    ],
    
    # === Germany ===
    'Germany': [
        'SAP.DE', 'SIE.DE', 'ALV.DE', 'DTE.DE', 'BAS.DE', 'BMW.DE'
    ],
    
    # === France ===
    'France': [
        'OR.PA', 'MC.PA', 'TTE.PA', 'SAN.PA', 'AIR.PA', 'BNP.PA'
    ],
    
    # === Japan ===
    'Japan': [
        '7203.T', '6758.T', '9984.T', '6861.T', '7267.T', '8306.T'
    ],
    
    # === China ===
    'China': [
        '9988.HK', '9618.HK', '3690.HK', '1810.HK', '2020.HK', '0968.HK'
    ],
    
    # === Hong Kong ===
    'HongKong': [
        '0700.HK', '0005.HK', '1299.HK', '0941.HK', '0388.HK', '0016.HK'
    ],
    
    # === Taiwan (NEW - 22nd market) ===
    'Taiwan': [
        '2330.TW', '2317.TW', '2454.TW', '2308.TW', '2412.TW', '2882.TW'
    ],
    
    # === Australia ===
    'Australia': [
        'BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX', 'WBC.AX', 'ANZ.AX'
    ],
    
    # === Canada ===
    'Canada': [
        'RY.TO', 'TD.TO', 'SHOP.TO', 'ENB.TO', 'CNR.TO', 'BMO.TO'
    ],
    
    # === Brazil ===
    'Brazil': [
        'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'B3SA3.SA', 'WEGE3.SA'
    ],
    
    # === Korea ===
    'Korea': [
        '005930.KS', '000660.KS', '035420.KS', '051910.KS', '006400.KS', '035720.KS'
    ],
    
    # === Singapore ===
    'Singapore': [
        'D05.SI', 'O39.SI', 'U11.SI', 'Z74.SI', 'C38U.SI', 'A17U.SI'
    ],
    
    # === Switzerland ===
    'Switzerland': [
        'NESN.SW', 'ROG.SW', 'NOVN.SW', 'UBSG.SW', 'ZURN.SW', 'ABBN.SW'
    ],
    
    # === Netherlands ===
    'Netherlands': [
        'ASML.AS', 'INGA.AS', 'PHIA.AS', 'UNA.AS', 'HEIA.AS', 'AD.AS'
    ],
    
    # === Spain ===
    'Spain': [
        'SAN.MC', 'IBE.MC', 'ITX.MC', 'BBVA.MC', 'TEF.MC', 'REP.MC'
    ],
    
    # === Italy ===
    'Italy': [
        'ENI.MI', 'ENEL.MI', 'ISP.MI', 'UCG.MI', 'RACE.MI', 'STM.MI'
    ],
    
    # === Crypto ===
    'Crypto': [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD', 'SOL-USD',
        'ADA-USD', 'DOGE-USD', 'AVAX-USD'
    ],
    
    # === ETF ===
    'ETF': [
        'SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VOO', 'ARKK', 'GLD'
    ],
    
    # === Commodities ===
    'Commodities': [
        'GC=F', 'CL=F', 'SI=F', 'NG=F', 'HG=F', 'PL=F'
    ],
    
    # === Forex ===
    'Forex': [
        'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'USDCHF=X'
    ],
}

# Currency mapping by symbol suffix - Using Unicode escapes for safety
CURRENCY_MAP = {
    '.NS': '\u20B9',  # ₹ Indian Rupee
    '.BO': '\u20B9',  # ₹ Indian Rupee
    '.L': '\u00A3',   # £ British Pound
    '.DE': '\u20AC',  # € Euro
    '.PA': '\u20AC',  # € Euro
    '.AS': '\u20AC',  # € Euro
    '.MC': '\u20AC',  # € Euro
    '.MI': '\u20AC',  # € Euro
    '.T': '\u00A5',   # ¥ Japanese Yen
    '.AX': 'A$',      # Australian Dollar
    '.TO': 'C$',      # Canadian Dollar
    '.SA': 'R$',      # Brazilian Real
    '.KS': '\u20A9',  # ₩ Korean Won
    '.SI': 'S$',      # Singapore Dollar
    '.SW': 'CHF',     # Swiss Franc
    '.HK': 'HK$',     # Hong Kong Dollar
    '.TW': 'NT$',     # Taiwan Dollar (NEW)
}

# Base price ranges by category (for demo data)
BASE_PRICES = {
    'US_Tech': (100, 500),
    'India': (500, 5000),
    'UK': (300, 12000),
    'Germany': (50, 700),
    'France': (30, 800),
    'Japan': (1000, 70000),
    'China': (20, 300),
    'HongKong': (20, 700),
    'Taiwan': (100, 1000),  # NEW
    'Australia': (20, 300),
    'Canada': (30, 200),
    'Brazil': (10, 100),
    'Korea': (30000, 100000),
    'Singapore': (2, 40),
    'Switzerland': (50, 500),
    'Netherlands': (20, 1000),
    'Spain': (2, 50),
    'Italy': (5, 80),
    'Crypto': (0.1, 110000),
    'ETF': (100, 600),
    'Commodities': (1, 3000),
    'Forex': (0.5, 160),
}

# Stock names for display - ALL 22 MARKETS
STOCK_NAMES = {
    # US Tech
    'AAPL': 'Apple Inc.',
    'NVDA': 'NVIDIA Corporation',
    'TSLA': 'Tesla Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'AMD': 'AMD Inc.',
    'ADBE': 'Adobe Inc.',
    'CRM': 'Salesforce Inc.',
    'NFLX': 'Netflix Inc.',
    'INTC': 'Intel Corporation',
    
    # India
    'RELIANCE.NS': 'Reliance Industries',
    'TCS.NS': 'Tata Consultancy Services',
    'INFY.NS': 'Infosys Limited',
    'HDFCBANK.NS': 'HDFC Bank',
    'ICICIBANK.NS': 'ICICI Bank',
    'WIPRO.NS': 'Wipro Limited',
    'SBIN.NS': 'State Bank of India',
    'BHARTIARTL.NS': 'Bharti Airtel',
    
    # UK
    'HSBA.L': 'HSBC Holdings',
    'BP.L': 'BP plc',
    'SHEL.L': 'Shell plc',
    'AZN.L': 'AstraZeneca',
    'GSK.L': 'GSK plc',
    'VOD.L': 'Vodafone Group',
    'LLOY.L': 'Lloyds Banking',
    
    # Germany
    'SAP.DE': 'SAP SE',
    'SIE.DE': 'Siemens AG',
    'ALV.DE': 'Allianz SE',
    'DTE.DE': 'Deutsche Telekom',
    'BAS.DE': 'BASF SE',
    'BMW.DE': 'BMW AG',
    
    # France
    'OR.PA': "L'Oreal SA",
    'MC.PA': 'LVMH',
    'TTE.PA': 'TotalEnergies',
    'SAN.PA': 'Sanofi',
    'AIR.PA': 'Airbus SE',
    'BNP.PA': 'BNP Paribas',
    
    # Japan
    '7203.T': 'Toyota Motor Corp',
    '6758.T': 'Sony Group Corp',
    '9984.T': 'SoftBank Group',
    '6861.T': 'Keyence Corporation',
    '7267.T': 'Honda Motor',
    '8306.T': 'Mitsubishi UFJ',
    
    # China
    '9988.HK': 'Alibaba Group',
    '9618.HK': 'JD.com Inc',
    '3690.HK': 'Meituan',
    '1810.HK': 'Xiaomi Corp',
    '2020.HK': 'Anta Sports',
    '0968.HK': 'Xinyi Solar',
    
    # Hong Kong
    '0700.HK': 'Tencent Holdings',
    '0005.HK': 'HSBC Holdings HK',
    '1299.HK': 'AIA Group',
    '0941.HK': 'China Mobile',
    '0388.HK': 'HK Exchanges',
    '0016.HK': 'Sun Hung Kai',
    
    # Taiwan (NEW)
    '2330.TW': 'TSMC',
    '2317.TW': 'Hon Hai Precision',
    '2454.TW': 'MediaTek Inc',
    '2308.TW': 'Delta Electronics',
    '2412.TW': 'Chunghwa Telecom',
    '2882.TW': 'Cathay Financial',
    
    # Australia
    'BHP.AX': 'BHP Group',
    'CBA.AX': 'Commonwealth Bank',
    'CSL.AX': 'CSL Limited',
    'NAB.AX': 'National Australia Bank',
    'WBC.AX': 'Westpac Banking',
    'ANZ.AX': 'ANZ Group',
    
    # Canada
    'RY.TO': 'Royal Bank of Canada',
    'TD.TO': 'Toronto-Dominion Bank',
    'SHOP.TO': 'Shopify Inc',
    'ENB.TO': 'Enbridge Inc',
    'CNR.TO': 'Canadian National Railway',
    'BMO.TO': 'Bank of Montreal',
    
    # Brazil
    'PETR4.SA': 'Petrobras',
    'VALE3.SA': 'Vale SA',
    'ITUB4.SA': 'Itau Unibanco',
    'BBDC4.SA': 'Bradesco',
    'B3SA3.SA': 'B3 SA',
    'WEGE3.SA': 'WEG SA',
    
    # Korea
    '005930.KS': 'Samsung Electronics',
    '000660.KS': 'SK Hynix',
    '035420.KS': 'Naver Corp',
    '051910.KS': 'LG Chem',
    '006400.KS': 'Samsung SDI',
    '035720.KS': 'Kakao Corp',
    
    # Singapore
    'D05.SI': 'DBS Group',
    'O39.SI': 'OCBC Bank',
    'U11.SI': 'UOB Ltd',
    'Z74.SI': 'Singtel',
    'C38U.SI': 'CapitaLand Integrated',
    'A17U.SI': 'Ascendas REIT',
    
    # Switzerland
    'NESN.SW': 'Nestle SA',
    'ROG.SW': 'Roche Holding',
    'NOVN.SW': 'Novartis AG',
    'UBSG.SW': 'UBS Group',
    'ZURN.SW': 'Zurich Insurance',
    'ABBN.SW': 'ABB Ltd',
    
    # Netherlands
    'ASML.AS': 'ASML Holding',
    'INGA.AS': 'ING Group',
    'PHIA.AS': 'Philips NV',
    'UNA.AS': 'Unilever NV',
    'HEIA.AS': 'Heineken NV',
    'AD.AS': 'Ahold Delhaize',
    
    # Spain
    'SAN.MC': 'Banco Santander',
    'IBE.MC': 'Iberdrola SA',
    'ITX.MC': 'Inditex SA',
    'BBVA.MC': 'BBVA SA',
    'TEF.MC': 'Telefonica SA',
    'REP.MC': 'Repsol SA',
    
    # Italy
    'ENI.MI': 'Eni SpA',
    'ENEL.MI': 'Enel SpA',
    'ISP.MI': 'Intesa Sanpaolo',
    'UCG.MI': 'UniCredit SpA',
    'RACE.MI': 'Ferrari NV',
    'STM.MI': 'STMicroelectronics',
    
    # Crypto
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'BNB-USD': 'Binance Coin',
    'XRP-USD': 'Ripple',
    'SOL-USD': 'Solana',
    'ADA-USD': 'Cardano',
    'DOGE-USD': 'Dogecoin',
    'AVAX-USD': 'Avalanche',
    
    # ETF
    'SPY': 'SPDR S&P 500 ETF',
    'QQQ': 'Invesco QQQ Trust',
    'DIA': 'SPDR Dow Jones ETF',
    'IWM': 'iShares Russell 2000',
    'VTI': 'Vanguard Total Stock Market',
    'VOO': 'Vanguard S&P 500 ETF',
    'ARKK': 'ARK Innovation ETF',
    'GLD': 'SPDR Gold Shares',
    
    # Commodities
    'GC=F': 'Gold Futures',
    'CL=F': 'Crude Oil Futures',
    'SI=F': 'Silver Futures',
    'NG=F': 'Natural Gas Futures',
    'HG=F': 'Copper Futures',
    'PL=F': 'Platinum Futures',
    
    # Forex
    'EURUSD=X': 'EUR/USD',
    'GBPUSD=X': 'GBP/USD',
    'USDJPY=X': 'USD/JPY',
    'AUDUSD=X': 'AUD/USD',
    'USDCAD=X': 'USD/CAD',
    'USDCHF=X': 'USD/CHF',
}

# Forced oversold/overbought stocks for demo testing (spread across markets)
FORCED_OVERSOLD = [
    'INTC', 'AMD', 'BP.L', 'AUDUSD=X', 'VOD.L', 'NG=F',
    'BBDC4.SA', '035720.KS', 'PHIA.AS', 'ENI.MI', '2308.TW'
]
FORCED_OVERBOUGHT = [
    'NVDA', 'META', 'XRP-USD', 'SOL-USD', 'GC=F',
    '2330.TW', 'ASML.AS', 'NESN.SW', 'MC.PA', '0700.HK'
]


def get_currency_for_symbol(symbol: str) -> str:
    """Determine currency symbol based on ticker suffix."""
    symbol = symbol.upper()
    
    for suffix, currency in CURRENCY_MAP.items():
        if symbol.endswith(suffix):
            return currency
    
    # Special cases
    if '-USD' in symbol:
        return '$'
    if symbol.endswith('=X'):
        return '$'
    if symbol.endswith('=F'):
        return '$'
    
    return '$'


def generate_deterministic_value(symbol: str, seed_offset: int = 0) -> int:
    """Generate a deterministic value based on symbol hash."""
    hash_input = f"{symbol}_{seed_offset}".encode()
    return int(hashlib.md5(hash_input).hexdigest()[:8], 16)


def generate_demo_stock_data(symbol: str, category: str) -> Dict:
    """Generate deterministic demo data for a symbol."""
    hash_val = generate_deterministic_value(symbol)
    
    # Get price range for category
    min_price, max_price = BASE_PRICES.get(category, (50, 500))
    
    # Generate price
    price_range = max_price - min_price
    price = min_price + (hash_val % int(price_range * 100)) / 100
    
    # Special handling for specific symbols to match expected values
    if symbol == 'BTC-USD':
        price = 106500 + (hash_val % 1000)
    elif symbol == 'ETH-USD':
        price = 3900 + (hash_val % 200)
    elif symbol == 'SPY':
        price = 600 + (hash_val % 20) / 10
    elif symbol == 'QQQ':
        price = 519 + (hash_val % 20) / 10
    elif symbol == 'AAPL':
        price = 249 + (hash_val % 10) / 10
    elif symbol == 'RELIANCE.NS':
        price = 1268 + (hash_val % 50) / 10
    elif symbol == 'BHP.AX':
        price = 42 + (hash_val % 10) / 10
    elif symbol == 'GC=F':
        price = 2655 + (hash_val % 50)
    elif symbol == 'CL=F':
        price = 69 + (hash_val % 5) / 10
    elif symbol == '7203.T':
        price = 2850 + (hash_val % 200)
    elif symbol == 'BP.L':
        price = 382 + (hash_val % 20) / 10
    elif symbol == '2330.TW':  # TSMC
        price = 580 + (hash_val % 50)
    elif symbol == '005930.KS':  # Samsung
        price = 72000 + (hash_val % 3000)
        
    # Generate change percent (-3% to +3%)
    change_hash = generate_deterministic_value(symbol, 1)
    change_pct = ((change_hash % 600) - 300) / 100
    
    # Generate RSI (25 to 75 normally, with some outliers)
    rsi_hash = generate_deterministic_value(symbol, 2)
    rsi = 25 + (rsi_hash % 50)
    
    # Force some stocks to be oversold/overbought for demo purposes
    if symbol in FORCED_OVERSOLD:
        rsi = 25 + (rsi_hash % 8)  # 25-33
        change_pct = -abs(change_pct) - 0.5  # Make negative
    elif symbol in FORCED_OVERBOUGHT:
        rsi = 70 + (rsi_hash % 10)  # 70-80
        change_pct = abs(change_pct) + 0.5  # Make positive
    
    # Determine signal based on RSI
    if rsi < 30:
        signal = 'STRONG_BUY'
    elif rsi < 40:
        signal = 'BUY'
    elif rsi > 70:
        signal = 'STRONG_SELL'
    elif rsi > 60:
        signal = 'SELL'
    else:
        signal = 'HOLD'
    
    return {
        'symbol': symbol,
        'name': STOCK_NAMES.get(symbol, symbol.split('.')[0]),
        'price': round(price, 2),
        'change_percent': round(change_pct, 2),
        'rsi': rsi,
        'signal': signal,
        'currency': get_currency_for_symbol(symbol),
        'category': category,
        'dataQuality': 'DEMO'
    }


@router.get("/universe")
async def get_screener_universe() -> Dict:
    """
    Get all stocks in the static universe with RSI and signals.
    
    Returns data organized by category for the frontend screener.
    Each stock includes: symbol, name, price, change_percent, rsi, signal, currency
    """
    all_stocks = []
    category_counts = {}
    
    for category, symbols in STATIC_UNIVERSE.items():
        category_stocks = []
        for symbol in symbols:
            stock_data = generate_demo_stock_data(symbol, category)
            category_stocks.append(stock_data)
            all_stocks.append(stock_data)
        category_counts[category] = len(category_stocks)
    
    # Count by signal type
    signal_counts = {
        'STRONG_BUY': len([s for s in all_stocks if s['signal'] == 'STRONG_BUY']),
        'BUY': len([s for s in all_stocks if s['signal'] == 'BUY']),
        'HOLD': len([s for s in all_stocks if s['signal'] == 'HOLD']),
        'SELL': len([s for s in all_stocks if s['signal'] == 'SELL']),
        'STRONG_SELL': len([s for s in all_stocks if s['signal'] == 'STRONG_SELL']),
    }
    
    return {
        "all": all_stocks,
        "categories": list(STATIC_UNIVERSE.keys()),
        "category_counts": category_counts,
        "signal_counts": signal_counts,
        "total_count": len(all_stocks),
        "total_markets": len(STATIC_UNIVERSE),  # Should be 22
        "demoMode": True,  # Always demo for screener to ensure reliability
        "timestamp": datetime.now().isoformat(),
        "refresh_interval": 60,
        "message": f"22 markets, {len(all_stocks)} stocks - Demo data for reliability"
    }


@router.get("/universe/{category}")
async def get_screener_category(category: str) -> Dict:
    """Get stocks for a specific category."""
    if category not in STATIC_UNIVERSE:
        return {
            "error": f"Category '{category}' not found",
            "available_categories": list(STATIC_UNIVERSE.keys())
        }
    
    stocks = []
    for symbol in STATIC_UNIVERSE[category]:
        stock_data = generate_demo_stock_data(symbol, category)
        stocks.append(stock_data)
    
    return {
        "category": category,
        "stocks": stocks,
        "count": len(stocks),
        "demoMode": True,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def screener_health():
    """Health check for screener service."""
    total_symbols = sum(len(symbols) for symbols in STATIC_UNIVERSE.values())
    return {
        "status": "healthy",
        "categories": len(STATIC_UNIVERSE),
        "total_symbols": total_symbols,
        "demo_mode": DEMO_MODE,
        "version": "5.8.5",
        "markets": "22 global markets",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test the module
    import asyncio
    
    async def test():
        print("\n" + "=" * 60)
        print("SCREENER UNIVERSE TEST v5.8.5 - ALL 22 MARKETS")
        print("=" * 60)
        
        result = await get_screener_universe()
        print(f"\nTotal Markets: {result['total_markets']}")
        print(f"Total Stocks: {result['total_count']}")
        print(f"Categories: {len(result['categories'])}")
        print(f"\nAll Categories:")
        for cat in result['categories']:
            print(f"   - {cat}")
        
        print(f"\nSignal Distribution:")
        for signal, count in result['signal_counts'].items():
            print(f"   {signal}: {count}")
        
        print(f"\nSample stocks (with currency):")
        for stock in result['all'][:10]:
            print(f"   {stock['symbol']}: {stock['currency']}{stock['price']} | RSI: {stock['rsi']} | {stock['signal']}")
        
        print(f"\nForced Oversold (RSI < 30):")
        oversold = [s for s in result['all'] if s['rsi'] < 30]
        for stock in oversold[:5]:
            print(f"   {stock['symbol']}: RSI {stock['rsi']} | {stock['signal']}")
        
        print(f"\nForced Overbought (RSI > 70):")
        overbought = [s for s in result['all'] if s['rsi'] > 70]
        for stock in overbought[:5]:
            print(f"   {stock['symbol']}: RSI {stock['rsi']} | {stock['signal']}")
    
    asyncio.run(test())
