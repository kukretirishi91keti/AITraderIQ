import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';

// ============================================================
// CONFIGURATION - v5.8.8: Added Portfolio add/remove functionality
// ============================================================

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const APP_VERSION = 'F';

// Smart polling intervals based on system health
const POLLING_INTERVALS = {
  HEALTHY: 60000,
  DEGRADED: 120000,
  CRITICAL: 300000,
  ERROR: 180000
};

const MARKETS = [
  { id: 'US', name: 'US', flag: '🇺🇸', currency: '$', currencyName: 'USD', defaultSymbol: 'AAPL' },
  { id: 'India', name: 'India', flag: '🇮🇳', currency: '₹', currencyName: 'INR', defaultSymbol: 'RELIANCE.NS' },
  { id: 'UK', name: 'UK', flag: '🇬🇧', currency: '£', currencyName: 'GBP', defaultSymbol: 'HSBA.L' },
  { id: 'Germany', name: 'Germany', flag: '🇩🇪', currency: '€', currencyName: 'EUR', defaultSymbol: 'SAP.DE' },
  { id: 'France', name: 'France', flag: '🇫🇷', currency: '€', currencyName: 'EUR', defaultSymbol: 'OR.PA' },
  { id: 'Japan', name: 'Japan', flag: '🇯🇵', currency: '¥', currencyName: 'JPY', defaultSymbol: '7203.T' },
  { id: 'China', name: 'China', flag: '🇨🇳', currency: '¥', currencyName: 'CNY', defaultSymbol: '9988.HK' },
  { id: 'HongKong', name: 'Hong Kong', flag: '🇭🇰', currency: 'HK$', currencyName: 'HKD', defaultSymbol: '0700.HK' },
  { id: 'Taiwan', name: 'Taiwan', flag: '🇹🇼', currency: 'NT$', currencyName: 'TWD', defaultSymbol: '2330.TW' },  // ← NEW (22nd market)
  { id: 'Australia', name: 'Australia', flag: '🇦🇺', currency: 'A$', currencyName: 'AUD', defaultSymbol: 'BHP.AX' },
  { id: 'Canada', name: 'Canada', flag: '🇨🇦', currency: 'C$', currencyName: 'CAD', defaultSymbol: 'RY.TO' },
  { id: 'Brazil', name: 'Brazil', flag: '🇧🇷', currency: 'R$', currencyName: 'BRL', defaultSymbol: 'PETR4.SA' },
  { id: 'Korea', name: 'Korea', flag: '🇰🇷', currency: '₩', currencyName: 'KRW', defaultSymbol: '005930.KS' },
  { id: 'Singapore', name: 'Singapore', flag: '🇸🇬', currency: 'S$', currencyName: 'SGD', defaultSymbol: 'D05.SI' },
  { id: 'Switzerland', name: 'Switzerland', flag: '🇨🇭', currency: 'CHF', currencyName: 'CHF', defaultSymbol: 'NESN.SW' },
  { id: 'Netherlands', name: 'Netherlands', flag: '🇳🇱', currency: '€', currencyName: 'EUR', defaultSymbol: 'ASML.AS' },
  { id: 'Spain', name: 'Spain', flag: '🇪🇸', currency: '€', currencyName: 'EUR', defaultSymbol: 'SAN.MC' },
  { id: 'Italy', name: 'Italy', flag: '🇮🇹', currency: '€', currencyName: 'EUR', defaultSymbol: 'ENI.MI' },
  { id: 'Crypto', name: 'Crypto', flag: '₿', currency: '$', currencyName: 'USD', defaultSymbol: 'BTC-USD' },
  { id: 'ETF', name: 'ETF', flag: '📊', currency: '$', currencyName: 'USD', defaultSymbol: 'SPY' },
  { id: 'Forex', name: 'Forex', flag: '💱', currency: '$', currencyName: 'USD', defaultSymbol: 'EURUSD=X' },
  { id: 'Commodities', name: 'Commodities', flag: '🛢️', currency: '$', currencyName: 'USD', defaultSymbol: 'GC=F' },
];


const STATIC_UNIVERSE = {
  // === US Markets ===
  'US Tech': [
    { symbol: 'AAPL', name: 'Apple', flag: '🇺🇸', currency: '$' },
    { symbol: 'MSFT', name: 'Microsoft', flag: '🇺🇸', currency: '$' },
    { symbol: 'GOOGL', name: 'Alphabet', flag: '🇺🇸', currency: '$' },
    { symbol: 'NVDA', name: 'NVIDIA', flag: '🇺🇸', currency: '$' },
    { symbol: 'TSLA', name: 'Tesla', flag: '🇺🇸', currency: '$' },
    { symbol: 'META', name: 'Meta', flag: '🇺🇸', currency: '$' },
    { symbol: 'AMZN', name: 'Amazon', flag: '🇺🇸', currency: '$' },
    { symbol: 'AMD', name: 'AMD', flag: '🇺🇸', currency: '$' },
  ],
  
  // === India ===
  'India': [
    { symbol: 'RELIANCE.NS', name: 'Reliance', flag: '🇮🇳', currency: '₹' },
    { symbol: 'TCS.NS', name: 'TCS', flag: '🇮🇳', currency: '₹' },
    { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', flag: '🇮🇳', currency: '₹' },
    { symbol: 'INFY.NS', name: 'Infosys', flag: '🇮🇳', currency: '₹' },
    { symbol: 'ICICIBANK.NS', name: 'ICICI Bank', flag: '🇮🇳', currency: '₹' },
    { symbol: 'HINDUNILVR.NS', name: 'HUL', flag: '🇮🇳', currency: '₹' },
  ],
  
  // === UK ===
  'UK': [
    { symbol: 'HSBA.L', name: 'HSBC', flag: '🇬🇧', currency: '£' },
    { symbol: 'BP.L', name: 'BP', flag: '🇬🇧', currency: '£' },
    { symbol: 'SHEL.L', name: 'Shell', flag: '🇬🇧', currency: '£' },
    { symbol: 'AZN.L', name: 'AstraZeneca', flag: '🇬🇧', currency: '£' },
    { symbol: 'GSK.L', name: 'GSK', flag: '🇬🇧', currency: '£' },
  ],
  
  // === Germany ===
  'Germany': [
    { symbol: 'SAP.DE', name: 'SAP', flag: '🇩🇪', currency: '€' },
    { symbol: 'SIE.DE', name: 'Siemens', flag: '🇩🇪', currency: '€' },
    { symbol: 'ALV.DE', name: 'Allianz', flag: '🇩🇪', currency: '€' },
    { symbol: 'DTE.DE', name: 'Deutsche Telekom', flag: '🇩🇪', currency: '€' },
  ],
  
  // === France ===
  'France': [
    { symbol: 'OR.PA', name: "L'Oreal", flag: '🇫🇷', currency: '€' },
    { symbol: 'MC.PA', name: 'LVMH', flag: '🇫🇷', currency: '€' },
    { symbol: 'TTE.PA', name: 'TotalEnergies', flag: '🇫🇷', currency: '€' },
    { symbol: 'SAN.PA', name: 'Sanofi', flag: '🇫🇷', currency: '€' },
  ],
  
  // === Japan ===
  'Japan': [
    { symbol: '7203.T', name: 'Toyota', flag: '🇯🇵', currency: '¥' },
    { symbol: '6758.T', name: 'Sony', flag: '🇯🇵', currency: '¥' },
    { symbol: '9984.T', name: 'SoftBank', flag: '🇯🇵', currency: '¥' },
    { symbol: '6861.T', name: 'Keyence', flag: '🇯🇵', currency: '¥' },
  ],
  
  // === China ===
  'China': [
    { symbol: '9988.HK', name: 'Alibaba', flag: '🇨🇳', currency: 'HK$' },
    { symbol: '9618.HK', name: 'JD.com', flag: '🇨🇳', currency: 'HK$' },
    { symbol: '3690.HK', name: 'Meituan', flag: '🇨🇳', currency: 'HK$' },
    { symbol: '1810.HK', name: 'Xiaomi', flag: '🇨🇳', currency: 'HK$' },
  ],
  
  // === Hong Kong ===
  'Hong Kong': [
    { symbol: '0700.HK', name: 'Tencent', flag: '🇭🇰', currency: 'HK$' },
    { symbol: '0005.HK', name: 'HSBC HK', flag: '🇭🇰', currency: 'HK$' },
    { symbol: '1299.HK', name: 'AIA Group', flag: '🇭🇰', currency: 'HK$' },
    { symbol: '0941.HK', name: 'China Mobile', flag: '🇭🇰', currency: 'HK$' },
  ],
  
  // === Taiwan (NEW) ===
  'Taiwan': [
    { symbol: '2330.TW', name: 'TSMC', flag: '🇹🇼', currency: 'NT$' },
    { symbol: '2317.TW', name: 'Hon Hai', flag: '🇹🇼', currency: 'NT$' },
    { symbol: '2454.TW', name: 'MediaTek', flag: '🇹🇼', currency: 'NT$' },
    { symbol: '2308.TW', name: 'Delta Electronics', flag: '🇹🇼', currency: 'NT$' },
  ],
  
  // === Australia ===
  'Australia': [
    { symbol: 'BHP.AX', name: 'BHP', flag: '🇦🇺', currency: 'A$' },
    { symbol: 'CBA.AX', name: 'CommBank', flag: '🇦🇺', currency: 'A$' },
    { symbol: 'CSL.AX', name: 'CSL', flag: '🇦🇺', currency: 'A$' },
    { symbol: 'NAB.AX', name: 'NAB', flag: '🇦🇺', currency: 'A$' },
  ],
  
  // === Canada ===
  'Canada': [
    { symbol: 'RY.TO', name: 'Royal Bank', flag: '🇨🇦', currency: 'C$' },
    { symbol: 'TD.TO', name: 'TD Bank', flag: '🇨🇦', currency: 'C$' },
    { symbol: 'SHOP.TO', name: 'Shopify', flag: '🇨🇦', currency: 'C$' },
    { symbol: 'ENB.TO', name: 'Enbridge', flag: '🇨🇦', currency: 'C$' },
  ],
  
  // === Brazil ===
  'Brazil': [
    { symbol: 'PETR4.SA', name: 'Petrobras', flag: '🇧🇷', currency: 'R$' },
    { symbol: 'VALE3.SA', name: 'Vale', flag: '🇧🇷', currency: 'R$' },
    { symbol: 'ITUB4.SA', name: 'Itau', flag: '🇧🇷', currency: 'R$' },
    { symbol: 'BBDC4.SA', name: 'Bradesco', flag: '🇧🇷', currency: 'R$' },
  ],
  
  // === Korea ===
  'Korea': [
    { symbol: '005930.KS', name: 'Samsung', flag: '🇰🇷', currency: '₩' },
    { symbol: '000660.KS', name: 'SK Hynix', flag: '🇰🇷', currency: '₩' },
    { symbol: '035420.KS', name: 'Naver', flag: '🇰🇷', currency: '₩' },
    { symbol: '051910.KS', name: 'LG Chem', flag: '🇰🇷', currency: '₩' },
  ],
  
  // === Singapore ===
  'Singapore': [
    { symbol: 'D05.SI', name: 'DBS', flag: '🇸🇬', currency: 'S$' },
    { symbol: 'O39.SI', name: 'OCBC', flag: '🇸🇬', currency: 'S$' },
    { symbol: 'U11.SI', name: 'UOB', flag: '🇸🇬', currency: 'S$' },
    { symbol: 'Z74.SI', name: 'Singtel', flag: '🇸🇬', currency: 'S$' },
  ],
  
  // === Switzerland ===
  'Switzerland': [
    { symbol: 'NESN.SW', name: 'Nestle', flag: '🇨🇭', currency: 'CHF' },
    { symbol: 'ROG.SW', name: 'Roche', flag: '🇨🇭', currency: 'CHF' },
    { symbol: 'NOVN.SW', name: 'Novartis', flag: '🇨🇭', currency: 'CHF' },
    { symbol: 'UBSG.SW', name: 'UBS', flag: '🇨🇭', currency: 'CHF' },
  ],
  
  // === Netherlands ===
  'Netherlands': [
    { symbol: 'ASML.AS', name: 'ASML', flag: '🇳🇱', currency: '€' },
    { symbol: 'INGA.AS', name: 'ING', flag: '🇳🇱', currency: '€' },
    { symbol: 'PHIA.AS', name: 'Philips', flag: '🇳🇱', currency: '€' },
    { symbol: 'UNA.AS', name: 'Unilever', flag: '🇳🇱', currency: '€' },
  ],
  
  // === Spain ===
  'Spain': [
    { symbol: 'SAN.MC', name: 'Santander', flag: '🇪🇸', currency: '€' },
    { symbol: 'IBE.MC', name: 'Iberdrola', flag: '🇪🇸', currency: '€' },
    { symbol: 'ITX.MC', name: 'Inditex', flag: '🇪🇸', currency: '€' },
    { symbol: 'BBVA.MC', name: 'BBVA', flag: '🇪🇸', currency: '€' },
  ],
  
  // === Italy ===
  'Italy': [
    { symbol: 'ENI.MI', name: 'ENI', flag: '🇮🇹', currency: '€' },
    { symbol: 'ENEL.MI', name: 'Enel', flag: '🇮🇹', currency: '€' },
    { symbol: 'ISP.MI', name: 'Intesa', flag: '🇮🇹', currency: '€' },
    { symbol: 'UCG.MI', name: 'UniCredit', flag: '🇮🇹', currency: '€' },
  ],
  
  // === Crypto ===
  'Crypto': [
    { symbol: 'BTC-USD', name: 'Bitcoin', flag: '₿', currency: '$' },
    { symbol: 'ETH-USD', name: 'Ethereum', flag: 'Ξ', currency: '$' },
    { symbol: 'SOL-USD', name: 'Solana', flag: '◎', currency: '$' },
    { symbol: 'XRP-USD', name: 'Ripple', flag: '✕', currency: '$' },
    { symbol: 'BNB-USD', name: 'Binance', flag: '🔶', currency: '$' },
  ],
  
  // === ETF ===
  'ETF': [
    { symbol: 'SPY', name: 'S&P 500', flag: '📊', currency: '$' },
    { symbol: 'QQQ', name: 'Nasdaq 100', flag: '📊', currency: '$' },
    { symbol: 'IWM', name: 'Russell 2000', flag: '📊', currency: '$' },
    { symbol: 'GLD', name: 'Gold ETF', flag: '📊', currency: '$' },
    { symbol: 'VTI', name: 'Total Stock', flag: '📊', currency: '$' },
  ],
  
  // === Forex ===
  'Forex': [
    { symbol: 'EURUSD=X', name: 'EUR/USD', flag: '💱', currency: '$' },
    { symbol: 'GBPUSD=X', name: 'GBP/USD', flag: '💱', currency: '$' },
    { symbol: 'USDJPY=X', name: 'USD/JPY', flag: '💱', currency: '¥' },
    { symbol: 'AUDUSD=X', name: 'AUD/USD', flag: '💱', currency: '$' },
  ],
  
  // === Commodities ===
  'Commodities': [
    { symbol: 'GC=F', name: 'Gold', flag: '🥇', currency: '$' },
    { symbol: 'SI=F', name: 'Silver', flag: '🥈', currency: '$' },
    { symbol: 'CL=F', name: 'Crude Oil', flag: '🛢️', currency: '$' },
    { symbol: 'NG=F', name: 'Natural Gas', flag: '🔥', currency: '$' },
  ],
};

// Trading styles with descriptions
const TRADING_STYLES = {
  'Day': {
    name: 'Day Trader',
    focus: 'intraday momentum, quick entries/exits, scalping opportunities',
    timeframe: '1-minute to 15-minute charts',
    riskProfile: 'aggressive, tight stop-losses, multiple trades per day'
  },
  'Swing': {
    name: 'Swing Trader',
    focus: 'multi-day trends, support/resistance levels, chart patterns',
    timeframe: '1-hour to daily charts',
    riskProfile: 'moderate, wider stops, 2-10 day holds'
  },
  'Position': {
    name: 'Position Trader',
    focus: 'long-term trends, fundamental analysis, sector rotation',
    timeframe: 'daily to weekly charts',
    riskProfile: 'conservative, wide stops, weeks to months holds'
  },
  'Scalper': {
    name: 'Scalper',
    focus: 'micro-movements, bid-ask spreads, rapid execution',
    timeframe: 'tick to 5-minute charts',
    riskProfile: 'very aggressive, very tight stops, dozens of trades daily'
  }
};

// AI prompts for suggested questions
const AI_PROMPTS = [
  "What's the best entry point?",
  "Give me support/resistance levels",
  "Risk/reward analysis",
  "Should I buy or sell now?",
  "Technical outlook summary"
];

// Market-specific demo movers - All 21 markets
// Market-specific demo movers - All 22 markets
const MARKET_MOVERS = {
  'US': ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META'],
  'India': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS'],
  'UK': ['HSBA.L', 'BP.L', 'SHEL.L', 'AZN.L'],
  'Germany': ['SAP.DE', 'SIE.DE', 'VOW3.DE', 'BMW.DE'],
  'France': ['OR.PA', 'MC.PA', 'AIR.PA', 'TTE.PA'],
  'Japan': ['7203.T', '6758.T', '9984.T', '7974.T'],
  'China': ['9988.HK', '0700.HK', '3690.HK', '9618.HK'],
  'HongKong': ['0700.HK', '9988.HK', '0005.HK', '0388.HK'],
  'Taiwan': ['2330.TW', '2317.TW', '2454.TW', '2308.TW'],  // NEW - 22nd market
  'Australia': ['BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX'],
  'Canada': ['RY.TO', 'TD.TO', 'ENB.TO', 'SHOP.TO'],
  'Brazil': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'ABEV3.SA'],
  'Korea': ['005930.KS', '000660.KS', '035420.KS'],
  'Singapore': ['D05.SI', 'O39.SI', 'U11.SI'],
  'Switzerland': ['NESN.SW', 'NOVN.SW', 'ROG.SW', 'UBSG.SW'],
  'Netherlands': ['ASML.AS', 'INGA.AS', 'PHIA.AS', 'ADYEN.AS'],
  'Spain': ['SAN.MC', 'BBVA.MC', 'ITX.MC', 'IBE.MC'],
  'Italy': ['ENI.MI', 'ENEL.MI', 'ISP.MI', 'RACE.MI'],
  'Crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD'],
  'ETF': ['SPY', 'QQQ', 'IWM', 'DIA'],
  'Commodities': ['GC=F', 'CL=F', 'SI=F', 'NG=F'],
  'Forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X'],
};

