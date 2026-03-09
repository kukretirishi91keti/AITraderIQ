"""
Financials Service v4.9
=======================
Location: backend/services/financials_service.py

Provides company financial data:
- Key metrics (P/E, Market Cap, Revenue)
- AI-generated summary via Groq
- Caching for efficiency
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try imports
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

try:
    from starlette.concurrency import run_in_threadpool
except ImportError:
    import asyncio
    async def run_in_threadpool(func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args)

try:
    from services.cache_manager import get_cache_manager
    from services.genai_service import get_genai_service
except ImportError:
    from cache_manager import get_cache_manager
    try:
        from genai_service import get_genai_service
    except:
        get_genai_service = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _format_large_number(num: Optional[float]) -> str:
    """Format large numbers with B/M/K suffixes."""
    if num is None:
        return "N/A"
    
    try:
        num = float(num)
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        elif num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        elif num >= 1e3:
            return f"${num/1e3:.2f}K"
        else:
            return f"${num:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _format_percentage(num: Optional[float]) -> str:
    """Format as percentage."""
    if num is None:
        return "N/A"
    try:
        return f"{float(num)*100:.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def _format_ratio(num: Optional[float]) -> str:
    """Format ratio."""
    if num is None:
        return "N/A"
    try:
        return f"{float(num):.2f}"
    except (ValueError, TypeError):
        return "N/A"


# =============================================================================
# YFINANCE FETCH
# =============================================================================

def _fetch_financials_sync(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch company financials from yfinance.
    
    Uses ticker.info which is heavier but contains fundamentals.
    Cached aggressively since fundamentals don't change minute-to-minute.
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if not info:
            return None
        
        # Extract key metrics
        financials = {
            # Identification
            'symbol': symbol,
            'name': info.get('longName') or info.get('shortName') or symbol,
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            
            # Valuation
            'marketCap': info.get('marketCap'),
            'marketCapFormatted': _format_large_number(info.get('marketCap')),
            'enterpriseValue': info.get('enterpriseValue'),
            'enterpriseValueFormatted': _format_large_number(info.get('enterpriseValue')),
            
            # Price Ratios
            'pe': info.get('trailingPE'),
            'peFormatted': _format_ratio(info.get('trailingPE')),
            'forwardPe': info.get('forwardPE'),
            'forwardPeFormatted': _format_ratio(info.get('forwardPE')),
            'peg': info.get('pegRatio'),
            'pegFormatted': _format_ratio(info.get('pegRatio')),
            'priceToBook': info.get('priceToBook'),
            'priceToBookFormatted': _format_ratio(info.get('priceToBook')),
            
            # Profitability
            'revenue': info.get('totalRevenue'),
            'revenueFormatted': _format_large_number(info.get('totalRevenue')),
            'grossProfit': info.get('grossProfits'),
            'grossProfitFormatted': _format_large_number(info.get('grossProfits')),
            'netIncome': info.get('netIncomeToCommon'),
            'netIncomeFormatted': _format_large_number(info.get('netIncomeToCommon')),
            'profitMargin': info.get('profitMargins'),
            'profitMarginFormatted': _format_percentage(info.get('profitMargins')),
            'operatingMargin': info.get('operatingMargins'),
            'operatingMarginFormatted': _format_percentage(info.get('operatingMargins')),
            
            # Growth
            'revenueGrowth': info.get('revenueGrowth'),
            'revenueGrowthFormatted': _format_percentage(info.get('revenueGrowth')),
            'earningsGrowth': info.get('earningsGrowth'),
            'earningsGrowthFormatted': _format_percentage(info.get('earningsGrowth')),
            
            # Dividends
            'dividendYield': info.get('dividendYield'),
            'dividendYieldFormatted': _format_percentage(info.get('dividendYield')),
            'dividendRate': info.get('dividendRate'),
            'payoutRatio': info.get('payoutRatio'),
            'payoutRatioFormatted': _format_percentage(info.get('payoutRatio')),
            
            # Balance Sheet
            'totalCash': info.get('totalCash'),
            'totalCashFormatted': _format_large_number(info.get('totalCash')),
            'totalDebt': info.get('totalDebt'),
            'totalDebtFormatted': _format_large_number(info.get('totalDebt')),
            'debtToEquity': info.get('debtToEquity'),
            'currentRatio': info.get('currentRatio'),
            
            # Per Share
            'eps': info.get('trailingEps'),
            'epsFormatted': _format_ratio(info.get('trailingEps')),
            'bookValue': info.get('bookValue'),
            'bookValueFormatted': _format_ratio(info.get('bookValue')),
            
            # Analyst
            'targetPrice': info.get('targetMeanPrice'),
            'targetPriceFormatted': _format_ratio(info.get('targetMeanPrice')),
            'recommendation': info.get('recommendationKey', 'N/A'),
            'numberOfAnalysts': info.get('numberOfAnalystOpinions'),
            
            # Meta
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', 'N/A'),
            'dataQuality': 'LIVE',
            'source': 'YFINANCE',
            'timestamp': datetime.now().isoformat()
        }
        
        return financials
        
    except Exception as e:
        logger.warning(f"Financials fetch failed for {symbol}: {e}")
        return None


# =============================================================================
# FALLBACK DATA
# =============================================================================

def _generate_fallback_financials(symbol: str) -> Dict[str, Any]:
    """Generate placeholder financials when yfinance unavailable."""
    
    # Some hardcoded data for common symbols
    KNOWN_DATA = {
        'AAPL': {
            'name': 'Apple Inc.',
            'sector': 'Technology',
            'marketCap': 3200000000000,
            'pe': 28.5,
            'revenue': 394000000000,
            'profitMargin': 0.25
        },
        'MSFT': {
            'name': 'Microsoft Corporation',
            'sector': 'Technology',
            'marketCap': 2900000000000,
            'pe': 35.2,
            'revenue': 211000000000,
            'profitMargin': 0.36
        },
        'GOOGL': {
            'name': 'Alphabet Inc.',
            'sector': 'Technology',
            'marketCap': 1800000000000,
            'pe': 24.1,
            'revenue': 307000000000,
            'profitMargin': 0.22
        },
        'NVDA': {
            'name': 'NVIDIA Corporation',
            'sector': 'Technology',
            'marketCap': 1400000000000,
            'pe': 65.3,
            'revenue': 60000000000,
            'profitMargin': 0.55
        },
        'RELIANCE.NS': {
            'name': 'Reliance Industries Limited',
            'sector': 'Energy',
            'marketCap': 17500000000000,  # In INR
            'pe': 25.8,
            'revenue': 9500000000000,
            'profitMargin': 0.08
        }
    }
    
    known = KNOWN_DATA.get(symbol, {})
    
    return {
        'symbol': symbol,
        'name': known.get('name', symbol),
        'sector': known.get('sector', 'Unknown'),
        'industry': 'N/A',
        'marketCap': known.get('marketCap'),
        'marketCapFormatted': _format_large_number(known.get('marketCap')),
        'pe': known.get('pe'),
        'peFormatted': _format_ratio(known.get('pe')),
        'revenue': known.get('revenue'),
        'revenueFormatted': _format_large_number(known.get('revenue')),
        'profitMargin': known.get('profitMargin'),
        'profitMarginFormatted': _format_percentage(known.get('profitMargin')),
        'dataQuality': 'SIMULATED',
        'source': 'FALLBACK',
        'timestamp': datetime.now().isoformat()
    }


# =============================================================================
# AI SUMMARY
# =============================================================================

async def _generate_ai_summary(financials: Dict[str, Any]) -> str:
    """Generate AI summary of financials using Groq."""
    
    if not get_genai_service:
        return _generate_template_summary(financials)
    
    try:
        service = get_genai_service()
        
        # Build prompt
        prompt = f"""Provide a brief 2-3 sentence summary of this company's financial position:

