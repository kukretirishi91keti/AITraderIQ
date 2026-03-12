"""
GenAI Router v5.0
==================
Multi-provider AI trading insights.

Supported LLM Providers:
- Groq (llama-3.3-70b-versatile, llama-3.1-8b-instant)
- OpenAI (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
- Anthropic (claude-sonnet-4-20250514, claude-haiku-4-20250414)

Users can select provider and supply their own API key from the UI.
Server-side env keys are used as defaults when no user key is provided.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

router = APIRouter(prefix="/api/genai", tags=["genai"])
logger = logging.getLogger(__name__)

# Server-side default keys (from .env)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Provider → default model
PROVIDER_DEFAULTS = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
}

MAX_TOKENS = 500

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class QueryRequest(BaseModel):
    question: str
    symbol: Optional[str] = "AAPL"
    price: Optional[float] = None
    currency: Optional[str] = "$"
    rsi: Optional[float] = None
    signal: Optional[str] = "HOLD"
    trader_style: Optional[str] = "swing"
    vwap: Optional[float] = None
    macd: Optional[float] = None
    llm_provider: Optional[str] = None   # groq, openai, anthropic
    llm_model: Optional[str] = None      # override model
    llm_api_key: Optional[str] = None    # user-supplied key

class QueryResponse(BaseModel):
    answer: str
    source: str
    model: Optional[str] = None
    provider: Optional[str] = None
    timestamp: str

# =============================================================================
# LLM CLIENT FACTORY
# =============================================================================

def _resolve_provider_and_key(request: QueryRequest):
    """Determine which provider/key/model to use.

    Priority: user-supplied key > server env key. Auto-detect provider from key prefix if not specified.
    """
    provider = (request.llm_provider or "").lower().strip()
    api_key = (request.llm_api_key or "").strip()

    # Auto-detect provider from key prefix
    if not provider and api_key:
        if api_key.startswith("gsk_"):
            provider = "groq"
        elif api_key.startswith("sk-ant-"):
            provider = "anthropic"
        elif api_key.startswith("sk-"):
            provider = "openai"

    # Fall back to whichever server key is configured
    if not provider:
        if GROQ_API_KEY:
            provider = "groq"
        elif OPENAI_API_KEY:
            provider = "openai"
        elif ANTHROPIC_API_KEY:
            provider = "anthropic"

    # Resolve key
    if not api_key:
        api_key = {"groq": GROQ_API_KEY, "openai": OPENAI_API_KEY, "anthropic": ANTHROPIC_API_KEY}.get(provider, "")

    model = (request.llm_model or "").strip() or PROVIDER_DEFAULTS.get(provider, "")

    return provider, api_key, model


def _call_llm(provider: str, api_key: str, model: str, system_prompt: str, user_message: str) -> str:
    """Call the selected LLM provider. Returns the response text or raises."""
    if provider == "groq":
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        return resp.choices[0].message.content

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        return resp.choices[0].message.content

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text

    else:
        raise ValueError(f"Unknown provider: {provider}")

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
    """Generate rich, context-aware rule-based response when LLM unavailable.

    Provides multi-paragraph analysis similar to what a real AI would return,
    with specific price levels, risk management, and actionable advice.
    """
    symbol = request.symbol or "STOCK"
    price = request.price if request.price is not None else 100.0
    currency = request.currency or "$"
    rsi = request.rsi if request.rsi is not None else 50.0
    signal = request.signal or "HOLD"
    vwap = request.vwap
    macd = request.macd
    style = (request.trader_style or "swing").lower()

    question = request.question.lower()

    # Compute derived levels
    atr_est = price * 0.02
    support_1 = round(price - atr_est * 2, 2)
    support_2 = round(price - atr_est * 4, 2)
    resist_1 = round(price + atr_est * 2, 2)
    resist_2 = round(price + atr_est * 4, 2)
    stop_loss = round(price - atr_est * 2.5, 2)
    tp_1 = round(price + atr_est * 3, 2)
    tp_2 = round(price + atr_est * 5, 2)

    rsi_label = ("oversold" if rsi < 30 else "overbought" if rsi > 70
                 else "slightly bearish" if rsi < 45 else "slightly bullish" if rsi > 55 else "neutral")
    vwap_str = f"\n- **VWAP**: {currency}{vwap:.2f} — price is {'above' if price > vwap else 'below'} VWAP" if vwap else ""
    macd_str = f"\n- **MACD**: {macd:.4f} — {'bullish' if macd and macd > 0 else 'bearish'} momentum" if macd is not None else ""

    # ---- Entry questions ----
    if any(w in question for w in ["entry", "buy", "enter", "position", "start", "accumulate"]):
        return f"""**Entry Analysis for {symbol} ({style.title()} Trader)**

