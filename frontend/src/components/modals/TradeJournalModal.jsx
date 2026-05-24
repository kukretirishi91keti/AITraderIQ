import React, { useState, useEffect } from 'react';
import { authFetch } from '../../services/auth';
import { API_BASE } from '../../constants/appConfig';

// Minimal SVG equity curve — no external chart library needed
function EquityCurve({ points }) {
  if (!points || points.length < 2) {
    return (
      <div className="flex items-center justify-center h-28 text-gray-500 text-sm">
        Not enough closed trades yet
      </div>
    );
  }

  const values = points.map((p) => p.cumulative_pnl);
  const minV = Math.min(...values, 0);
  const maxV = Math.max(...values, 0);
  const range = maxV - minV || 1;
  const W = 500;
  const H = 100;
  const pad = 4;

  const toX = (i) => pad + (i / (points.length - 1)) * (W - pad * 2);
  const toY = (v) => H - pad - ((v - minV) / range) * (H - pad * 2);

  const polyline = points.map((p, i) => `${toX(i)},${toY(p.cumulative_pnl)}`).join(' ');
  const zeroY = toY(0);
  const lastVal = values[values.length - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-28" preserveAspectRatio="none">
      {/* Zero line */}
      <line x1={pad} y1={zeroY} x2={W - pad} y2={zeroY} stroke="#374151" strokeWidth="1" />
      {/* Filled area */}
      <polygon
        points={`${toX(0)},${zeroY} ${polyline} ${toX(points.length - 1)},${zeroY}`}
        fill={lastVal >= 0 ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'}
      />
      {/* Curve line */}
      <polyline
        points={polyline}
        fill="none"
        stroke={lastVal >= 0 ? '#22c55e' : '#ef4444'}
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* Final dot */}
      <circle
        cx={toX(points.length - 1)}
        cy={toY(lastVal)}
        r="3"
        fill={lastVal >= 0 ? '#22c55e' : '#ef4444'}
      />
    </svg>
  );
}

