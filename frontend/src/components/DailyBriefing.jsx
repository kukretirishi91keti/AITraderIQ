/**
 * DailyBriefing.jsx
 * Collapsible banner card shown at the top of the main dashboard.
 * Fetches top scanner picks and summarises the day's market mood
 * in plain English for novice traders.
 *
 * Props:
 *   apiBase       {string}   - base URL for API calls
 *   market        {string}   - e.g. 'India', 'India_BSE', 'US'
 *   onSymbolSelect{function} - called with a symbol string when user clicks a pick
 *   isCollapsed   {boolean}  - controlled collapse state
 *   onToggle      {function} - called when the chevron/header is clicked
 */
import React, { useState, useEffect, useRef } from 'react';

// ─── IST session derivation ────────────────────────────────────────────────────

/**
 * Returns current IST session label.
 * Pre-Market : 08:00–09:15
 * Open       : 09:15–15:30
 * After-Market: 15:30–17:00
 * Closed     : everything else
 */
function getISTSession() {
  const now = new Date();
  // Convert to IST (UTC+5:30)
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
  const istMs = utcMs + 5.5 * 60 * 60_000;
  const ist = new Date(istMs);

  const h = ist.getHours();
  const m = ist.getMinutes();
  const totalMin = h * 60 + m;

  const PRE_START  = 8 * 60;          // 08:00
  const OPEN_START = 9 * 60 + 15;     // 09:15
  const OPEN_END   = 15 * 60 + 30;    // 15:30
  const AFTER_END  = 17 * 60;         // 17:00

  if (totalMin >= PRE_START && totalMin < OPEN_START) return 'PRE-MARKET';
  if (totalMin >= OPEN_START && totalMin < OPEN_END)  return 'OPEN';
  if (totalMin >= OPEN_END   && totalMin < AFTER_END) return 'AFTER-MARKET';
  return 'CLOSED';
}

/** Friendly date string: "Mon, 26 May 2026" */
function formatDate(d) {
  return d.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  });
}

// ─── Plain-English reason builder ─────────────────────────────────────────────

/**
 * Derives a one-line reason for a scanner pick based on its direction + ai_score.
 *   direction: BULLISH | LEAN_BULLISH | BEARISH | LEAN_BEARISH | NEUTRAL
 *   ai_score : 0–100
 */
function buildReason(direction, aiScore) {
  const d = (direction || '').toUpperCase();
  const score = typeof aiScore === 'number' ? aiScore : 50;

  if (d === 'BULLISH' && score > 65) return 'Strong momentum + oversold setup';
  if (d === 'BULLISH')               return 'Technical setup favoring upside';
  if (d === 'LEAN_BULLISH')          return 'Technical setup favoring upside';
  if (d === 'BEARISH' && score < 35) return 'Bearish pressure — wait for stabilization';
  if (d === 'BEARISH')               return 'Weakening — consider avoiding today';
  if (d === 'LEAN_BEARISH')          return 'Weakening — consider avoiding today';
  return 'Neutral — watch for a directional breakout';
}

// ─── Rank badge (Unicode circled numbers) ─────────────────────────────────────

const RANK_BADGES = ['①', '②', '③', '④', '⑤'];

// ─── Signal / direction helpers ───────────────────────────────────────────────

function directionBadgeClass(direction) {
  const d = (direction || '').toUpperCase();
  if (d === 'BULLISH')      return 'bg-green-700/30 text-green-300 border border-green-700/40';
  if (d === 'LEAN_BULLISH') return 'bg-green-800/30 text-green-400 border border-green-700/30';
  if (d === 'BEARISH')      return 'bg-red-700/30 text-red-300 border border-red-700/40';
  if (d === 'LEAN_BEARISH') return 'bg-red-800/30 text-red-400 border border-red-700/30';
  return 'bg-gray-600/30 text-gray-400 border border-gray-600/40';
}

function directionLabel(direction) {
  const d = (direction || '').toUpperCase();
  if (d === 'BULLISH')      return 'BULLISH';
  if (d === 'LEAN_BULLISH') return 'LEAN BULLISH';
  if (d === 'BEARISH')      return 'BEARISH';
  if (d === 'LEAN_BEARISH') return 'LEAN BEARISH';
  return 'NEUTRAL';
}

/** Mood badge for the overall market_bias from scanner */
function moodBadge(bias) {
  const b = (bias || '').toUpperCase();
  if (b.includes('BULL')) return { cls: 'bg-green-600/25 text-green-300 border border-green-600/40', label: 'BULLISH' };
  if (b.includes('BEAR')) return { cls: 'bg-red-600/25 text-red-300 border border-red-600/40',   label: 'BEARISH' };
  return { cls: 'bg-gray-600/25 text-gray-300 border border-gray-600/40', label: 'NEUTRAL' };
}

/** Session badge appearance */
function sessionBadge(session) {
  if (session === 'OPEN')         return 'text-green-400';
  if (session === 'PRE-MARKET')   return 'text-yellow-400';
  if (session === 'AFTER-MARKET') return 'text-blue-400';
  return 'text-gray-500';
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function BriefingSkeleton() {
  return (
    <div className="space-y-2 animate-pulse px-4 pb-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-10 bg-gray-700/60 rounded-lg" />
      ))}
    </div>
  );
}

// ─── Pick Row ──────────────────────────────────────────────────────────────────