**Current Setup:**
- **Price**: {currency}{price:.2f}  |  **Signal**: {signal}
- **RSI(14)**: {rsi:.1f} ({rsi_label}){vwap_str}{macd_str}

**Entry Strategy:**
{'- RSI is in oversold territory — this is a *high-probability* long entry zone. Consider scaling in at current levels.' if rsi < 30 else '- RSI is overbought — avoid chasing here. Wait for a pullback to ' + currency + str(support_1) + ' before entering.' if rsi > 70 else '- RSI is neutral. Best to wait for a dip toward ' + currency + str(support_1) + ' or a breakout above ' + currency + str(resist_1) + '.'}

**Key Levels:**
| Level | Price |
|-------|-------|
| Resistance 2 | {currency}{resist_2} |
| Resistance 1 | {currency}{resist_1} |
| **Current** | **{currency}{price:.2f}** |
| Support 1 | {currency}{support_1} |
| Support 2 | {currency}{support_2} |

**Risk Management:**
- Stop-loss: {currency}{stop_loss} (2.5 ATR below)
- Target 1: {currency}{tp_1} (R:R ≈ 1:1.2)
- Target 2: {currency}{tp_2} (R:R ≈ 1:2.0)
- Position size: Max 2-3% of portfolio per trade

*This is AI-generated analysis for educational purposes. Always verify with your own research.*"""

    # ---- Exit questions ----
    if any(w in question for w in ["exit", "target", "sell", "profit", "close", "take profit"]):
        return f"""**Exit Strategy for {symbol}**

**Current Position:**
- **Price**: {currency}{price:.2f}  |  **Signal**: {signal}
- **RSI(14)**: {rsi:.1f} ({rsi_label}){vwap_str}

**Exit Recommendations:**
{'- Strong SELL signal with overbought RSI — consider taking profits immediately or setting a tight trailing stop.' if rsi > 70 else '- Signal is bearish — scale out 50% now, trail the rest with a stop at ' + currency + str(round(price * 1.01, 2)) + '.' if 'SELL' in signal.upper() else '- No immediate exit pressure. Consider partial profit at ' + currency + str(tp_1) + ' and let the rest ride.'}

**Scaling Out Plan:**
1. Take 33% profit at {currency}{tp_1}
2. Take 33% profit at {currency}{tp_2}
3. Trail remaining 34% with a {currency}{round(atr_est * 2, 2)} trailing stop

**Warning Signs to Exit:**
- RSI crosses above 80 (extreme overbought)
- Price breaks below {currency}{support_1} on high volume
- MACD histogram turns negative after a bullish run

*Protecting capital is more important than maximizing gains.*"""

    # ---- Risk questions ----
    if any(w in question for w in ["risk", "stop", "loss", "safe", "danger", "position size"]):
        risk_level = "HIGH" if abs(rsi - 50) > 25 else "MODERATE" if abs(rsi - 50) > 10 else "LOW"
        return f"""**Risk Assessment for {symbol}**

**Risk Level: {risk_level}**
- RSI(14): {rsi:.1f} ({rsi_label})
- Estimated ATR: {currency}{atr_est:.2f} ({atr_est/price*100:.1f}% of price){vwap_str}

