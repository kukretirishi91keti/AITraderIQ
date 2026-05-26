/**
 * PortfolioIntelligence.jsx
 * Full intelligence dashboard modal for novice traders.
 * Replaces the simple portfolio table with per-holding signal cards,
 * sector allocation, and a "Next Course of Action" summary.
 */
import React, { useState, useEffect, useRef } from 'react';
import { SYMBOL_INDEX } from '../constants/symbolIndex';

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Build a lookup map from SYMBOL_INDEX for O(1) access */
const SYMBOL_MAP = SYMBOL_INDEX.reduce((acc, item) => {
  acc[item.symbol] = item;
  return acc;
}, {});

/** Determine display currency from symbol suffix */
function getCurrency(symbol, fallback) {
  if (fallback) return fallback;
  if (/\.(NS|BO)$/i.test(symbol)) return '₹';
  return '$';
}

/** Format a number as a currency string */
function fmt(value, currency) {
  const abs = Math.abs(value);
  if (abs >= 1_00_000) {
    // Indian lakh notation for rupee amounts
    if (currency === '₹') {
      return currency + (abs / 1_00_000).toFixed(2) + 'L';
    }
    return currency + abs.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  return currency + abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Derive plain-English recommendation from signal + P&L% + RSI */
function getRecommendation(signal, pnlPct, rsi) {
  const s = (signal || '').toUpperCase();
  if (s === 'STRONG_BUY') return { text: 'Add More ▲▲', color: 'text-green-400' };
  if (s === 'BUY' && pnlPct > 0) return { text: 'Hold / Add ▲', color: 'text-green-400' };
  if (s === 'BUY' && pnlPct <= 0) return { text: 'Hold — signal improving →', color: 'text-yellow-400' };
  if ((s === 'HOLD' || s === 'NEUTRAL') && pnlPct > 5) return { text: 'Book partial profits ↘', color: 'text-yellow-400' };
  if (s === 'HOLD' || s === 'NEUTRAL') return { text: 'Wait for signal →', color: 'text-gray-400' };
  if (s === 'SELL' && pnlPct > 0) return { text: 'Book profits ▼', color: 'text-orange-400' };
  if (s === 'SELL' && pnlPct <= 0) return { text: 'Cut loss ▼', color: 'text-red-400' };
  if (s === 'STRONG_SELL') return { text: 'Exit now ✕', color: 'text-red-400' };
  // RSI fallbacks
  if (rsi !== null && rsi < 30) return { text: 'Oversold — consider adding ▲', color: 'text-green-400' };
  if (rsi !== null && rsi > 70) return { text: 'Overbought — trim position ↘', color: 'text-yellow-400' };
  return { text: 'Monitor position →', color: 'text-gray-400' };
}

/** One-line forward-looking projection based on trend/ATR/signal */
function getProjection(signal, atr, currentPrice, rsi) {
  const s = (signal || '').toUpperCase();
  const atrPct = atr && currentPrice ? ((atr / currentPrice) * 100).toFixed(1) : null;
  if (s === 'STRONG_BUY' || s === 'BUY') {
    return atrPct
      ? `Uptrend — +${atrPct}% possible in 5 days`
      : 'Upward momentum — watch for continuation';
  }
  if (s === 'STRONG_SELL' || s === 'SELL') {
    const support = currentPrice ? `₹${(currentPrice * 0.97).toFixed(1)}` : 'near lows';
    return `Bearish pressure — watch ${support} support`;
  }
  if (rsi !== null && rsi < 35) return 'Near oversold zone — potential bounce likely';
  if (rsi !== null && rsi > 65) return 'Near overbought zone — momentum may slow';
  return 'Consolidating — wait for directional breakout';
}

/** Signal badge colour */
function signalBadgeClass(signal) {
  const s = (signal || '').toUpperCase();
  if (s.includes('STRONG_BUY')) return 'bg-green-600/30 text-green-300 border border-green-600/40';
  if (s.includes('BUY')) return 'bg-green-800/30 text-green-400 border border-green-700/40';
  if (s.includes('STRONG_SELL')) return 'bg-red-600/30 text-red-300 border border-red-600/40';
  if (s.includes('SELL')) return 'bg-red-800/30 text-red-400 border border-red-700/40';
  return 'bg-gray-600/30 text-gray-400 border border-gray-600/40';
}

/** Sector colours — rotate through a palette */
const SECTOR_COLORS = [
  'bg-cyan-500', 'bg-purple-500', 'bg-yellow-500', 'bg-orange-500',
  'bg-pink-500', 'bg-teal-500', 'bg-blue-500', 'bg-lime-500',
  'bg-rose-500', 'bg-emerald-500',
];

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="bg-gray-800 rounded-xl p-4 animate-pulse space-y-3">
      <div className="flex items-center gap-3">
        <div className="h-5 w-24 bg-gray-700 rounded" />
        <div className="h-4 w-16 bg-gray-700 rounded" />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div className="h-10 bg-gray-700 rounded" />
        <div className="h-10 bg-gray-700 rounded" />
        <div className="h-10 bg-gray-700 rounded" />
      </div>
      <div className="h-4 w-3/4 bg-gray-700 rounded" />
      <div className="h-4 w-1/2 bg-gray-700 rounded" />
    </div>
  );
}

