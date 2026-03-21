/**
 * Market movers fetching and demo data generation.
 * Extracted from App.jsx.
 */

import { API_BASE } from '../constants/appConfig';

export const fetchTopMovers = async (marketId) => {
  try {
    const url = `${API_BASE}/api/v4/top-movers/${marketId}?limit=6`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    let allMovers = [];

    if (data.movers && Array.isArray(data.movers)) {
      allMovers = data.movers.map((m) => ({
        symbol: m.symbol?.includes('.') ? m.symbol.split('.')[0] : m.symbol,
        fullSymbol: m.fullSymbol || m.symbol,
        change: m.changePercent ?? m.change,
        price: m.price,
      }));
    } else if (data.gainers || data.losers) {
      allMovers = [
        ...(data.gainers || []).map((g) => ({
          symbol: g.ticker || g.symbol,
          fullSymbol: g.ticker || g.symbol,
          change: g.changePercent,
          price: g.price,
        })),
        ...(data.losers || []).map((l) => ({
          symbol: l.ticker || l.symbol,
          fullSymbol: l.ticker || l.symbol,
          change: l.changePercent,
          price: l.price,
        })),
      ];
    }

    allMovers.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
    return allMovers.slice(0, 6);
  } catch (error) {
    return generateDemoMovers(marketId);
  }
};

const DEMO_STOCKS = {
  US: ['AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT', 'GOOGL'],
  India: ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS'],
  UK: ['HSBA.L', 'BP.L', 'SHEL.L', 'AZN.L'],
  Germany: ['SAP.DE', 'SIE.DE', 'ALV.DE', 'BMW.DE'],
  France: ['OR.PA', 'MC.PA', 'SAN.PA', 'TTE.PA'],
  Japan: ['7203.T', '6758.T', '9984.T', '7974.T'],
  China: ['9988.HK', '0700.HK', '3690.HK', '9618.HK'],
  HongKong: ['0005.HK', '0011.HK', '0388.HK', '1299.HK'],
  Taiwan: ['2330.TW', '2317.TW', '2454.TW', '2308.TW'],
  Australia: ['BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX'],
  Canada: ['RY.TO', 'TD.TO', 'ENB.TO', 'SHOP.TO'],
  Brazil: ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'ABEV3.SA'],
  Korea: ['005930.KS', '000660.KS', '005380.KS', '035420.KS'],
  Singapore: ['D05.SI', 'O39.SI', 'U11.SI', 'Z74.SI'],
  Switzerland: ['NESN.SW', 'ROG.SW', 'NOVN.SW', 'UBSG.SW'],
  Netherlands: ['ASML.AS', 'INGA.AS', 'PHIA.AS', 'ABN.AS'],
  Spain: ['SAN.MC', 'BBVA.MC', 'ITX.MC', 'IBE.MC'],
  Italy: ['ENI.MI', 'ENEL.MI', 'ISP.MI', 'UCG.MI'],
  Crypto: ['BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD'],
  ETF: ['SPY', 'QQQ', 'IWM', 'GLD'],
  Forex: ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X'],
  Commodities: ['GC=F', 'CL=F', 'SI=F', 'NG=F'],
};

const hashCode = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
};

export const generateDemoMovers = (marketId) => {
  const symbols = DEMO_STOCKS[marketId] || DEMO_STOCKS['US'];

  return symbols.map((s) => {
    const hash = hashCode(s + new Date().toDateString());
    const change = ((hash % 1000) / 100 - 5).toFixed(2);
    return {
      symbol: s.includes('.')
        ? s.split('.')[0]
        : s.includes('-')
          ? s.split('-')[0]
          : s.includes('=')
            ? s.replace('=X', '')
            : s,
      fullSymbol: s,
      change: parseFloat(change),
    };
  });
};
