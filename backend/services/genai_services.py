"""
GenAI Service v4.9
==================
Location: backend/services/genai_service.py

Real LLM integration using Groq API.
Provides AI-powered trading assistant with context awareness.

Features:
- Groq API integration (llama-3.3-70b-versatile)
- Context injection (stock data, indicators, sentiment)
- Trader type customization (momentum, value, swing, day)
- Fallback to template responses if API unavailable
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

# =============================================================================
# GROQ CONFIGURATION
# =============================================================================

# Get API key from environment or use provided key
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.3-70b-versatile"  # Fast and capable
GROQ_BACKUP_MODEL = "llama-3.1-8b-instant"  # Fallback model

# Try to import groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

# =============================================================================
# CLIENT INITIALIZATION
# =============================================================================

_groq_client = None


def _get_groq_client():
    """Get or create Groq client."""
    global _groq_client
    
    if not GROQ_AVAILABLE or not GROQ_API_KEY:
        return None
    
    if _groq_client is None:
        try:
            _groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("✅ Groq client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            return None
    
    return _groq_client


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_BASE = """You are TraderAI, an expert AI trading assistant for day traders. You provide actionable insights based on technical analysis, market sentiment, and fundamental data.

Your expertise includes:
- Technical analysis (RSI, MACD, Bollinger Bands, moving averages)
- Market sentiment interpretation
- Risk management strategies
- Entry/exit point recommendations
- Portfolio allocation guidance

Guidelines:
1. Be specific with numbers and levels when possible
2. Always mention key support/resistance levels
3. Include risk management advice (stop-loss, position sizing)
4. Acknowledge uncertainty when data is limited
5. Never guarantee profits - always emphasize risk
6. Tailor advice to the trader's style (momentum, value, swing, day trading)

Current date: {date}
"""

TRADER_TYPE_PROMPTS = {
    'momentum': """
Focus on momentum trading strategies:
- Identify stocks with strong price momentum
- Look for breakout patterns and trend continuation
- Recommend holding periods of days to weeks
- Emphasize volume confirmation for signals
""",
    'value': """
Focus on value investing approach:
- Identify undervalued stocks relative to fundamentals
- Consider P/E ratios, book value, and earnings growth
- Recommend longer holding periods (weeks to months)
- Emphasize margin of safety in entry points
""",
    'swing': """
Focus on swing trading strategies:
- Look for short-term price swings within trends
- Identify support/resistance bounce opportunities
- Recommend holding periods of 2-10 days
- Use RSI and MACD for entry/exit timing
""",
    'day': """
Focus on day trading strategies:
- Identify intraday momentum opportunities
- Look for high volume, volatile stocks
- Recommend quick entries and exits (minutes to hours)
- Emphasize strict risk management and stop-losses
"""
}


# =============================================================================
# CONTEXT BUILDERS
# =============================================================================

def build_stock_context(
    symbol: str,
    quote: Optional[Dict] = None,
    signals: Optional[Dict] = None,
    sentiment: Optional[Dict] = None,
    financials: Optional[Dict] = None
) -> str:
    """Build context string from available data."""
    
    context_parts = [f"Stock: {symbol}"]
    
    if quote:
        context_parts.append(f"""
Price Data:
- Current Price: {quote.get('currency', '$')}{quote.get('price', 'N/A')}
- Change: {quote.get('changePercent', 0):.2f}%
- Previous Close: {quote.get('previousClose', 'N/A')}
- Day Range: {quote.get('dayLow', 'N/A')} - {quote.get('dayHigh', 'N/A')}
- Volume: {quote.get('volume', 'N/A'):,}
- Data Quality: {quote.get('dataQuality', 'UNKNOWN')}
""")
    
    if signals:
        context_parts.append(f"""
Technical Signals:
- Signal: {signals.get('signal', 'N/A')} ({signals.get('strength', 'N/A')})
- RSI (14): {signals.get('rsi', 'N/A'):.1f}
- MACD: {signals.get('macd', {}).get('value', 'N/A')}
- MACD Signal: {signals.get('macd', {}).get('signal', 'N/A')}
- Bollinger Position: {signals.get('bollinger', {}).get('position', 'N/A')}
- Confidence: {signals.get('confidence', 'N/A')}%
- Risk Level: {signals.get('risk', 'N/A')}
""")
    
    if sentiment:
        context_parts.append(f"""
Market Sentiment:
- News Sentiment: {sentiment.get('news_sentiment', 'N/A')}
- Sentiment Score: {sentiment.get('score', 0.5):.2f}
- Headlines Analyzed: {sentiment.get('headlines_analyzed', 0)}
- Sentiment Source: {sentiment.get('source', 'N/A')}
""")
    
    if financials:
        context_parts.append(f"""