Company: {financials.get('name', 'Unknown')}
Sector: {financials.get('sector', 'Unknown')}
Market Cap: {financials.get('marketCapFormatted', 'N/A')}
P/E Ratio: {financials.get('peFormatted', 'N/A')}
Revenue: {financials.get('revenueFormatted', 'N/A')}
Profit Margin: {financials.get('profitMarginFormatted', 'N/A')}
Revenue Growth: {financials.get('revenueGrowthFormatted', 'N/A')}
Analyst Recommendation: {financials.get('recommendation', 'N/A')}

Focus on valuation, profitability, and key insights for investors."""

        result = await service.query(
            question=prompt,
            symbol=financials.get('symbol'),
            trader_type="value"
        )
        
        if result.get('source') == 'GROQ_LLM':
            return result.get('answer', _generate_template_summary(financials))
        
    except Exception as e:
        logger.warning(f"AI summary generation failed: {e}")
    
    return _generate_template_summary(financials)


def _generate_template_summary(financials: Dict[str, Any]) -> str:
    """Generate template-based summary."""
    
    name = financials.get('name', 'This company')
    pe = financials.get('pe')
    market_cap = financials.get('marketCapFormatted', 'N/A')
    margin = financials.get('profitMargin')
    
    # Valuation assessment
    if pe and pe < 15:
        valuation = "appears undervalued"
    elif pe and pe > 30:
        valuation = "trades at a premium valuation"
    else:
        valuation = "is fairly valued"
    
    # Profitability assessment
    if margin and margin > 0.2:
        profitability = "with strong profit margins"
    elif margin and margin > 0.1:
        profitability = "with healthy profit margins"
    else:
        profitability = "with moderate profitability"
    
    return f"{name} ({market_cap} market cap) {valuation} {profitability}. Review the detailed metrics above for a complete picture of the company's financial health."


# =============================================================================
# MAIN SERVICE
# =============================================================================

class FinancialsService:
    """
    Service for company financial data.
    
    Features:
    - yfinance integration for live data
    - Aggressive caching (1 hour TTL)
    - AI-generated summaries
    - Fallback data for common symbols
    """
    
    def __init__(self):
        self.cache = get_cache_manager("financials")
        self.stats = {
            "live_fetches": 0,
            "cache_hits": 0,
            "fallback_used": 0
        }
    
    async def get_financials(
        self,
        symbol: str,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Get company financials with optional AI summary.
        
        Args:
            symbol: Stock symbol
            include_summary: Whether to include AI-generated summary
            
        Returns:
            Financial data dictionary
        """
        cache_key = f"financials:{symbol}"
        
        # Check cache (1 hour TTL for fundamentals)
        entry = self.cache.get(cache_key, ttl_seconds=3600)
        if entry:
            self.stats["cache_hits"] += 1
            data = entry.data
            data['cached'] = True
            return data
        
        # Try yfinance
        financials = None
        if YFINANCE_AVAILABLE:
            financials = await run_in_threadpool(_fetch_financials_sync, symbol)
            if financials:
                self.stats["live_fetches"] += 1
        
        # Fallback
        if not financials:
            self.stats["fallback_used"] += 1
            financials = _generate_fallback_financials(symbol)
        
        # Generate AI summary
        if include_summary:
            financials['summary'] = await _generate_ai_summary(financials)
        
        # Cache result
        self.cache.set(cache_key, financials)
        financials['cached'] = False
        
        return financials
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            "yfinance_available": YFINANCE_AVAILABLE,
            "cache_stats": self.cache.get_stats(),
            "service_stats": self.stats
        }


