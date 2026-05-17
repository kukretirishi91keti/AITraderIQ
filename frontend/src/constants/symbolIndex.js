/**
 * Symbol search index — used for autocomplete in the search bar.
 * Covers NSE Nifty 50, additional NSE stocks, and key global markets.
 * To add a new symbol: verify ticker at nseindia.com (for .NS) then append here.
 */

export const SYMBOL_INDEX = [
  // ── NSE India — Nifty 50 ────────────────────────────────────────────────────
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries', market: 'India', sector: 'Energy' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services', market: 'India', sector: 'IT' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', market: 'India', sector: 'Banking' },
  { symbol: 'INFY.NS', name: 'Infosys', market: 'India', sector: 'IT' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank', market: 'India', sector: 'Banking' },
  { symbol: 'HINDUNILVR.NS', name: 'Hindustan Unilever', market: 'India', sector: 'FMCG' },
  { symbol: 'ITC.NS', name: 'ITC', market: 'India', sector: 'FMCG' },
  { symbol: 'SBIN.NS', name: 'State Bank of India', market: 'India', sector: 'Banking' },
  { symbol: 'BHARTIARTL.NS', name: 'Bharti Airtel', market: 'India', sector: 'Telecom' },
  { symbol: 'BAJFINANCE.NS', name: 'Bajaj Finance', market: 'India', sector: 'NBFC' },
  { symbol: 'KOTAKBANK.NS', name: 'Kotak Mahindra Bank', market: 'India', sector: 'Banking' },
  { symbol: 'LT.NS', name: 'Larsen & Toubro', market: 'India', sector: 'Infra' },
  { symbol: 'ASIANPAINT.NS', name: 'Asian Paints', market: 'India', sector: 'Paints' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank', market: 'India', sector: 'Banking' },
  { symbol: 'MARUTI.NS', name: 'Maruti Suzuki', market: 'India', sector: 'Auto' },
  { symbol: 'SUNPHARMA.NS', name: 'Sun Pharmaceutical', market: 'India', sector: 'Pharma' },
  { symbol: 'TITAN.NS', name: 'Titan Company', market: 'India', sector: 'Consumer' },
  { symbol: 'WIPRO.NS', name: 'Wipro', market: 'India', sector: 'IT' },
  { symbol: 'NTPC.NS', name: 'NTPC', market: 'India', sector: 'Power' },
  { symbol: 'POWERGRID.NS', name: 'Power Grid Corporation', market: 'India', sector: 'Power' },
  { symbol: 'ULTRACEMCO.NS', name: 'UltraTech Cement', market: 'India', sector: 'Cement' },
  { symbol: 'NESTLEIND.NS', name: 'Nestle India', market: 'India', sector: 'FMCG' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors', market: 'India', sector: 'Auto' },
  { symbol: 'TECHM.NS', name: 'Tech Mahindra', market: 'India', sector: 'IT' },
  { symbol: 'HCLTECH.NS', name: 'HCL Technologies', market: 'India', sector: 'IT' },
  { symbol: 'TATASTEEL.NS', name: 'Tata Steel', market: 'India', sector: 'Metals' },
  { symbol: 'JSWSTEEL.NS', name: 'JSW Steel', market: 'India', sector: 'Metals' },
  { symbol: 'ONGC.NS', name: 'ONGC', market: 'India', sector: 'Energy' },
  { symbol: 'DRREDDY.NS', name: "Dr. Reddy's Laboratories", market: 'India', sector: 'Pharma' },
  { symbol: 'CIPLA.NS', name: 'Cipla', market: 'India', sector: 'Pharma' },
  { symbol: 'ADANIPORTS.NS', name: 'Adani Ports', market: 'India', sector: 'Logistics' },
  { symbol: 'GRASIM.NS', name: 'Grasim Industries', market: 'India', sector: 'Cement' },
  { symbol: 'HEROMOTOCO.NS', name: 'Hero MotoCorp', market: 'India', sector: 'Auto' },
  { symbol: 'EICHERMOT.NS', name: 'Eicher Motors', market: 'India', sector: 'Auto' },
  { symbol: 'BAJAJFINSV.NS', name: 'Bajaj Finserv', market: 'India', sector: 'NBFC' },
  { symbol: 'TATACONSUM.NS', name: 'Tata Consumer Products', market: 'India', sector: 'FMCG' },
  { symbol: 'APOLLOHOSP.NS', name: 'Apollo Hospitals', market: 'India', sector: 'Healthcare' },
  { symbol: 'INDUSINDBK.NS', name: 'IndusInd Bank', market: 'India', sector: 'Banking' },
  { symbol: 'BPCL.NS', name: 'BPCL', market: 'India', sector: 'Energy' },
  { symbol: 'COALINDIA.NS', name: 'Coal India', market: 'India', sector: 'Mining' },
  { symbol: 'SHRIRAMFIN.NS', name: 'Shriram Finance', market: 'India', sector: 'NBFC' },
  { symbol: 'BRITANNIA.NS', name: 'Britannia Industries', market: 'India', sector: 'FMCG' },
  { symbol: 'DIVISLAB.NS', name: "Divi's Laboratories", market: 'India', sector: 'Pharma' },
  { symbol: 'HDFCLIFE.NS', name: 'HDFC Life Insurance', market: 'India', sector: 'Insurance' },
  { symbol: 'SBILIFE.NS', name: 'SBI Life Insurance', market: 'India', sector: 'Insurance' },
  { symbol: 'M&M.NS', name: 'Mahindra & Mahindra', market: 'India', sector: 'Auto' },
  { symbol: 'HINDALCO.NS', name: 'Hindalco Industries', market: 'India', sector: 'Metals' },
  // ── NSE — Defence / PSU / Mid-cap ───────────────────────────────────────────
  { symbol: 'BEL.NS', name: 'Bharat Electronics', market: 'India', sector: 'Defence' },
  { symbol: 'HAL.NS', name: 'Hindustan Aeronautics (HAL)', market: 'India', sector: 'Defence' },
  { symbol: 'BHEL.NS', name: 'Bharat Heavy Electricals', market: 'India', sector: 'Engineering' },
  { symbol: 'IRFC.NS', name: 'Indian Railway Finance Corp', market: 'India', sector: 'Finance' },
  { symbol: 'PFC.NS', name: 'Power Finance Corporation', market: 'India', sector: 'Finance' },
  { symbol: 'RECLTD.NS', name: 'REC Limited', market: 'India', sector: 'Finance' },
  { symbol: 'IRCTC.NS', name: 'IRCTC', market: 'India', sector: 'Travel' },
  { symbol: 'PIDILITIND.NS', name: 'Pidilite Industries', market: 'India', sector: 'Chemical' },
  { symbol: 'DMART.NS', name: 'DMart (Avenue Supermarts)', market: 'India', sector: 'Retail' },
  { symbol: 'AMBUJACEM.NS', name: 'Ambuja Cements', market: 'India', sector: 'Cement' },
  { symbol: 'BANKBARODA.NS', name: 'Bank of Baroda', market: 'India', sector: 'Banking' },
  { symbol: 'CANBK.NS', name: 'Canara Bank', market: 'India', sector: 'Banking' },
  { symbol: 'PNB.NS', name: 'Punjab National Bank', market: 'India', sector: 'Banking' },
  { symbol: 'ZOMATO.NS', name: 'Zomato', market: 'India', sector: 'Tech' },
  { symbol: 'PAYTM.NS', name: 'Paytm (One97 Communications)', market: 'India', sector: 'Tech' },
  { symbol: 'NYKAA.NS', name: 'Nykaa (FSN E-Commerce)', market: 'India', sector: 'Tech' },
  { symbol: 'TRENT.NS', name: 'Trent (Westside / Zudio)', market: 'India', sector: 'Retail' },
  { symbol: 'MUTHOOTFIN.NS', name: 'Muthoot Finance', market: 'India', sector: 'Finance' },
  { symbol: 'BAJAJ-AUTO.NS', name: 'Bajaj Auto', market: 'India', sector: 'Auto' },
  { symbol: 'SOLARINDS.NS', name: 'Solar Industries India', market: 'India', sector: 'Defence' },
  { symbol: 'NHPC.NS', name: 'NHPC', market: 'India', sector: 'Power' },
  { symbol: 'SJVN.NS', name: 'SJVN', market: 'India', sector: 'Power' },
  // ── US Tech ─────────────────────────────────────────────────────────────────
  { symbol: 'AAPL', name: 'Apple', market: 'US', sector: 'Tech' },
  { symbol: 'MSFT', name: 'Microsoft', market: 'US', sector: 'Tech' },
  { symbol: 'GOOGL', name: 'Alphabet (Google)', market: 'US', sector: 'Tech' },
  { symbol: 'AMZN', name: 'Amazon', market: 'US', sector: 'Tech' },
  { symbol: 'NVDA', name: 'NVIDIA', market: 'US', sector: 'Tech' },
  { symbol: 'META', name: 'Meta Platforms', market: 'US', sector: 'Tech' },
  { symbol: 'TSLA', name: 'Tesla', market: 'US', sector: 'Auto' },
  { symbol: 'AMD', name: 'AMD', market: 'US', sector: 'Tech' },
  { symbol: 'NFLX', name: 'Netflix', market: 'US', sector: 'Tech' },
  { symbol: 'CRM', name: 'Salesforce', market: 'US', sector: 'Tech' },
  { symbol: 'ADBE', name: 'Adobe', market: 'US', sector: 'Tech' },
  // ── US Financials / ETFs ─────────────────────────────────────────────────────
  { symbol: 'JPM', name: 'JPMorgan Chase', market: 'US', sector: 'Banking' },
  { symbol: 'SPY', name: 'S&P 500 ETF (SPDR)', market: 'US', sector: 'ETF' },
  { symbol: 'QQQ', name: 'Nasdaq 100 ETF (Invesco)', market: 'US', sector: 'ETF' },
  // ── Crypto ───────────────────────────────────────────────────────────────────
  { symbol: 'BTC-USD', name: 'Bitcoin', market: 'Crypto', sector: 'Crypto' },
  { symbol: 'ETH-USD', name: 'Ethereum', market: 'Crypto', sector: 'Crypto' },
];

/**
 * Search the index by query string.
 * Matches on symbol prefix first, then name substring, then sector.
 * Returns up to `limit` results.
 */
export function searchSymbols(query, limit = 8) {
  if (!query || query.length < 1) return [];
  const q = query.toLowerCase().trim();

  const symbolPrefix = [];
  const nameMatch = [];

  for (const item of SYMBOL_INDEX) {
    const sym = item.symbol.toLowerCase();
    const name = item.name.toLowerCase();
    if (sym.startsWith(q) || sym.replace('.ns', '').startsWith(q)) {
      symbolPrefix.push(item);
    } else if (name.includes(q) || item.sector.toLowerCase().includes(q)) {
      nameMatch.push(item);
    }
    if (symbolPrefix.length + nameMatch.length >= limit * 2) break;
  }

  return [...symbolPrefix, ...nameMatch].slice(0, limit);
}