// ─── Holding Card ─────────────────────────────────────────────────────────────

function HoldingCard({ pos, liveData, onSymbolSelect, onClose }) {
  const meta = SYMBOL_MAP[pos.symbol] || {};
  const currency = getCurrency(pos.symbol, pos.currency);
  const quote = liveData?.quote;
  const signals = liveData?.signals;

  const currentPrice = quote?.price ?? pos.avgPrice;
  const cost = pos.shares * pos.avgPrice;
  const value = pos.shares * currentPrice;
  const pnl = value - cost;
  const pnlPct = cost > 0 ? ((value - cost) / cost) * 100 : 0;

  const signal = signals?.signal || quote?.signal || 'HOLD';
  const rsi = signals?.rsi ?? quote?.rsi ?? null;
  const atr = signals?.atr ?? null;

  const rec = getRecommendation(signal, pnlPct, rsi);
  const projection = getProjection(signal, atr, currentPrice, rsi);

  return (
    <div className="bg-gray-800 border border-gray-700/60 rounded-xl p-4 space-y-3 hover:border-cyan-700/40 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-cyan-400 text-base">{pos.symbol.replace(/\.(NS|BO)$/i, '')}</span>
            {meta.name && (
              <span className="text-gray-400 text-xs truncate max-w-[160px]">{meta.name}</span>
            )}
          </div>
          {meta.sector && (
            <span className="inline-block mt-1 px-2 py-0.5 text-[10px] rounded-full bg-gray-700/60 text-gray-300 border border-gray-600/40">
              {meta.sector}
            </span>
          )}
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold shrink-0 ${signalBadgeClass(signal)}`}>
          {signal.replace('_', ' ')}
        </span>
      </div>

      {/* Price / value grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div className="bg-gray-900/50 rounded-lg p-2">
          <div className="text-gray-500 text-[10px] uppercase tracking-wide mb-0.5">Invested</div>
          <div className="text-white font-medium">
            {pos.shares} × {fmt(pos.avgPrice, currency)}
          </div>
          <div className="text-gray-400 text-xs">{fmt(cost, currency)}</div>
        </div>
        <div className="bg-gray-900/50 rounded-lg p-2">
          <div className="text-gray-500 text-[10px] uppercase tracking-wide mb-0.5">Current</div>
          <div className="text-white font-medium">{fmt(currentPrice, currency)}</div>
          <div className="text-gray-400 text-xs">{fmt(value, currency)}</div>
        </div>
        <div className="bg-gray-900/50 rounded-lg p-2">
          <div className="text-gray-500 text-[10px] uppercase tracking-wide mb-0.5">P&amp;L</div>
          <div className={`font-bold text-sm ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {pnl >= 0 ? '+' : '-'}{fmt(Math.abs(pnl), currency)}
          </div>
          <div className={`text-xs ${pnlPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
          </div>
        </div>
        {rsi !== null && (
          <div className="bg-gray-900/50 rounded-lg p-2">
            <div className="text-gray-500 text-[10px] uppercase tracking-wide mb-0.5">RSI</div>
            <div className={`font-bold text-sm ${rsi < 30 ? 'text-green-400' : rsi > 70 ? 'text-yellow-400' : 'text-white'}`}>
              {rsi.toFixed(1)}
            </div>
            <div className="text-gray-500 text-xs">
              {rsi < 30 ? 'Oversold' : rsi > 70 ? 'Overbought' : 'Normal'}
            </div>
          </div>
        )}
      </div>

      {/* Recommendation */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-500 text-xs shrink-0">Action:</span>
        <span className={`font-semibold ${rec.color}`}>{rec.text}</span>
      </div>

      {/* Projection */}
      <div className="flex items-start gap-2 text-xs text-gray-400">
        <span className="shrink-0 text-gray-500">Where it&apos;s headed:</span>
        <span>{projection}</span>
      </div>

      {/* View Chart */}
      <button
        onClick={() => { onSymbolSelect(pos.symbol); onClose(); }}
        className="w-full mt-1 py-1.5 text-xs text-cyan-400 border border-cyan-700/40 rounded-lg hover:bg-cyan-900/20 transition-colors"
      >
        View Chart →
      </button>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PortfolioIntelligence({
  onClose,
  portfolio,
  apiBase,
  investorProfile,
  onSymbolSelect,
  isLoggedIn,
}) {
  const [liveData, setLiveData] = useState({}); // { [symbol]: { quote, signals } }
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState(15); // target return %
  const abortRef = useRef(null);

  // ── Fetch quote + signals for every holding concurrently ───────────────────
  useEffect(() => {
    if (!portfolio?.length) { setLoading(false); return; }

    const controller = new AbortController();
    abortRef.current = controller;
    const { signal } = controller;

    const base = apiBase || '';

    const fetches = portfolio.map((pos) => {
      const quotePromise = fetch(`${base}/api/v4/quote/${encodeURIComponent(pos.symbol)}`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
      const signalsPromise = fetch(`${base}/api/v4/signals/${encodeURIComponent(pos.symbol)}`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null);
      return Promise.allSettled([quotePromise, signalsPromise]).then(([q, s]) => ({
        symbol: pos.symbol,
        quote: q.status === 'fulfilled' ? q.value : null,
        signals: s.status === 'fulfilled' ? s.value : null,
      }));
    });

    Promise.allSettled(fetches).then((results) => {
      if (controller.signal.aborted) return;
      const map = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled' && r.value) {
          map[r.value.symbol] = { quote: r.value.quote, signals: r.value.signals };
        }
      });
      setLiveData(map);
      setLoading(false);
    });

    return () => controller.abort();
  }, [portfolio, apiBase]);

  // ── Derived portfolio totals ───────────────────────────────────────────────
  const totals = React.useMemo(() => {
    let invested = 0;
    let currentValue = 0;
    portfolio.forEach((pos) => {
      const live = liveData[pos.symbol];
      const price = live?.quote?.price ?? pos.avgPrice;
      invested += pos.shares * pos.avgPrice;
      currentValue += pos.shares * price;
    });
    const pnl = currentValue - invested;
    const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;
    return { invested, currentValue, pnl, pnlPct };
  }, [portfolio, liveData]);

  const progressToTarget = Math.min(100, (totals.pnlPct / target) * 100);

  // ── Sector allocation ──────────────────────────────────────────────────────
  const sectorAlloc = React.useMemo(() => {
    const map = {};
    portfolio.forEach((pos) => {
      const live = liveData[pos.symbol];
      const price = live?.quote?.price ?? pos.avgPrice;
      const value = pos.shares * price;
      const sector = SYMBOL_MAP[pos.symbol]?.sector || 'Other';
      map[sector] = (map[sector] || 0) + value;
    });
    const total = Object.values(map).reduce((s, v) => s + v, 0) || 1;
    return Object.entries(map)
      .map(([sector, value]) => ({ sector, value, pct: (value / total) * 100 }))
      .sort((a, b) => b.value - a.value);
  }, [portfolio, liveData]);

  // ── Signal counts for "Next Course of Action" ──────────────────────────────
  const actionSummary = React.useMemo(() => {
    let buyCount = 0;
    let sellCount = 0;
    let bestOpportunity = null;
    let biggestRisk = null;
    let bestScore = -Infinity;
    let worstPnl = Infinity;

    portfolio.forEach((pos) => {
      const live = liveData[pos.symbol];
      const signal = (live?.signals?.signal || live?.quote?.signal || 'HOLD').toUpperCase();
      const price = live?.quote?.price ?? pos.avgPrice;
      const pnlPct = pos.avgPrice > 0 ? ((price - pos.avgPrice) / pos.avgPrice) * 100 : 0;
      const score = live?.signals?.score ?? live?.quote?.score ?? 50;

      if (signal.includes('BUY')) buyCount++;
      if (signal.includes('SELL')) sellCount++;

      if (score > bestScore) {
        bestScore = score;
        bestOpportunity = { symbol: pos.symbol, signal, score };
      }
      if (signal.includes('SELL') && pnlPct < worstPnl) {
        worstPnl = pnlPct;
        biggestRisk = { symbol: pos.symbol, signal, pnlPct };
      }
    });

    const total = portfolio.length || 1;
    let mood = '';
    if (sellCount / total > 0.5) {
      mood = 'Consider reducing exposure — more holdings showing sell signals.';
    } else if (buyCount / total > 0.5) {
      mood = 'Portfolio has positive momentum — majority of holdings signal bullish.';
    } else {
      mood = 'Mixed signals — portfolio is in a wait-and-watch phase.';
    }

    return { mood, bestOpportunity, biggestRisk, buyCount, sellCount };
  }, [portfolio, liveData]);

  // ── Default currency for totals ────────────────────────────────────────────
  const defaultCurrency = portfolio.length > 0 ? getCurrency(portfolio[0].symbol, portfolio[0].currency) : '₹';

  return (
    <div
      className="fixed inset-0 bg-black/85 flex items-start justify-center z-50 p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 rounded-2xl max-w-4xl w-full my-4 overflow-hidden shadow-2xl border border-gray-700/50"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Modal Header ── */}
        <div className="px-6 py-4 border-b border-gray-700/60 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Portfolio Intelligence</h2>
            <p className="text-xs text-gray-500 mt-0.5">{portfolio.length} position{portfolio.length !== 1 ? 's' : ''} — live signals</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700/50 text-xl transition-colors"
          >
            &times;
          </button>
        </div>

        <div className="p-5 space-y-6">

          {/* ── Summary Bar ── */}
          <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Total Invested</div>
                <div className="text-white font-bold text-lg">{fmt(totals.invested, defaultCurrency)}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Current Value</div>
                <div className="text-white font-bold text-lg">{fmt(totals.currentValue, defaultCurrency)}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Total P&amp;L</div>
                <div className={`font-bold text-lg ${totals.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {totals.pnl >= 0 ? '+' : '-'}{fmt(Math.abs(totals.pnl), defaultCurrency)}
                  <span className="text-sm ml-1">({totals.pnlPct >= 0 ? '+' : ''}{totals.pnlPct.toFixed(2)}%)</span>
                </div>
              </div>
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide mb-1">Target Return</div>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={target}
                    onChange={(e) => setTarget(Number(e.target.value) || 15)}
                    className="w-16 bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600/50 focus:border-cyan-500 focus:outline-none"
                  />
                  <span className="text-gray-400 text-sm">%</span>
                </div>
              </div>
            </div>
            {/* Progress to target */}
            <div>
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>Progress to {target}% target</span>
                <span>{progressToTarget.toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    progressToTarget >= 100
                      ? 'bg-green-400'
                      : progressToTarget >= 50
                      ? 'bg-cyan-400'
                      : 'bg-yellow-500'
                  }`}
                  style={{ width: `${Math.max(2, progressToTarget)}%` }}
                />
              </div>
            </div>
          </div>

          {/* ── Empty state ── */}
          {portfolio.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg mb-2">Portfolio is empty</p>
              <p className="text-sm">Add stocks using the &quot;+ Portfolio&quot; button.</p>
            </div>
          )}

          {/* ── Holdings cards ── */}
          {portfolio.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Holdings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {loading
                  ? portfolio.map((_, i) => <CardSkeleton key={i} />)
                  : portfolio.map((pos) => (
                      <HoldingCard
                        key={pos.symbol}
                        pos={pos}
                        liveData={liveData[pos.symbol]}
                        onSymbolSelect={onSymbolSelect}
                        onClose={onClose}
                      />
                    ))}
              </div>
            </div>
          )}

          {/* ── Sector Allocation ── */}
          {!loading && sectorAlloc.length > 0 && (
            <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Sector Allocation</h3>
              <div className="space-y-2">
                {sectorAlloc.map(({ sector, value, pct }, idx) => (
                  <div key={sector} className="flex items-center gap-3">
                    <span className="text-gray-400 text-xs w-20 shrink-0 truncate">{sector}</span>
                    <div className="flex-1 h-2.5 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${SECTOR_COLORS[idx % SECTOR_COLORS.length]}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-10 text-right shrink-0">{pct.toFixed(1)}%</span>
                    <span className="text-xs text-gray-500 w-20 text-right shrink-0 hidden sm:block">
                      {fmt(value, defaultCurrency)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Next Course of Action ── */}
          {!loading && portfolio.length > 0 && (
            <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-semibold text-gray-300">Next Course of Action</h3>

              {/* Mood line */}
              <p className="text-sm text-gray-300">{actionSummary.mood}</p>

              {/* Signal tally */}
              <div className="flex gap-4 text-xs">
                <span className="text-green-400 font-medium">{actionSummary.buyCount} BUY signal{actionSummary.buyCount !== 1 ? 's' : ''}</span>
                <span className="text-gray-500">/</span>
                <span className="text-red-400 font-medium">{actionSummary.sellCount} SELL signal{actionSummary.sellCount !== 1 ? 's' : ''}</span>
                <span className="text-gray-500">/</span>
                <span className="text-gray-400">{portfolio.length - actionSummary.buyCount - actionSummary.sellCount} HOLD</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                {/* Best opportunity */}
                {actionSummary.bestOpportunity && (
                  <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-3">
                    <div className="text-green-400 text-xs font-semibold uppercase tracking-wide mb-1">Best Opportunity</div>
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-bold text-sm">
                        {actionSummary.bestOpportunity.symbol.replace(/\.(NS|BO)$/i, '')}
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${signalBadgeClass(actionSummary.bestOpportunity.signal)}`}>
                        {actionSummary.bestOpportunity.signal.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-gray-400 text-xs mt-1">
                      Score: {Math.round(actionSummary.bestOpportunity.score)}
                    </div>
                  </div>
                )}

                {/* Biggest risk */}
                {actionSummary.biggestRisk && (
                  <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-3">
                    <div className="text-red-400 text-xs font-semibold uppercase tracking-wide mb-1">Biggest Risk</div>
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-bold text-sm">
                        {actionSummary.biggestRisk.symbol.replace(/\.(NS|BO)$/i, '')}
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${signalBadgeClass(actionSummary.biggestRisk.signal)}`}>
                        {actionSummary.biggestRisk.signal.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-red-400 text-xs mt-1">
                      P&amp;L: {actionSummary.biggestRisk.pnlPct.toFixed(2)}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>

        {/* ── Footer ── */}
        <div className="px-6 py-4 border-t border-gray-700/60 flex items-center justify-between">
          <button
            onClick={onClose}
            className="text-cyan-400 text-sm hover:text-cyan-300 hover:underline"
          >
            + Add to Portfolio
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
