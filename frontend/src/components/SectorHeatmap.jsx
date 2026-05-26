/**
 * SectorHeatmap — Industry sector overview for India NSE.
 * Fetches /api/screener/universe, groups stocks by sector, and displays
 * outlook cards sorted BULLISH → MIXED → BEARISH.
 *
 * Props:
 *   apiBase       {string}   Base URL for the API (e.g. "http://localhost:5000")
 *   onSymbolSelect {fn}      Called with a symbol string when top pick is clicked
 */
import React, { useState, useEffect } from 'react';
import { SYMBOL_INDEX } from '../constants/symbolIndex';

// ── Sector lookup: symbol → sector ────────────────────────────────────────────
const SECTOR_MAP = {};
SYMBOL_INDEX.forEach(({ symbol, sector }) => {
  SECTOR_MAP[symbol] = sector || 'Other';
});

const BUY_SIGNALS = new Set(['BUY', 'STRONG_BUY', 'STRONG BUY']);
const SELL_SIGNALS = new Set(['SELL', 'STRONG_SELL', 'STRONG SELL']);

function normaliseSignal(raw = '') {
  return raw.toUpperCase().replace(/\s+/g, '_');
}

function computeOutlook(bullCount, bearCount) {
  if (bullCount > bearCount + 2) return 'BULLISH';
  if (bearCount > bullCount + 2) return 'BEARISH';
  return 'MIXED';
}

function outlookWeight(o) {
  if (o === 'BULLISH') return 0;
  if (o === 'MIXED') return 1;
  return 2; // BEARISH
}

function cardClass(outlook) {
  if (outlook === 'BULLISH')
    return 'bg-green-900/30 border border-green-700/60 hover:border-green-500/80';
  if (outlook === 'BEARISH')
    return 'bg-red-900/30 border border-red-700/60 hover:border-red-500/80';
  return 'bg-gray-800/60 border border-gray-600/60 hover:border-gray-400/80';
}

function badgeClass(outlook) {
  if (outlook === 'BULLISH') return 'bg-green-700/60 text-green-300';
  if (outlook === 'BEARISH') return 'bg-red-700/60 text-red-300';
  return 'bg-gray-600/60 text-gray-300';
}

function rsiTextClass(rsi) {
  if (rsi === null || rsi === undefined) return 'text-gray-500';
  if (rsi < 30) return 'text-green-400';
  if (rsi > 70) return 'text-red-400';
  return 'text-yellow-400';
}

function rsiBarClass(rsi) {
  if (rsi === null || rsi === undefined) return 'bg-gray-600';
  if (rsi < 30) return 'bg-green-400';
  if (rsi > 70) return 'bg-red-400';
  return 'bg-yellow-400';
}

function signalTextClass(signal) {
  if (!signal) return 'text-gray-400';
  const s = normaliseSignal(signal);
  if (BUY_SIGNALS.has(s)) return 'text-green-400';
  if (SELL_SIGNALS.has(s)) return 'text-red-400';
  return 'text-yellow-400';
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 animate-pulse space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="h-4 bg-gray-700 rounded w-2/3" />
        <div className="h-4 bg-gray-700 rounded w-1/5" />
      </div>
      <div className="space-y-1.5">
        <div className="h-3 bg-gray-700 rounded w-full" />
        <div className="h-2 bg-gray-700 rounded w-full" />
      </div>
      <div className="h-3 bg-gray-700 rounded w-1/2" />
      <div className="h-px bg-gray-700 rounded" />
      <div className="h-3 bg-gray-700 rounded w-2/5" />
    </div>
  );
}