// Keyboard shortcuts configuration
const KEYBOARD_SHORTCUTS = [
  { key: '/', description: 'Focus search', action: 'search' },
  { key: '1-6', description: 'Change timeframe', action: 'timeframe' },
  { key: 'W', description: 'Toggle watchlist', action: 'watchlist' },
  { key: 'P', description: 'Open portfolio', action: 'portfolio' },
  { key: 'S', description: 'Open screener', action: 'screener' },
  { key: 'A', description: 'Set alert', action: 'alerts' },
  { key: '?', description: 'Show shortcuts', action: 'help' },
  { key: 'Esc', description: 'Close modal', action: 'close' },
];

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

// Format Unix timestamp (milliseconds) to readable date/time - v5.8.3 FIXED
const formatTimestamp = (timestamp, interval = '1d') => {
  // Handle null/undefined/empty
  if (timestamp === null || timestamp === undefined || timestamp === '') {
    console.warn('[formatTimestamp] Empty timestamp received');
    return '';
  }
  
  // Handle ISO date strings (from backend 'date' field)
  if (typeof timestamp === 'string' && timestamp.includes('T')) {
    const date = new Date(timestamp);
    if (!isNaN(date.getTime())) {
      // Short intraday: time only
      if (['1m', '5m', '15m', '30m'].includes(interval)) {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      }
      // 1H spans multiple days: show date + time
      if (interval === '1h') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      }
      // Daily/weekly: date only
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  }
  
  // Handle numeric timestamps (milliseconds or seconds)
  const numTs = Number(timestamp);
  if (isNaN(numTs) || numTs <= 0) {
    console.warn('[formatTimestamp] Invalid timestamp:', timestamp);
    return '';
  }
  
  // Convert seconds to milliseconds if needed
  const ms = numTs > 1e12 ? numTs : numTs * 1000;
  const date = new Date(ms);
  
  if (isNaN(date.getTime())) {
    console.warn('[formatTimestamp] Could not parse date from:', timestamp);
    return '';
  }
  
  // Format based on interval
  // Short intraday (1m-30m): time only
  if (['1m', '5m', '15m', '30m'].includes(interval)) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  // 1H spans multiple days (100 candles = ~4 days): show date + time
  if (interval === '1h') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  // Daily/weekly: date only
  if (['1d', '1wk'].includes(interval)) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

// Fetch top movers from backend API - v5.8.6 FIXED: Better error handling and logging
const fetchTopMovers = async (marketId) => {
  console.log('[fetchTopMovers] Fetching for market:', marketId);
  try {
    const url = `${API_BASE}/api/v4/top-movers/${marketId}?limit=6`;
    console.log('[fetchTopMovers] URL:', url);
    
    const response = await fetch(url);
    if (!response.ok) {
      console.warn('[fetchTopMovers] HTTP error:', response.status);
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('[fetchTopMovers] Response:', data);
    
    // v5.8.4 FIX: Backend returns { movers: [...] }, not { gainers: [], losers: [] }
    let allMovers = [];
    
    if (data.movers && Array.isArray(data.movers)) {
      // New format: { movers: [...] }
      allMovers = data.movers.map(m => ({
        symbol: m.symbol?.includes('.') ? m.symbol.split('.')[0] : m.symbol,
        fullSymbol: m.fullSymbol || m.symbol,
        change: m.changePercent ?? m.change,
        price: m.price
      }));
      console.log('[fetchTopMovers] Parsed movers:', allMovers.map(m => `${m.symbol}(${m.fullSymbol})`));
    } else if (data.gainers || data.losers) {
      // Legacy format: { gainers: [...], losers: [...] }
      allMovers = [
        ...(data.gainers || []).map(g => ({
          symbol: g.ticker || g.symbol,
          fullSymbol: g.ticker || g.symbol,
          change: g.changePercent,
          price: g.price
        })),
        ...(data.losers || []).map(l => ({
          symbol: l.ticker || l.symbol,
          fullSymbol: l.ticker || l.symbol,
          change: l.changePercent,
          price: l.price
        }))
      ];
    }
    
    // Sort by absolute change and return top 6
    allMovers.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
    return allMovers.slice(0, 6);
  } catch (error) {
    console.warn(`[fetchTopMovers] Failed for ${marketId}:`, error.message);
    return generateDemoMovers(marketId);
  }
};

// Fallback demo movers when API fails - v5.8.6: Deterministic changes
const generateDemoMovers = (marketId) => {
  const demoStocksPerMarket = {
    'US': ['AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT', 'GOOGL'],
    'India': ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS'],
    'UK': ['HSBA.L', 'BP.L', 'SHEL.L', 'AZN.L'],
    'Germany': ['SAP.DE', 'SIE.DE', 'ALV.DE', 'BMW.DE'],
    'France': ['OR.PA', 'MC.PA', 'SAN.PA', 'TTE.PA'],
    'Japan': ['7203.T', '6758.T', '9984.T', '7974.T'],
    'China': ['9988.HK', '0700.HK', '3690.HK', '9618.HK'],
    'HongKong': ['0005.HK', '0011.HK', '0388.HK', '1299.HK'],
    'Taiwan': ['2330.TW', '2317.TW', '2454.TW', '2308.TW'],  // NEW - 22nd market
    'Australia': ['BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX'],
    'Canada': ['RY.TO', 'TD.TO', 'ENB.TO', 'SHOP.TO'],
    'Brazil': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'ABEV3.SA'],
    'Korea': ['005930.KS', '000660.KS', '005380.KS', '035420.KS'],
    'Singapore': ['D05.SI', 'O39.SI', 'U11.SI', 'Z74.SI'],
    'Switzerland': ['NESN.SW', 'ROG.SW', 'NOVN.SW', 'UBSG.SW'],
    'Netherlands': ['ASML.AS', 'INGA.AS', 'PHIA.AS', 'ABN.AS'],
    'Spain': ['SAN.MC', 'BBVA.MC', 'ITX.MC', 'IBE.MC'],
    'Italy': ['ENI.MI', 'ENEL.MI', 'ISP.MI', 'UCG.MI'],
    'Crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD'],
    'ETF': ['SPY', 'QQQ', 'IWM', 'GLD'],
    'Forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X'],
    'Commodities': ['GC=F', 'CL=F', 'SI=F', 'NG=F']
  };
  
  const symbols = demoStocksPerMarket[marketId] || demoStocksPerMarket['US'];
  console.log('[generateDemoMovers] Market:', marketId, 'Symbols:', symbols);
  
  // Use deterministic "random" based on symbol hash for consistent demo data
  const hashCode = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  };
  
  const result = symbols.map((s, i) => {
    const hash = hashCode(s + new Date().toDateString()); // Changes daily
    const change = ((hash % 1000) / 100 - 5).toFixed(2); // Range: -5 to +5
    return {
      symbol: s.includes('.') ? s.split('.')[0] : (s.includes('-') ? s.split('-')[0] : (s.includes('=') ? s.replace('=X', '') : s)),
      fullSymbol: s,
      change: parseFloat(change)
    };
  });
  
  console.log('[generateDemoMovers] Result:', result.map(m => `${m.symbol}(${m.fullSymbol}): ${m.change}%`));
  return result;
};

