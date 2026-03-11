import { describe, it, expect } from 'vitest';
import { API_BASE, ENDPOINTS, REFRESH_INTERVALS, FRESHNESS, UI_CONFIG } from './config';

describe('config', () => {
  it('has a valid API_BASE', () => {
    expect(API_BASE).toBeDefined();
    expect(typeof API_BASE).toBe('string');
  });

  it('ENDPOINTS build correct URLs', () => {
    expect(ENDPOINTS.QUOTE('AAPL')).toContain('/api/v4/quote/AAPL');
    expect(ENDPOINTS.CANDLES('MSFT', '1h', 50)).toContain('/api/v4/candles/MSFT');
    expect(ENDPOINTS.CANDLES('MSFT', '1h', 50)).toContain('interval=1h');
    expect(ENDPOINTS.CANDLES('MSFT', '1h', 50)).toContain('lookback=50');
  });

  it('REFRESH_INTERVALS are reasonable', () => {
    expect(REFRESH_INTERVALS.QUOTE).toBeGreaterThanOrEqual(10000);
    expect(REFRESH_INTERVALS.CANDLES).toBeGreaterThanOrEqual(30000);
    expect(REFRESH_INTERVALS.HEALTH).toBeGreaterThanOrEqual(30000);
  });

  it('FRESHNESS thresholds are ordered', () => {
    expect(FRESHNESS.LIVE).toBeLessThan(FRESHNESS.FRESH);
    expect(FRESHNESS.FRESH).toBeLessThan(FRESHNESS.STALE);
    expect(FRESHNESS.STALE).toBeLessThan(FRESHNESS.EXPIRED);
  });

  it('UI_CONFIG has valid defaults', () => {
    expect(UI_CONFIG.DEFAULT_WATCHLIST.length).toBeGreaterThan(0);
    expect(UI_CONFIG.CHART_INTERVALS).toContain('1d');
    expect(UI_CONFIG.DEFAULT_LOOKBACK).toBeGreaterThan(0);
  });
});
