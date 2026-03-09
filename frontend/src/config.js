/**
 * config.js
 * =========
 * Location: frontend/src/config.js
 * 
 * Central configuration for the frontend application.
 */

// API Base URL
export const API_BASE = 
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// API Endpoints
export const ENDPOINTS = {
  QUOTE: (symbol) => `${API_BASE}/api/v4/quote/${symbol}`,
  QUOTES_BATCH: `${API_BASE}/api/v4/quotes`,
  CANDLES: (symbol, interval = '1d', lookback = 100) => 
    `${API_BASE}/api/v4/candles/${symbol}?interval=${interval}&lookback=${lookback}`,
  STOCK: (symbol, timeframe = '1d') => 
    `${API_BASE}/api/v4/stock/${symbol}?timeframe=${timeframe}`,
  WATCHLIST: `${API_BASE}/api/v4/watchlist`,
  MARKET_OVERVIEW: `${API_BASE}/api/v4/market-overview`,
  HEALTH: `${API_BASE}/api/v4/health`,
  ROADMAP: `${API_BASE}/api/v4/roadmap`,
};

// Refresh intervals (milliseconds)
export const REFRESH_INTERVALS = {
  QUOTE: 5000,
  CANDLES: 30000,
  HEALTH: 10000,
  WATCHLIST: 10000,
};

// Data freshness thresholds (seconds)
export const FRESHNESS = {
  LIVE: 10,
  FRESH: 60,
  STALE: 300,
  EXPIRED: 3600,
};

// Data quality configuration
export const DATA_QUALITY = {
  LIVE: {
    label: 'LIVE',
    color: 'green',
    description: 'Real-time data',
    icon: '🟢',
  },
  STALE: {
    label: 'CACHED',
    color: 'yellow',
    description: 'Last-Known-Good data',
    icon: '🟡',
  },
  SIMULATED: {
    label: 'SIMULATED',
    color: 'purple',
    description: 'Modeled data',
    icon: '🟣',
  },
};

// UI Configuration
export const UI_CONFIG = {
  DEFAULT_CHART_INTERVAL: '1d',
  CHART_INTERVALS: ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1mo'],
  DEFAULT_LOOKBACK: 100,
  DEFAULT_WATCHLIST: [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    'TSLA', 'META', 'AMD', 'NFLX',
    'RELIANCE.NS', 'TCS.NS',
    'BTC-USD', 'ETH-USD',
  ],
};

export default {
  API_BASE,
  ENDPOINTS,
  REFRESH_INTERVALS,
  FRESHNESS,
  DATA_QUALITY,
  UI_CONFIG,
};