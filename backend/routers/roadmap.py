# ================================================================
# roadmap.py - Coming Soon / Roadmap API Endpoint
# TraderAI Pro v5.6.6
# ================================================================

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# ============================================================
# DATA MODELS
# ============================================================

class Feature(BaseModel):
    name: str
    description: str
    status: str  # done, in_progress, planned, future
    progress: int  # 0-100
    eta: Optional[str] = None

class Category(BaseModel):
    name: str
    icon: str
    features: List[Feature]

class HighlightFeature(BaseModel):
    title: str
    tagline: str
    description: str
    inputs: List[dict]
    outputs: List[str]
    status: str

class RoadmapResponse(BaseModel):
    highlight: HighlightFeature
    categories: List[Category]
    stats: dict
    version: str
    last_updated: str

# ============================================================
# ROADMAP DATA
# ============================================================

ROADMAP_DATA = {
    "highlight": {
        "title": "AI Stock Discovery",
        "tagline": "Don't know what to trade? Let AI find opportunities for you!",
        "description": "Tell us your investment goals and constraints, and our AI will analyze thousands of stocks to find the best matches for your profile.",
        "inputs": [
            {"id": "budget", "label": "Investment Budget", "icon": "💰", "options": ["$1K - $5K", "$5K - $25K", "$25K - $100K", "$100K+"]},
            {"id": "timeline", "label": "Time Horizon", "icon": "⏱️", "options": ["1 Day", "1 Week", "1 Month", "3 Months", "6 Months+"]},
            {"id": "risk", "label": "Risk Tolerance", "icon": "📊", "options": ["Conservative", "Moderate", "Aggressive", "Very Aggressive"]},
            {"id": "markets", "label": "Preferred Markets", "icon": "🌍", "options": ["US Only", "US + India", "Global", "Crypto Included"]}
        ],
        "outputs": [
            "Top 5 AI-recommended stocks matching your criteria",
            "Expected profit/loss % range for each stock",
            "Entry price, Stop loss, and Target levels",
            "Confidence score and risk rating",
            "Detailed AI rationale for each recommendation"
        ],
        "status": "coming_soon"
    },
    "categories": [
        {
            "name": "Trading Features",
            "icon": "📈",
            "features": [
                {"name": "Candlestick Charts", "description": "OHLC candles with pattern detection", "status": "in_progress", "progress": 80, "eta": "v6.0"},
                {"name": "Drawing Tools", "description": "Trendlines, Fibonacci, Support/Resistance", "status": "planned", "progress": 40, "eta": "v6.1"},
                {"name": "20+ More Indicators", "description": "Bollinger Bands, MACD histogram, Stochastic, ATR", "status": "planned", "progress": 25, "eta": "v6.2"},
                {"name": "Pattern Recognition", "description": "Head & Shoulders, Double Top/Bottom, Flags", "status": "future", "progress": 0, "eta": "v7.0"}
            ]
        },
        {
            "name": "Platform Upgrades",
            "icon": "🛠️",
            "features": [
                {"name": "Real-time WebSocket Data", "description": "Live streaming prices without polling", "status": "in_progress", "progress": 60, "eta": "v6.0"},
                {"name": "User Authentication", "description": "Login, user profiles, cloud sync", "status": "planned", "progress": 30, "eta": "v6.1"},
                {"name": "Mobile App", "description": "iOS & Android native applications", "status": "planned", "progress": 10, "eta": "v7.0"},
                {"name": "Broker Integration", "description": "Connect Zerodha, Alpaca, Interactive Brokers", "status": "future", "progress": 0, "eta": "v7.0+"}
            ]
        },
        {
            "name": "AI Enhancements",
            "icon": "🤖",
            "features": [
                {"name": "AI Rationale Engine", "description": "Detailed explanations for every Buy/Sell signal", "status": "in_progress", "progress": 70, "eta": "v6.0"},
                {"name": "Trader Profiles", "description": "Momentum vs Value trading strategies", "status": "planned", "progress": 50, "eta": "v6.1"},
                {"name": "Backtest Results", "description": "Historical AI accuracy and performance metrics", "status": "planned", "progress": 35, "eta": "v6.2"}
            ]
        },
        {
            "name": "Data & Calendars",
            "icon": "📅",
            "features": [
                {"name": "Earnings Calendar", "description": "Track upcoming earnings dates for watchlist", "status": "planned", "progress": 50, "eta": "v6.1"},
                {"name": "Economic Calendar", "description": "Fed meetings, GDP, Jobs reports", "status": "planned", "progress": 40, "eta": "v6.1"},
                {"name": "News Aggregation", "description": "Multi-source news feed with sentiment", "status": "future", "progress": 20, "eta": "v6.2"}
            ]
        },
        {
            "name": "Smart Alerts",
            "icon": "🔔",
            "features": [
                {"name": "Price Alerts", "description": "Alert when price crosses threshold", "status": "done", "progress": 100, "eta": None},
                {"name": "RSI Alerts", "description": "Notify when RSI crosses 30/70 levels", "status": "planned", "progress": 60, "eta": "v6.0"},
                {"name": "Breakout Alerts", "description": "Support/Resistance break notifications", "status": "planned", "progress": 30, "eta": "v6.1"},
                {"name": "Signal Change Alerts", "description": "When AI signal changes (BUY→SELL)", "status": "planned", "progress": 45, "eta": "v6.1"},
                {"name": "Email/Push Notifications", "description": "Get alerts on phone and email", "status": "future", "progress": 0, "eta": "v7.0"}
            ]
        },
        {
            "name": "Export & Integration",
            "icon": "📱",
            "features": [
                {"name": "Export to CSV", "description": "Download portfolio, watchlist, trade history", "status": "planned", "progress": 70, "eta": "v6.0"},
                {"name": "PDF Reports", "description": "AI-generated analysis reports", "status": "future", "progress": 20, "eta": "v6.2"},
                {"name": "Google Sheets Sync", "description": "Live portfolio sync to spreadsheets", "status": "future", "progress": 0, "eta": "v7.0"},
                {"name": "Telegram Bot", "description": "Get alerts and query stocks via Telegram", "status": "future", "progress": 0, "eta": "v7.0"}
            ]
        }
    ],
    "stats": {
        "total_features": 23,
        "done": 1,
        "in_progress": 4,
        "planned": 12,
        "future": 6
    },
    "version": "5.6.6",
    "last_updated": datetime.now().strftime("%Y-%m-%d")
}

# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/roadmap", response_model=RoadmapResponse)
async def get_roadmap():
    """Get the product roadmap and coming soon features"""
    return ROADMAP_DATA

@router.get("/roadmap/highlight")
async def get_highlight():
    """Get just the highlight feature (AI Stock Discovery)"""
    return ROADMAP_DATA["highlight"]

@router.get("/roadmap/categories")
async def get_categories():
    """Get all feature categories"""
    return {"categories": ROADMAP_DATA["categories"]}

@router.get("/roadmap/stats")
async def get_stats():
    """Get roadmap statistics"""
    return ROADMAP_DATA["stats"]