const generateMoversForMarket = (marketId) => {
  // Use the same logic as generateDemoMovers for consistency
  return generateDemoMovers(marketId);
};

const getSignalValue = (val) => {
  if (val === undefined || val === null) return null;
  if (typeof val === 'object') {
    return val.value ?? val.current ?? val;
  }
  return val;
};

const formatPrice = (value, currency = '$', decimals = 2) => {
  const v = getSignalValue(value);
  if (v === null || v === undefined || isNaN(v)) return '-';
  return `${currency}${Number(v).toFixed(decimals)}`;
};

const formatLargeNumber = (value) => {
  if (!value || isNaN(value)) return 'N/A';
  const num = Number(value);
  if (num >= 1e12) return `${(num / 1e12).toFixed(2)}T`;
  if (num >= 1e9) return `${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(2)}M`;
  return num.toLocaleString();
};

const getSignalColor = (signal) => {
  if (!signal) return 'text-gray-400';
  const s = signal.toUpperCase();
  if (s === 'BUY' || s === 'STRONG BUY' || s === 'STRONG_BUY') return 'text-green-400';
  if (s === 'SELL' || s === 'STRONG SELL' || s === 'STRONG_SELL') return 'text-red-400';
  return 'text-yellow-400';
};

const getRsiColor = (rsi) => {
  if (rsi === null || rsi === undefined) return 'text-gray-400';
  if (rsi < 30) return 'text-green-400';
  if (rsi > 70) return 'text-red-400';
  return 'text-yellow-400';
};

// ============================================================
// USER GUIDE MODAL COMPONENT
// ============================================================

const UserGuideModal = ({ onClose }) => (
  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div 
      className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto"
      onClick={e => e.stopPropagation()}
    >
      <div className="sticky top-0 bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-cyan-400">📖 TraderAI Pro User Guide</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
      </div>
      
      <div className="p-4 space-y-6">
        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🌍 Markets</h3>
          <p className="text-gray-300 text-sm">
            Click any market flag to switch between 22 global markets. Each market displays prices 
            in its native currency (USD, EUR, INR, JPY, etc.).
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">📊 Screener</h3>
          <p className="text-gray-300 text-sm">
            The screener scans stocks across categories. Filter by RSI conditions:
          </p>
          <ul className="text-gray-300 text-sm mt-2 space-y-1 list-disc list-inside">
            <li><span className="text-green-400">Oversold (RSI &lt; 30)</span> - Potential buy opportunities</li>
            <li><span className="text-red-400">Overbought (RSI &gt; 70)</span> - Potential sell signals</li>
            <li><span className="text-yellow-400">Neutral (30-70)</span> - No extreme conditions</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🤖 AI Assistant</h3>
          <p className="text-gray-300 text-sm">
            Ask questions about any stock. The AI considers your trading style and provides 
            tailored advice. Try suggested prompts or type your own questions.
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">📈 Technical Indicators</h3>
          <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
            <li><strong>RSI (14)</strong> - Momentum oscillator (0-100)</li>
            <li><strong>SMA 20</strong> - 20-period Simple Moving Average</li>
            <li><strong>EMA 12</strong> - 12-period Exponential Moving Average</li>
            <li><strong>VWAP</strong> - Volume Weighted Average Price</li>
            <li><strong>ATR</strong> - Average True Range (volatility)</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">⭐ Watchlist & Alerts</h3>
          <p className="text-gray-300 text-sm">
            Click "+ Watchlist" to track stocks. Set price alerts with "Set Alert" - 
            you'll be notified when conditions are met.
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🎯 Trading Styles</h3>
          <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
            <li><strong>Day</strong> - Intraday focus, quick trades</li>
            <li><strong>Swing</strong> - Multi-day trends, support/resistance</li>
            <li><strong>Position</strong> - Long-term, fundamental analysis</li>
            <li><strong>Scalper</strong> - Micro-movements, rapid execution</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">⌨️ Keyboard Shortcuts</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {KEYBOARD_SHORTCUTS.map(s => (
              <div key={s.key} className="flex justify-between text-gray-300">
                <kbd className="px-2 py-1 bg-gray-700 rounded text-cyan-400">{s.key}</kbd>
                <span>{s.description}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
      
      <div className="sticky bottom-0 bg-gray-800 p-4 border-t border-gray-700">
        <button 
          onClick={onClose}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
        >
          Got it!
        </button>
      </div>
    </div>
  </div>
);

// ============================================================
// WHAT'S NEXT / ROADMAP MODAL COMPONENT
// ============================================================

