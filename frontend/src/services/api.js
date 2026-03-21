/**
 * api.js
 * ======
 * Location: frontend/src/services/api.js
 *
 * Centralized API service for all backend calls.
 */

import { API_BASE, ENDPOINTS } from '../config';

// =============================================================================
// ERROR HANDLING
// =============================================================================

class APIError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

// =============================================================================
// BASE FETCH
// =============================================================================

async function apiFetch(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(errorData.detail || `HTTP ${response.status}`, response.status, errorData);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(error.message || 'Network error', 0, null);
  }
}

// =============================================================================
// QUOTE ENDPOINTS
// =============================================================================

export async function getQuote(symbol) {
  const data = await apiFetch(ENDPOINTS.QUOTE(symbol));
  return {
    symbol: data.symbol,
    price: data.price,
    prevClose: data.prevClose,
    change: data.change,
    changePercent: data.changePercent,
    currency: data.currency || '$',
    market: data.market || 'US',
    source: data.source,
    dataQuality: data.dataQuality,
    asOf: data.asOf,
    isStale: data.isStale,
    isAnchored: data.isAnchored,
  };
}

export async function getQuotesBatch(symbols) {
  const data = await apiFetch(ENDPOINTS.QUOTES_BATCH, {
    method: 'POST',
    body: JSON.stringify({ symbols }),
  });
  return {
    count: data.count,
    asOf: data.asOf,
    results: data.results,
  };
}

// =============================================================================
// CANDLES ENDPOINTS
// =============================================================================

export async function getCandles(symbol, interval = '1d', lookback = 100) {
  const data = await apiFetch(ENDPOINTS.CANDLES(symbol, interval, lookback));
  return {
    symbol: data.symbol,
    interval: data.interval,
    count: data.count,
    candles: data.candles,
    source: data.source,
    dataQuality: data.dataQuality,
    isAnchored: data.isAnchored,
  };
}

// =============================================================================
// COMBINED ENDPOINTS
// =============================================================================

export async function getStockData(symbol, timeframe = '1d') {
  const data = await apiFetch(ENDPOINTS.STOCK(symbol, timeframe));
  return {
    ticker: data.ticker,
    quote: data.quote,
    chart: data.chart,
    metadata: data.metadata,
  };
}

// =============================================================================
// WATCHLIST ENDPOINTS
// =============================================================================

export async function getWatchlist(symbols = null) {
  let url = ENDPOINTS.WATCHLIST;
  if (symbols && symbols.length > 0) {
    url += `?symbols=${symbols.join(',')}`;
  }
  return await apiFetch(url);
}

// =============================================================================
// MARKET ENDPOINTS
// =============================================================================

export async function getMarketOverview() {
  return await apiFetch(ENDPOINTS.MARKET_OVERVIEW);
}

// =============================================================================
// SYSTEM ENDPOINTS
// =============================================================================

export async function getHealth() {
  return await apiFetch(ENDPOINTS.HEALTH);
}

export async function getRoadmap() {
  return await apiFetch(ENDPOINTS.ROADMAP);
}

// =============================================================================
// UTILITIES
// =============================================================================

export async function checkConnection() {
  try {
    await getHealth();
    return true;
  } catch {
    return false;
  }
}

export function extractDataStatus(response) {
  return {
    quality: response.dataQuality || 'UNKNOWN',
    source: response.source || 'unknown',
    age: response.asOf ? Math.floor(Date.now() / 1000) - response.asOf : 0,
    isStale: response.isStale || false,
    isAnchored: response.isAnchored || false,
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  getQuote,
  getQuotesBatch,
  getCandles,
  getStockData,
  getWatchlist,
  getMarketOverview,
  getHealth,
  getRoadmap,
  checkConnection,
  extractDataStatus,
  APIError,
};
