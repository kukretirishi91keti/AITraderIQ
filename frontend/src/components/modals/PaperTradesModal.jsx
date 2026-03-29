import React, { useState, useEffect } from 'react';
import { authFetch } from '../../services/auth';
import { API_BASE } from '../../constants/appConfig';

const PaperTradesModal = ({ onClose }) => {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [levels, setLevels] = useState({}); // { [tradeId]: { stopLoss: '', takeProfit: '' } }
  const [saving, setSaving] = useState({});

  const fetchTrades = async () => {
    try {
      const res = await authFetch(`${API_BASE}/api/paper-trade?status=open`);
      const data = await res.json();
      setTrades(data.trades || []);
      // Initialise levels state from existing values
      const init = {};
      (data.trades || []).forEach((t) => {
        init[t.id] = {
          stopLoss: t.stop_loss_price != null ? String(t.stop_loss_price) : '',
          takeProfit: t.take_profit_price != null ? String(t.take_profit_price) : '',
        };
      });
      setLevels(init);
    } catch {
      setTrades([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  const handleSaveLevels = async (tradeId) => {
    setSaving((prev) => ({ ...prev, [tradeId]: true }));
    try {
      const { stopLoss, takeProfit } = levels[tradeId] || {};
      await authFetch(`${API_BASE}/api/paper-trade/${tradeId}/levels`, {
        method: 'PUT',
        body: JSON.stringify({
          stop_loss_price: stopLoss ? parseFloat(stopLoss) : null,
          take_profit_price: takeProfit ? parseFloat(takeProfit) : null,
        }),
      });
    } catch {
      // fail silently — levels remain in local state
    } finally {
      setSaving((prev) => ({ ...prev, [tradeId]: false }));
    }
  };

  const handleCloseTrade = async (tradeId) => {
    try {
      await authFetch(`${API_BASE}/api/paper-trade/${tradeId}/close`, { method: 'POST' });
      await fetchTrades();
    } catch {
      // ignore
    }
  };

  const updateLevel = (tradeId, field, value) => {
    setLevels((prev) => ({
      ...prev,
      [tradeId]: { ...(prev[tradeId] || {}), [field]: value },
    }));
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-cyan-400">📋 Open Paper Trades</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
            &times;
          </button>
        </div>

        <div className="p-4 overflow-y-auto flex-1">
          {loading ? (
            <p className="text-gray-400 text-center py-8">Loading trades…</p>
          ) : trades.length === 0 ? (
            <p className="text-gray-400 text-center py-8">
              No open paper trades. Use Strategy Intelligence to place a trade.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-center py-2">Side</th>
                  <th className="text-right py-2">Qty</th>
                  <th className="text-right py-2">Entry</th>
                  <th className="text-left py-2 pl-3">Stop-Loss</th>
                  <th className="text-left py-2">Take-Profit</th>
                  <th className="text-left py-2">Strategy</th>
                  <th className="text-center py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => {
                  const lvl = levels[trade.id] || {};
                  return (
                    <tr key={trade.id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                      <td className="py-3 font-medium text-cyan-400">{trade.symbol}</td>
                      <td className="py-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            trade.side === 'buy'
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}
                        >
                          {trade.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3 text-right">{trade.quantity}</td>
                      <td className="py-3 text-right">
                        {trade.currency}
                        {trade.entry_price?.toFixed(2)}
                      </td>
                      <td className="py-3 pl-3">
                        <input
                          type="number"
                          step="0.01"
                          placeholder="e.g. 148.00"
                          value={lvl.stopLoss || ''}
                          onChange={(e) => updateLevel(trade.id, 'stopLoss', e.target.value)}
                          className="w-24 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-red-300 placeholder-gray-500 focus:outline-none focus:border-red-500"
                        />
                      </td>
                      <td className="py-3">
                        <input
                          type="number"
                          step="0.01"
                          placeholder="e.g. 165.00"
                          value={lvl.takeProfit || ''}
                          onChange={(e) => updateLevel(trade.id, 'takeProfit', e.target.value)}
                          className="w-24 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs text-green-300 placeholder-gray-500 focus:outline-none focus:border-green-500"
                        />
                      </td>
                      <td className="py-3 text-gray-400 text-xs">{trade.strategy || '—'}</td>
                      <td className="py-3 text-center">
                        <div className="flex gap-1 justify-center">
                          <button
                            onClick={() => handleSaveLevels(trade.id)}
                            disabled={saving[trade.id]}
                            className="px-2 py-1 text-xs bg-cyan-700/40 hover:bg-cyan-700/60 text-cyan-300 rounded disabled:opacity-50"
                          >
                            {saving[trade.id] ? '…' : 'Set'}
                          </button>
                          <button
                            onClick={() => handleCloseTrade(trade.id)}
                            className="px-2 py-1 text-xs bg-red-700/40 hover:bg-red-700/60 text-red-300 rounded"
                          >
                            Close
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="p-4 border-t border-gray-700 flex justify-between items-center text-xs text-gray-500">
          <span>
            Stop-loss &amp; take-profit levels are monitored automatically every 60 seconds.
          </span>
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
};

export default PaperTradesModal;
