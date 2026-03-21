/**
 * StockContext.jsx - ENHANCED VERSION
 * ====================================
 * Location: frontend/src/context/StockContext.jsx
 *
 * Added: Market overview, indices ticker, full quote fields
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const REFRESH_INTERVALS = {
  QUOTE: 30000, // 30 seconds (was 5s - too aggressive for demo data)
  CANDLES: 60000, // 60 seconds
  OVERVIEW: 120000, // 2 minutes
};

const StockContext = createContext(undefined);

export const StockProvider = ({ children, initialSymbol = 'AAPL' }) => {
  // Core State
  const [symbol, setSymbolState] = useState(initialSymbol);
  const [quote, setQuote] = useState(null);
  const [candles, setCandles] = useState([]);
  const [marketOverview, setMarketOverview] = useState(null);
  const [health, setHealth] = useState(null);

  // Resilience Metadata
  const [dataQuality, setDataQuality] = useState('UNKNOWN');
  const [dataSource, setDataSource] = useState('unknown');
  const [dataAge, setDataAge] = useState(0);
  const [isAnchored, setIsAnchored] = useState(false);

  // UI State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chartInterval, setChartInterval] = useState('1d');

  // Set symbol
  const setSymbol = useCallback(
    (newSymbol) => {
      const normalized = newSymbol.toUpperCase().trim();
      if (normalized && normalized !== symbol) {
        setSymbolState(normalized);
        setIsLoading(true);
      }
    },
    [symbol]
  );

  // Fetch Quote
  const refreshQuote = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/quote/${symbol}`);
      if (!res.ok) throw new Error('Quote fetch failed');
      const data = await res.json();

      // Normalize quote data - handle different field names
      const normalizedQuote = {
        symbol: data.symbol || symbol,
        price: data.price,
        prevClose: data.prevClose || data.previousClose,
        change: data.change,
        changePercent: data.changePercent,
        currency: data.currency || '$',
        market: data.market || 'US',
        // Day stats - try multiple field names
        dayOpen: data.dayOpen || data.open || data.regularMarketOpen,
        dayHigh: data.dayHigh || data.high || data.regularMarketDayHigh,
        dayLow: data.dayLow || data.low || data.regularMarketDayLow,
        volume: data.volume || data.regularMarketVolume,
        // Company info
        companyName: data.companyName || data.shortName || data.longName,
        // Resilience fields
        source: data.source,
        dataQuality: data.dataQuality,
        asOf: data.asOf,
        isStale: data.isStale,
        isAnchored: data.isAnchored,
      };

      setQuote(normalizedQuote);

      // Update resilience status
      setDataQuality(data.dataQuality || 'LIVE');
      setDataSource(data.source || 'yfinance');
      setIsAnchored(data.isAnchored || false);
      if (data.asOf) {
        setDataAge(Math.floor(Date.now() / 1000) - data.asOf);
      }
      setError(null);
    } catch (err) {
      console.error('Quote Error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  // Fetch Candles
  const refreshCandles = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v4/candles/${symbol}?interval=${chartInterval}&lookback=100`
      );
      if (!res.ok) throw new Error('Candles fetch failed');
      const data = await res.json();
      // Handle both 'results' and 'candles' field names
      setCandles(data.results || data.candles || []);
    } catch (err) {
      console.error('Candle Error:', err);
    }
  }, [symbol, chartInterval]);

  // Fetch Market Overview (indices)
  const refreshMarketOverview = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/market-overview`);
      if (res.ok) {
        const data = await res.json();
        setMarketOverview(data);
      }
    } catch (e) {
      console.warn('Market Overview failed', e);
    }
  }, []);

  // Fetch Health
  const refreshHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v4/health`);
      if (res.ok) {
        setHealth(await res.json());
      }
    } catch (e) {
      console.warn('Health check failed', e);
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshQuote();
    refreshCandles();
    refreshMarketOverview();
    refreshHealth();

    // Set up intervals
    const quoteTimer = setInterval(refreshQuote, REFRESH_INTERVALS.QUOTE);
    const overviewTimer = setInterval(refreshMarketOverview, REFRESH_INTERVALS.OVERVIEW);

    return () => {
      clearInterval(quoteTimer);
      clearInterval(overviewTimer);
    };
  }, [refreshQuote, refreshCandles, refreshMarketOverview, refreshHealth]);

  // Refresh candles when interval changes
  useEffect(() => {
    refreshCandles();
  }, [chartInterval, refreshCandles]);

  // Update data age every second
  useEffect(() => {
    const timer = setInterval(() => {
      if (quote?.asOf) {
        setDataAge(Math.floor(Date.now() / 1000) - quote.asOf);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [quote?.asOf]);

  const value = {
    // Data
    symbol,
    setSymbol,
    quote,
    candles,
    marketOverview,
    health,

    // UI State
    isLoading,
    error,
    chartInterval,
    setChartInterval,

    // Resilience (for badges)
    dataQuality,
    dataSource,
    dataAge,
    isAnchored,

    // Actions
    refreshAll: () => {
      refreshQuote();
      refreshCandles();
      refreshMarketOverview();
    },
  };

  return <StockContext.Provider value={value}>{children}</StockContext.Provider>;
};

export const useStock = () => {
  const context = useContext(StockContext);
  if (!context) throw new Error('useStock must be used within StockProvider');
  return context;
};

// Additional hooks for specific use cases
export const useDataStatus = () => {
  const { dataQuality, dataSource, dataAge, isAnchored, health } = useStock();
  return { dataQuality, dataSource, dataAge, isAnchored, health };
};

export const useQuote = () => {
  const { quote, isLoading, error } = useStock();
  return { quote, isLoading, error };
};

export const useChart = () => {
  const { candles, chartInterval, setChartInterval } = useStock();
  return { candles, chartInterval, setChartInterval };
};

export default StockContext;