const WhatsNextModal = ({ onClose }) => {
  const upcomingFeatures = [
    { 
      name: 'Real-time WebSocket Streaming',
      description: 'Live price updates without polling',
      eta: 'Q1 2026',
      priority: 'High',
      icon: '⚡'
    },
    { 
      name: 'Advanced Charting',
      description: 'TradingView-style drawing tools & indicators',
      eta: 'Q1 2026',
      priority: 'High',
      icon: '📈'
    },
    { 
      name: 'Pattern Recognition AI',
      description: 'Automatic detection of head & shoulders, double tops, etc.',
      eta: 'Q2 2026',
      priority: 'Medium',
      icon: '🔍'
    },
    { 
      name: 'Portfolio Analytics',
      description: 'Track P&L, risk metrics, and performance',
      eta: 'Q1 2026',
      priority: 'High',
      icon: '💼'
    },
    { 
      name: 'Broker Integration',
      description: 'One-click trading with Zerodha, Alpaca, IBKR',
      eta: 'Q2 2026',
      priority: 'High',
      icon: '🔗'
    },
    { 
      name: 'Mobile App',
      description: 'React Native app for iOS and Android',
      eta: 'Q3 2026',
      priority: 'Medium',
      icon: '📱'
    },
  ];

  const recentUpdates = [
    { version: '5.8.0', date: 'Dec 2025', changes: 'Fixed chart timestamps, fundamentals, screener data' },
    { version: '5.7.0', date: 'Dec 2025', changes: 'Keyboard shortcuts, Watchlist editing, Roadmap modal' },
    { version: '5.5.0', date: 'Dec 2025', changes: 'Demo mode, circuit breaker, sentiment APIs' },
  ];

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-gray-800 rounded-lg max-w-3xl w-full max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-cyan-400">🚀 What's Next</h2>
            <p className="text-sm text-gray-400">TraderAI Pro Roadmap</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>
        
        <div className="p-4 space-y-6">
          {/* Recent Updates */}
          <section>
            <h3 className="text-lg font-semibold text-green-400 mb-3">✅ Recent Updates</h3>
            <div className="space-y-2">
              {recentUpdates.map((update, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-700/50 rounded-lg">
                  <span className="px-2 py-0.5 bg-green-600/30 text-green-400 text-xs rounded font-mono">
                    v{update.version}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-white">{update.changes}</p>
                    <p className="text-xs text-gray-500">{update.date}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Upcoming Features */}
          <section>
            <h3 className="text-lg font-semibold text-cyan-400 mb-3">🔮 Coming Soon</h3>
            <div className="grid gap-3">
              {upcomingFeatures.map((feature, i) => (
                <div key={i} className="p-4 bg-gray-700/50 rounded-lg border border-gray-600 hover:border-cyan-500/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{feature.icon}</span>
                      <div>
                        <h4 className="font-medium text-white">{feature.name}</h4>
                        <p className="text-sm text-gray-400">{feature.description}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        feature.priority === 'High' ? 'bg-red-600/30 text-red-400' :
                        feature.priority === 'Medium' ? 'bg-yellow-600/30 text-yellow-400' :
                        'bg-gray-600/30 text-gray-400'
                      }`}>
                        {feature.priority}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">ETA: {feature.eta}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Feedback */}
          <section className="p-4 bg-cyan-600/10 rounded-lg border border-cyan-600/30">
            <h3 className="text-lg font-semibold text-cyan-400 mb-2">💡 Have a Feature Request?</h3>
            <p className="text-sm text-gray-300">
              We're building TraderAI Pro with your feedback. Connect with us on kukretirishi91@gmail.com.
            </p>
          </section>
        </div>
        
        <div className="sticky bottom-0 bg-gray-800 p-4 border-t border-gray-700">
          <button 
            onClick={onClose}
            className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// WATCHLIST EDIT MODAL COMPONENT
// ============================================================

const WatchlistEditModal = ({ 
  onClose, 
  watchlist, 
  setWatchlist, 
  onSelectSymbol, 
  setAlerts,
  currentSymbol 
}) => {
  const [newSymbol, setNewSymbol] = useState('');
  const [draggedIndex, setDraggedIndex] = useState(null);

  const handleAdd = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (symbol && !watchlist.includes(symbol)) {
      setWatchlist(prev => [...prev, symbol]);
      setNewSymbol('');
    }
  };

  const handleRemove = (symbol) => {
    setWatchlist(prev => prev.filter(s => s !== symbol));
  };

  const handleAddAlert = (symbol) => {
    setAlerts(prev => [...prev, { symbol, condition: 'above', price: 0 }]);
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    
    const newWatchlist = [...watchlist];
    const draggedItem = newWatchlist[draggedIndex];
    newWatchlist.splice(draggedIndex, 1);
    newWatchlist.splice(index, 0, draggedItem);
    
    setWatchlist(newWatchlist);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="bg-gray-800 rounded-lg max-w-md w-full max-h-[80vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-yellow-400">⭐ Edit Watchlist</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>
        
        {/* Add new symbol */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="Add symbol (e.g., AAPL)"
              className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
            <button
              onClick={handleAdd}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
            >
              Add
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">Drag items to reorder • Click symbol to view</p>
        </div>
        
        {/* Watchlist items */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {watchlist.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Your watchlist is empty</p>
          ) : (
            watchlist.map((symbol, index) => (
              <div
                key={symbol}
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                className={`flex items-center justify-between p-3 bg-gray-700/50 rounded-lg cursor-move hover:bg-gray-700 transition-colors ${
                  draggedIndex === index ? 'opacity-50 border-2 border-cyan-500' : ''
                } ${symbol === currentSymbol ? 'border border-cyan-500' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 cursor-grab">⋮⋮</span>
                  <button
                    onClick={() => { onSelectSymbol(symbol); onClose(); }}
                    className="text-cyan-400 font-medium hover:underline"
                  >
                    {symbol}
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleAddAlert(symbol)}
                    className="px-2 py-1 text-xs bg-orange-600/30 text-orange-400 rounded hover:bg-orange-600/50"
                    title="Add alert"
                  >
                    🔔
                  </button>
                  <button
                    onClick={() => handleRemove(symbol)}
                    className="px-2 py-1 text-xs bg-red-600/30 text-red-400 rounded hover:bg-red-600/50"
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        
        <div className="p-4 border-t border-gray-700 flex gap-2">
          <button 
            onClick={() => setWatchlist([])}
            className="flex-1 py-2 bg-red-600/30 hover:bg-red-600/50 text-red-400 rounded text-sm font-medium"
          >
            Clear All
          </button>
          <button 
            onClick={onClose}
            className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================
// KEYBOARD SHORTCUTS MODAL
// ============================================================

const KeyboardShortcutsModal = ({ onClose }) => (
  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div 
      className="bg-gray-800 rounded-lg max-w-md w-full"
      onClick={e => e.stopPropagation()}
    >
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-cyan-400">⌨️ Keyboard Shortcuts</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
      </div>
      
      <div className="p-4">
        <div className="space-y-3">
          {KEYBOARD_SHORTCUTS.map(shortcut => (
            <div key={shortcut.key} className="flex items-center justify-between">
              <kbd className="px-3 py-1.5 bg-gray-700 rounded text-cyan-400 font-mono text-sm min-w-[60px] text-center">
                {shortcut.key}
              </kbd>
              <span className="text-gray-300 text-sm">{shortcut.description}</span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="p-4 border-t border-gray-700">
        <button 
          onClick={onClose}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
        >
          Got it!
        </button>
      </div>
    </div>
  </div>
);

// ============================================================
// MAIN APP COMPONENT
// ============================================================

export default function App() {
  // Core state
  const [selectedMarket, setSelectedMarket] = useState('US');
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [searchQuery, setSearchQuery] = useState('');
  const [traderStyle, setTraderStyle] = useState('Swing');
  const [chartInterval, setChartInterval] = useState('1d');

  // Data state
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]); // Empty array, never null
  const [signals, setSignals] = useState(null);
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [movers, setMovers] = useState([]);
  const [screenerData, setScreenerData] = useState({});

  // UI state
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('technicals');
  const [financials, setFinancials] = useState(null);
  const [financialsLoading, setFinancialsLoading] = useState(false);
  const [showScreener, setShowScreener] = useState(false);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showUserGuide, setShowUserGuide] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [showWhatsNext, setShowWhatsNext] = useState(false);
  const [showWatchlistEdit, setShowWatchlistEdit] = useState(false);
  const [showAddToPortfolio, setShowAddToPortfolio] = useState(false);
  const [portfolioShares, setPortfolioShares] = useState('');
  const [portfolioAvgPrice, setPortfolioAvgPrice] = useState('');
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Screener filters
  const [screenerFilter, setScreenerFilter] = useState('all');
  const [screenerCategory, setScreenerCategory] = useState('all');
  const [screenerLoading, setScreenerLoading] = useState(false);
  const [screenerCategories, setScreenerCategories] = useState([]); // Dynamic from backend

  // Watchlist & Alerts
  const [watchlist, setWatchlist] = useState(['AAPL', 'NVDA', 'TSLA', 'BTC-USD', 'SPY']);
  const [alerts, setAlerts] = useState([
    { symbol: 'AAPL', condition: 'above', price: 250 },
    { symbol: 'BTC-USD', condition: 'above', price: 110000 }
  ]);
  const [newAlertPrice, setNewAlertPrice] = useState('');
  const [newAlertCondition, setNewAlertCondition] = useState('above');

  // Portfolio
  const [portfolio, setPortfolio] = useState([
    { symbol: 'AAPL', shares: 10, avgPrice: 150 },
    { symbol: 'NVDA', shares: 5, avgPrice: 450 },
    { symbol: 'MSFT', shares: 8, avgPrice: 380 },
  ]);

  // Investor Profile
  const [investorProfile, setInvestorProfile] = useState(() => {
    const saved = localStorage.getItem('investorProfile');
    return saved ? JSON.parse(saved) : {
      name: '',
      riskTolerance: 'moderate',
      investmentHorizon: 'medium',
      experience: 'intermediate',
      capitalRange: 'medium',
      goals: []
    };
  });
  const [showInvestorProfile, setShowInvestorProfile] = useState(false);

  // AI Chat
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  // Health monitoring
  const [healthStatus, setHealthStatus] = useState('HEALTHY');
  const [pollingInterval, setPollingInterval] = useState(POLLING_INTERVALS.HEALTHY);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // Refs
  const intervalRef = useRef(null);
  const searchInputRef = useRef(null);

  // Current market configuration
  const currentMarket = useMemo(() => 
    MARKETS.find(m => m.id === selectedMarket) || MARKETS[0],
    [selectedMarket]
  );

  // ============================================================
  // KEYBOARD SHORTCUTS
  // ============================================================

  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') {
          e.target.blur();
        }
        return;
      }

      // Check for modals first
      const anyModalOpen = showScreener || showPortfolio || showAddToPortfolio || showAlerts || 
                          showUserGuide || showWhatsNext || showWatchlistEdit || showKeyboardHelp;

      switch (e.key) {
        case '/':
          e.preventDefault();
          searchInputRef.current?.focus();
          break;
        case '1':
          e.preventDefault();
          setChartInterval('1m');
          break;
        case '2':
          e.preventDefault();
          setChartInterval('5m');
          break;
        case '3':
          e.preventDefault();
          setChartInterval('15m');
          break;
        case '4':
          e.preventDefault();
          setChartInterval('1h');
          break;
        case '5':
          e.preventDefault();
          setChartInterval('1d');
          break;
        case '6':
          e.preventDefault();
          setChartInterval('1wk');
          break;
        case 'w':
        case 'W':
          e.preventDefault();
          if (!watchlist.includes(selectedSymbol)) {
            setWatchlist(prev => [...prev, selectedSymbol]);
          } else {
            setWatchlist(prev => prev.filter(s => s !== selectedSymbol));
          }
          break;
        case 'p':
        case 'P':
          e.preventDefault();
          if (!anyModalOpen) {
            setShowPortfolio(true);
          }
          break;
        case 's':
        case 'S':
          e.preventDefault();
          if (!anyModalOpen) {
            setShowScreener(true);
            fetchScreenerData();
          }
          break;
        case 'a':
        case 'A':
          e.preventDefault();
          if (!anyModalOpen) {
            setShowAlerts(true);
          }
          break;
        case '?':
          e.preventDefault();
          if (!anyModalOpen) {
            setShowKeyboardHelp(true);
          }
          break;
        case 'Escape':
          // Close any open modal
          setShowScreener(false);
          setShowPortfolio(false);
          setShowAddToPortfolio(false);
          setShowAlerts(false);
          setShowUserGuide(false);
          setShowWhatsNext(false);
          setShowWatchlistEdit(false);
          setShowKeyboardHelp(false);
          setShowDebug(false);
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedSymbol, watchlist, showScreener, showPortfolio, showAlerts, 
      showUserGuide, showWhatsNext, showWatchlistEdit, showAddToPortfolio, showKeyboardHelp]);

  // ============================================================
  // SYMBOL & MARKET HANDLERS
  // ============================================================

  const handleSymbolSelect = useCallback((symbol) => {
    const upperSymbol = symbol.toUpperCase();
    setSelectedSymbol(upperSymbol);
    setSearchQuery('');
    setAiMessages([]);
    
    // Auto-detect market from symbol
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) {
      setSelectedMarket('India');
    } else if (upperSymbol.endsWith('.L')) {
      setSelectedMarket('UK');
    } else if (upperSymbol.endsWith('.DE')) {
      setSelectedMarket('Germany');
    } else if (upperSymbol.endsWith('.T')) {
      setSelectedMarket('Japan');
    } else if (upperSymbol.endsWith('.AX')) {
      setSelectedMarket('Australia');
    } else if (upperSymbol.includes('-USD') || upperSymbol === 'BTC' || upperSymbol === 'ETH') {
      setSelectedMarket('Crypto');
    } else if (upperSymbol.includes('=X')) {
      setSelectedMarket('Forex');
    } else if (upperSymbol.includes('=F')) {
      setSelectedMarket('Commodities');
    } else if (['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'GLD'].includes(upperSymbol)) {
      setSelectedMarket('ETF');
    }
  }, []);

  const handleMarketChange = useCallback(async (marketId) => {
    console.log('[Market] ===== CHANGING MARKET TO:', marketId, '=====');
    
    // First, immediately update movers with fallback data to show instant feedback
    const fallbackMovers = generateDemoMovers(marketId);
    console.log('[Market] Setting fallback movers:', fallbackMovers.map(m => m.symbol));
    setMovers(fallbackMovers);
    
    // Update market and symbol
    setSelectedMarket(marketId);
    const market = MARKETS.find(m => m.id === marketId);
    if (market) {
      setSelectedSymbol(market.defaultSymbol);
      setAiMessages([]);
      
      // Then try to fetch real top movers from backend
      try {
        console.log('[Market] Fetching real movers from API for:', marketId);
        const freshMovers = await fetchTopMovers(marketId);
        if (freshMovers && freshMovers.length > 0) {
          console.log('[Market] Got API movers:', freshMovers.map(m => m.symbol));
          setMovers(freshMovers);
        }
      } catch (err) {
        console.warn('[Market] API fetch failed, keeping fallback:', err.message);
        // Fallback already set above
      }
    }
  }, []);

  // ============================================================
  // DATA FETCHING - v5.8.2: AbortController for React 18 Strict Mode
  // ============================================================

  const fetchAllData = useCallback(async (signal = null) => {
    if (!selectedSymbol) return;
    
    setLoading(true);
    
    try {
      // Fetch quote
      const quoteRes = await fetch(`${API_BASE}/api/v4/quote/${selectedSymbol}`, { signal });
      if (signal?.aborted) return;
      if (quoteRes.ok) {
        const quoteData = await quoteRes.json();
        setQuote(quoteData);
      }
      
      // Fetch history
      const historyRes = await fetch(`${API_BASE}/api/v4/history/${selectedSymbol}?interval=${chartInterval}`, { signal });
      if (signal?.aborted) return;
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        // Backend returns: {candles: [...], history: [...], data: [...]}
        const chartData = historyData.candles || historyData.history || historyData.data || historyData.prices || [];
        console.log('[Chart] Loaded', chartData.length, 'candles for', selectedSymbol, 'interval:', chartInterval);
        
        // v5.8.2: Log first/last candle for debugging timestamps
        if (chartData.length > 0) {
          console.log('[Chart] First candle:', chartData[0]);
          console.log('[Chart] Last candle:', chartData[chartData.length - 1]);
        }
        
        setHistory(Array.isArray(chartData) ? chartData : []);
      } else {
        console.error('[Chart] Failed to load history:', historyRes.status);
        setHistory([]);
      }
      
      // Fetch signals
      const signalsRes = await fetch(`${API_BASE}/api/v4/signals/${selectedSymbol}`, { signal });
      if (signal?.aborted) return;
      if (signalsRes.ok) {
        const signalsData = await signalsRes.json();
        setSignals(signalsData);
      }
      
      // Fetch news
      const newsRes = await fetch(`${API_BASE}/api/news/${selectedSymbol}`, { signal });
      if (signal?.aborted) return;
      if (newsRes.ok) {
        const newsData = await newsRes.json();
        setNews(newsData.articles || []);
      }
      
      // Fetch sentiment
      const sentimentRes = await fetch(`${API_BASE}/api/sentiment/reddit/${selectedSymbol}`, { signal });
      if (signal?.aborted) return;
      if (sentimentRes.ok) {
        const sentimentData = await sentimentRes.json();
        setSentiment(sentimentData);
      }
      
      // Fetch financials - FIXED: Map backend snake_case to frontend camelCase
      setFinancialsLoading(true);
      try {
        const financialsRes = await fetch(`${API_BASE}/api/v4/financials/${selectedSymbol}`, { signal });
        if (signal?.aborted) return;
        if (financialsRes.ok) {
          const data = await financialsRes.json();
          console.log('[Financials] Raw response:', data);
          
          // Backend returns: { success, symbol, name, currency, financials: {...}, source, timestamp }
          if (data.success && data.financials) {
            const f = data.financials;
            // Map snake_case to camelCase and add formatted values
            const mapped = {
              symbol: data.symbol,
              name: data.name,
              currency: data.currency,
              sector: f.sector || 'Technology',
              industry: f.industry || 'Software',
              // Formatted display values
              marketCap: f.market_cap_formatted || formatLargeNumber(f.market_cap),
              peRatio: f.pe_ratio ? f.pe_ratio.toFixed(2) : 'N/A',
              revenue: f.revenue_formatted || formatLargeNumber(f.revenue),
              eps: f.eps ? `$${f.eps.toFixed(2)}` : 'N/A',
              dividendYield: f.dividend_yield ? `${f.dividend_yield.toFixed(2)}%` : '0%',
              beta: f.beta ? f.beta.toFixed(2) : 'N/A',
              fiftyTwoWeekHigh: f['52_week_high'] || f.fiftyTwoWeekHigh,
              fiftyTwoWeekLow: f['52_week_low'] || f.fiftyTwoWeekLow,
              profitMargin: f.profit_margin ? `${f.profit_margin.toFixed(1)}%` : 'N/A',
              // Raw values for calculations
              marketCapRaw: f.market_cap,
              revenueRaw: f.revenue,
              netIncomeRaw: f.net_income,
              dataQuality: data.source || 'DEMO',
            };
            setFinancials(mapped);
            console.log('[Financials] Mapped for', selectedSymbol, ':', mapped);
          } else if (data.marketCap || data.peRatio) {
            // Already in correct format
            setFinancials(data);
          } else {
            console.warn('[Financials] Unexpected structure:', Object.keys(data));
            setFinancials(null);
          }
        } else {
          console.error('[Financials] Failed:', financialsRes.status, financialsRes.statusText);
          setFinancials(null);
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('[Financials] Error:', err);
        setFinancials(null);
      } finally {
        if (!signal?.aborted) setFinancialsLoading(false);
      }
      
      // Check health
      const healthRes = await fetch(`${API_BASE}/api/health`, { signal });
      if (signal?.aborted) return;
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealthStatus(healthData.status?.toUpperCase() || 'HEALTHY');
        
        // Adjust polling based on health
        if (healthData.polling_recommendation) {
          setPollingInterval(healthData.polling_recommendation * 1000);
        }
      }
      
      setLastFetchTime(new Date());
      setLoading(false);
      
    } catch (err) {
      // Ignore AbortError - this is expected when component unmounts
      if (err.name === 'AbortError') {
        console.log('[Fetch] Request aborted (cleanup)');
        return;
      }
      console.error('Fetch error:', err);
      setHealthStatus('ERROR');
      setPollingInterval(POLLING_INTERVALS.ERROR);
      // Don't override movers on error - keep existing movers
      // setMovers(generateMoversForMarket(selectedMarket)); // REMOVED - was causing market movers to reset
      setLoading(false);
    }
  }, [selectedSymbol, chartInterval, selectedMarket]);

  // ============================================================
  // SCREENER DATA FETCHING - FIXED
  // ============================================================

  const fetchScreenerData = useCallback(async () => {
    setScreenerLoading(true);
    console.log('[Screener] Fetching data from /api/screener/universe');
    
    try {
      const response = await fetch(`${API_BASE}/api/screener/universe`);
      console.log('[Screener] Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // Backend returns: { timestamp, categories, total_stocks, source, "US Tech": [...], "India": [...], ... }
      const metaKeys = ['timestamp', 'categories', 'total_stocks', 'source', 'category_counts', 'signal_counts', 'all', 'total_count', 'demoMode', 'refresh_interval', 'message'];
      const categoryKeys = Object.keys(data).filter(k => !metaKeys.includes(k));
      
      console.log('[Screener] Found categories:', categoryKeys);
      
      // Store categories for dropdown
      if (categoryKeys.length > 0) {
        setScreenerCategories(categoryKeys);
      }
      
      const processed = {};
      
      // Process each category
      categoryKeys.forEach(category => {
        const stocks = data[category];
        if (Array.isArray(stocks) && stocks.length > 0) {
          processed[category] = stocks.map(s => ({
            symbol: s.symbol,
            name: s.name || s.symbol.split('.')[0],
            price: s.price,
            changePct: s.change_percent || s.changePct || 0,
            rsi: s.rsi,
            signal: s.signal,
            currency: s.currency || '$',
            flag: getFlagForSymbol(s.symbol), // Add flag based on symbol
            dataQuality: s.dataQuality || 'DEMO'
          }));
        }
      });
      
      if (Object.keys(processed).length === 0) {
        console.warn('[Screener] No valid categories found, using demo data');
        Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
          processed[category] = stocks.map(s => ({
            ...s,
            rsi: Math.random() * 100,
            signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
            price: 100 + Math.random() * 500,
            changePct: (Math.random() * 10 - 5).toFixed(2),
            flag: s.flag || getFlagForSymbol(s.symbol),
            dataQuality: 'DEMO'
          }));
        });
        setScreenerCategories(Object.keys(STATIC_UNIVERSE));
      } else {
        console.log('[Screener] Successfully processed', Object.keys(processed).length, 'categories with', 
          Object.values(processed).reduce((sum, arr) => sum + arr.length, 0), 'total stocks');
      }
      
      setScreenerData(processed);
      
    } catch (err) {
      console.error('[Screener] Fetch error:', err);
      console.log('[Screener] Falling back to demo data');
      
      const demo = {};
      Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
        demo[category] = stocks.map(s => ({
          ...s,
          rsi: Math.random() * 100,
          signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
          price: 100 + Math.random() * 500,
          changePct: (Math.random() * 10 - 5).toFixed(2),
          flag: s.flag || getFlagForSymbol(s.symbol),
          dataQuality: 'DEMO'
        }));
      });
      setScreenerData(demo);
      setScreenerCategories(Object.keys(STATIC_UNIVERSE));
      
    } finally {
      setScreenerLoading(false);
    }
  }, []);

  // ============================================================
  // AI CHAT
  // ============================================================

  const handleAiSubmit = async (customPrompt = null) => {
    const prompt = customPrompt || aiInput.trim();
    if (!prompt || aiLoading) return;
    
    const userMessage = { role: 'user', content: prompt };
    setAiMessages(prev => [...prev, userMessage]);
    setAiInput('');
    setAiLoading(true);
    
    try {
      const styleInfo = TRADING_STYLES[traderStyle];
      const response = await fetch(`${API_BASE}/api/genai/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: prompt,
          symbol: selectedSymbol,
          price: quote?.price,
          currency: currentMarket.currency,
          market: currentMarket.name,
          trader_type: traderStyle.toLowerCase(),
          rsi: getSignalValue(signals?.rsi),
          signal: signals?.signal || signals?.overall_signal
        })
      });
      
      const data = await response.json();
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || data.response || 'Unable to generate response',
        source: data.source || 'ai'
      };
      setAiMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('AI error:', err);
      setAiMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `AI service temporarily unavailable. Error: ${err.message}`, 
        source: 'error' 
      }]);
    } finally {
      setAiLoading(false);
    }
  };

  // ============================================================
  // WATCHLIST HANDLERS
  // ============================================================

  const addToWatchlist = useCallback(() => {
    if (selectedSymbol && !watchlist.includes(selectedSymbol)) {
      setWatchlist(prev => [...prev, selectedSymbol]);
    }
  }, [selectedSymbol, watchlist]);

  const removeFromWatchlist = useCallback((symbol) => {
    setWatchlist(prev => prev.filter(s => s !== symbol));
  }, []);

  const isInWatchlist = useMemo(() => 
    watchlist.includes(selectedSymbol),
    [watchlist, selectedSymbol]
  );

  // ============================================================
  // PORTFOLIO HANDLERS
  // ============================================================

  const isInPortfolio = useMemo(() => 
    portfolio.some(p => p.symbol === selectedSymbol),
    [portfolio, selectedSymbol]
  );

  const getPortfolioPosition = useCallback((symbol) => {
    return portfolio.find(p => p.symbol === symbol);
  }, [portfolio]);

  const addToPortfolio = useCallback(() => {
    const shares = parseFloat(portfolioShares);
    const avgPrice = parseFloat(portfolioAvgPrice);
    
    if (isNaN(shares) || shares <= 0 || isNaN(avgPrice) || avgPrice <= 0) {
      return;
    }
    
    setPortfolio(prev => {
      const existing = prev.find(p => p.symbol === selectedSymbol);
      if (existing) {
        // Update existing position (average down/up)
        const totalShares = existing.shares + shares;
        const newAvgPrice = ((existing.shares * existing.avgPrice) + (shares * avgPrice)) / totalShares;
        return prev.map(p => 
          p.symbol === selectedSymbol 
            ? { ...p, shares: totalShares, avgPrice: newAvgPrice }
            : p
        );
      } else {
        // Add new position
        return [...prev, { symbol: selectedSymbol, shares, avgPrice }];
      }
    });
    
    setPortfolioShares('');
    setPortfolioAvgPrice('');
    setShowAddToPortfolio(false);
  }, [selectedSymbol, portfolioShares, portfolioAvgPrice]);

  const removeFromPortfolio = useCallback((symbol) => {
    setPortfolio(prev => prev.filter(p => p.symbol !== symbol));
  }, []);

  const updatePortfolioPosition = useCallback((symbol, shares, avgPrice) => {
    setPortfolio(prev => prev.map(p => 
      p.symbol === symbol ? { ...p, shares, avgPrice } : p
    ));
  }, []);

  // ============================================================
  // ALERT HANDLERS
  // ============================================================

  const addAlert = useCallback(() => {
    const price = parseFloat(newAlertPrice);
    if (isNaN(price) || price <= 0) return;
    
    const newAlert = {
      symbol: selectedSymbol,
      condition: newAlertCondition,
      price: price
    };
    
    const exists = alerts.some(a => 
      a.symbol === newAlert.symbol && 
      a.condition === newAlert.condition && 
      a.price === newAlert.price
    );
    
    if (!exists) {
      setAlerts(prev => [...prev, newAlert]);
      setNewAlertPrice('');
    }
  }, [selectedSymbol, newAlertCondition, newAlertPrice, alerts]);

  const removeAlert = useCallback((index) => {
    setAlerts(prev => prev.filter((_, i) => i !== index));
  }, []);

  // ============================================================
  // EFFECTS
  // ============================================================

  // Initial market movers - v5.8.6: Fixed to properly update on market change
  useEffect(() => {
    console.log('[Movers Effect] Market changed to:', selectedMarket);
    const loadMovers = async () => {
      try {
        console.log('[Movers Effect] Fetching movers for:', selectedMarket);
        const freshMovers = await fetchTopMovers(selectedMarket);
        console.log('[Movers Effect] Got movers:', freshMovers?.map(m => m.symbol));
        if (freshMovers && freshMovers.length > 0) {
          setMovers(freshMovers);
        } else {
          console.log('[Movers Effect] No movers from API, using fallback');
          setMovers(generateDemoMovers(selectedMarket));
        }
      } catch (err) {
        console.warn('[Movers Effect] Failed, using fallback:', err.message);
        setMovers(generateDemoMovers(selectedMarket));
      }
    };
    loadMovers();
  }, [selectedMarket]);

  // Data polling - v5.8.2: AbortController for React 18 Strict Mode cleanup
  useEffect(() => {
    const controller = new AbortController();
    
    // Initial fetch with abort signal
    fetchAllData(controller.signal);
    
    // Set up polling with new controller for each interval
    intervalRef.current = setInterval(() => {
      // Don't abort the interval-based fetches, only component cleanup
      fetchAllData(null);
    }, pollingInterval);
    
    // Cleanup: abort in-flight requests and clear interval
    return () => {
      controller.abort();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchAllData, pollingInterval]);

  // v5.8.4 FIX: Clear chart immediately when interval changes
  // This provides instant feedback and prevents stale data display
  useEffect(() => {
    setHistory([]);
    setLoading(true);
    console.log('[Chart] Interval changed to:', chartInterval, '- clearing chart for fresh load');
  }, [chartInterval]);

  // ============================================================
  // FILTERED SCREENER DATA
  // ============================================================

  const filteredScreenerData = useMemo(() => {
    let data = { ...screenerData };
    
    // Filter by category
    if (screenerCategory !== 'all') {
      data = { [screenerCategory]: screenerData[screenerCategory] || [] };
    }
    
    // Filter by RSI condition
    if (screenerFilter !== 'all') {
      const filtered = {};
      Object.entries(data).forEach(([cat, stocks]) => {
        if (!Array.isArray(stocks)) return;
        
        const filteredStocks = stocks.filter(stock => {
          const rsi = stock.rsi || 50;
          if (screenerFilter === 'oversold') return rsi < 30;
          if (screenerFilter === 'overbought') return rsi > 70;
          if (screenerFilter === 'buy') {
            const sig = (stock.signal || '').toUpperCase();
            return sig === 'BUY' || sig === 'STRONG BUY' || sig === 'STRONG_BUY';
          }
          return true;
        });
        
        if (filteredStocks.length > 0) {
          filtered[cat] = filteredStocks;
        }
      });
      data = filtered;
    }
    
    return data;
  }, [screenerData, screenerCategory, screenerFilter]);

  // ============================================================
  // CHART RENDERING - FIXED TIMESTAMPS
  // ============================================================

  const renderChart = () => {
    // Enhanced validation
    if (!history || !Array.isArray(history)) {
      console.warn('[Chart] History is not an array:', typeof history);
      return (
        <div className="h-64 flex flex-col items-center justify-center text-gray-500">
          <svg className="w-12 h-12 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>Loading chart for {selectedSymbol}...</p>
          <p className="text-xs text-gray-600 mt-1">Initializing chart data...</p>
        </div>
      );
    }
    
    if (history.length === 0) {
      return (
        <div className="h-64 flex flex-col items-center justify-center text-gray-500">
          <svg className="w-12 h-12 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>Loading chart for {selectedSymbol}...</p>
          <p className="text-xs text-gray-600 mt-1">
            Waiting for historical data... ({chartInterval} interval)
          </p>
        </div>
      );
    }

    try {
      const prices = history.map(h => h.close || h.price || 0).filter(p => p > 0);
      
      if (prices.length === 0) {
        console.error('[Chart] No valid prices in history data:', history.slice(0, 2));
        return (
          <div className="h-64 flex items-center justify-center text-gray-500">
            <p>No valid price data for chart. Check console for details.</p>
          </div>
        );
      }

      const minPrice = Math.min(...prices);
      const maxPrice = Math.max(...prices);
      const range = maxPrice - minPrice || 1;
      
      const width = 700;
      const height = 200;
      const padding = 40;
      
      const points = history.map((h, i) => {
        const x = padding + (i / (history.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((h.close || h.price || 0) - minPrice) / range * (height - 2 * padding);
        return `${x},${y}`;
      }).join(' ');

      const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`;

      // Format timestamps for display - v5.8.2 FIXED with better fallback
      const firstCandle = history[0];
      const lastCandle = history[history.length - 1];
      
      // Try timestamp first (numeric ms), then date (ISO string)
      const firstTimestamp = firstCandle?.timestamp || firstCandle?.date;
      const lastTimestamp = lastCandle?.timestamp || lastCandle?.date;
      
      // Debug logging for timestamp issues
      if (!firstTimestamp || !lastTimestamp) {
        console.warn('[Chart] Missing timestamps - first:', firstCandle, 'last:', lastCandle);
      }
      
      const startLabel = formatTimestamp(firstTimestamp, chartInterval);
      const endLabel = formatTimestamp(lastTimestamp, chartInterval);
      
      // Use formatted labels or generate fallback based on interval
      const displayStartLabel = startLabel || (chartInterval.includes('m') || chartInterval.includes('h') 
        ? new Date(Date.now() - history.length * 60000).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})
        : new Date(Date.now() - history.length * 86400000).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}));
      const displayEndLabel = endLabel || 'Now';

      return (
        <svg viewBox={`0 0 ${width} ${height + 20}`} className="w-full h-64">
          <defs>
            <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3"/>
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0"/>
            </linearGradient>
          </defs>
          
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map(pct => (
            <line
              key={pct}
              x1={padding}
              y1={padding + pct * (height - 2 * padding)}
              x2={width - padding}
              y2={padding + pct * (height - 2 * padding)}
              stroke="#374151"
              strokeDasharray="4"
            />
          ))}
          
          {/* Area fill */}
          <polygon points={areaPoints} fill="url(#chartGradient)" />
          
          {/* Line */}
          <polyline
            points={points}
            fill="none"
            stroke="#06b6d4"
            strokeWidth="2"
          />
          
          {/* Price labels */}
          <text x={padding - 5} y={padding + 5} fill="#9ca3af" fontSize="10" textAnchor="end">
            {currentMarket.currency}{maxPrice.toFixed(2)}
          </text>
          <text x={padding - 5} y={height - padding + 5} fill="#9ca3af" fontSize="10" textAnchor="end">
            {currentMarket.currency}{minPrice.toFixed(2)}
          </text>
          
          {/* Time labels - v5.8.2 FIXED: Now properly formatted with fallbacks */}
          <text x={padding} y={height - padding + 20} fill="#9ca3af" fontSize="10">
            {displayStartLabel}
          </text>
          <text x={width - padding} y={height - padding + 20} fill="#9ca3af" fontSize="10" textAnchor="end">
            {displayEndLabel}
          </text>
        </svg>
      );
    } catch (error) {
      console.error('Chart rendering error:', error);
      return (
        <div className="h-64 flex items-center justify-center text-red-400">
          <p>Error rendering chart: {error.message}</p>
        </div>
      );
    }
  };

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Status Bar */}
      <div className="bg-gray-950 px-4 py-1 flex items-center justify-between text-xs text-gray-500 border-b border-gray-800">
        <span>
          {healthStatus === 'HEALTHY' ? '🟢' : healthStatus === 'DEGRADED' ? '🟡' : '🔴'}
          {healthStatus === 'HEALTHY' ? ' System healthy' : ` Status: ${healthStatus}`}
          {' • Polling: '}{pollingInterval / 1000}s
          {' • Press ? for shortcuts'}
        </span>
        <a href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">
          API Docs
        </a>
      </div>

      {/* Header */}
      <header className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-cyan-400">TraderAI Pro</h1>
            <span className="text-xs text-gray-500">v{APP_VERSION}</span>
            
            {/* Search */}
            <div className="relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    handleSymbolSelect(searchQuery.trim().toUpperCase());
                  }
                  if (e.key === 'Escape') {
                    e.target.blur();
                    setSearchQuery('');
                  }
                }}
                placeholder="Search symbols... (press /)"
                className="bg-gray-700 px-4 py-2 rounded-lg text-sm w-56 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button 
              onClick={() => { setShowScreener(true); fetchScreenerData(); }}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm font-medium"
            >
              Screener
            </button>
            <button 
              onClick={() => setShowPortfolio(true)}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium"
            >
              💰 Portfolio
            </button>
            <button 
              onClick={() => setShowAlerts(true)}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-500 rounded-lg text-sm font-medium relative"
            >
              🔔 Alerts
              {alerts.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {alerts.length}
                </span>
              )}
            </button>
            <button 
              onClick={() => setShowWhatsNext(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium"
            >
              🚀 What's Next
            </button>
            <button 
              onClick={() => setShowUserGuide(true)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium"
            >
              📖 Guide
            </button>
            <button 
              onClick={() => setShowDebug(!showDebug)}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg text-sm font-medium"
            >
              🔧
            </button>
          </div>
        </div>

        {/* Market Selector */}
        <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-2">
          {MARKETS.map(market => (
            <button
              key={market.id}
              onClick={() => handleMarketChange(market.id)}
              className={`px-3 py-1 rounded text-sm whitespace-nowrap transition-colors ${
                selectedMarket === market.id
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {market.flag} {market.name}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-56 bg-gray-800 border-r border-gray-700 p-4 space-y-6 overflow-y-auto">
          {/* Trading Style */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Trading Style</h3>
            <select
              value={traderStyle}
              onChange={(e) => setTraderStyle(e.target.value)}
              className="w-full bg-gray-700 text-white px-3 py-2 rounded text-sm"
            >
              {Object.keys(TRADING_STYLES).map(style => (
                <option key={style} value={style}>{style}</option>
              ))}
            </select>
          </div>

          {/* Investor Profile - Collapsible */}
          <div className="bg-gray-700/50 rounded-lg border border-gray-600/50 overflow-hidden">
            <button
              onClick={() => setShowInvestorProfile(!showInvestorProfile)}
              className="w-full p-3 flex items-center justify-between hover:bg-gray-700/30 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span>👤</span>
                <span className="font-medium text-sm">Investor Profile</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded border ${
                  investorProfile.riskTolerance === 'conservative' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  investorProfile.riskTolerance === 'aggressive' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                }`}>
                  {investorProfile.riskTolerance?.toUpperCase() || 'MODERATE'}
                </span>
                <span className={`transform transition-transform text-xs ${showInvestorProfile ? 'rotate-180' : ''}`}>▼</span>
              </div>
            </button>

            {showInvestorProfile && (
              <div className="p-3 border-t border-gray-600/50 space-y-3">
                {/* Name */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Display Name</label>
                  <input
                    type="text"
                    value={investorProfile.name}
                    onChange={(e) => setInvestorProfile(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Your name"
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Risk Tolerance */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Risk Tolerance</label>
                  <div className="grid grid-cols-3 gap-1">
                    {['conservative', 'moderate', 'aggressive'].map(level => (
                      <button
                        key={level}
                        onClick={() => setInvestorProfile(prev => ({ ...prev, riskTolerance: level }))}
                        className={`py-1.5 px-1 rounded text-xs font-medium transition-all border ${
                          investorProfile.riskTolerance === level
                            ? level === 'conservative' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                              level === 'aggressive' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                              'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                            : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                        }`}
                      >
                        {level === 'conservative' ? '🛡️' : level === 'aggressive' ? '🔥' : '⚖️'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Investment Horizon */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Horizon</label>
                  <select
                    value={investorProfile.investmentHorizon}
                    onChange={(e) => setInvestorProfile(prev => ({ ...prev, investmentHorizon: e.target.value }))}
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="short">Short (&lt;1 year)</option>
                    <option value="medium">Medium (1-5 years)</option>
                    <option value="long">Long (5+ years)</option>
                  </select>
                </div>

                {/* Experience */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Experience</label>
                  <select
                    value={investorProfile.experience}
                    onChange={(e) => setInvestorProfile(prev => ({ ...prev, experience: e.target.value }))}
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="beginner">🌱 Beginner</option>
                    <option value="intermediate">📈 Intermediate</option>
                    <option value="advanced">🎯 Advanced</option>
                    <option value="expert">🏆 Expert</option>
                  </select>
                </div>

                {/* Capital Range */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Capital Range</label>
                  <select
                    value={investorProfile.capitalRange}
                    onChange={(e) => setInvestorProfile(prev => ({ ...prev, capitalRange: e.target.value }))}
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="small">$1K - $10K</option>
                    <option value="medium">$10K - $100K</option>
                    <option value="large">$100K - $1M</option>
                    <option value="institutional">$1M+</option>
                  </select>
                </div>

                {/* Goals */}
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Goals</label>
                  <div className="flex flex-wrap gap-1">
                    {['income', 'growth', 'preservation', 'speculation'].map(goal => (
                      <button
                        key={goal}
                        onClick={() => {
                          const goals = investorProfile.goals || [];
                          const newGoals = goals.includes(goal)
                            ? goals.filter(g => g !== goal)
                            : [...goals, goal];
                          setInvestorProfile(prev => ({ ...prev, goals: newGoals }));
                        }}
                        className={`py-1 px-2 rounded text-xs transition-all border ${
                          (investorProfile.goals || []).includes(goal)
                            ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                            : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                        }`}
                      >
                        {goal === 'income' ? '💰' : goal === 'growth' ? '📈' : goal === 'preservation' ? '🛡️' : '🎲'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Save Button */}
                <button
                  onClick={() => {
                    localStorage.setItem('investorProfile', JSON.stringify(investorProfile));
                    setShowInvestorProfile(false);
                  }}
                  className="w-full py-2 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium rounded hover:opacity-90 transition-opacity"
                >
                  Save Profile
                </button>

                {/* Summary */}
                {investorProfile.name && (
                  <div className="p-2 bg-gray-700/30 rounded text-xs text-gray-400">
                    <span className="text-white font-medium">{investorProfile.name}</span> • {investorProfile.experience} • {investorProfile.riskTolerance} risk
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Top Movers */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Movers</h3>
            <div className="space-y-1">
              {movers.slice(0, 4).map(mover => (
                <button
                  key={mover.symbol}
                  onClick={() => handleSymbolSelect(mover.fullSymbol || mover.symbol)}
                  className="w-full flex items-center justify-between p-2 rounded text-sm hover:bg-gray-700 transition-colors"
                >
                  <span className="text-cyan-400">{mover.symbol}</span>
                  <span className={`text-sm ${parseFloat(mover.change) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {parseFloat(mover.change) >= 0 ? '+' : ''}{mover.change}%
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Watchlist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs text-gray-400 uppercase tracking-wide">Watchlist</h3>
              <button 
                onClick={() => setShowWatchlistEdit(true)}
                className="text-xs text-cyan-400 hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="space-y-1">
              {watchlist.slice(0, 5).map(symbol => (
                <button
                  key={symbol}
                  onClick={() => handleSymbolSelect(symbol)}
                  className={`w-full text-left p-2 rounded text-sm transition-colors ${
                    selectedSymbol === symbol ? 'bg-cyan-600/30 text-cyan-400' : 'hover:bg-gray-700'
                  }`}
                >
                  {symbol}
                </button>
              ))}
              {watchlist.length > 5 && (
                <button 
                  onClick={() => setShowWatchlistEdit(true)}
                  className="w-full text-center text-xs text-gray-500 hover:text-cyan-400 py-1"
                >
                  +{watchlist.length - 5} more
                </button>
              )}
            </div>
          </div>
        </aside>

        {/* Main Panel */}
        <main className="flex-1 p-4 overflow-y-auto">
          {/* Symbol Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold">{selectedSymbol}</h2>
                <span className="px-2 py-0.5 bg-cyan-600/30 text-cyan-400 text-xs rounded">DEMO</span>
                <span className="text-2xl font-bold">
                  {currentMarket.currency}{quote?.price?.toFixed(2) || '-'}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span>{currentMarket.flag} {currentMarket.name}</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-400">{currentMarket.currencyName}</span>
                {quote?.changePercent !== undefined && (
                  <span className={quote.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {quote.changePercent >= 0 ? '+' : ''}{quote.changePercent.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <button 
                onClick={addToWatchlist}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  isInWatchlist 
                    ? 'bg-yellow-600/30 text-yellow-400 border border-yellow-600' 
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {isInWatchlist ? '★ Watching' : '+ Watchlist'}
              </button>
              <button 
                onClick={() => {
                  if (isInPortfolio) {
                    removeFromPortfolio(selectedSymbol);
                  } else {
                    setPortfolioShares('');
                    setPortfolioAvgPrice(quote?.price?.toFixed(2) || '');
                    setShowAddToPortfolio(true);
                  }
                }}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  isInPortfolio 
                    ? 'bg-green-600/30 text-green-400 border border-green-600' 
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {isInPortfolio ? '💰 In Portfolio' : '+ Portfolio'}
              </button>
              <button 
                onClick={() => setShowAlerts(true)}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
              >
                Set Alert
              </button>
            </div>
          </div>

          {/* Time Interval Buttons */}
          <div className="flex gap-2 mb-4">
            {['1m', '5m', '15m', '1h', '1d', '1wk'].map((interval, idx) => (
              <button
                key={interval}
                onClick={() => setChartInterval(interval)}
                className={`px-3 py-1 rounded text-sm ${
                  chartInterval === interval
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {interval.toUpperCase()}
                <span className="ml-1 text-xs text-gray-500">({idx + 1})</span>
              </button>
            ))}
            <span className="ml-auto text-sm text-gray-400">
              Last: {lastFetchTime?.toLocaleTimeString() || '-'} • Poll: {pollingInterval / 1000}s
            </span>
          </div>

          {/* Chart - v5.8.4: Added key to force React re-render on interval/symbol change */}
          <div key={`chart-${selectedSymbol}-${chartInterval}`} className="bg-gray-800 rounded-lg p-4 mb-4">
            {renderChart()}
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-4">
            {['technicals', 'fundamentals', 'sentiment', 'news'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded text-sm font-medium capitalize ${
                  activeTab === tab ? 'bg-cyan-600 text-white' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="bg-gray-800 rounded-lg p-4">
            {activeTab === 'technicals' && (
              <div className="grid grid-cols-3 gap-4">
                {/* RSI */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">RSI (14)</h4>
                  <div className={`text-2xl font-bold ${getRsiColor(getSignalValue(signals?.rsi))}`}>
                    {getSignalValue(signals?.rsi)?.toFixed(1) || '-'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {getSignalValue(signals?.rsi) < 30 ? 'Oversold' : 
                     getSignalValue(signals?.rsi) > 70 ? 'Overbought' : 'Neutral'}
                  </p>
                </div>
                
                {/* Signal */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">Signal</h4>
                  <div className={`text-2xl font-bold ${getSignalColor(signals?.signal || signals?.overall_signal)}`}>
                    {signals?.signal || signals?.overall_signal || '-'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">AI recommendation</p>
                </div>
                
                {/* SMA 20 */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">SMA 20</h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(getSignalValue(signals?.sma_20 || signals?.sma20), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Moving average</p>
                </div>
                
                {/* EMA 12 */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">EMA 12</h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(getSignalValue(signals?.ema_12 || signals?.ema12), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Exponential MA</p>
                </div>
                
                {/* VWAP */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">VWAP</h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(getSignalValue(signals?.vwap), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Volume weighted</p>
                </div>
                
                {/* ATR */}
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">ATR</h4>
                  <div className="text-2xl font-bold text-orange-400">
                    {formatPrice(getSignalValue(signals?.atr), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Volatility</p>
                </div>
              </div>
            )}

            {activeTab === 'sentiment' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <h4 className="text-sm text-gray-400 mb-2">Reddit Sentiment</h4>
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-bold">
                        {sentiment?.sentiment?.bullish || sentiment?.bullish_percent || 50}%
                      </div>
                      <div className="flex-1">
                        <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-green-500"
                            style={{ width: `${sentiment?.sentiment?.bullish || sentiment?.bullish_percent || 50}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Bearish</span>
                          <span>Bullish</span>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-400 mt-2">
                      {sentiment?.mentions || 0} mentions • {sentiment?.sentiment?.label || 'N/A'}
                    </p>
                  </div>
                  
                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <h4 className="text-sm text-gray-400 mb-2 flex items-center gap-2">
                      Overall Sentiment
                      <span className="text-xs text-gray-500 font-normal">
                        (Neutral: 40-60%)
                      </span>
                    </h4>
                    <div className="text-xl font-bold text-cyan-400">
                      {(sentiment?.sentiment?.bullish || 50) > 60 ? '🚀 Bullish' : 
                       (sentiment?.sentiment?.bullish || 50) < 40 ? '🐻 Bearish' : '😐 Neutral'}
                    </div>
                    <p className="text-sm text-gray-400 mt-2">
                      Bullish: {sentiment?.sentiment?.bullish || 50}% • Bearish: {sentiment?.sentiment?.bearish || 30}%
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'fundamentals' && (
              <div>
                {financialsLoading ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3"></div>
                    <p>Loading financial data...</p>
                  </div>
                ) : !financials ? (
                  <div className="text-center py-8 text-gray-400">
                    <p>Financial data not available for {selectedSymbol}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Company Overview */}
                    <div className="bg-gray-700/50 rounded-lg p-4">
                      <h4 className="text-sm font-semibold text-cyan-400 mb-3">Company Overview</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-400">Sector</p>
                          <p className="text-sm text-white">{financials.sector || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-400">Industry</p>
                          <p className="text-sm text-white">{financials.industry || 'N/A'}</p>
                        </div>
                      </div>
                    </div>

                    {/* Key Metrics Grid - FIXED field names */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Market Cap</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.marketCap || 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">P/E Ratio</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.peRatio || 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Revenue</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.revenue || 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">EPS</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.eps || 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Div Yield</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.dividendYield || 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">52W High</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.fiftyTwoWeekHigh ? `${currentMarket.currency}${financials.fiftyTwoWeekHigh}` : 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">52W Low</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.fiftyTwoWeekLow ? `${currentMarket.currency}${financials.fiftyTwoWeekLow}` : 'N/A'}
                        </p>
                      </div>
                      
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">Beta</p>
                        <p className="text-lg font-semibold text-white">
                          {financials.beta || 'N/A'}
                        </p>
                      </div>
                    </div>

                    {/* Data Quality Badge */}
                    <div className="text-xs text-gray-500 text-center">
                      Data Quality: <span className={`px-2 py-0.5 rounded ${
                        financials.dataQuality === 'LIVE' ? 'bg-green-600' :
                        financials.dataQuality === 'CACHED' ? 'bg-blue-600' :
                        'bg-orange-600'
                      } text-white`}>
                        {financials.dataQuality || 'DEMO'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'news' && (
              <div className="space-y-3">
                {news.length === 0 ? (
                  <p className="text-gray-400 text-center py-4">No recent news available</p>
                ) : (
                  news.slice(0, 5).map((item, i) => (
                    <div key={i} className="p-3 bg-gray-700/50 rounded-lg">
                      <h4 className="font-medium text-sm mb-1">{item.title || item.headline}</h4>
                      <p className="text-xs text-gray-400">
                        {item.source} • {item.time_ago || item.time || item.date || 'Recent'}
                        {item.sentiment && (
                          <span className={`ml-2 ${
                            item.sentiment === 'positive' ? 'text-green-400' :
                            item.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'
                          }`}>
                            • {item.sentiment}
                          </span>
                        )}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </main>

        {/* Right Sidebar - AI Chat */}
        <aside className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-cyan-400">AI Assistant</h3>
              <span className="text-xs text-green-400">● Active</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {aiMessages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-3">🤖</div>
                <p className="text-sm mb-2">Ask me about {selectedSymbol}</p>
                <p className="text-xs text-gray-600 mb-4">
                  Style: {traderStyle} ({TRADING_STYLES[traderStyle]?.focus})
                </p>
                
                {/* AI Suggested Prompts */}
                <div className="space-y-2">
                  {AI_PROMPTS.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleAiSubmit(prompt)}
                      className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-xs text-left transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              aiMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg text-sm ${
                    msg.role === 'user'
                      ? 'bg-cyan-600/30 ml-8'
                      : 'bg-gray-700/50 mr-8'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.source && msg.role === 'assistant' && (
                    <p className="text-xs text-gray-500 mt-1">via {msg.source}</p>
                  )}
                </div>
              ))
            )}
            {aiLoading && (
              <div className="p-3 bg-gray-700/50 rounded-lg mr-8">
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
                  <span className="text-sm text-gray-400">Thinking...</span>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-gray-700">
            <div className="flex gap-2">
              <input
                type="text"
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAiSubmit()}
                placeholder="Ask about this stock..."
                className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <button
                onClick={() => handleAiSubmit()}
                disabled={aiLoading || !aiInput.trim()}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium"
              >
                Send
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 px-4 py-2 border-t border-gray-700 text-xs text-gray-500 flex justify-between">
        <span>TraderAI Pro v{APP_VERSION} • Press ? for keyboard shortcuts</span>
        <span>Data: DEMO • Watchlist: {watchlist.length} • Alerts: {alerts.length}</span>
      </footer>

      {/* Modals */}
      {showUserGuide && <UserGuideModal onClose={() => setShowUserGuide(false)} />}
      {showWhatsNext && <WhatsNextModal onClose={() => setShowWhatsNext(false)} />}
      {showKeyboardHelp && <KeyboardShortcutsModal onClose={() => setShowKeyboardHelp(false)} />}
      {showWatchlistEdit && (
        <WatchlistEditModal 
          onClose={() => setShowWatchlistEdit(false)}
          watchlist={watchlist}
          setWatchlist={setWatchlist}
          onSelectSymbol={handleSymbolSelect}
          setAlerts={setAlerts}
          currentSymbol={selectedSymbol}
        />
      )}

      {/* Screener Modal - FIXED */}
      {showScreener && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowScreener(false)}>
          <div 
            className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-xl font-bold text-cyan-400">📊 Stock Screener</h2>
              <button onClick={() => setShowScreener(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
            </div>
            
            {/* Filters */}
            <div className="p-4 border-b border-gray-700 flex gap-4 flex-wrap">
              <select
                value={screenerCategory}
                onChange={(e) => setScreenerCategory(e.target.value)}
                className="bg-gray-700 text-white px-3 py-1 rounded text-sm"
              >
                <option value="all">All Categories</option>
                {screenerCategories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              
              <div className="flex gap-2">
                {['all', 'oversold', 'overbought', 'buy'].map(filter => (
                  <button
                    key={filter}
                    onClick={() => setScreenerFilter(filter)}
                    className={`px-3 py-1 rounded text-sm ${
                      screenerFilter === filter ? 'bg-cyan-600' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                  >
                    {filter === 'all' ? 'All' : 
                     filter === 'oversold' ? 'RSI < 30' :
                     filter === 'overbought' ? 'RSI > 70' : 'Buy Signal'}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Screener Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {screenerLoading ? (
                <div className="text-center py-8 text-gray-400">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3"></div>
                  <p>Loading screener data...</p>
                </div>
              ) : Object.keys(filteredScreenerData).length === 0 ? (
                <div className="text-center py-8 text-gray-400">No stocks match your filters</div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(filteredScreenerData).map(([category, stocks]) => {
                    if (!Array.isArray(stocks) || stocks.length === 0) return null;
                    
                    return (
                      <div key={category}>
                        <h3 className="text-cyan-400 font-medium mb-2">{category}</h3>
                        <div className="grid grid-cols-4 gap-2">
                          {stocks.map(stock => {
                            const rsi = stock.rsi;
                            const rsiColor = rsi < 30 ? 'text-green-400' : rsi > 70 ? 'text-red-400' : 'text-yellow-400';
                            
                            return (
                              <button
                                key={stock.symbol}
                                onClick={() => { handleSymbolSelect(stock.symbol); setShowScreener(false); }}
                                className="p-3 bg-gray-700/50 rounded text-left hover:bg-gray-700 transition-colors border border-transparent hover:border-cyan-500/50"
                              >
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-cyan-400 font-bold text-sm">
                                    {stock.symbol.replace('.NS', '').replace('.KS', '').replace('.AS', '')}
                                  </span>
                                  <span className="text-xs">{stock.flag}</span>
                                </div>
                                <div className="text-sm text-white">{stock.currency}{stock.price?.toFixed(2) || '-'}</div>
                                <div className="flex justify-between text-xs mt-1">
                                  <span className={rsiColor}>RSI: {rsi?.toFixed(0) || '-'}</span>
                                  <span className={getSignalColor(stock.signal)}>{stock.signal}</span>
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Portfolio Modal */}
      {showPortfolio && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowPortfolio(false)}>
          <div 
            className="bg-gray-800 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-xl font-bold text-green-400">💰 Portfolio</h2>
              <button onClick={() => setShowPortfolio(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {portfolio.length === 0 ? (
                <p className="text-gray-400 text-center py-8">Your portfolio is empty. Add stocks using the "+ Portfolio" button.</p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="text-gray-400 text-sm border-b border-gray-700">
                      <th className="text-left py-2">Symbol</th>
                      <th className="text-right py-2">Shares</th>
                      <th className="text-right py-2">Avg Price</th>
                      <th className="text-right py-2">Current</th>
                      <th className="text-right py-2">Value</th>
                      <th className="text-right py-2">P&L</th>
                      <th className="text-right py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.map((pos, i) => {
                      const currentPrice = quote?.symbol === pos.symbol ? quote.price : pos.avgPrice * (1 + (Math.random() - 0.5) * 0.1);
                      const value = pos.shares * currentPrice;
                      const cost = pos.shares * pos.avgPrice;
                      const pnl = value - cost;
                      const pnlPercent = ((currentPrice / pos.avgPrice) - 1) * 100;
                      
                      return (
                        <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                          <td className="py-3">
                            <button 
                              onClick={() => { handleSymbolSelect(pos.symbol); setShowPortfolio(false); }}
                              className="text-cyan-400 font-medium hover:underline"
                            >
                              {pos.symbol}
                            </button>
                          </td>
                          <td className="py-3 text-right">{pos.shares}</td>
                          <td className="py-3 text-right">${pos.avgPrice.toFixed(2)}</td>
                          <td className="py-3 text-right">${currentPrice.toFixed(2)}</td>
                          <td className="py-3 text-right">${value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                          <td className={`py-3 text-right font-medium ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} ({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(1)}%)
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => removeFromPortfolio(pos.symbol)}
                              className="text-red-400 hover:text-red-300 text-sm px-2 py-1 hover:bg-red-900/30 rounded"
                              title="Remove from portfolio"
                            >
                              ✕ Remove
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="font-bold border-t border-gray-600">
                      <td className="py-3">Total</td>
                      <td></td>
                      <td></td>
                      <td></td>
                      <td className="py-3 text-right text-green-400">
                        ${portfolio.reduce((sum, p) => sum + p.shares * p.avgPrice, 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                      </td>
                      <td></td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              )}
            </div>
            <div className="p-4 border-t border-gray-700 flex justify-between items-center">
              <span className="text-gray-400 text-sm">{portfolio.length} position{portfolio.length !== 1 ? 's' : ''}</span>
              <button
                onClick={() => setShowPortfolio(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add to Portfolio Modal */}
      {showAddToPortfolio && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowAddToPortfolio(false)}>
          <div 
            className="bg-gray-800 rounded-lg max-w-md w-full"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-xl font-bold text-green-400">💰 Add to Portfolio</h2>
              <button onClick={() => setShowAddToPortfolio(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
            </div>
            <div className="p-4">
              <div className="mb-4">
                <p className="text-lg font-medium text-cyan-400 mb-2">{selectedSymbol}</p>
                {quote && (
                  <p className="text-gray-400">Current Price: ${quote.price?.toFixed(2)}</p>
                )}
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Number of Shares</label>
                  <input
                    type="number"
                    value={portfolioShares}
                    onChange={(e) => setPortfolioShares(e.target.value)}
                    placeholder="e.g., 10"
                    className="w-full bg-gray-700 px-3 py-2 rounded text-white"
                    min="0"
                    step="any"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Average Price per Share ($)</label>
                  <input
                    type="number"
                    value={portfolioAvgPrice}
                    onChange={(e) => setPortfolioAvgPrice(e.target.value)}
                    placeholder="e.g., 150.00"
                    className="w-full bg-gray-700 px-3 py-2 rounded text-white"
                    min="0"
                    step="any"
                  />
                </div>
                
                {portfolioShares && portfolioAvgPrice && (
                  <div className="p-3 bg-gray-700/50 rounded">
                    <p className="text-sm text-gray-400">
                      Total Cost: <span className="text-white font-medium">${(parseFloat(portfolioShares) * parseFloat(portfolioAvgPrice)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                    </p>
                  </div>
                )}
              </div>
              
              <div className="flex gap-2 mt-6">
                <button
                  onClick={() => setShowAddToPortfolio(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={addToPortfolio}
                  disabled={!portfolioShares || !portfolioAvgPrice}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium"
                >
                  {isInPortfolio ? 'Update Position' : 'Add to Portfolio'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Alerts Modal */}
      {showAlerts && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={() => setShowAlerts(false)}>
          <div 
            className="bg-gray-800 rounded-lg max-w-md w-full"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h2 className="text-xl font-bold text-orange-400">🔔 Price Alerts</h2>
              <button onClick={() => setShowAlerts(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
            </div>
            <div className="p-4">
              {/* Add new alert */}
              <div className="flex gap-2 mb-4">
                <input
                  type="number"
                  value={newAlertPrice}
                  onChange={(e) => setNewAlertPrice(e.target.value)}
                  placeholder="Price"
                  className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm"
                />
                <select
                  value={newAlertCondition}
                  onChange={(e) => setNewAlertCondition(e.target.value)}
                  className="bg-gray-700 px-3 py-2 rounded text-sm"
                >
                  <option value="above">Above</option>
                  <option value="below">Below</option>
                </select>
                <button
                  onClick={addAlert}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
                >
                  Add
                </button>
              </div>
              
              {/* Alert list */}
              <div className="space-y-2">
                {alerts.length === 0 ? (
                  <p className="text-gray-400 text-center py-4">No alerts set</p>
                ) : (
                  alerts.map((alert, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-gray-700/50 rounded">
                      <span>
                        <span className="text-cyan-400 font-medium">{alert.symbol}</span>
                        {' '}{alert.condition}{' '}
                        <span className="text-white">${alert.price}</span>
                      </span>
                      <button
                        onClick={() => removeAlert(i)}
                        className="text-red-400 hover:text-red-300"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Debug Panel */}
      {showDebug && (
        <div className="fixed bottom-0 right-0 w-96 max-h-64 bg-gray-900 border border-gray-700 rounded-tl-lg overflow-auto text-xs font-mono p-2 z-50">
          <div className="flex justify-between items-center mb-2">
            <span className="text-cyan-400">Debug Info</span>
            <button onClick={() => setShowDebug(false)} className="text-gray-400">×</button>
          </div>
          <pre className="text-gray-300 whitespace-pre-wrap">
            {JSON.stringify({
              version: APP_VERSION,
              market: selectedMarket,
              symbol: selectedSymbol,
              chartInterval,
              healthStatus,
              pollingInterval,
              historyLength: history?.length || 0,
              screenerCategories: screenerCategories.length,
              watchlistCount: watchlist.length,
              alertsCount: alerts.length,
              financials: financials ? {
                marketCap: financials.marketCap,
                peRatio: financials.peRatio,
                dataQuality: financials.dataQuality
              } : null,
              signals: signals ? {
                rsi: getSignalValue(signals.rsi),
                signal: signals.signal || signals.overall_signal,
              } : null
            }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}