Fundamentals:
- Market Cap: {financials.get('marketCap', 'N/A')}
- P/E Ratio: {financials.get('pe', 'N/A')}
- Revenue: {financials.get('revenue', 'N/A')}
- Profit Margin: {financials.get('profitMargin', 'N/A')}
""")
    
    return "\n".join(context_parts)


# =============================================================================
# GROQ API CALL
# =============================================================================

def query_groq(
    question: str,
    context: str = "",
    trader_type: str = "swing",
    model: str = GROQ_MODEL
) -> Optional[str]:
    """
    Query Groq API with context.
    
    Returns response text or None if failed.
    """
    client = _get_groq_client()
    if not client:
        logger.warning("Groq client not available")
        return None
    
    # Build system prompt
    system_prompt = SYSTEM_PROMPT_BASE.format(date=datetime.now().strftime('%Y-%m-%d'))
    system_prompt += TRADER_TYPE_PROMPTS.get(trader_type.lower(), TRADER_TYPE_PROMPTS['swing'])
    
    # Build user message with context
    user_message = question
    if context:
        user_message = f"""Given the following market data:

{context}

User Question: {question}

Provide a helpful, specific response based on the data above."""
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9
        )
        
        response = completion.choices[0].message.content
        logger.info(f"Groq response received ({len(response)} chars)")
        return response
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"Groq API error: {error_str}")
        
        # Try backup model on rate limit
        if 'rate' in error_str.lower() and model != GROQ_BACKUP_MODEL:
            logger.info(f"Trying backup model: {GROQ_BACKUP_MODEL}")
            return query_groq(question, context, trader_type, GROQ_BACKUP_MODEL)
        
        return None


# =============================================================================
# FALLBACK RESPONSES
# =============================================================================

def generate_fallback_response(
    question: str,
    symbol: str = None,
    quote: Dict = None,
    signals: Dict = None,
    trader_type: str = "swing"
) -> str:
    """
    Generate template-based response when Groq unavailable.
    """
    question_lower = question.lower()
    symbol = symbol or "the stock"
    
    price_str = f"${quote.get('price', 0):.2f}" if quote else "current levels"
    change_pct = quote.get('changePercent', 0) if quote else 0
    
    rsi = signals.get('rsi', 50) if signals else 50
    signal = signals.get('signal', 'HOLD') if signals else 'HOLD'
    
    # Determine market condition
    if rsi < 30:
        rsi_status = "oversold territory (RSI < 30)"
        rsi_action = "watch for potential bounce"
    elif rsi > 70:
        rsi_status = "overbought territory (RSI > 70)"
        rsi_action = "consider taking profits or tightening stops"
    else:
        rsi_status = "neutral range"
        rsi_action = "wait for clearer signals"
    
    # Build response based on question type
    if any(w in question_lower for w in ['buy', 'entry', 'start']):
        return f"""Based on current data for {symbol} at {price_str}:

**Technical Position:** {signal} signal with RSI at {rsi:.1f} ({rsi_status})

**Entry Consideration:**
- Current price shows {change_pct:+.2f}% change today
- RSI suggests {rsi_action}
- As a {trader_type} trader, consider scaling into position

**Risk Management:**
- Suggested stop-loss: 3-5% below entry
- Position size: 2-3% of portfolio maximum
- Consider setting alerts at key support levels

*Note: This analysis is for educational purposes. Always do your own research.*"""

    elif any(w in question_lower for w in ['sell', 'exit', 'close']):
        return f"""Exit analysis for {symbol} at {price_str}:

**Current Status:** {signal} with RSI at {rsi:.1f}

**Exit Considerations:**
- If in profit: Consider {rsi_action}
- Use trailing stop-loss to protect gains
- Watch for breakdown below recent support

**For {trader_type} traders:**
- Set target profit levels at +5%, +10%, +15%
- Scale out in 3 tranches rather than all at once

*Remember: Protecting capital is more important than maximizing gains.*"""

    elif any(w in question_lower for w in ['risk', 'safe', 'danger']):
        return f"""Risk Assessment for {symbol}:

**Current Risk Level:** {'HIGH' if abs(change_pct) > 3 else 'MODERATE' if abs(change_pct) > 1 else 'LOW'}
- Daily volatility: {abs(change_pct):.2f}%
- RSI: {rsi:.1f} ({rsi_status})

**Risk Management Guidelines:**
1. Never risk more than 1-2% of portfolio per trade
2. Set stop-loss before entering any position
3. Monitor position size relative to liquidity

**Current Conditions:**
- Signal strength: {signals.get('confidence', 50) if signals else 50}%
- Consider reduced position size in current conditions"""

    else:
        # General analysis
        return f"""Analysis for {symbol} at {price_str}:

