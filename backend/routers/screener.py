"""
stock_router.py - Missing API Endpoints for TraderAI Pro v5.7.1
================================================================
This router adds all the endpoints that the frontend expects but are missing.

FIXES in v5.7.1:
- Added sentiment bias: AAPL/NVDA/TSLA show bullish, INTC shows bearish
- Fixed news time field (returns both 'time' and 'time_ago')
- Improved demo data realism

Missing endpoints added:
- GET /api/v4/history/{symbol}   - Historical price data
- GET /api/signals/{symbol}      - Trading signals  
- GET /api/sentiment/reddit/{symbol} - Reddit sentiment
- GET /api/sentiment/twitter/{symbol} - Twitter sentiment
- GET /api/news/{symbol}         - News articles
- GET /api/v4/financials/{symbol} - Company financials
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
import random
import hashlib
import math

router = APIRouter(tags=["Stock Data"])

# ============================================================
# SENTIMENT BIAS CONFIGURATION
# ============================================================

# Stocks that tend to have bullish sentiment (AI leaders, growth stocks)
BULLISH_STOCKS = {
    'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD', 'NFLX',
    'BTC-USD', 'ETH-USD', 'SOL-USD',  # Crypto tends bullish in communities
    'SPY', 'QQQ',  # Index ETFs
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS',  # Indian IT leaders
}

# Stocks that tend to have bearish sentiment (struggling companies)
BEARISH_STOCKS = {
    'INTC',  # Intel struggling
    'BA',    # Boeing issues
    'DIS',   # Disney streaming losses
    'PYPL',  # PayPal competition
    'SNAP',  # Snap struggling
}

def get_sentiment_bias(symbol: str) -> tuple:
    """
    Get sentiment bias range for a symbol.
    Returns (min_bullish, max_bullish) percentage range.
    """
    symbol_upper = symbol.upper()
    
    if symbol_upper in BULLISH_STOCKS:
        return (58, 82)  # Bullish bias: 58-82% bullish
    elif symbol_upper in BEARISH_STOCKS:
        return (22, 42)  # Bearish bias: 22-42% bullish
    else:
        return (40, 60)  # Neutral: 40-60% bullish


# ============================================================
# DEMO DATA CONFIGURATION
# ============================================================

DEMO_STOCKS = {
    # US Stocks
    'AAPL': {'name': 'Apple Inc.', 'base_price': 238.50, 'currency': '$'},
    'MSFT': {'name': 'Microsoft Corp', 'base_price': 430.90, 'currency': '$'},
    'GOOGL': {'name': 'Alphabet Inc', 'base_price': 175.80, 'currency': '$'},
    'AMZN': {'name': 'Amazon.com', 'base_price': 220.25, 'currency': '$'},
    'NVDA': {'name': 'NVIDIA Corp', 'base_price': 933.20, 'currency': '$'},
    'META': {'name': 'Meta Platforms', 'base_price': 580.75, 'currency': '$'},
    'TSLA': {'name': 'Tesla Inc', 'base_price': 420.50, 'currency': '$'},
    'AMD': {'name': 'AMD Inc', 'base_price': 145.30, 'currency': '$'},
    'NFLX': {'name': 'Netflix Inc', 'base_price': 850.90, 'currency': '$'},
    'INTC': {'name': 'Intel Corp', 'base_price': 22.50, 'currency': '$'},
    'JPM': {'name': 'JPMorgan Chase', 'base_price': 195.40, 'currency': '$'},
    'V': {'name': 'Visa Inc', 'base_price': 278.60, 'currency': '$'},
    'JNJ': {'name': 'Johnson & Johnson', 'base_price': 156.80, 'currency': '$'},
    'WMT': {'name': 'Walmart Inc', 'base_price': 162.30, 'currency': '$'},
    'PG': {'name': 'Procter & Gamble', 'base_price': 158.90, 'currency': '$'},
    'DIS': {'name': 'Walt Disney', 'base_price': 112.45, 'currency': '$'},
    # India
    'RELIANCE.NS': {'name': 'Reliance Industries', 'base_price': 1250.75, 'currency': '₹'},
    'TCS.NS': {'name': 'Tata Consultancy', 'base_price': 4100.50, 'currency': '₹'},
    'HDFCBANK.NS': {'name': 'HDFC Bank', 'base_price': 1678.25, 'currency': '₹'},
    'INFY.NS': {'name': 'Infosys Ltd', 'base_price': 1850.80, 'currency': '₹'},
    'ICICIBANK.NS': {'name': 'ICICI Bank', 'base_price': 1023.45, 'currency': '₹'},
    # UK
    'HSBA.L': {'name': 'HSBC Holdings', 'base_price': 678.50, 'currency': '£'},
    'BP.L': {'name': 'BP plc', 'base_price': 478.25, 'currency': '£'},
    'SHEL.L': {'name': 'Shell plc', 'base_price': 2567.00, 'currency': '£'},
    'AZN.L': {'name': 'AstraZeneca', 'base_price': 10234.00, 'currency': '£'},
    # Germany
    'SAP.DE': {'name': 'SAP SE', 'base_price': 178.45, 'currency': '€'},
    'SIE.DE': {'name': 'Siemens AG', 'base_price': 165.78, 'currency': '€'},
    'VOW3.DE': {'name': 'Volkswagen AG', 'base_price': 108.56, 'currency': '€'},
    # France
    'OR.PA': {'name': "L'Oreal SA", 'base_price': 425.60, 'currency': '€'},
    'MC.PA': {'name': 'LVMH', 'base_price': 745.80, 'currency': '€'},
    'SAN.PA': {'name': 'Sanofi SA', 'base_price': 89.45, 'currency': '€'},
    # Japan
    '7203.T': {'name': 'Toyota Motor', 'base_price': 2678.00, 'currency': '¥'},
    '6758.T': {'name': 'Sony Group', 'base_price': 12456.00, 'currency': '¥'},
    '9984.T': {'name': 'SoftBank Group', 'base_price': 8234.00, 'currency': '¥'},
    # Australia
    'BHP.AX': {'name': 'BHP Group', 'base_price': 45.67, 'currency': 'A$'},
    'CBA.AX': {'name': 'Commonwealth Bank', 'base_price': 112.34, 'currency': 'A$'},
    'CSL.AX': {'name': 'CSL Limited', 'base_price': 278.90, 'currency': 'A$'},
    # Korea
    '005930.KS': {'name': 'Samsung Electronics', 'base_price': 71500, 'currency': '₩'},
    '000660.KS': {'name': 'SK Hynix', 'base_price': 134500, 'currency': '₩'},
    # China/Hong Kong
    '9988.HK': {'name': 'Alibaba Group', 'base_price': 85.00, 'currency': 'HK$'},
    '0700.HK': {'name': 'Tencent Holdings', 'base_price': 380.00, 'currency': 'HK$'},
    # Singapore
    'D05.SI': {'name': 'DBS Group', 'base_price': 35.00, 'currency': 'S$'},
    # Switzerland
    'NESN.SW': {'name': 'Nestle SA', 'base_price': 98.56, 'currency': 'CHF'},
    'NOVN.SW': {'name': 'Novartis AG', 'base_price': 89.78, 'currency': 'CHF'},
    # Crypto
    'BTC-USD': {'name': 'Bitcoin USD', 'base_price': 98542.30, 'currency': '$'},
    'ETH-USD': {'name': 'Ethereum USD', 'base_price': 3456.78, 'currency': '$'},
    'SOL-USD': {'name': 'Solana USD', 'base_price': 189.45, 'currency': '$'},
    # ETFs
    'SPY': {'name': 'SPDR S&P 500', 'base_price': 590.90, 'currency': '$'},
    'QQQ': {'name': 'Invesco QQQ', 'base_price': 510.56, 'currency': '$'},
    'IWM': {'name': 'iShares Russell 2000', 'base_price': 198.34, 'currency': '$'},
    # Commodities
    'GC=F': {'name': 'Gold Futures', 'base_price': 2045.60, 'currency': '$'},
    'CL=F': {'name': 'Crude Oil', 'base_price': 78.45, 'currency': '$'},
    'SI=F': {'name': 'Silver Futures', 'base_price': 24.56, 'currency': '$'},
    # Forex
    'EURUSD=X': {'name': 'EUR/USD', 'base_price': 1.0856, 'currency': '$'},
    'GBPUSD=X': {'name': 'GBP/USD', 'base_price': 1.2678, 'currency': '$'},
    'USDJPY=X': {'name': 'USD/JPY', 'base_price': 149.45, 'currency': '¥'},
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_seed(symbol: str) -> int:
    """Generate consistent seed from symbol."""
    return int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)

def get_stock_info(symbol: str) -> dict:
    """Get stock info or generate default."""
    symbol_upper = symbol.upper()
    if symbol_upper in DEMO_STOCKS:
        return DEMO_STOCKS[symbol_upper]
    # Generate default for unknown symbols
    return {
        'name': f'{symbol_upper} Corp',
        'base_price': 100 + (get_seed(symbol_upper) % 400),
        'currency': '$'
    }

def get_current_price(symbol: str) -> float:
    """Get simulated current price."""
    info = get_stock_info(symbol)
    base = info['base_price']
    seed = get_seed(symbol)
    random.seed(seed + int(datetime.now().timestamp() / 60))  # Change every minute
    variation = random.uniform(-0.02, 0.02)
    return round(base * (1 + variation), 2)

def generate_ohlcv(symbol: str, timestamp: datetime, interval_minutes: int = 15) -> dict:
    """Generate OHLCV data for a timestamp."""
    info = get_stock_info(symbol)
    base = info['base_price']
    seed = get_seed(symbol) + int(timestamp.timestamp() / (interval_minutes * 60))
    random.seed(seed)
    
    volatility = 0.008 if interval_minutes <= 5 else 0.015 if interval_minutes <= 60 else 0.025
    
    open_price = base * (1 + random.uniform(-volatility, volatility))
    close_price = open_price * (1 + random.uniform(-volatility, volatility))
    high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility))
    low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility))
    volume = int(random.uniform(100000, 5000000))
    
    return {
        'timestamp': timestamp.isoformat(),
        'open': round(open_price, 2),
        'high': round(high_price, 2),
        'low': round(low_price, 2),
        'close': round(close_price, 2),
        'volume': volume
    }

# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/api/v4/history/{symbol}")
async def get_history(symbol: str, period: str = "5d", interval: str = "15m"):
    """
    Get historical OHLCV data for a symbol.
    
    Args:
        symbol: Stock symbol (e.g., AAPL, RELIANCE.NS)
        period: Time period (1d, 5d, 1mo, 3mo, 1y)
        interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk)
    """
    # Parse interval to minutes
    interval_map = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440, '1wk': 10080
    }
    interval_minutes = interval_map.get(interval, 15)
    
    # Parse period to days
    period_map = {
        '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365
    }
    days = period_map.get(period, 5)
    
    # Calculate number of candles
    candles_per_day = 1440 // interval_minutes
    total_candles = min(candles_per_day * days, 500)  # Max 500 candles
    
    # Generate historical data
    now = datetime.now()
    data = []
    
    for i in range(total_candles, 0, -1):
        ts = now - timedelta(minutes=i * interval_minutes)
        candle = generate_ohlcv(symbol, ts, interval_minutes)
        data.append(candle)
    
    info = get_stock_info(symbol)
    
    return {
        "symbol": symbol.upper(),
        "name": info['name'],
        "currency": info['currency'],
        "interval": interval,
        "period": period,
        "data": data,
        "count": len(data),
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/signals/{symbol}")
async def get_signals(symbol: str):
    """
    Get trading signals for a symbol.
    
    Returns RSI, MACD, trend, signal recommendation, and risk score.
    """
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 300)  # Change every 5 min
    random.seed(seed)
    
    # Generate indicators
    rsi = random.uniform(25, 75)
    macd = random.uniform(-5, 5)
    macd_signal = macd + random.uniform(-1, 1)
    macd_histogram = macd - macd_signal
    
    price = get_current_price(symbol)
    sma_20 = price * random.uniform(0.97, 1.03)
    ema_12 = price * random.uniform(0.98, 1.02)
    vwap = price * random.uniform(0.99, 1.01)
    atr = round(price * random.uniform(0.01, 0.03), 2)
    
    # Bollinger Bands
    bb_middle = sma_20
    bb_std = price * 0.02
    bb_upper = bb_middle + (2 * bb_std)
    bb_lower = bb_middle - (2 * bb_std)
    
    # Determine signal
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
    
    info = get_stock_info(symbol)
    
    return {
        "symbol": symbol.upper(),
        "name": info['name'],
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
        "currency": info['currency'],
        "price": price,
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/sentiment/reddit/{symbol}")
async def get_reddit_sentiment(symbol: str):
    """Get Reddit sentiment analysis for a symbol with sentiment bias."""
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 600)
    random.seed(seed)
    
    # Get sentiment bias for this symbol
    min_bullish, max_bullish = get_sentiment_bias(symbol)
    
    # Generate biased sentiment
    bullish = random.randint(min_bullish, max_bullish)
    bearish = random.randint(10, min(40, 100 - bullish - 10))
    neutral = 100 - bullish - bearish
    
    mentions = random.randint(50, 500)
    sentiment_score = (bullish - 50) / 50  # -1 to 1 scale
    
    # Determine label based on actual bullish percentage
    if bullish >= 60:
        sentiment_label = "Bullish"
    elif bullish <= 40:
        sentiment_label = "Bearish"
    else:
        sentiment_label = "Neutral"
    
    post_templates = [
        f"${symbol} is looking strong! 🚀",
        f"Just bought more ${symbol}, great setup",
        f"${symbol} technical analysis thread",
        f"What's your price target for ${symbol}?",
        f"${symbol} earnings play discussion",
        f"${symbol} support levels holding well",
        f"Is ${symbol} a buy at current levels?",
        f"${symbol} momentum building 📈",
        f"${symbol} consolidation pattern forming",
        f"Long term bullish on ${symbol}"
    ]
    
    posts = []
    for i in range(5):
        posts.append({
            "title": random.choice(post_templates),
            "subreddit": random.choice(["wallstreetbets", "stocks", "investing", "options", "stockmarket"]),
            "upvotes": random.randint(50, 2000),
            "comments": random.randint(10, 300),
            "sentiment": random.choice(["bullish", "neutral"]) if bullish > 50 else random.choice(["bearish", "neutral"]),
            "time_ago": f"{random.randint(1, 24)}h ago"
        })
    
    return {
        "symbol": symbol.upper(),
        "platform": "reddit",
        "sentiment": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "score": round(sentiment_score, 2),
            "label": sentiment_label
        },
        "mentions": mentions,
        "trending": mentions > 200,
        "posts": posts,
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/sentiment/twitter/{symbol}")
async def get_twitter_sentiment(symbol: str):
    """Get Twitter/X sentiment analysis for a symbol with sentiment bias."""
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 600) + 1
    random.seed(seed)
    
    # Get sentiment bias for this symbol
    min_bullish, max_bullish = get_sentiment_bias(symbol)
    
    # Generate biased sentiment
    bullish = random.randint(min_bullish, max_bullish)
    bearish = random.randint(10, min(40, 100 - bullish - 10))
    neutral = 100 - bullish - bearish
    
    mentions = random.randint(100, 2000)
    sentiment_score = (bullish - 50) / 50
    
    # Determine label based on actual bullish percentage
    if bullish >= 60:
        sentiment_label = "Bullish"
    elif bullish <= 40:
        sentiment_label = "Bearish"
    else:
        sentiment_label = "Neutral"
    
    tweet_templates = [
        f"${symbol} looking bullish today! 📈",
        f"${symbol} breaking out! 🚀",
        f"Watching ${symbol} closely",
        f"${symbol} technical setup looks good",
        f"Added ${symbol} to my portfolio",
        f"${symbol} support holding strong",
        f"${symbol} earnings play 💰"
    ]
    
    tweets = []
    for i in range(5):
        tweets.append({
            "text": random.choice(tweet_templates),
            "user": f"@trader{random.randint(100, 999)}",
            "likes": random.randint(10, 500),
            "retweets": random.randint(5, 100),
            "sentiment": random.choice(["bullish", "neutral"]) if bullish > 50 else random.choice(["bearish", "neutral"]),
            "time_ago": f"{random.randint(1, 12)}h ago"
        })
    
    return {
        "symbol": symbol.upper(),
        "platform": "twitter",
        "sentiment": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "score": round(sentiment_score, 2),
            "label": sentiment_label
        },
        "mentions": mentions,
        "trending": mentions > 500,
        "tweets": tweets,
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """Get news articles for a symbol."""
    info = get_stock_info(symbol)
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 3600)
    random.seed(seed)
    
    news_templates = [
        {"title": f"Investors Eye {info['name']} Amid Market Volatility", "sentiment": "neutral"},
        {"title": f"{info['name']} Announces Strategic Partnership", "sentiment": "positive"},
        {"title": f"Analysts Upgrade {info['name']} Stock", "sentiment": "positive"},
        {"title": f"{info['name']} Expands Market Presence", "sentiment": "positive"},
        {"title": f"{info['name']} CEO Discusses Growth Strategy", "sentiment": "neutral"},
        {"title": f"Market Watch: {info['name']} Technical Analysis", "sentiment": "neutral"},
        {"title": f"{info['name']} Reports Strong Quarterly Results", "sentiment": "positive"},
        {"title": f"What's Next for {info['name']}?", "sentiment": "neutral"},
        {"title": f"{info['name']} Innovation Drives Future Growth", "sentiment": "positive"},
        {"title": f"{info['name']} Faces Industry Competition", "sentiment": "neutral"},
    ]
    
    sources = ["Reuters", "Bloomberg", "CNBC", "MarketWatch", "Yahoo Finance", "WSJ", "Financial Times"]
    
    articles = []
    random.shuffle(news_templates)
    
    for i, template in enumerate(news_templates[:6]):
        hours_ago = random.randint(1, 48)
        time_ago_str = f"{hours_ago}h ago"
        
        articles.append({
            "title": template["title"],
            "source": random.choice(sources),
            "sentiment": template["sentiment"],
            "summary": f"Latest updates on {info['name']} ({symbol.upper()}) stock performance and market outlook.",
            "url": f"https://example.com/news/{symbol.lower()}-{i}",
            "published": (datetime.now() - timedelta(hours=hours_ago)).isoformat(),
            "time_ago": time_ago_str,  # For frontend compatibility
            "time": time_ago_str,       # Alternative field name
        })
    
    return {
        "symbol": symbol.upper(),
        "name": info['name'],
        "articles": articles,
        "count": len(articles),
        "source": "DEMO",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/v4/financials/{symbol}")
async def get_financials(symbol: str):
    """Get company financials for a symbol."""
    info = get_stock_info(symbol)
    seed = get_seed(symbol)
    random.seed(seed)
    
    # Generate realistic financials based on price
    price = info['base_price']
    shares_outstanding = random.randint(500, 5000) * 1_000_000
    market_cap = price * shares_outstanding
    
    revenue = market_cap * random.uniform(0.3, 0.8)
    net_income = revenue * random.uniform(0.05, 0.25)
    eps = net_income / shares_outstanding
    pe_ratio = price / eps if eps > 0 else 0
    
    return {
        "symbol": symbol.upper(),
        "name": info['name'],
        "currency": info['currency'],
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


# ============================================================
# AI SUMMARY ENDPOINT
# ============================================================

@router.get("/api/v4/summary/{symbol}")
async def get_ai_summary(symbol: str):
    """Get AI-generated summary for a symbol."""
    info = get_stock_info(symbol)
    price = get_current_price(symbol)
    
    seed = get_seed(symbol) + int(datetime.now().timestamp() / 3600)
    random.seed(seed)
    
    change = random.uniform(-3, 3)
    trend = "bullish" if change > 0 else "bearish"
    
    summary = f"""**{info['name']} ({symbol.upper()}) Analysis**

Current Price: {info['currency']}{price:,.2f} ({'+' if change > 0 else ''}{change:.2f}%)

**Technical Outlook:** The stock is showing {trend} momentum with RSI indicating {'oversold' if random.random() > 0.5 else 'neutral'} conditions. Key support at {info['currency']}{price * 0.95:,.2f} and resistance at {info['currency']}{price * 1.05:,.2f}.

**Sentiment:** Social media sentiment is {'positive' if change > 0 else 'mixed'} with increased mentions across trading communities.

**Recommendation:** {'Consider accumulating on dips' if change > 0 else 'Watch for confirmation of trend reversal'} with appropriate position sizing.
"""
    
    return {
        "symbol": symbol.upper(),
        "name": info['name'],
        "summary": summary,
        "generated_at": datetime.now().isoformat(),
        "source": "AI-DEMO"
    }
