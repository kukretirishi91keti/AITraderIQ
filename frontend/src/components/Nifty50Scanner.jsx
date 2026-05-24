/**
 * Nifty 50 Morning Scanner
 * Shows top ranked NSE stocks by composite AI score.
 * Calls GET /api/scanner/nifty50
 */
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../constants/appConfig';

const DIRECTION_COLOR = {
  BULLISH: 'text-green-400',
  LEAN_BULLISH: 'text-green-300',
  BEARISH: 'text-red-400',
  LEAN_BEARISH: 'text-red-300',
  NEUTRAL: 'text-gray-400',
};

const DIRECTION_BADGE = {
  BULLISH: { label: 'Bullish', cls: 'bg-green-700/30 text-green-300' },
  LEAN_BULLISH: { label: 'Lean Bullish', cls: 'bg-green-800/30 text-green-400' },
  BEARISH: { label: 'Bearish', cls: 'bg-red-700/30 text-red-300' },
  LEAN_BEARISH: { label: 'Lean Bearish', cls: 'bg-red-800/30 text-red-400' },
  NEUTRAL: { label: 'Neutral', cls: 'bg-gray-600/30 text-gray-400' },
};

const SESSION_LABEL = {
  OPEN: { label: 'Open', cls: 'text-green-400' },
  PRE_OPEN: { label: 'Pre-open', cls: 'text-yellow-400' },
  PRE_MARKET: { label: 'Pre-market', cls: 'text-gray-400' },
  CLOSED: { label: 'Market Closed', cls: 'text-gray-500' },
  CLOSED_WEEKEND: { label: 'Weekend', cls: 'text-gray-500' },
};

export default function Nifty50Scanner({ traderStyle = 'Day', onSymbolSelect, market = 'India' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [style, setStyle] = useState(traderStyle);

  const isBSE = market === 'India_BSE';
  const exchange = isBSE ? 'BSE' : 'NSE';
  const scannerTitle = isBSE ? 'Sensex 30 Scanner' : 'Nifty 50 Scanner';

  const load = useCallback(
    async (ts) => {
      setLoading(true);
      setError(null);
      try {
        const exchangeParam = isBSE ? 'BSE' : 'NSE';
        const res = await fetch(
          `${API_BASE}/api/scanner/nifty50?trader_type=${ts}&top_n=30&market=${exchangeParam}`
        );
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        setData(await res.json());
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [isBSE]
  );

  useEffect(() => {
    load(style);
  }, [style, load, market]);

  const session = data ? SESSION_LABEL[data.session] || SESSION_LABEL.CLOSED : null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-white">{scannerTitle}</h3>
          {session && (
            <span className={`text-xs ${session.cls}`}>
              {exchange} {session.label}
            </span>
          )}
        </div>
        <select
          value={style}
          onChange={(e) => setStyle(e.target.value)}
          className="bg-gray-700 text-sm rounded px-2 py-1 text-white border-0"
        >
          <option value="Day">Intraday</option>
          <option value="Swing">Swing</option>
          <option value="Position">Positional</option>
          <option value="Scalper">Scalper</option>
        </select>
      </div>

      {/* Market Bias */}
      {data && (
        <div
          className={`p-3 rounded-lg text-sm ${
            data.market_bias === 'BULLISH'
              ? 'bg-green-900/30 border border-green-700/40'
              : data.market_bias === 'BEARISH'
                ? 'bg-red-900/30 border border-red-700/40'
                : 'bg-gray-700/40 border border-gray-600/40'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`font-semibold ${
                data.market_bias === 'BULLISH'
                  ? 'text-green-400'
                  : data.market_bias === 'BEARISH'
                    ? 'text-red-400'
                    : 'text-gray-300'
              }`}
            >
              {data.market_bias === 'BULLISH' ? '↑' : data.market_bias === 'BEARISH' ? '↓' : '→'}{' '}
              {data.market_bias}
            </span>
            <span className="text-gray-400 text-xs">
              {data.bullish_count}B / {data.bearish_count}Be / {data.neutral_count}N
            </span>
          </div>
          <p className="text-gray-300 text-xs">{data.bias_label}</p>
        </div>
      )}

      {loading && (
        <div className="text-center py-6 text-gray-400 text-sm">
          Scanning {isBSE ? 'Sensex 30' : 'Nifty 50'}...
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 text-red-400 p-3 rounded text-sm">
          Scan error: {error}
          <button onClick={() => load(style)} className="ml-2 underline">
            Retry
          </button>
        </div>
      )}

      {/* Rankings */}
      {data && !loading && (
        <div className="space-y-1">
          {data.top_picks.map((pick) => {
            const badge = DIRECTION_BADGE[pick.direction] || DIRECTION_BADGE.NEUTRAL;
            const barW = `${Math.round(pick.ai_score)}%`;
            const symbol = pick.symbol.replace('.NS', '').replace('.BO', '');
            return (
              <button
                key={pick.symbol}
                onClick={() => onSymbolSelect && onSymbolSelect(pick.symbol)}
                className="w-full text-left p-2.5 rounded-lg bg-gray-700/50 hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-5">#{pick.rank}</span>
                    <span className="font-medium text-cyan-400">{symbol}</span>
                    <span className={`px-1.5 py-0.5 text-xs rounded ${badge.cls}`}>
                      {badge.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span title="RSI">RSI {Math.round(pick.rsi)}</span>
                    <span title="Win rate">W {Math.round(pick.win_rate)}%</span>
                    <span className="font-bold text-white">AI {pick.ai_score}</span>
                  </div>
                </div>
                {/* Score bar */}
                <div className="h-1 bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      pick.ai_score >= 65
                        ? 'bg-green-500'
                        : pick.ai_score >= 45
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                    }`}
                    style={{ width: barW }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      )}

      {data && (
        <button
          onClick={() => load(style)}
          className="w-full text-xs text-gray-500 hover:text-gray-300 py-1"
        >
          Refresh scan
        </button>
      )}
    </div>
  );
}
