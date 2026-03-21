/**
 * AIScanner - AI-ranked market opportunities.
 * Shows symbols ranked by composite AI score (technicals + backtest + sentiment).
 */
import React, { useState, useEffect, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function AIScanner({ traderStyle = 'swing', onSymbolSelect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all'); // all, BULLISH, BEARISH

  useEffect(() => {
    fetchRankings();
  }, [traderStyle]);

  const fetchRankings = async () => {
    setLoading(true);
    try {
      const url = `${API_BASE}/api/scanner/rank?trader_type=${traderStyle}`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.success) setData(json);
    } catch (e) {
      console.error('Scanner fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const filtered = (data?.rankings || []).filter((r) => {
    if (filter === 'all') return true;
    return r.direction.includes(filter);
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-cyan-400">AI Scanner</h3>
        <div className="flex gap-1">
          {['all', 'BULLISH', 'BEARISH'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded text-[10px] ${
                filter === f ? 'bg-cyan-600' : 'bg-gray-700 text-gray-400'
              }`}
            >
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-4 text-sm">Scanning markets...</div>
      ) : (
        <div className="space-y-1">
          {filtered.map((r) => (
            <div
              key={r.symbol}
              className="flex items-center justify-between p-2 bg-gray-800/50 rounded hover:bg-gray-700/50 cursor-pointer"
              onClick={() => onSymbolSelect?.(r.symbol)}
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-gray-500 w-5">#{r.rank}</span>
                <div>
                  <span className="font-medium text-cyan-400 text-sm">{r.symbol}</span>
                  <div className="flex gap-2 mt-0.5">
                    <span
                      className={`text-[10px] font-medium ${
                        r.signal.includes('BUY')
                          ? 'text-green-400'
                          : r.signal.includes('SELL')
                            ? 'text-red-400'
                            : 'text-gray-400'
                      }`}
                    >
                      {r.signal}
                    </span>
                    <span className="text-[10px] text-gray-500">RSI {r.rsi?.toFixed(0)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-xs text-gray-400">
                    {r.win_rate}% win | Sent: {r.sentiment_score > 0 ? '+' : ''}
                    {r.sentiment_score}
                  </div>
                </div>
                <div className="w-10 text-center">
                  <div
                    className={`text-lg font-bold ${
                      r.ai_score >= 65
                        ? 'text-green-400'
                        : r.ai_score >= 45
                          ? 'text-yellow-400'
                          : 'text-red-400'
                    }`}
                  >
                    {r.ai_score}
                  </div>
                  <div className="text-[8px] text-gray-500">SCORE</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data?.top_pick && (
        <div className="bg-cyan-900/20 border border-cyan-800 rounded p-2 text-center">
          <span className="text-xs text-cyan-400">
            Top Pick: <strong>{data.top_pick.symbol}</strong> (Score: {data.top_pick.ai_score})
          </span>
        </div>
      )}
    </div>
  );
}

export default memo(AIScanner);
