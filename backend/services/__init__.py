"""
TraderAI Pro Services Package v5.0
==================================
All imports are safe - missing dependencies degrade gracefully.
"""

import logging

logger = logging.getLogger(__name__)

# Cache
try:
    from .cache_manager import (
        get_cache_manager, get_singleflight,
        CacheManager, SingleFlight, CacheEntry
    )
except ImportError as e:
    logger.warning(f"cache_manager not available: {e}")

# Market Data
try:
    from .market_data_service import (
        get_market_data_service, MarketDataService,
        MARKET_CONFIG, GLOBAL_STOCKS
    )
except ImportError as e:
    logger.warning(f"market_data_service not available: {e}")

# FinBERT Sentiment — optional, not active in current release.
# torch + transformers are NOT in requirements.txt; stubs are used instead.
# To enable: install torch + transformers, create services/finbert_service.py.
def analyze_sentiment(*a, **kw): return {"label": "neutral", "score": 0}
def analyze_batch(*a, **kw): return []
def analyze_news_for_symbol(*a, **kw): return []
def aggregate_sentiment(*a, **kw): return {"label": "neutral", "score": 0}
def is_finbert_available(): return False
def get_finbert_status(): return {"status": "unavailable"}

# News
try:
    from .news_service import (
        get_news_service, get_news_with_sentiment, NewsService
    )
except (ImportError, Exception) as e:
    logger.warning(f"news_service not available: {e}")

# GenAI
try:
    from .genai_service import (
        get_genai_service, GenAIService
    )
except (ImportError, Exception) as e:
    logger.warning(f"genai_service not available: {e}")

# Financials
try:
    from .financials_service import (
        get_financials_service, FinancialsService
    )
except (ImportError, Exception) as e:
    logger.warning(f"financials_service not available: {e}")
