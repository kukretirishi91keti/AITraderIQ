/**
 * Formatting and display utility functions.
 * Extracted from App.jsx for reusability.
 */

export const formatTimestamp = (timestamp, interval = '1d') => {
  if (timestamp === null || timestamp === undefined || timestamp === '') {
    return '';
  }

  if (typeof timestamp === 'string' && timestamp.includes('T')) {
    const date = new Date(timestamp);
    if (!isNaN(date.getTime())) {
      if (['1m', '5m', '15m', '30m'].includes(interval)) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      }
      if (interval === '1h') {
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      }
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  }

  const numTs = Number(timestamp);
  if (isNaN(numTs) || numTs <= 0) {
    return '';
  }

  const ms = numTs > 1e12 ? numTs : numTs * 1000;
  const date = new Date(ms);

  if (isNaN(date.getTime())) {
    return '';
  }

  if (['1m', '5m', '15m', '30m'].includes(interval)) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  if (interval === '1h') {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  if (['1d', '1wk'].includes(interval)) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

export const getSignalValue = (val) => {
  if (val === undefined || val === null) return null;
  if (typeof val === 'object') {
    return val.value ?? val.current ?? val;
  }
  return val;
};

export const formatPrice = (value, currency = '$', decimals = 2) => {
  const v = getSignalValue(value);
  if (v === null || v === undefined || isNaN(v)) return '-';
  return `${currency}${Number(v).toFixed(decimals)}`;
};

export const formatLargeNumber = (value) => {
  if (!value || isNaN(value)) return 'N/A';
  const num = Number(value);
  if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
  return num.toLocaleString();
};

export const getSignalColor = (signal) => {
  if (!signal) return 'text-gray-400';
  const s = signal.toUpperCase();
  if (s === 'BUY' || s === 'STRONG BUY' || s === 'STRONG_BUY') return 'text-green-400';
  if (s === 'SELL' || s === 'STRONG SELL' || s === 'STRONG_SELL') return 'text-red-400';
  return 'text-yellow-400';
};

export const getRsiColor = (rsi) => {
  if (rsi === null || rsi === undefined) return 'text-gray-400';
  if (rsi < 30) return 'text-green-400';
  if (rsi > 70) return 'text-red-400';
  return 'text-yellow-400';
};

const SUFFIX_TO_FLAG = {
  '.NS': '\u{1F1EE}\u{1F1F3}',
  '.BO': '\u{1F1EE}\u{1F1F3}',
  '.L': '\u{1F1EC}\u{1F1E7}',
  '.DE': '\u{1F1E9}\u{1F1EA}',
  '.PA': '\u{1F1EB}\u{1F1F7}',
  '.T': '\u{1F1EF}\u{1F1F5}',
  '.HK': '\u{1F1ED}\u{1F1F0}',
  '.TW': '\u{1F1F9}\u{1F1FC}',
  '.AX': '\u{1F1E6}\u{1F1FA}',
  '.TO': '\u{1F1E8}\u{1F1E6}',
  '.SA': '\u{1F1E7}\u{1F1F7}',
  '.KS': '\u{1F1F0}\u{1F1F7}',
  '.SI': '\u{1F1F8}\u{1F1EC}',
  '.SW': '\u{1F1E8}\u{1F1ED}',
  '.AS': '\u{1F1F3}\u{1F1F1}',
  '.MC': '\u{1F1EA}\u{1F1F8}',
  '.MI': '\u{1F1EE}\u{1F1F9}',
};

export const getFlagForSymbol = (symbol) => {
  if (!symbol) return '\u{1F1FA}\u{1F1F8}';
  if (symbol.includes('-USD')) return '\u20BF';
  if (symbol.includes('=X')) return '\u{1F4B1}';
  if (symbol.includes('=F')) return '\u{1F6E2}\uFE0F';
  for (const [suffix, flag] of Object.entries(SUFFIX_TO_FLAG)) {
    if (symbol.endsWith(suffix)) return flag;
  }
  return '\u{1F1FA}\u{1F1F8}';
};
