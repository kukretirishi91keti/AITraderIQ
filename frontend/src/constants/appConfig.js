/**
 * Application configuration constants.
 * Extracted from App.jsx for maintainability.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
export const APP_VERSION = 'F';

export const POLLING_INTERVALS = {
  HEALTHY: 60000,
  DEGRADED: 120000,
  CRITICAL: 300000,
  ERROR: 180000,
};

export const TRADING_STYLES = {
  Day: {
    name: 'Day Trader',
    focus: 'intraday momentum, quick entries/exits, scalping opportunities',
    timeframe: '1-minute to 15-minute charts',
    riskProfile: 'aggressive, tight stop-losses, multiple trades per day',
  },
  Swing: {
    name: 'Swing Trader',
    focus: 'multi-day trends, support/resistance levels, chart patterns',
    timeframe: '1-hour to daily charts',
    riskProfile: 'moderate, wider stops, 2-10 day holds',
  },
  Position: {
    name: 'Position Trader',
    focus: 'long-term trends, fundamental analysis, sector rotation',
    timeframe: 'daily to weekly charts',
    riskProfile: 'conservative, wide stops, weeks to months holds',
  },
  Scalper: {
    name: 'Scalper',
    focus: 'micro-movements, bid-ask spreads, rapid execution',
    timeframe: 'tick to 5-minute charts',
    riskProfile: 'very aggressive, very tight stops, dozens of trades daily',
  },
};

export const AI_PROMPTS = [
  "What's the best entry point?",
  'Give me support/resistance levels',
  'Risk/reward analysis',
  'Should I buy or sell now?',
  'Technical outlook summary',
];

export const KEYBOARD_SHORTCUTS = [
  { key: '/', description: 'Focus search', action: 'search' },
  { key: '1-6', description: 'Change timeframe', action: 'timeframe' },
  { key: 'W', description: 'Toggle watchlist', action: 'watchlist' },
  { key: 'P', description: 'Open portfolio', action: 'portfolio' },
  { key: 'S', description: 'Open screener', action: 'screener' },
  { key: 'A', description: 'Set alert', action: 'alerts' },
  { key: '?', description: 'Show shortcuts', action: 'help' },
  { key: 'Esc', description: 'Close modal', action: 'close' },
];
