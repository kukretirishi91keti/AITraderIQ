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
import asyncio
import logging

router = APIRouter(prefix="/api/genai", tags=["genai"])
logger = logging.getLogger(__name__)

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 300
# Hard ceiling for one AI answer. Must stay below the proxy timeouts in front of
# the backend (Netlify ~26s), otherwise the browser sees a dropped connection
# ("Failed to fetch") instead of a clean rule-based fallback.
GROQ_TOTAL_TIMEOUT_S = 18.0
# Models Groq has retired; requests for them are transparently upgraded.
RETIRED_MODELS = {"mixtral-8x7b-32768", "gemma2-9b-it", "llama3-70b-8192", "llama3-8b-8192"}


async def _groq_chat(api_key: str, model: str, messages: list, max_tokens: int) -> str:
    """Non-blocking Groq call with a bounded total time.

    The previous implementation used the synchronous client inside an async
    endpoint, which froze the whole event loop (every other request) for up to
    ~45s while Groq retried. This uses AsyncGroq + one retry + a hard timeout.
    """
    from groq import AsyncGroq

    client = AsyncGroq(api_key=api_key, timeout=12.0, max_retries=1)
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        ),
        timeout=GROQ_TOTAL_TIMEOUT_S,
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("Empty response from model")
    return content

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
    risk_tolerance: Optional[str] = None      # conservative, moderate, aggressive
    experience_level: Optional[str] = None    # beginner, intermediate, advanced, expert
    investment_horizon: Optional[str] = None  # short, medium, long
    vwap: Optional[float] = None
    macd: Optional[float] = None
    model: Optional[str] = None  # User-selected model override
    groq_api_key: Optional[str] = None  # User-supplied key overrides server env key

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
        return Groq(api_key=GROQ_API_KEY, timeout=15.0)
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
    "day": """You are an intraday trading assistant for NSE Indian markets. Focus on:
- Intraday price action and momentum on NSE stocks
- Quick MIS entry/exit points before 3:20 PM IST
- Volume surges and delivery % signals
- Circuit filter awareness (upper/lower circuit)
Keep responses very brief (1-2 sentences). Time-sensitive insights only.""",

    "swing": """You are a swing trading assistant for NSE/BSE Indian markets. Focus on:
- Multi-day trends in Nifty 50 and midcap stocks
- Key support/resistance levels for CNC delivery
- BTST (Buy Today Sell Tomorrow) setups
- FII/DII activity and sector rotation cues
Keep responses concise (2-3 sentences).""",

    "position": """You are a positional trading assistant for Indian markets. Focus on:
- Weekly/monthly trends in Nifty 50
- Fundamental triggers (quarterly results, FII flows, macro)
- Major technical levels for CNC long-term holds
- Sector rotation and thematic investing
Provide thoughtful analysis (2-3 sentences).""",

    "scalper": """You are a scalping assistant for NSE Bank Nifty / liquid Nifty stocks. Focus on:
- Micro price movements in Bank Nifty, Reliance, HDFC Bank
- Order flow and bid-ask spread in MIS mode
- Sub-5-minute opportunities
- Very tight stop-losses, exit before 3:25 PM IST
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

    # Investor profile context
    if request.risk_tolerance:
        context += f"\n- Risk Tolerance: {request.risk_tolerance}"
    if request.experience_level:
        context += f"\n- Experience Level: {request.experience_level}"
    if request.investment_horizon:
        context += f"\n- Investment Horizon: {request.investment_horizon}"

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
    # Use user-supplied key if provided, otherwise fall back to server env key
    effective_key = (request.groq_api_key or '').strip() or GROQ_API_KEY
    groq_error = None

    if effective_key:
        selected_model = request.model or DEFAULT_MODEL
        if selected_model in RETIRED_MODELS:
            selected_model = DEFAULT_MODEL
        messages = [
            {"role": "system", "content": get_system_prompt(request)},
            {"role": "user", "content": request.question},
        ]
        try:
            answer = await _groq_chat(effective_key, selected_model, messages, MAX_TOKENS)
            return QueryResponse(
                answer=answer,
                source="groq",
                model=selected_model,
                timestamp=datetime.now().isoformat(),
            )
        except ImportError:
            groq_error = "groq library not installed on server"
        except asyncio.TimeoutError:
            groq_error = f"timed out after {GROQ_TOTAL_TIMEOUT_S:.0f}s"
        except Exception as e:
            msg = str(e)
            # Model retired/unknown -> one retry on the default model
            if selected_model != DEFAULT_MODEL and ("model" in msg.lower() and ("decommission" in msg.lower() or "not found" in msg.lower() or "does not exist" in msg.lower())):
                try:
                    answer = await _groq_chat(effective_key, DEFAULT_MODEL, messages, MAX_TOKENS)
                    return QueryResponse(
                        answer=answer, source="groq", model=DEFAULT_MODEL,
                        timestamp=datetime.now().isoformat(),
                    )
                except Exception as e2:
                    msg = str(e2)
            if "401" in msg or "invalid_api_key" in msg.lower() or "invalid api key" in msg.lower():
                groq_error = "invalid API key — re-enter it via 🔑 AI Key"
            elif "429" in msg or "rate limit" in msg.lower():
                groq_error = "Groq rate limit reached — try again in a minute"
            else:
                groq_error = msg[:120]
        if groq_error:
            logger.error(f"Groq API error: {groq_error}")

    # Fallback response
    try:
        answer = generate_fallback_response(request)
    except Exception as e:
        logger.error(f"Fallback generation error: {e}")
        answer = f"I can help analyze {request.symbol or 'this stock'}. Please check the technical indicators panel for RSI, MACD, and signal recommendations."

    if not effective_key:
        reason = "No API key — click 🔑 AI Key in toolbar to add yours (free at console.groq.com)"
    elif groq_error:
        reason = f"Groq error: {groq_error}"
    else:
        reason = "Groq unavailable"
    return QueryResponse(
        answer=answer,
        source=f"rule-based | {reason}",
        model=None,
        timestamp=datetime.now().isoformat()
    )

class TestKeyRequest(BaseModel):
    groq_api_key: str

@router.post("/test-key")
async def test_api_key(request: TestKeyRequest):
    """Validate a user-supplied Groq API key with a minimal test call."""
    key = (request.groq_api_key or '').strip()
    if not key:
        return {"ok": False, "error": "No key provided"}
    try:
        await _groq_chat(key, DEFAULT_MODEL, [{"role": "user", "content": "hi"}], 5)
        return {"ok": True, "model": DEFAULT_MODEL}
    except asyncio.TimeoutError:
        return {"ok": False, "error": "Groq did not answer in time — try again"}
    except ImportError:
        return {"ok": False, "error": "Groq library not installed on server"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}

@router.get("/health")
async def genai_health():
    """Check GenAI service health."""
    if GROQ_API_KEY:
        try:
            await _groq_chat(GROQ_API_KEY, DEFAULT_MODEL, [{"role": "user", "content": "test"}], 5)
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
                "error": (str(e) or type(e).__name__)[:100],
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
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B", "provider": "groq", "recommended": True, "description": "Best quality, deeper analysis"},
            {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B", "provider": "groq", "fast": True, "description": "Fastest responses"},
        ],
        "default": DEFAULT_MODEL,
        "fallback": "rule-based"
    }