// ── Sector card ───────────────────────────────────────────────────────────────
function SectorCard({ sector, onSymbolSelect }) {
  const { name, avgRSI, bullCount, bearCount, totalStocks, outlook, topPick } = sector;

  const rsiDisplay = avgRSI !== null ? avgRSI.toFixed(1) : '--';
  const rsiPct = avgRSI !== null ? Math.min(100, Math.max(0, avgRSI)) : 0;

  return (
    <div
      className={`rounded-xl p-4 space-y-3 transition-colors duration-150 ${cardClass(outlook)}`}
    >
      {/* Name + outlook badge */}
      <div className="flex items-start justify-between gap-2">
        <span className="font-bold text-white text-sm leading-tight">{name}</span>
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${badgeClass(outlook)}`}
        >
          {outlook}
        </span>
      </div>

      {/* RSI bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-[11px] text-gray-400">
          <span>Avg RSI</span>
          <span className={rsiTextClass(avgRSI)}>{rsiDisplay}</span>
        </div>
        <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${rsiBarClass(avgRSI)}`}
            style={{ width: `${rsiPct}%` }}
          />
        </div>
        {/* RSI range markers */}
        <div className="flex justify-between text-[9px] text-gray-600 select-none">
          <span>0</span>
          <span className="text-green-700">30</span>
          <span className="text-red-700">70</span>
          <span>100</span>
        </div>
      </div>

      {/* Bull / Bear counts */}
      <div className="flex items-center gap-3 text-xs">
        <span className="text-green-400 font-medium">{bullCount} stocks &#8593;</span>
        <span className="text-red-400 font-medium">{bearCount} stocks &#8595;</span>
        <span className="text-gray-500 ml-auto">{totalStocks} total</span>
      </div>

      {/* Top pick */}
      {topPick && (
        <div className="pt-1 border-t border-gray-700/60">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">Top Pick</span>
          <div className="flex items-center gap-2 mt-0.5">
            <button
              onClick={() => onSymbolSelect && onSymbolSelect(topPick.symbol)}
              className="text-cyan-400 hover:text-cyan-300 text-xs font-semibold underline underline-offset-2 transition-colors"
            >
              {topPick.symbol.replace('.NS', '').replace('.BO', '')}
            </button>
            {topPick.signal && (
              <span className={`text-[10px] font-medium ${signalTextClass(topPick.signal)}`}>
                {topPick.signal.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function SectorHeatmap({ apiBase = '', onSymbolSelect }) {
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchedAt, setFetchedAt] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${apiBase}/api/screener/universe`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;

        const stocks = data.all || data.stocks || [];

        // Group stocks by sector
        const grouped = {};
        stocks.forEach((stock) => {
          const sector = SECTOR_MAP[stock.symbol] || 'Other';
          if (!grouped[sector]) grouped[sector] = [];
          grouped[sector].push(stock);
        });

        const sectorList = Object.entries(grouped).map(([name, list]) => {
          // Average RSI
          const rsiValues = list.map((s) => parseFloat(s.rsi)).filter((v) => !isNaN(v));
          const avgRSI =
            rsiValues.length > 0 ? rsiValues.reduce((a, b) => a + b, 0) / rsiValues.length : null;

          // Bull / bear counts
          let bullCount = 0;
          let bearCount = 0;
          list.forEach((s) => {
            const sig = normaliseSignal(s.signal || '');
            if (BUY_SIGNALS.has(sig)) bullCount++;
            else if (SELL_SIGNALS.has(sig)) bearCount++;
          });

          const outlook = computeOutlook(bullCount, bearCount);

          // Top pick: highest score
          const topPick = list.reduce((best, s) => {
            const score = parseFloat(s.score);
            if (!isNaN(score) && (best === null || score > best.score)) {
              return { symbol: s.symbol, signal: s.signal, score };
            }
            return best;
          }, null);

          return { name, avgRSI, bullCount, bearCount, totalStocks: list.length, outlook, topPick };
        });

        // Sort: BULLISH → MIXED → BEARISH
        sectorList.sort((a, b) => outlookWeight(a.outlook) - outlookWeight(b.outlook));

        setSectors(sectorList);
        setFetchedAt(new Date());
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const timestamp = fetchedAt
    ? fetchedAt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <div className="bg-gray-900 rounded-2xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-base font-bold text-white tracking-wide">
            Market Sectors <span className="text-gray-400 font-normal text-sm">— India NSE</span>
          </h2>
          {timestamp && <p className="text-xs text-gray-500 mt-0.5">Updated {timestamp}</p>}
        </div>

        {!loading && (
          <div className="flex gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
              Bullish
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-500 inline-block" />
              Mixed
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
              Bearish
            </span>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
          Failed to load sector data: {error}
        </div>
      )}

      {/* Sector grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {loading
          ? Array.from({ length: 9 }).map((_, i) => <SkeletonCard key={i} />)
          : sectors.map((sector) => (
              <SectorCard key={sector.name} sector={sector} onSymbolSelect={onSymbolSelect} />
            ))}
      </div>

      {!loading && sectors.length === 0 && !error && (
        <p className="text-gray-500 text-sm text-center py-8">No sector data available.</p>
      )}
    </div>
  );
}