function MetricCard({ label, value, color = 'text-white', sub }) {
  return (
    <div className="bg-gray-700/50 rounded-lg p-3">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function TradeJournalModal({ onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    authFetch(`${API_BASE}/api/paper-trade/journal`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError('Could not load journal data'))
      .finally(() => setLoading(false));
  }, []);

  const m = data?.metrics || {};
  const trades = data?.trades || [];
  const curve = data?.equity_curve || [];
  // derive currency symbol from the first closed trade (₹ for Indian, $ for US, etc.)
  const curSym = trades[0]?.currency || '$';

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex justify-between items-center flex-shrink-0">
          <h2 className="text-xl font-bold text-cyan-400">📊 Trade Journal &amp; Risk Metrics</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
            &times;
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-4 space-y-5">
          {loading && (
            <div className="text-center py-12 text-gray-400">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3" />
              <p>Loading journal…</p>
            </div>
          )}

          {error && <p className="text-center text-red-400 py-8">{error}</p>}

          {!loading && !error && (
            <>
              {/* Risk metrics grid */}
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Performance Metrics</h3>
                {m.total_closed === 0 ? (
                  <p className="text-gray-500 text-sm">
                    No closed trades yet. Close some paper trades to see your stats.
                  </p>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                    <MetricCard
                      label="Total P&L"
                      value={`${m.total_pnl >= 0 ? '+' : ''}${curSym}${m.total_pnl?.toFixed(2)}`}
                      color={m.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}
                      sub={`${m.total_closed} closed trades`}
                    />
                    <MetricCard
                      label="Win Rate"
                      value={`${m.win_rate?.toFixed(1)}%`}
                      color={m.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}
                      sub="% of winning trades"
                    />
                    <MetricCard
                      label="Avg Win"
                      value={`+${curSym}${m.avg_win?.toFixed(2)}`}
                      color="text-green-400"
                      sub="per winning trade"
                    />
                    <MetricCard
                      label="Avg Loss"
                      value={`${curSym}${m.avg_loss?.toFixed(2)}`}
                      color="text-red-400"
                      sub="per losing trade"
                    />
                    <MetricCard
                      label="Profit Factor"
                      value={m.profit_factor != null ? m.profit_factor.toFixed(2) : 'N/A'}
                      color={
                        m.profit_factor == null
                          ? 'text-gray-400'
                          : m.profit_factor >= 1.5
                            ? 'text-green-400'
                            : m.profit_factor >= 1
                              ? 'text-yellow-400'
                              : 'text-red-400'
                      }
                      sub="gross win ÷ gross loss"
                    />
                    <MetricCard
                      label="Max Drawdown"
                      value={`-${curSym}${m.max_drawdown?.toFixed(2)}`}
                      color="text-orange-400"
                      sub="largest peak→trough"
                    />
                    <MetricCard
                      label="Best Trade"
                      value={`+${curSym}${m.best_trade?.toFixed(2)}`}
                      color="text-green-400"
                    />
                    <MetricCard
                      label="Worst Trade"
                      value={`${curSym}${m.worst_trade?.toFixed(2)}`}
                      color="text-red-400"
                    />
                  </div>
                )}
              </div>

              {/* Equity curve */}
              {curve.length >= 2 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">
                    Equity Curve{' '}
                    <span className="text-gray-500 text-xs font-normal">
                      (cumulative P&amp;L over closed trades)
                    </span>
                  </h3>
                  <div className="bg-gray-700/40 rounded-lg p-3">
                    <EquityCurve points={curve} />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>First trade</span>
                      <span>
                        Final:{' '}
                        <span
                          className={
                            curve[curve.length - 1]?.cumulative_pnl >= 0
                              ? 'text-green-400'
                              : 'text-red-400'
                          }
                        >
                          {curve[curve.length - 1]?.cumulative_pnl >= 0 ? '+' : ''}
                          {curSym}
                          {curve[curve.length - 1]?.cumulative_pnl?.toFixed(2)}
                        </span>
                      </span>
                      <span>Latest trade</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Trade log table */}
              {trades.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Trade Log</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-700">
                          <th className="text-left py-2 pr-3">Symbol</th>
                          <th className="text-center py-2 pr-3">Side</th>
                          <th className="text-right py-2 pr-3">Qty</th>
                          <th className="text-right py-2 pr-3">Entry</th>
                          <th className="text-right py-2 pr-3">Exit</th>
                          <th className="text-right py-2 pr-3">P&amp;L</th>
                          <th className="text-right py-2 pr-3">%</th>
                          <th className="text-left py-2 pr-3">Strategy</th>
                          <th className="text-left py-2">Closed</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trades.map((t) => (
                          <tr
                            key={t.id}
                            className="border-b border-gray-700/40 hover:bg-gray-700/20"
                          >
                            <td className="py-2 pr-3 font-medium text-cyan-400">{t.symbol}</td>
                            <td className="py-2 pr-3 text-center">
                              <span
                                className={`px-1.5 py-0.5 rounded ${t.side === 'buy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}
                              >
                                {t.side.toUpperCase()}
                              </span>
                            </td>
                            <td className="py-2 pr-3 text-right">{t.quantity}</td>
                            <td className="py-2 pr-3 text-right">
                              {t.currency}
                              {t.entry_price?.toFixed(2)}
                            </td>
                            <td className="py-2 pr-3 text-right">
                              {t.exit_price ? `${t.currency}${t.exit_price.toFixed(2)}` : '—'}
                            </td>
                            <td
                              className={`py-2 pr-3 text-right font-medium ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}
                            >
                              {t.pnl != null
                                ? `${t.pnl >= 0 ? '+' : ''}${t.currency}${t.pnl.toFixed(2)}`
                                : '—'}
                            </td>
                            <td
                              className={`py-2 pr-3 text-right ${t.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}
                            >
                              {t.pnl_percent != null
                                ? `${t.pnl_percent >= 0 ? '+' : ''}${t.pnl_percent.toFixed(1)}%`
                                : '—'}
                            </td>
                            <td className="py-2 pr-3 text-gray-400">{t.strategy || '—'}</td>
                            <td className="py-2 text-gray-500">
                              {t.closed_at
                                ? new Date(t.closed_at).toLocaleDateString('en-GB', {
                                    day: 'numeric',
                                    month: 'short',
                                  })
                                : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="p-4 border-t border-gray-700 flex justify-end flex-shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
