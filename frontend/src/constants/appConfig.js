/**
 * Application configuration constants.
 * Extracted from App.jsx for maintainability.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
export const APP_VERSION = '6.0.0';

// ─── India-first defaults ─────────────────────────────────────────────────────
export const DEFAULT_MARKET = 'India'; // matches markets.js id: 'India'
export const DEFAULT_SYMBOL = 'RELIANCE.NS';

/** Top 10 Nifty 50 heavyweights — shown as default watchlist on first load */
export const NIFTY_50_WATCHLIST = [
  'RELIANCE.NS',
  'TCS.NS',
  'HDFCBANK.NS',
  'INFY.NS',
  'ICICIBANK.NS',
  'BAJFINANCE.NS',
  'BHARTIARTL.NS',
  'SBIN.NS',
  'LT.NS',
  'KOTAKBANK.NS',
];

/** Full Nifty 50 for the scanner — 50 most liquid NSE stocks */
export const NIFTY_50_FULL = [
  'RELIANCE.NS',
  'TCS.NS',
  'HDFCBANK.NS',
  'INFY.NS',
  'ICICIBANK.NS',
  'HINDUNILVR.NS',
  'ITC.NS',
  'SBIN.NS',
  'BHARTIARTL.NS',
  'BAJFINANCE.NS',
  'KOTAKBANK.NS',
  'LT.NS',
  'ASIANPAINT.NS',
  'AXISBANK.NS',
  'MARUTI.NS',
  'SUNPHARMA.NS',
  'TITAN.NS',
  'WIPRO.NS',
  'NTPC.NS',
  'POWERGRID.NS',
  'ULTRACEMCO.NS',
  'NESTLEIND.NS',
  'TATAMOTORS.NS',
  'TECHM.NS',
  'HCLTECH.NS',
  'TATASTEEL.NS',
  'JSWSTEEL.NS',
  'ONGC.NS',
  'DRREDDY.NS',
  'CIPLA.NS',
  'ADANIPORTS.NS',
  'GRASIM.NS',
  'HEROMOTOCO.NS',
  'EICHERMOT.NS',
  'BAJAJFINSV.NS',
  'TATACONSUM.NS',
  'APOLLOHOSP.NS',
  'INDUSINDBK.NS',
  'BPCL.NS',
  'COALINDIA.NS',
  'SHRIRAMFIN.NS',
  'BRITANNIA.NS',
  'DIVISLAB.NS',
  'HDFCLIFE.NS',
  'SBILIFE.NS',
  'M&M.NS',
  'HINDALCO.NS',
];

/**
 * NSE trading session in IST.
 * Pre-open: 09:00–09:15  |  Regular: 09:15–15:30  |  Closed: rest
 */
export const NSE_HOURS = {
  preOpen: { start: '09:00', end: '09:15' },
  regular: { start: '09:15', end: '15:30' },
  timezone: 'Asia/Kolkata',
};

// ─── Polling ──────────────────────────────────────────────────────────────────
// Backend caches NSE quotes for 5 minutes (Twelve Data free tier = 8 req/min).
// Polling faster than the cache TTL just adds load without fresher data.
export const POLLING_INTERVALS = {
  HEALTHY: 300000,  // 5 min — matches backend quote cache TTL
  DEGRADED: 300000,
  CRITICAL: 600000,
  ERROR: 300000,
};

// ─── Trading styles (India-aware language) ────────────────────────────────────
export const TRADING_STYLES = {
  Day: {
    name: 'Intraday Trader',
    focus: 'intraday momentum on NSE, quick entries/exits, MIS orders',
    timeframe: '1-minute to 15-minute charts',
    riskProfile: 'aggressive, tight stop-losses, square off before 3:20 PM IST',
  },
  Swing: {
    name: 'Swing Trader',
    focus: 'multi-day trends on Nifty 50 stocks, support/resistance, BTST setups',
    timeframe: '1-hour to daily charts',
    riskProfile: 'moderate, wider stops, 2-10 day CNC holds',
  },
  Position: {
    name: 'Positional Trader',
    focus: 'long-term Nifty trends, FII/DII flow, sector rotation',
    timeframe: 'daily to weekly charts',
    riskProfile: 'conservative, wide stops, weeks to months CNC delivery',
  },
  Scalper: {
    name: 'Scalper',
    focus: 'micro-movements in Bank Nifty futures, bid-ask spreads, rapid MIS',
    timeframe: 'tick to 5-minute charts',
    riskProfile: 'very aggressive, very tight stops, dozens of trades daily',
  },
};

// ─── AI quick-prompt suggestions ─────────────────────────────────────────────
export const AI_PROMPTS = [
  'Should I buy or sell today?',
  'What are the support/resistance levels?',
  'Is this stock near 52-week high/low?',
  'Risk/reward analysis for this trade',
  'What does FII/DII activity suggest?',
  'Is this a good BTST setup?',
];

// ─── Keyboard shortcuts ───────────────────────────────────────────────────────
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
