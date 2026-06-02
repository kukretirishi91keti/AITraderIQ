/**
 * TradeSetupPanel — Complete trade setup card shown below the chart.
 *
 * Calculates entry, ATR-based stop, targets, risk:reward, and
 * position size purely from props — no API calls.
 *
 * Props:
 *   symbol          {string}  Ticker symbol, e.g. "RELIANCE.NS"
 *   quote           {object}  Must have .price
 *   signals         {object}  Must have .atr; also uses .signal
 *   investorProfile {object}  Optional; used for capital range
 *   currency        {string}  Currency prefix (default "₹")
 *   onPaperTrade    {fn}      Called with trade details object
 */
import React from 'react';
import { getSignalValue } from '../utils/formatters';
import GlossaryTooltip from './GlossaryTooltip';

const BUY_SIGNALS = new Set(['BUY', 'STRONG_BUY', 'STRONG BUY']);
const SELL_SIGNALS = new Set(['SELL', 'STRONG_SELL', 'STRONG SELL']);

function capitalFromProfile(profile) {
  if (!profile) return 50000;
  const range = (profile.capitalRange || profile.capital_range || '').toLowerCase();
  if (range === 'small') return 25000;
  if (range === 'medium') return 100000;
  if (range === 'large') return 500000;
  if (range === 'institutional') return 2000000;
  return 50000;
}

function rrColorClass(rr) {
  if (rr >= 2) return 'text-green-400';
  if (rr >= 1) return 'text-yellow-400';
  return 'text-red-400';
}

function rrLabel(rr) {
  if (rr >= 2) return 'Good setup';
  if (rr >= 1) return 'Marginal';
  return 'Poor setup';
}

// ── Sub-component: labelled data point ───────────────────────────────────────
function DataPoint({ label, value, sub, valueClass = 'text-white' }) {
  return (
    <div className="bg-gray-700/40 rounded-lg p-2.5 space-y-0.5">
      <p className="text-[10px] text-gray-400 uppercase tracking-wider select-none">{label}</p>
      <p className={`text-sm font-semibold ${valueClass}`}>{value}</p>
      {sub && <p className="text-[10px] text-gray-500">{sub}</p>}
    </div>
  );
}

// ── Skeleton shown while signals are loading ──────────────────────────────────
function TradeSetupSkeleton() {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-2xl p-4 space-y-4 animate-pulse">
      <div className="flex justify-between items-center">
        <div className="h-4 bg-gray-700 rounded w-32" />
        <div className="h-5 bg-gray-700 rounded-full w-20" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="bg-gray-700/40 rounded-lg p-2.5 space-y-1.5">
            <div className="h-2.5 bg-gray-600 rounded w-16" />
            <div className="h-5 bg-gray-600 rounded w-24" />
          </div>
        ))}
      </div>
      <div className="h-20 bg-gray-700/40 rounded-xl" />
    </div>
  );
}

// ── Fallback shown when price is known but ATR is unavailable ─────────────────
function TradeSetupNoATR({ symbol, entry, currency, signal }) {
  return (
    <div className="bg-gray-800 border border-gray-700/60 rounded-2xl p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-white">Trade Setup</h3>
          <span className="text-xs text-gray-400 font-mono">{symbol}</span>
        </div>
        {signal && (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-700 text-gray-300 border border-gray-600">
            {signal}
          </span>
        )}
      </div>
      <div className="bg-gray-700/40 rounded-lg p-2.5 inline-block">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Entry</p>
        <p className="text-sm font-semibold text-white">
          {currency}
          {entry.toFixed(2)}
        </p>
      </div>
      <p className="text-xs text-gray-500">
        Stop/target estimates need more price history (
        <GlossaryTooltip term="ATR">ATR</GlossaryTooltip> unavailable).
      </p>
    </div>
  );
}

// ATR multipliers per trader style
const STYLE_ATR = {
  Scalper: { stop: 0.5, t1: 1.0, t2: 1.5 },
  Day: { stop: 1.0, t1: 1.5, t2: 2.5 },
  Swing: { stop: 1.5, t1: 2.0, t2: 3.0 },
  Position: { stop: 2.0, t1: 3.0, t2: 5.0 },
};

