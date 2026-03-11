import { describe, it, expect } from 'vitest';
import {
  formatPrice,
  formatLargeNumber,
  getSignalColor,
  getRsiColor,
  getSignalValue,
  getFlagForSymbol,
  formatTimestamp,
} from './formatters';

describe('formatPrice', () => {
  it('formats basic prices', () => {
    expect(formatPrice(123.456)).toBe('$123.46');
    expect(formatPrice(0)).toBe('$0.00');
  });

  it('handles currency symbol', () => {
    expect(formatPrice(100, '€')).toBe('€100.00');
  });

  it('handles custom decimals', () => {
    expect(formatPrice(99.999, '$', 1)).toBe('$100.0');
  });

  it('returns dash for invalid values', () => {
    expect(formatPrice(null)).toBe('-');
    expect(formatPrice(undefined)).toBe('-');
    expect(formatPrice(NaN)).toBe('-');
  });

  it('unwraps object values', () => {
    expect(formatPrice({ value: 42.5 })).toBe('$42.50');
    expect(formatPrice({ current: 10 })).toBe('$10.00');
  });
});

describe('formatLargeNumber', () => {
  it('formats trillions', () => {
    expect(formatLargeNumber(2.5e12)).toBe('2.50T');
  });

  it('formats billions', () => {
    expect(formatLargeNumber(1.23e9)).toBe('1.23B');
  });

  it('formats millions', () => {
    expect(formatLargeNumber(5.67e6)).toBe('5.67M');
  });

  it('formats smaller numbers with locale string', () => {
    expect(formatLargeNumber(1234)).toBe('1,234');
  });

  it('returns N/A for invalid input', () => {
    expect(formatLargeNumber(null)).toBe('N/A');
    expect(formatLargeNumber(undefined)).toBe('N/A');
    expect(formatLargeNumber(NaN)).toBe('N/A');
  });
});

describe('getSignalColor', () => {
  it('returns green for buy signals', () => {
    expect(getSignalColor('BUY')).toBe('text-green-400');
    expect(getSignalColor('STRONG BUY')).toBe('text-green-400');
    expect(getSignalColor('STRONG_BUY')).toBe('text-green-400');
  });

  it('returns red for sell signals', () => {
    expect(getSignalColor('SELL')).toBe('text-red-400');
    expect(getSignalColor('STRONG_SELL')).toBe('text-red-400');
  });

  it('returns yellow for neutral/hold', () => {
    expect(getSignalColor('HOLD')).toBe('text-yellow-400');
  });

  it('returns gray for null/undefined', () => {
    expect(getSignalColor(null)).toBe('text-gray-400');
    expect(getSignalColor(undefined)).toBe('text-gray-400');
  });
});

describe('getRsiColor', () => {
  it('returns green for oversold (<30)', () => {
    expect(getRsiColor(25)).toBe('text-green-400');
  });

  it('returns red for overbought (>70)', () => {
    expect(getRsiColor(75)).toBe('text-red-400');
  });

  it('returns yellow for neutral range', () => {
    expect(getRsiColor(50)).toBe('text-yellow-400');
  });

  it('returns gray for null', () => {
    expect(getRsiColor(null)).toBe('text-gray-400');
  });
});

describe('getSignalValue', () => {
  it('returns primitive values directly', () => {
    expect(getSignalValue(42)).toBe(42);
    expect(getSignalValue('test')).toBe('test');
  });

  it('unwraps object.value', () => {
    expect(getSignalValue({ value: 99 })).toBe(99);
  });

  it('unwraps object.current', () => {
    expect(getSignalValue({ current: 55 })).toBe(55);
  });

  it('returns null for null/undefined', () => {
    expect(getSignalValue(null)).toBeNull();
    expect(getSignalValue(undefined)).toBeNull();
  });
});

describe('getFlagForSymbol', () => {
  it('returns US flag for plain symbols', () => {
    expect(getFlagForSymbol('AAPL')).toContain('\u{1F1FA}');
  });

  it('returns Indian flag for .NS symbols', () => {
    expect(getFlagForSymbol('RELIANCE.NS')).toContain('\u{1F1EE}');
  });

  it('returns BTC symbol for crypto', () => {
    expect(getFlagForSymbol('BTC-USD')).toBe('\u20BF');
  });

  it('returns US flag for null', () => {
    expect(getFlagForSymbol(null)).toContain('\u{1F1FA}');
  });
});

describe('formatTimestamp', () => {
  it('returns empty string for null/undefined/empty', () => {
    expect(formatTimestamp(null)).toBe('');
    expect(formatTimestamp(undefined)).toBe('');
    expect(formatTimestamp('')).toBe('');
  });

  it('returns empty string for invalid numbers', () => {
    expect(formatTimestamp(-1)).toBe('');
    expect(formatTimestamp(0)).toBe('');
  });

  it('handles ISO string timestamps', () => {
    const result = formatTimestamp('2024-01-15T10:30:00Z', '1d');
    expect(result).toContain('Jan');
  });

  it('handles unix timestamps in seconds', () => {
    const result = formatTimestamp(1705312200, '1d');
    expect(result).toContain('Jan');
  });
});
