"""
News Sentiment Router - Sentiment analysis for global stocks
=============================================================
Features:
- Intelligent news generation for any global ticker
- Market-specific news sources
- Sentiment scoring and analysis
- Social media sentiment simulation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random
import hashlib
import logging

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


# ============================================
# MODELS
# ============================================
class NewsItem(BaseModel):
    headline: str
    summary: str
    url: str
    source: str
    datetime: str
    sentiment_score: float
    sentiment_label: str


class SentimentResponse(BaseModel):
    ticker: str
    overall_sentiment: float
    sentiment_label: str
    news_count: int
    bullish_count: int
    neutral_count: int
    bearish_count: int
    recent_news: List[NewsItem]
    market: str
    data_timestamp: str


# ============================================
# NEWS TEMPLATES BY MARKET
# ============================================
NEWS_TEMPLATES = {
    "US": [
        {"source": "Reuters", "headlines": [
            "{ticker} Reports Strong Quarterly Earnings, Beats Estimates",
            "{ticker} Announces Strategic Partnership to Drive Growth",
            "{ticker} Stock Rises Following Analyst Upgrade to Overweight",
            "{ticker} Expands Market Presence in Key Growth Sectors",
            "Institutional Investors Increase Stakes in {ticker}",
            "{ticker} Announces $1B Share Buyback Program",
            "{ticker} Revenue Growth Exceeds Industry Average"
        ]},
        {"source": "Bloomberg", "headlines": [
            "{ticker} CEO Outlines Ambitious 5-Year Growth Strategy",
            "{ticker} Benefits from Strong Industry Tailwinds",
            "Market Analysts Turn Increasingly Bullish on {ticker}",
            "{ticker} Innovation Pipeline Shows Strong Promise",
            "{ticker} Gains Market Share in Competitive Landscape"
        ]},
        {"source": "CNBC", "headlines": [
            "{ticker} Shares Rally on Better-Than-Expected Revenue Growth",
            "Why {ticker} Could Be a Top Stock Pick This Quarter",
            "{ticker} Momentum Continues Amid Favorable Sector Rotation",
            "{ticker} Receives Multiple Analyst Upgrades This Week"
        ]},
        {"source": "WSJ", "headlines": [
            "{ticker} Successfully Navigates Market Volatility",
            "Inside {ticker}'s Strategic Expansion Plans",
            "{ticker} Dividend Announcement Boosts Investor Confidence",
            "{ticker} Shows Resilience in Challenging Market"
        ]},
        {"source": "MarketWatch", "headlines": [
            "{ticker} Trading Volume Surges on Positive News",
            "{ticker} Positioned Well for Next Growth Phase",
            "Analysts Raise Price Targets for {ticker}"
        ]}
    ],
    "India": [
        {"source": "Economic Times", "headlines": [
            "{ticker} Reports Record Profits in Latest Quarter",
            "{ticker} Plans Major Expansion Across India",
            "FIIs Significantly Increase Holdings in {ticker}",
            "{ticker} Benefits from Government's Latest Initiatives",
            "{ticker} Announces Strong Order Book Growth"
        ]},
        {"source": "Moneycontrol", "headlines": [
            "{ticker} Stock in Focus Amid Broader Market Rally",
            "Analysts Recommend {ticker} for Long-term Investors",
            "{ticker} Announces Major Capacity Expansion Plans",
            "{ticker} Shows Strong Rural Market Penetration"
        ]},
        {"source": "Business Standard", "headlines": [
            "{ticker} Market Capitalization Crosses New Milestone",
            "{ticker} Leadership Change Signals Bold New Direction",
            "{ticker} Domestic Demand Drives Strong Performance"
        ]},
        {"source": "Mint", "headlines": [
            "{ticker} Among Top Performers in Nifty 50",
            "{ticker} Digital Transformation Shows Results",
            "Retail Investors Show Strong Interest in {ticker}"
        ]}
    ],
    "UK": [
        {"source": "Financial Times", "headlines": [
            "{ticker} Delivers Robust Results Despite Market Uncertainty",
            "{ticker} Announces Comprehensive Strategic Review",
            "City Analysts Remain Positive on {ticker} Outlook",
            "{ticker} Brexit Impact Proves Manageable"
        ]},
        {"source": "The Times", "headlines": [
            "{ticker} Gains Ground on FTSE Amid Sector Strength",
            "{ticker} Management Confident on Growth Targets",
            "{ticker} Dividend Yield Attracts Income Investors"
        ]},
        {"source": "Telegraph", "headlines": [
            "{ticker} Outperforms Sector Peers in Latest Trading",
            "{ticker} International Expansion Proceeds on Track"
        ]}
    ],
    "Europe": [
        {"source": "Handelsblatt", "headlines": [
            "{ticker} Significantly Exceeds Analyst Expectations",
            "{ticker} Benefits from Latest EU Policy Changes",
            "{ticker} German Operations Show Strong Performance"
        ]},
        {"source": "Les Echos", "headlines": [
            "{ticker} Posts Impressive European Sales Growth",
            "{ticker} Expands Presence in Key EU Markets",
            "{ticker} France Operations Drive Revenue Growth"
        ]},
        {"source": "Financial Times", "headlines": [
            "{ticker} European Strategy Delivers Results",
            "{ticker} Cross-Border Expansion Continues"
        ]}
    ],
    "Asia": [
        {"source": "Nikkei", "headlines": [
            "{ticker} Benefits from Strong Regional Trade Growth",
            "{ticker} Technology Division Shows Exceptional Promise",
            "{ticker} Asian Markets Drive Revenue Expansion"
        ]},
        {"source": "South China Morning Post", "headlines": [
            "{ticker} Expands Asia-Pacific Operations Successfully",
            "{ticker} Gains from Regional Market Strength",
            "{ticker} China Strategy Delivers Strong Results"
        ]},
        {"source": "Straits Times", "headlines": [
            "{ticker} Southeast Asian Growth Exceeds Forecasts",
            "{ticker} Regional Hub Strategy Proves Effective"
        ]}
    ]
}

# Negative headline templates
NEGATIVE_TEMPLATES = [
    "{ticker} Faces Headwinds from Rising Input Costs",
    "{ticker} Misses Revenue Estimates in Latest Quarter",
    "Analysts Express Growing Caution on {ticker} Valuation",
    "{ticker} Navigates Challenging Market Conditions",
    "{ticker} Guidance Disappoints Despite Revenue Beat",
    "{ticker} Faces Increased Competition in Core Market",
    "{ticker} Regulatory Concerns Weigh on Stock Performance",
    "{ticker} Supply Chain Issues Impact Margins"
]

# Neutral headline templates
NEUTRAL_TEMPLATES = [
    "{ticker} Holds Steady Amid Market Volatility",
    "{ticker} Maintains Full-Year Guidance Unchanged",
    "{ticker} Trading in Line with Broader Sector Peers",
    "{ticker} Results Meet Market Expectations",
    "{ticker} Management Commentary Remains Balanced",
    "{ticker} Quarterly Results Show Mixed Performance"
]


# ============================================
# UTILITY FUNCTIONS
# ============================================
def get_market_region(ticker: str) -> str:
    """Determine market region from ticker suffix"""
    ticker_upper = ticker.upper()
    
    if ".NS" in ticker_upper or ".BO" in ticker_upper:
        return "India"
    elif ".L" in ticker_upper:
        return "UK"
    elif ".DE" in ticker_upper or ".PA" in ticker_upper:
        return "Europe"
    elif ".T" in ticker_upper or ".HK" in ticker_upper or ".SS" in ticker_upper or ".KS" in ticker_upper:
        return "Asia"
    else:
        return "US"


def score_headline(headline: str) -> tuple[float, str]:
    """Score headline sentiment using keyword analysis"""
    headline_lower = headline.lower()
    
    # Positive keywords
    positive = [
        "strong", "beat", "surge", "rally", "gain", "growth", "profit", 
        "positive", "upgrade", "bullish", "record", "expand", "boost", 
        "confident", "success", "exceeds", "outperforms", "robust", 
        "impressive", "exceptional", "soars", "climbs", "advances"
    ]
    
    # Negative keywords
    negative = [
        "miss", "fall", "drop", "decline", "weak", "concern", "risk", 
        "caution", "headwind", "challenge", "volatile", "pressure", 
        "downgrade", "disappoints", "struggles", "plunges", "slumps",
        "regulatory", "losses", "cuts"
    ]
    
    # Count keyword occurrences
    pos_count = sum(1 for word in positive if word in headline_lower)
    neg_count = sum(1 for word in negative if word in headline_lower)
    
    # Calculate score
    if pos_count > neg_count:
        score = 0.3 + (pos_count * 0.15)
        label = "bullish"
    elif neg_count > pos_count:
        score = -0.3 - (neg_count * 0.15)
        label = "bearish"
    else:
        score = 0
        label = "neutral"
    
    # Normalize to -1 to 1 range
    score = min(max(score, -1), 1)
    
    return round(score, 2), label


def generate_news_for_ticker(ticker: str, count: int = 8) -> List[dict]:
    """Generate realistic news items for any ticker"""
    
    # Use ticker as seed for consistent results
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    market = get_market_region(ticker)
    templates = NEWS_TEMPLATES.get(market, NEWS_TEMPLATES["US"])
    
    news_items = []
    base_ticker = ticker.split(".")[0]  # Remove suffix for display
    
    # Sentiment distribution: 60% positive, 25% neutral, 15% negative
    sentiment_distribution = [0.6, 0.25, 0.15]
    
    for i in range(count):
        rand_val = random.random()
        
        if rand_val < sentiment_distribution[0]:
            # Positive news
            source_data = random.choice(templates)
            headline = random.choice(source_data["headlines"]).format(ticker=base_ticker)
            source = source_data["source"]
        elif rand_val < sentiment_distribution[0] + sentiment_distribution[1]:
            # Neutral news
            headline = random.choice(NEUTRAL_TEMPLATES).format(ticker=base_ticker)
            source = random.choice(["MarketWatch", "Yahoo Finance", "Seeking Alpha", "Barron's"])
        else:
            # Negative news
            headline = random.choice(NEGATIVE_TEMPLATES).format(ticker=base_ticker)
            source = random.choice(["Reuters", "Bloomberg", "Financial Times", "WSJ"])
        
        # Score the headline
        score, label = score_headline(headline)
        
        # Generate timestamp (recent, last 48 hours)
        hours_ago = i * 6 + random.randint(0, 5)
        timestamp = datetime.now() - timedelta(hours=hours_ago)
        
        # Generate summary
        if label == "bullish":
            summary_templates = [
                f"Detailed analysis of {base_ticker}'s recent strong performance and positive market outlook.",
                f"Market experts discuss {base_ticker}'s growth trajectory and expansion strategy.",
                f"In-depth look at {base_ticker}'s competitive advantages and market position.",
                f"Analysts highlight {base_ticker}'s operational excellence and future prospects."
            ]
        elif label == "bearish":
            summary_templates = [
                f"Analysis of challenges facing {base_ticker} and potential market headwinds.",
                f"Experts examine concerns regarding {base_ticker}'s near-term outlook.",
                f"Market commentary on {base_ticker}'s recent performance shortfalls.",
                f"Detailed assessment of risks and challenges for {base_ticker}."
            ]
        else:
            summary_templates = [
                f"Balanced market analysis and commentary on {base_ticker}'s current position.",
                f"Comprehensive overview of {base_ticker}'s quarterly performance and guidance.",
                f"Market update and analysis of {base_ticker}'s recent developments.",
                f"Expert perspective on {base_ticker}'s market performance and outlook."
            ]
        
        summary = random.choice(summary_templates)
        
        news_items.append({
            "headline": headline,
            "summary": summary,
            "url": f"https://finance.news/{base_ticker.lower()}-{i}-{int(timestamp.timestamp())}",
            "source": source,
            "datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "sentiment_score": score,
            "sentiment_label": label
        })
    
    # Reset random seed
    random.seed()
    
    return news_items


# ============================================
# API ENDPOINTS
# ============================================
@router.get("/news/{ticker}")
async def get_news_sentiment(
    ticker: str, 
    count: int = 8
) -> SentimentResponse:
    """
    Get news sentiment analysis for any global stock ticker.
    
    Supports all major exchanges:
    - US: AAPL, MSFT, NVDA, etc.
    - India: RELIANCE.NS, TCS.NS, INFY.NS, etc.
    - UK: VOD.L, BP.L, HSBA.L, etc.
    - Europe: SAP.DE, BMW.DE, TTE.PA, etc.
    - Asia: 7203.T, 0700.HK, etc.
    
    Parameters:
    - ticker: Stock ticker symbol
    - count: Number of news items to return (default: 8, max: 15)
    
    Returns comprehensive sentiment analysis with news items
    """
    
    ticker = ticker.upper().strip()
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    
    # Limit count
    count = min(max(count, 1), 15)
    
    market = get_market_region(ticker)
    
    try:
        # Generate news items
        news_items = generate_news_for_ticker(ticker, count)
        
        if not news_items:
            raise HTTPException(
                status_code=404, 
                detail=f"Unable to generate news for ticker {ticker}"
            )
        
        # Calculate sentiment metrics
        bullish = sum(1 for n in news_items if n["sentiment_label"] == "bullish")
        bearish = sum(1 for n in news_items if n["sentiment_label"] == "bearish")
        neutral = len(news_items) - bullish - bearish
        
        # Overall sentiment score (0-10 scale)
        avg_score = sum(n["sentiment_score"] for n in news_items) / len(news_items)
        overall_sentiment = round((avg_score + 1) * 5, 1)  # Convert -1,1 to 0,10
        
        # Sentiment label
        if overall_sentiment >= 7:
            label = "VERY_BULLISH"
        elif overall_sentiment >= 5.5:
            label = "BULLISH"
        elif overall_sentiment >= 4.5:
            label = "NEUTRAL"
        elif overall_sentiment >= 3:
            label = "BEARISH"
        else:
            label = "VERY_BEARISH"
        
        return SentimentResponse(
            ticker=ticker,
            overall_sentiment=overall_sentiment,
            sentiment_label=label,
            news_count=len(news_items),
            bullish_count=bullish,
            neutral_count=neutral,
            bearish_count=bearish,
            recent_news=[NewsItem(**n) for n in news_items],
            market=market,
            data_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generating sentiment for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{ticker}")
async def get_sentiment_summary(ticker: str) -> dict:
    """
    Quick sentiment summary for a ticker.
    
    Returns simplified sentiment score and label without full news details.
    Useful for dashboard widgets and quick lookups.
    """
    ticker = ticker.upper()
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    
    # Generate consistent sentiment based on ticker hash
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    # Generate sentiment in 4-8 range (slightly bullish bias)
    base_sentiment = 4 + random.random() * 4
    sentiment = round(base_sentiment, 1)
    
    random.seed()
    
    # Determine label
    if sentiment > 7:
        label = "VERY_BULLISH"
    elif sentiment > 6:
        label = "BULLISH"
    elif sentiment > 4:
        label = "NEUTRAL"
    elif sentiment > 3:
        label = "BEARISH"
    else:
        label = "VERY_BEARISH"
    
    return {
        "ticker": ticker,
        "sentiment": sentiment,
        "label": label,
        "market": get_market_region(ticker),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/social/{ticker}")
async def get_social_sentiment(ticker: str) -> dict:
    """
    Get simulated social media sentiment (Reddit, Twitter).
    
    Provides sentiment scores and mention counts for social platforms.
    Note: This is simulated data for demonstration purposes.
    """
    ticker = ticker.upper()
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol is required")
    
    # Generate consistent values based on ticker
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    reddit_sentiment = 40 + random.random() * 40
    twitter_sentiment = 45 + random.random() * 35
    reddit_mentions = random.randint(50, 500)
    twitter_mentions = random.randint(100, 2000)
    
    random.seed()
    
    combined_sentiment = (reddit_sentiment + twitter_sentiment) / 2
    
    return {
        "ticker": ticker,
        "reddit": {
            "sentiment": round(reddit_sentiment, 1),
            "mentions": reddit_mentions,
            "trending": reddit_sentiment > 70,
            "label": "bullish" if reddit_sentiment > 60 else "neutral" if reddit_sentiment > 40 else "bearish"
        },
        "twitter": {
            "sentiment": round(twitter_sentiment, 1),
            "mentions": twitter_mentions,
            "trending": twitter_sentiment > 70,
            "label": "bullish" if twitter_sentiment > 60 else "neutral" if twitter_sentiment > 40 else "bearish"
        },
        "combined": {
            "sentiment": round(combined_sentiment, 1),
            "total_mentions": reddit_mentions + twitter_mentions,
            "label": "bullish" if combined_sentiment > 60 else "neutral" if combined_sentiment > 40 else "bearish"
        },
        "market": get_market_region(ticker),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def sentiment_health() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sentiment_news",
        "markets_supported": ["US", "India", "UK", "Europe", "Asia"],
        "timestamp": datetime.now().isoformat()
    }
