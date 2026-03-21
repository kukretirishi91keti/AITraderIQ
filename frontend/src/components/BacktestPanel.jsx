/**
 * BacktestPanel - Shows signal backtesting results for a symbol.
 * Displays win rate, Sharpe ratio, signal breakdown, and strategy comparison.
 */
import React, { useState, useEffect, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function BacktestPanel({ symbol, traderStyle = 'swing' }) {
  const [data, setData] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('single'); // 'single' | 'compare'

  useEffect(() => {
    if (!symbol) return;
    fetchBacktest();
  }, [symbol, traderStyle]);

  const fetchBacktest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/backtest/run/${symbol}?trader_type=${traderStyle}`);
      const json = await res.json();
      if (json.success) setData(json);
    } catch (e) {
      console.error('Backtest fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchComparison = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/backtest/compare?symbol=${symbol}`);
      const json = await res.json();
      if (json.success) setComparison(json);
      setView('compare');
    } catch (e) {
      console.error('Comparison fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-gray-400">Running backtest for {symbol}...</div>;
  }

  if (!data) {
    return (
      <div className="p-4 text-center text-gray-500">Select a symbol to see backtest results</div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-cyan-400">Signal Backtest: {symbol}</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setView('single')}
            className={`px-3 py-1 rounded text-xs ${
              view === 'single' ? 'bg-cyan-600' : 'bg-gray-700'
            }`}
          >
            Results
          </button>
          <button
            onClick={fetchComparison}
            className={`px-3 py-1 rounded text-xs ${
              view === 'compare' ? 'bg-cyan-600' : 'bg-gray-700'
            }`}
          >
            Compare Strategies
          </button>
        </div>
      </div>

      {view === 'single' ? (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-4 gap-3">
            <MetricCard
              label="Win Rate"
              value={`${data.win_rate}%`}
              color={
                data.win_rate >= 55
                  ? 'text-green-400'
                  : data.win_rate >= 45
                    ? 'text-yellow-400'
                    : 'text-red-400'
              }
            />
            <MetricCard
              label="Avg Return"
              value={`${data.avg_return > 0 ? '+' : ''}${data.avg_return}%`}
              color={data.avg_return > 0 ? 'text-green-400' : 'text-red-400'}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={data.sharpe_ratio.toFixed(2)}
              color={
                data.sharpe_ratio > 1
                  ? 'text-green-400'
                  : data.sharpe_ratio > 0
                    ? 'text-yellow-400'
                    : 'text-red-400'
              }
            />
            <MetricCard label="Total Signals" value={data.total_signals} color="text-cyan-400" />
          </div>

          {/* Signal Breakdown */}
          <div className="bg-gray-800/50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Signal Breakdown</h4>
            <div className="space-y-2">
              {Object.entries(data.signal_breakdown || {}).map(([sig, stats]) => (
                <div key={sig} className="flex items-center justify-between text-sm">
                  <span
                    className={`font-medium ${
                      sig.includes('BUY')
                        ? 'text-green-400'
                        : sig.includes('SELL')
                          ? 'text-red-400'
                          : 'text-gray-400'
                    }`}
                  >
                    {sig}
                  </span>
                  <div className="flex gap-4 text-gray-300">
                    <span>{stats.count} signals</span>
                    <span className={stats.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}>
                      {stats.win_rate}% win
                    </span>
                    <span className={stats.avg_return > 0 ? 'text-green-400' : 'text-red-400'}>
                      {stats.avg_return > 0 ? '+' : ''}
                      {stats.avg_return}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Signals */}
          <div className="bg-gray-800/50 rounded-lg p-3">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Recent Signals</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    <th className="text-left py-1">Signal</th>
                    <th className="text-right py-1">Price</th>
                    <th className="text-right py-1">Outcome</th>
                    <th className="text-right py-1">Return</th>
                    <th className="text-center py-1">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.recent_signals || [])
                    .slice(-10)
                    .reverse()
                    .map((s, i) => (
                      <tr key={i} className="border-b border-gray-800">
                        <td
                          className={`py-1 font-medium ${
                            s.signal.includes('BUY')
                              ? 'text-green-400'
                              : s.signal.includes('SELL')
                                ? 'text-red-400'
                                : 'text-gray-400'
                          }`}
                        >
                          {s.signal}
                        </td>
                        <td className="py-1 text-right text-gray-300">${s.price}</td>
                        <td className="py-1 text-right text-gray-300">${s.outcome_price}</td>
                        <td
                          className={`py-1 text-right ${s.return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}
                        >
                          {s.return_pct > 0 ? '+' : ''}
                          {s.return_pct}%
                        </td>
                        <td className="py-1 text-center">
                          {s.correct ? (
                            <span className="text-green-400">W</span>
                          ) : (
                            <span className="text-red-400">L</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : comparison ? (
        /* Strategy Comparison */
        <div className="space-y-3">
          <div className="bg-green-900/20 border border-green-800 rounded p-3">
            <p className="text-sm text-green-400">
              Recommended: <strong>{comparison.recommended}</strong> - {comparison.reason}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {Object.entries(comparison.strategies || {}).map(([style, stats]) => (
              <div
                key={style}
                className={`bg-gray-800/50 rounded-lg p-3 border ${
                  style === comparison.recommended ? 'border-cyan-500' : 'border-gray-700'
                }`}
              >
                <h4 className="font-medium text-cyan-400 capitalize mb-2">
                  {style} {style === comparison.recommended && '(Best)'}
                </h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Win Rate</span>
                    <span className={stats.win_rate >= 55 ? 'text-green-400' : 'text-gray-300'}>
                      {stats.win_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Avg Return</span>
                    <span className={stats.avg_return > 0 ? 'text-green-400' : 'text-red-400'}>
                      {stats.avg_return}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Sharpe</span>
                    <span className="text-gray-300">{stats.sharpe_ratio}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Signals</span>
                    <span className="text-gray-300">{stats.total_signals}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default memo(BacktestPanel);

function MetricCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 text-center">
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}