function PickRow({ pick, rank, onSymbolSelect }) {
  const symbol = (pick.symbol || '').replace(/\.(NS|BO)$/i, '');
  const reason = buildReason(pick.direction, pick.ai_score);
  const badgeCls = directionBadgeClass(pick.direction);
  const label = directionLabel(pick.direction);

  return (
    <button
      onClick={() => onSymbolSelect && onSymbolSelect(pick.symbol)}
      className="w-full text-left flex items-start gap-3 p-3 rounded-lg bg-gray-800/50 hover:bg-gray-700/60 border border-gray-700/30 hover:border-cyan-700/30 transition-colors group"
    >
      {/* Rank */}
      <span className="text-lg leading-none text-gray-500 group-hover:text-cyan-400 transition-colors shrink-0 mt-0.5">
        {RANK_BADGES[rank] || `#${rank + 1}`}
      </span>

      {/* Symbol + reason */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-cyan-400 text-sm">{symbol}</span>
          <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${badgeCls}`}>
            {label}
          </span>
          <span className="text-[10px] text-gray-500 ml-auto">
            Score {Math.round(pick.ai_score ?? 0)}
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-0.5 truncate">{reason}</p>
      </div>

      {/* Chevron */}
      <span className="text-gray-600 group-hover:text-cyan-400 text-xs self-center transition-colors shrink-0">
        →
      </span>
    </button>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────

export default function DailyBriefing({
  apiBase,
  market,
  onSymbolSelect,
  isCollapsed,
  onToggle,
}) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [session]           = useState(() => getISTSession());
  const [today]             = useState(() => formatDate(new Date()));
  const abortRef            = useRef(null);

  // ── Fetch scanner data on mount ────────────────────────────────────────────
  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;

    const base = apiBase || '';
    // Always use NSE endpoint — the scanner works for both markets
    const url = `${base}/api/scanner/nifty50?top_n=5&market=NSE`;

    setLoading(true);
    setError(null);

    fetch(url, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`Server error ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (controller.signal.aborted) return;
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setError(err.message || 'Failed to load');
        setLoading(false);
      });

    return () => controller.abort();
  }, [apiBase, market]);

  // ── Derived mood ───────────────────────────────────────────────────────────
  const mood = data ? moodBadge(data.market_bias) : null;
  const picks = data?.top_picks?.slice(0, 3) ?? [];

  const sessCls  = sessionBadge(session);

  // ── Collapsed header (always visible) ─────────────────────────────────────
  return (
    <div className="bg-gray-800/70 border border-gray-700/50 rounded-xl overflow-hidden shadow-lg">

      {/* ── Header row — always visible ── */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap min-w-0">
          <span className="font-semibold text-white text-sm shrink-0">Today's Briefing</span>
          <span className="text-gray-500 text-xs hidden sm:inline">•</span>
          <span className="text-gray-400 text-xs hidden sm:inline">{today}</span>
          <span className="text-gray-500 text-xs hidden sm:inline">•</span>
          <span className={`text-xs font-medium ${sessCls} hidden sm:inline`}>
            Session: {session}
          </span>

          {/* Mood badge — visible even when collapsed */}
          {mood && !loading && (
            <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-semibold rounded-full border ${mood.cls}`}>
              {mood.label === 'BULLISH' ? '↑' : mood.label === 'BEARISH' ? '↓' : '→'}{' '}
              {mood.label}
            </span>
          )}

          {/* Loading pulse on badge */}
          {loading && (
            <span className="inline-block h-4 w-16 bg-gray-700 rounded-full animate-pulse" />
          )}
        </div>

        {/* Collapse / expand chevron */}
        <span
          className={`text-gray-400 text-xs ml-3 shrink-0 transition-transform duration-200 ${
            isCollapsed ? '' : 'rotate-180'
          }`}
          aria-hidden="true"
        >
          ▼
        </span>
      </button>

      {/* ── Expandable body ── */}
      {!isCollapsed && (
        <div className="border-t border-gray-700/40">

          {/* Mobile date / session row */}
          <div className="flex items-center gap-2 px-4 pt-3 pb-1 sm:hidden flex-wrap">
            <span className="text-gray-400 text-xs">{today}</span>
            <span className="text-gray-500 text-xs">•</span>
            <span className={`text-xs font-medium ${sessCls}`}>Session: {session}</span>
          </div>

          {/* Loading skeleton */}
          {loading && (
            <div className="px-4 pb-4 pt-3">
              <BriefingSkeleton />
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="px-4 py-4 text-sm text-gray-400">
              Market data loading...
            </div>
          )}

          {/* Picks */}
          {!loading && !error && data && (
            <div className="px-4 pb-4 pt-3 space-y-2">

              {/* Bias detail line */}
              {data.bias_label && (
                <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                  {data.bias_label}
                  {typeof data.bullish_count === 'number' && (
                    <span className="ml-2 text-gray-500">
                      ({data.bullish_count}B / {data.bearish_count}Be / {data.neutral_count}N)
                    </span>
                  )}
                </p>
              )}

              {/* Top 3 picks */}
              {picks.length > 0 ? (
                picks.map((pick, idx) => (
                  <PickRow
                    key={pick.symbol}
                    pick={pick}
                    rank={idx}
                    onSymbolSelect={onSymbolSelect}
                  />
                ))
              ) : (
                <p className="text-xs text-gray-500 py-2">No picks available right now.</p>
              )}

              {/* Footer note */}
              <p className="text-[10px] text-gray-600 pt-1 text-center">
                Scores refresh every 5 min • Not financial advice
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