# =============================================================================
# SINGLETON
# =============================================================================

_financials_service: Optional[FinancialsService] = None


def get_financials_service() -> FinancialsService:
    """Get singleton financials service."""
    global _financials_service
    if _financials_service is None:
        _financials_service = FinancialsService()
    return _financials_service


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("\n" + "="*60)
        print("FINANCIALS SERVICE TEST")
        print("="*60)
        
        service = get_financials_service()
        
        # Test status
        print("\n📊 Service Status:")
        status = service.get_service_status()
        print(f"   yfinance Available: {status['yfinance_available']}")
        
        # Test fetch
        symbols = ['AAPL', 'RELIANCE.NS']
        
        for symbol in symbols:
            print(f"\n📈 Financials for {symbol}:")
            data = await service.get_financials(symbol, include_summary=True)
            
            print(f"   Name: {data.get('name', 'N/A')}")
            print(f"   Sector: {data.get('sector', 'N/A')}")
            print(f"   Market Cap: {data.get('marketCapFormatted', 'N/A')}")
            print(f"   P/E Ratio: {data.get('peFormatted', 'N/A')}")
            print(f"   Revenue: {data.get('revenueFormatted', 'N/A')}")
            print(f"   Source: {data.get('source', 'N/A')}")
            print(f"   Summary: {data.get('summary', 'N/A')[:100]}...")
    
    asyncio.run(test())