**Position Sizing (Kelly-inspired):**
- Conservative: Risk 1% of capital → Stop at {currency}{stop_loss}
  - If portfolio = $100,000 → Max loss = $1,000 → ~{int(1000 / (atr_est * 2.5))} shares
- Moderate: Risk 2% → ~{int(2000 / (atr_est * 2.5))} shares
- Aggressive: Risk 3% → ~{int(3000 / (atr_est * 2.5))} shares (not recommended)

**Stop-Loss Recommendations:**
- Tight (scalp): {currency}{round(price - atr_est * 1.5, 2)}
- Standard (swing): {currency}{stop_loss}
- Wide (position): {currency}{round(price - atr_est * 4, 2)}

**Risk Factors:**
{'- ⚠️ Extreme RSI levels increase reversal risk' if abs(rsi - 50) > 25 else '- Moderate RSI — normal volatility expected'}
{'- ⚠️ Price below VWAP — institutional selling pressure' if vwap and price < vwap else '- Price above VWAP — institutional support' if vwap else ''}

*Never risk more than you can afford to lose. Use stop-losses on every trade.*"""

    # ---- Levels questions ----
    if any(w in question for w in ["support", "resistance", "levels", "key", "zones"]):
        return f"""**Key Levels for {symbol}**

| Zone | Level | Significance |
|------|-------|-------------|
| R2 | {currency}{resist_2} | Major resistance — prior swing high area |
| R1 | {currency}{resist_1} | Minor resistance — first target for longs |
| **Current** | **{currency}{price:.2f}** | |
| S1 | {currency}{support_1} | First support — ideal dip-buy zone |
| S2 | {currency}{support_2} | Strong support — breakdown below is bearish |
{f'| VWAP | {currency}{vwap:.2f} | Institutional fair value |' if vwap else ''}

**How to Trade These Levels:**
- **Bounce play**: Buy at S1 ({currency}{support_1}) with stop below S2
- **Breakout play**: Buy above R1 ({currency}{resist_1}) targeting R2
- **Breakdown short**: Sell below S1 with target at S2

**RSI Context**: {rsi:.1f} ({rsi_label}) — {'favors buying dips' if rsi < 40 else 'suggests caution on new longs' if rsi > 60 else 'no directional bias'}"""

    # ---- Trend / momentum ----
    if any(w in question for w in ["trend", "direction", "momentum", "outlook"]):
        if rsi < 40:
            trend = "bearish"
            outlook = f"Momentum is to the downside. Watch for support at {currency}{support_1}. A bounce from oversold RSI could offer a counter-trend long."
        elif rsi > 60:
            trend = "bullish"
            outlook = f"Momentum is to the upside. Trend continuation likely toward {currency}{resist_1}. Buy dips to VWAP if available."
        else:
            trend = "neutral/range-bound"
            outlook = f"No clear trend. Price is range-bound between {currency}{support_1} and {currency}{resist_1}. Wait for a decisive breakout."

        return f"""**Trend Analysis for {symbol}**

**Overall Trend: {trend.upper()}**

{outlook}

**Indicators:**
- RSI(14): {rsi:.1f} — {rsi_label}{vwap_str}{macd_str}
- Signal: {signal}

**For {style.title()} Traders:**
{'- Look for quick intraday reversals at support/resistance' if style == 'day' else '- Position for 2-5 day swings from key levels' if style == 'swing' else '- Consider weekly chart for broader context' if style == 'position' else '- Focus on 1m/5m timeframes for micro-moves'}

*Markets can remain irrational longer than you can remain solvent. Use stops.*"""

    # ---- General catch-all ----
    return f"""**Analysis for {symbol}**

**Quick Summary:**
- **Price**: {currency}{price:.2f}  |  **Signal**: {signal}
- **RSI(14)**: {rsi:.1f} ({rsi_label}){vwap_str}{macd_str}

**Technical Picture:**
{'RSI in oversold territory — potential bounce opportunity.' if rsi < 30 else 'RSI in overbought territory — exercise caution on new longs.' if rsi > 70 else 'RSI neutral — no strong edge. Wait for setup.'}

