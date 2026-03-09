"""
TraderAI Pro Services Package v4.9
==================================
Location: backend/services/__init__.py

Production-grade services:
- market_data_service: Real yfinance + LKG cache + MME fallback
- finbert_service: FinBERT sentiment analysis
- news_service: NewsAPI + curated fallback
- genai_service: Groq LLM integration
- financials_service: Company financials
- cache_manager: JSON file cache with locking
"""

from .cache_manager import (
    get_cache_manager,
    get_singleflight,
    CacheManager,
    SingleFlight,
    CacheEntry
)

from .market_data_service import (
    get_market_data_service,
    MarketDataService,
    MARKET_CONFIG,
    GLOBAL_STOCKS
)

from .finbert_service import (
    analyze_sentiment,
    analyze_batch,
    analyze_news_for_symbol,
    aggregate_sentiment,
    is_finbert_available,
    get_service_status as get_finbert_status
)

from .news_service import (
    get_news_service,
    get_news_with_sentiment,
    NewsService
)

from .genai_service import (
    get_genai_service,
    GenAIService
)

from .financials_service import (
    get_financials_service,
    FinancialsService
)

__all__ = [
    # Cache
    'get_cache_manager',
    'get_singleflight',
    'CacheManager',
    'SingleFlight',
    'CacheEntry',
    
    # Market Data
    'get_market_data_service',
    'MarketDataService',
    'MARKET_CONFIG',
    'GLOBAL_STOCKS',
    
    # FinBERT
    'analyze_sentiment',
    'analyze_batch',
    'analyze_news_for_symbol',
    'aggregate_sentiment',
    'is_finbert_available',
    'get_finbert_status',
    
    # News
    'get_news_service',
    'get_news_with_sentiment',
    'NewsService',
    
    # GenAI
    'get_genai_service',
    'GenAIService',
    
    # Financials
    'get_financials_service',
    'FinancialsService',
]