// ── Main component ────────────────────────────────────────────────────────────
export default function TradeSetupPanel({
  symbol,
  quote,
  signals,
  investorProfile,
  currency = '₹',
  onPaperTrade,
  loading = false,
  traderStyle = 'Swing',
}) {
  // Show skeleton while data is in-flight
  if (loading) return <TradeSetupSkeleton />;

  const entry = quote?.price ? parseFloat(quote.price) : null;
  const atrRaw = signals?.atr !== undefined ? getSignalValue(signals.atr) : null;
  const atr = atrRaw !== null ? parseFloat(atrRaw) : null;

  // Need at least a price to show anything
  if (!entry || isNaN(entry)) return null;

  // Have price but no usable ATR — show partial card
  if (!atr || isNaN(atr) || atr <= 0) {
    return (
      <TradeSetupNoATR symbol={symbol} entry={entry} currency={currency} signal={signals?.signal} />
    );
  }

  // Normalise signal
  const signalRaw = (signals?.signal || '').toUpperCase().replace(/\s+/g, '_');
  const isSell = SELL_SIGNALS.has(signalRaw);
  const isBuy = BUY_SIGNALS.has(signalRaw);

  // ATR multipliers driven by trading style
  const mults = STYLE_ATR[traderStyle] || STYLE_ATR.Swing;

  // Price levels
  const stop = isSell ? entry + mults.stop * atr : entry - mults.stop * atr;
  const target1 = isSell ? entry - mults.t1 * atr : entry + mults.t1 * atr;
  const target2 = isSell ? entry - mults.t2 * atr : entry + mults.t2 * atr;

  const riskPerShare = Math.abs(entry - stop);
  const rewardPerShare = Math.abs(target1 - entry);
  const rr = riskPerShare > 0 ? rewardPerShare / riskPerShare : 0;

  // Position sizing (2% capital risk rule)
  const capital = capitalFromProfile(investorProfile);
  const riskAmount = capital * 0.02;
  const suggestedShares = Math.max(1, Math.floor(riskAmount / riskPerShare));
  const positionSize = suggestedShares * entry;

  // Direction badge
  let dirLabel = 'NEUTRAL';
  let dirClass = 'bg-gray-700 text-gray-300 border border-gray-600';
  if (isBuy) {
    dirLabel = 'BUY Setup';
    dirClass = 'bg-green-700/50 text-green-300 border border-green-600/60';
  } else if (isSell) {
    dirLabel = 'SELL Setup';
    dirClass = 'bg-red-700/50 text-red-300 border border-red-600/60';
  }

  function handlePaperTrade() {
    if (!onPaperTrade) return;
    onPaperTrade({
      symbol,
      side: isSell ? 'sell' : 'buy',
      shares: suggestedShares,
      entry,
      stop,
      target: target1,
    });
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-2xl p-4 space-y-4">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-white">Trade Setup</h3>
          <span className="text-xs text-gray-400 font-mono">{symbol}</span>
        </div>
        <span className={`text-xs font-bold px-3 py-1 rounded-full ${dirClass}`}>{dirLabel}</span>
      </div>

      {/* ── Main layout: data grid + position box ── */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* 4-point grid */}
        <div className="grid grid-cols-2 gap-3 flex-1">
          <DataPoint
            label="Entry"
            value={`${currency}${entry.toFixed(2)}`}
            valueClass="text-white"
          />
          <DataPoint
            label={<GlossaryTooltip term="Stop Loss">Stop Loss</GlossaryTooltip>}
            value={`${currency}${stop.toFixed(2)}`}
            sub="ATR-based"
            valueClass="text-red-400"
          />
          <DataPoint
            label={<GlossaryTooltip term="Take Profit">Target</GlossaryTooltip>}
            value={`${currency}${target1.toFixed(2)}`}
            sub={`/ ${currency}${target2.toFixed(2)} aggr.`}
            valueClass="text-green-400"
          />
          <DataPoint
            label={<GlossaryTooltip term="Risk:Reward">Risk : Reward</GlossaryTooltip>}
            value={`${rr.toFixed(1)} : 1`}
            sub={rrLabel(rr)}
            valueClass={rrColorClass(rr)}
          />
        </div>

        {/* Position sizing box */}
        <div className="bg-gray-700/50 border border-gray-600/60 rounded-xl p-3 space-y-2 lg:min-w-[210px]">
          <p className="text-[11px] text-gray-400 uppercase tracking-wider">
            Position Size (2% risk rule)
          </p>
          <p className="text-white text-sm font-semibold">
            <span className="text-cyan-400 text-lg">{suggestedShares}</span> shares
          </p>
          <p className="text-gray-300 text-xs">
            = {currency}
            {positionSize.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-gray-500 text-[10px]">
            Capital: {currency}
            {capital.toLocaleString('en-IN')} · 2% = {currency}
            {riskAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>

          <button
            onClick={handlePaperTrade}
            className="w-full mt-1 bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors"
          >
            Paper Trade This Setup
          </button>
        </div>
      </div>

      {/* ── Disclaimer ── */}
      <p className="text-[10px] text-gray-500 leading-relaxed">
        [{traderStyle}] Stop = {mults.stop}&times;ATR {isSell ? 'above' : 'below'} entry &middot;
        Target = {mults.t1}–{mults.t2}&times;ATR {isSell ? 'below' : 'above'} &middot; 2% capital
        risk rule
      </p>
    </div>
  );
}