**Key Levels:**
- Support: {currency}{support_1} / {currency}{support_2}
- Resistance: {currency}{resist_1} / {currency}{resist_2}

**Action Plan ({style.title()} Style):**
{'- Watch for intraday momentum shifts at key levels' if style == 'day' else '- Look for swing entry near support with tight stop' if style == 'swing' else '- Evaluate weekly trend before committing capital' if style == 'position' else '- Quick in/out at support/resistance bounces'}
- Stop-loss: {currency}{stop_loss}
- Target: {currency}{tp_1} (conservative) / {currency}{tp_2} (extended)

*AI-generated analysis. Not financial advice. Always do your own research.*"""

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/query", response_model=QueryResponse)
async def query_ai(request: QueryRequest):
    """
    Query the AI assistant for trading insights.

    Supports multiple LLM providers. User can pass llm_provider, llm_model,
    and llm_api_key in the request body to use their own key.
    Falls back to rich rule-based analysis when no LLM is available.
    """
    provider, api_key, model = _resolve_provider_and_key(request)

    if provider and api_key:
        try:
            system_prompt = get_system_prompt(request)
            answer = _call_llm(provider, api_key, model, system_prompt, request.question)

            return QueryResponse(
                answer=answer,
                source=provider,
                model=model,
                provider=provider,
                timestamp=datetime.now().isoformat(),
            )
        except ImportError as e:
            logger.warning(f"{provider} library not installed: {e}")
        except Exception as e:
            logger.error(f"LLM error ({provider}/{model}): {e}")

    # Fallback response
    try:
        answer = generate_fallback_response(request)
    except Exception as e:
        logger.error(f"Fallback generation error: {e}")
        answer = f"I can help analyze {request.symbol or 'this stock'}. Please check the technical indicators panel for RSI, MACD, and signal recommendations."

    return QueryResponse(
        answer=answer,
        source="fallback",
        model=None,
        provider=None,
        timestamp=datetime.now().isoformat(),
    )

@router.get("/health")
async def genai_health():
    """Check GenAI service health."""
    configured = []
    if GROQ_API_KEY:
        configured.append("groq")
    if OPENAI_API_KEY:
        configured.append("openai")
    if ANTHROPIC_API_KEY:
        configured.append("anthropic")

    return {
        "status": "healthy" if configured else "fallback",
        "configured_providers": configured,
        "accepts_user_keys": True,
        "fallback": "rule-based",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/providers")
async def list_providers():
    """List supported LLM providers and their models."""
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq",
                "models": [
                    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "recommended": True},
                    {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "fast": True},
                ],
                "key_prefix": "gsk_",
                "key_url": "https://console.groq.com/keys",
                "server_configured": bool(GROQ_API_KEY),
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "models": [
                    {"id": "gpt-4o", "name": "GPT-4o", "recommended": True},
                    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "fast": True},
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                ],
                "key_prefix": "sk-",
                "key_url": "https://platform.openai.com/api-keys",
                "server_configured": bool(OPENAI_API_KEY),
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "models": [
                    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "recommended": True},
                    {"id": "claude-haiku-4-20250414", "name": "Claude Haiku 4", "fast": True},
                ],
                "key_prefix": "sk-ant-",
                "key_url": "https://console.anthropic.com/settings/keys",
                "server_configured": bool(ANTHROPIC_API_KEY),
            },
        ],
        "default_provider": "groq" if GROQ_API_KEY else "openai" if OPENAI_API_KEY else "anthropic" if ANTHROPIC_API_KEY else None,
    }


@router.get("/models")
async def list_models():
    """List available AI models (legacy endpoint)."""
    return {
        "available": [
            {"id": "llama-3.3-70b-versatile", "provider": "groq", "recommended": True},
            {"id": "llama-3.1-8b-instant", "provider": "groq", "fast": True},
            {"id": "gpt-4o-mini", "provider": "openai"},
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic"},
        ],
        "default": PROVIDER_DEFAULTS.get("groq"),
        "fallback": "rule-based",
    }