**Market Overview:**
- Current change: {change_pct:+.2f}%
- Technical signal: {signal}
- RSI (14): {rsi:.1f} ({rsi_status})

**Key Observations:**
- {rsi_action.capitalize()}
- Monitor volume for confirmation of moves
- Watch key support/resistance levels

**For {trader_type.title()} Traders:**
- Focus on your timeframe-specific setups
- Maintain disciplined risk management
- Set alerts rather than watching continuously

*This is AI-generated analysis. Verify with multiple sources before trading.*"""


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class GenAIService:
    """
    GenAI service for trading assistant.
    
    Uses Groq API with intelligent fallback.
    """
    
    def __init__(self):
        self.stats = {
            "groq_calls": 0,
            "groq_successes": 0,
            "fallback_used": 0,
            "total_queries": 0
        }
    
    async def query(
        self,
        question: str,
        symbol: Optional[str] = None,
        quote: Optional[Dict] = None,
        signals: Optional[Dict] = None,
        sentiment: Optional[Dict] = None,
        financials: Optional[Dict] = None,
        trader_type: str = "swing"
    ) -> Dict[str, Any]:
        """
        Process a user query with full context.
        
        Args:
            question: User's question
            symbol: Stock symbol
            quote: Quote data from market_data_service
            signals: Signal data
            sentiment: Sentiment analysis result
            financials: Company financials
            trader_type: User's trading style
            
        Returns:
            Response with answer and metadata
        """
        self.stats["total_queries"] += 1
        
        # Build context
        context = ""
        if symbol:
            context = build_stock_context(
                symbol=symbol,
                quote=quote,
                signals=signals,
                sentiment=sentiment,
                financials=financials
            )
        
        # Try Groq
        response = None
        source = "FALLBACK"
        
        if GROQ_AVAILABLE and GROQ_API_KEY:
            self.stats["groq_calls"] += 1
            response = query_groq(
                question=question,
                context=context,
                trader_type=trader_type
            )
            
            if response:
                self.stats["groq_successes"] += 1
                source = "GROQ_LLM"
        
        # Fallback if Groq failed
        if not response:
            self.stats["fallback_used"] += 1
            response = generate_fallback_response(
                question=question,
                symbol=symbol,
                quote=quote,
                signals=signals,
                trader_type=trader_type
            )
            source = "TEMPLATE_FALLBACK"
        
        return {
            "answer": response,
            "response": response,  # Alias for compatibility
            "symbol": symbol,
            "trader_type": trader_type,
            "source": source,
            "model": GROQ_MODEL if source == "GROQ_LLM" else None,
            "context_provided": bool(context),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status."""
        success_rate = 0
        if self.stats["groq_calls"] > 0:
            success_rate = self.stats["groq_successes"] / self.stats["groq_calls"] * 100
        
        return {
            "groq_available": GROQ_AVAILABLE,
            "groq_api_key_configured": bool(GROQ_API_KEY),
            "model": GROQ_MODEL,
            "backup_model": GROQ_BACKUP_MODEL,
            "stats": self.stats,
            "success_rate": round(success_rate, 2),
            "client_initialized": _groq_client is not None
        }


# =============================================================================
# SINGLETON
# =============================================================================

_genai_service: Optional[GenAIService] = None


def get_genai_service() -> GenAIService:
    """Get singleton GenAI service."""
    global _genai_service
    if _genai_service is None:
        _genai_service = GenAIService()
    return _genai_service


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("\n" + "="*60)
        print("GENAI SERVICE TEST")
        print("="*60)
        
        service = get_genai_service()
        
        # Test status
        print("\n📊 Service Status:")
        status = service.get_service_status()
        print(f"   Groq Available: {status['groq_available']}")
        print(f"   API Key Configured: {status['groq_api_key_configured']}")
        print(f"   Model: {status['model']}")
        
        # Test query
        print("\n🤖 Testing AI Query...")
        
        mock_quote = {
            'symbol': 'AAPL',
            'price': 195.50,
            'changePercent': 1.25,
            'previousClose': 193.09,
            'currency': '$',
            'dataQuality': 'LIVE'
        }
        
        mock_signals = {
            'signal': 'BUY',
            'strength': 'MODERATE',
            'rsi': 32.5,
            'confidence': 72,
            'risk': 'MEDIUM',
            'macd': {'value': 0.5, 'signal': 0.3},
            'bollinger': {'position': 'LOWER'}
        }
        
        result = await service.query(
            question="Should I buy AAPL now? What's your analysis?",
            symbol="AAPL",
            quote=mock_quote,
            signals=mock_signals,
            trader_type="swing"
        )
        
        print(f"\n📝 Response Source: {result['source']}")
        print(f"   Model: {result.get('model', 'N/A')}")
        print(f"\n{result['answer'][:500]}...")
        
    asyncio.run(test())
