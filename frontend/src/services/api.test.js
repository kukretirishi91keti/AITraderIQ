import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../config', () => ({
  API_BASE: 'http://test',
  ENDPOINTS: {
    QUOTE: (sym) => `http://test/api/v4/quote/${sym}`,
    QUOTES_BATCH: 'http://test/api/v4/quotes',
    CANDLES: (sym, interval, lookback) =>
      `http://test/api/v4/candles/${sym}?interval=${interval}&lookback=${lookback}`,
    HEALTH: 'http://test/api/v4/health',
    MARKET_OVERVIEW: 'http://test/api/v4/market-overview',
  },
}));

import {
  getQuote,
  getQuotesBatch,
  getCandles,
  getHealth,
  checkConnection,
  extractDataStatus,
} from './api';

globalThis.fetch = vi.fn();

describe('api service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    fetch.mockReset();
  });

  it('getQuote returns parsed data', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        symbol: 'AAPL',
        price: 150,
        prevClose: 148,
        change: 2,
        changePercent: 1.35,
      }),
    });

    const result = await getQuote('AAPL');
    expect(result.symbol).toBe('AAPL');
    expect(result.price).toBe(150);
  });

  it('getQuote throws on failure', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Server error' }),
    });

    await expect(getQuote('AAPL')).rejects.toThrow();
  });

  it('getCandles includes query params', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ symbol: 'AAPL', interval: '1h', count: 0, candles: [] }),
    });

    await getCandles('AAPL', '1h', 50);

    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('interval=1h'), expect.any(Object));
  });

  it('getQuotesBatch sends POST', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 2, asOf: 0, results: [] }),
    });

    await getQuotesBatch(['AAPL', 'MSFT']);

    expect(fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('getHealth returns object', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    const result = await getHealth();
    expect(result.status).toBe('healthy');
  });

  it('checkConnection returns true on success', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    const connected = await checkConnection();
    expect(connected).toBe(true);
  });

  it('checkConnection returns false on error', async () => {
    fetch.mockRejectedValueOnce(new Error('Network failure'));

    const connected = await checkConnection();
    expect(connected).toBe(false);
  });
});
