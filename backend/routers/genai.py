"""
GenAI Router v4.9.6
====================
AI-powered trading insights using Groq LLM.

FIXES in v4.9.6:
- Fixed TypeError: '<' not supported between NoneType and int
- Added null-safe checks for rsi, price, vwap, macd
- Improved fallback response generation

Features:
- Context-aware responses based on stock data
- Currency-aware formatting
- Trader style customization
- Rate limiting and error handling
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

router = APIRouter(prefix="/api/genai", tags=["genai"])
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 300

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class QueryRequest(BaseModel):
    question: str
    symbol: Optional[str] = "AAPL"
    price: Optional[float] = None  # Allow None
    currency: Optional[str] = "$"
    rsi: Optional[float] = None    # Allow None
    signal: Optional[str] = "HOLD"
    trader_style: Optional[str] = "swing"
    vwap: Optional[float] = None
    macd: Optional[float] = None

class QueryResponse(BaseModel):
    answer: str
    source: str
    model: Optional[str] = None
    timestamp: str

# =============================================================================
# GROQ CLIENT
# =============================================================================

def get_groq_client():
    """Get or create Groq client."""
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except ImportError:
        logger.warning("Groq library not installed")
        return None
    except Exception as e:
        logger.error(f"Failed to create Groq client: {e}")
        return None

# =============================================================================
# SYSTEM PROMPTS BY TRADER STYLE
# =============================================================================

TRADER_PROMPTS = {
    "day": """You are a day trading assistant. Focus on:
- Intraday price action and momentum
- Quick entry/exit points
- Scalping opportunities
- Volume and volatility analysis
Keep responses very brief (1-2 sentences). Time-sensitive insights only.""",

    "swing": """You are a swing trading assistant. Focus on:
- Multi-day trend analysis
- Key support/resistance levels
- Optimal entry zones for 2-5 day holds
- Risk/reward setups
Keep responses concise (2-3 sentences).""",

    "position": """You are a position trading assistant. Focus on:
- Weekly/monthly trends
- Fundamental catalysts
- Major technical levels
- Long-term accumulation zones
Provide thoughtful analysis (2-3 sentences).""",

    "scalper": """You are a scalping assistant. Focus on:
- Micro price movements
- Order flow signals
- Sub-minute opportunities
- Tight stop-loss levels
Ultra-brief responses (1 sentence max). Speed is critical."""
}

def get_system_prompt(request: QueryRequest) -> str:
    """Build system prompt based on context."""
    style = (request.trader_style or "swing").lower()
    base_prompt = TRADER_PROMPTS.get(style, TRADER_PROMPTS["swing"])
    
    # Safe defaults for None values
    symbol = request.symbol or "STOCK"
    currency = request.currency or "$"
    price = request.price if request.price is not None else 100.0
    rsi = request.rsi if request.rsi is not None else 50.0
    signal = request.signal or "HOLD"
    
    context = f"""

Current Context:
- Stock: {symbol} at {currency}{price:.2f}
- RSI(14): {rsi:.1f}
- Signal: {signal}"""
    
    if request.vwap is not None:
        context += f"\n- VWAP: {currency}{request.vwap:.2f}"
    if request.macd is not None:
        context += f"\n- MACD: {request.macd:.4f}"
    
    context += f"\n\nAlways use {currency} for price references. Be actionable and specific."""
    
    return base_prompt + context

# =============================================================================
# FALLBACK RESPONSE GENERATOR
# =============================================================================

def generate_fallback_response(request: QueryRequest) -> str:
    """Generate rule-based response when LLM unavailable."""
    # Safe defaults for None values - THIS FIXES THE BUG
    symbol = request.symbol or "STOCK"
    price = request.price if request.price is not None else 100.0
    currency = request.currency or "$"
    rsi = request.rsi if request.rsi is not None else 50.0  # Default to neutral
    signal = request.signal or "HOLD"
    
    question = request.question.lower()

    # AI backend / intelligence engine questions
    if any(word in question for word in ["ai model", "ai backend", "intelligence", "how does", "what powers", "engine", "what ai", "models power"]):
        return (
            "TraderAI Pro uses a multi-layer intelligence engine:\n\n"
            "1. **AI Model**: Groq Llama 3.3 70B (primary) with Llama 3.1 8B (fast fallback)\n"
            "2. **Technical Analysis**: RSI, MACD, Bollinger Bands, VWAP, ATR computed in real-time\n"
            "3. **Sentiment Engine**: Aggregates StockTwits (35%), Reddit (30%), News (35%) into a -100 to +100 score\n"
            "4. **Strategy Intelligence**: 6 ranked strategies scored against your profile + market conditions\n"
            "5. **Backtesting**: Historical signal accuracy tracked per strategy type\n\n"
            "To get a Groq API key for full AI responses: visit console.groq.com (free tier available). "
            "Set GROQ_API_KEY in your .env file. Without it, you still get rule-based analysis from our technical engine."
        )

    # Strategy-related questions
    if any(word in question for word in ["best strategy", "which strategy", "strategy for", "recommend strategy"]):
        rsi_hint = f"RSI at {rsi:.0f}" if rsi else "neutral RSI"
        if rsi and rsi < 35:
            return f"With {rsi_hint}, {symbol} looks oversold. **Mean Reversion** or **Value Dip Buying** strategies work best here. Use the Strategy AI button in the toolbar for a full ranked analysis with entry/exit rules."
        elif rsi and rsi > 65:
            return f"With {rsi_hint}, {symbol} shows strong momentum. **Momentum Breakout** or **Trend Following** could work. Click 'Strategy AI' for personalized recommendations based on your capital and risk tolerance."
        else:
            return f"{symbol} is in a neutral zone ({rsi_hint}). Open the **Strategy AI** wizard (toolbar button) — it analyzes 6 strategies against current market conditions and your growth goals to find the best fit."

    # Entry point questions
    if any(word in question for word in ["entry", "buy", "enter", "position"]):
        if rsi < 30:
            return f"With RSI at {rsi:.0f}, {symbol} appears oversold. Consider entries near {currency}{price:.2f} with a stop below recent lows."
        elif rsi > 70:
            return f"RSI at {rsi:.0f} shows overbought conditions. Wait for a pullback to {currency}{price * 0.97:.2f} area before entering."
        else:
            return f"RSI at {rsi:.0f} is neutral. Current price {currency}{price:.2f} offers no clear edge—wait for better setup."
    
    # Exit/target questions
    if any(word in question for word in ["exit", "target", "sell", "profit"]):
        if signal == "SELL":
            return f"The SELL signal suggests taking profits. Consider exits near {currency}{price:.2f} or scale out over {currency}{price * 1.02:.2f}."
        elif signal == "BUY":
            return f"With BUY signal active, let winners run. Consider partial profit at {currency}{price * 1.05:.2f}, trail stop for remainder."
        else:
            return f"HOLD signal active. No immediate exit needed, but watch {currency}{price * 0.95:.2f} support and {currency}{price * 1.05:.2f} resistance."
    
    # Risk questions
    if any(word in question for word in ["risk", "stop", "loss"]):
        atr_estimate = price * 0.02
        return f"For {symbol} at {currency}{price:.2f}, consider stop-loss at {currency}{price - atr_estimate * 2:.2f} (2 ATR). Position size based on 1-2% account risk."
    
    # Support/Resistance questions
    if any(word in question for word in ["support", "resistance", "levels"]):
        support = price * 0.95
        resistance = price * 1.05
        return f"{symbol} key levels: Support at {currency}{support:.2f}, Resistance at {currency}{resistance:.2f}. RSI at {rsi:.0f} suggests {'oversold bounce potential' if rsi < 40 else 'overbought risk' if rsi > 60 else 'range-bound action'}."
    
    # Trend questions
    if any(word in question for word in ["trend", "direction", "momentum"]):
        if rsi < 40:
            return f"{symbol} showing bearish momentum with RSI at {rsi:.0f}. Watch for reversal signals near {currency}{price * 0.95:.2f} support."
        elif rsi > 60:
            return f"{symbol} showing bullish momentum with RSI at {rsi:.0f}. Trend continuation likely toward {currency}{price * 1.05:.2f}."
        else:
            return f"{symbol} in consolidation phase with RSI at {rsi:.0f}. Wait for breakout above {currency}{price * 1.02:.2f} or breakdown below {currency}{price * 0.98:.2f}."
    
    # General analysis (catch-all)
    rsi_status = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
    action = "Consider entries" if rsi < 40 else "Exercise caution" if rsi > 60 else "Wait for clearer setup"
    
    return f"{symbol} at {currency}{price:.2f} with RSI {rsi:.0f} ({rsi_status}). Current signal: {signal}. {action}."

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/query", response_model=QueryResponse)
async def query_ai(request: QueryRequest):
    """
    Query the AI assistant for trading insights.
    
    The AI provides context-aware responses based on:
    - Current stock price and technical indicators
    - Trader style preferences
    - Specific question asked
    """
    client = get_groq_client()
    
    if client and GROQ_API_KEY:
        try:
            system_prompt = get_system_prompt(request)
            
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.question}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.7
            )
            
            return QueryResponse(
                answer=response.choices[0].message.content,
                source="groq",
                model=DEFAULT_MODEL,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            # Fall through to fallback
    
    # Fallback response - now with null-safe handling
    try:
        answer = generate_fallback_response(request)
    except Exception as e:
        logger.error(f"Fallback generation error: {e}")
        answer = f"I can help analyze {request.symbol or 'this stock'}. Please check the technical indicators panel for RSI, MACD, and signal recommendations."
    
    return QueryResponse(
        answer=answer,
        source="fallback",
        model=None,
        timestamp=datetime.now().isoformat()
    )

@router.get("/health")
async def genai_health():
    """Check GenAI service health."""
    client = get_groq_client()
    
    if client and GROQ_API_KEY:
        try:
            # Quick test call
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return {
                "status": "healthy",
                "provider": "groq",
                "model": DEFAULT_MODEL,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "degraded",
                "provider": "groq",
                "error": str(e)[:100],
                "fallback": "rule-based",
                "timestamp": datetime.now().isoformat()
            }
    
    return {
        "status": "fallback",
        "provider": "rule-based",
        "reason": "Groq not configured",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/models")
async def list_models():
    """List available AI models."""
    return {
        "available": [
            {"id": "llama-3.3-70b-versatile", "provider": "groq", "recommended": True},
            {"id": "llama-3.1-8b-instant", "provider": "groq", "fast": True},
        ],
        "default": DEFAULT_MODEL,
        "fallback": "rule-based"
    }
