import { useState, useEffect, useCallback, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function PaperTradingPanel({ symbol, price, currency = '$', onSymbolSelect }) {
  const [view, setView] = useState('trade');       // trade | positions | history | stats
  const [positions, setPositions] = useState([]);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Order form
  const [side, setSide] = useState('BUY');
  const [quantity, setQuantity] = useState(10);
  const [orderPrice, setOrderPrice] = useState(price || 0);
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');

  const token = localStorage.getItem('auth_token');

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };

  // Update order price when symbol price changes
  useEffect(() => {
    if (price) setOrderPrice(price);
  }, [price]);

  const fetchPositions = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/paper/positions`, { headers });
      const json = await res.json();
      if (json.success) {
        setPositions(json.positions);
        setBalance(json.balance);
      }
    } catch (e) {
      console.error('Fetch positions error:', e);
    }
  }, [token]);

  const fetchHistory = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/paper/history?limit=20`, { headers });
      const json = await res.json();
      if (json.success) setHistory(json.trades);
    } catch (e) {
      console.error('Fetch history error:', e);
    }
  }, [token]);

  const fetchStats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/paper/stats`, { headers });
      const json = await res.json();
      if (json.success) {
        setStats(json.stats);
        setBalance(json.balance);
      }
    } catch (e) {
      console.error('Fetch stats error:', e);
    }
  }, [token]);

  useEffect(() => {
    fetchPositions();
  }, [fetchPositions]);

  useEffect(() => {
    if (view === 'history') fetchHistory();
    if (view === 'stats') fetchStats();
  }, [view, fetchHistory, fetchStats]);

  const placeOrder = async () => {
    if (!token) { setError('Login required to paper trade'); return; }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${API_BASE}/api/paper/order`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          symbol: symbol || 'AAPL',
          side,
          quantity: parseFloat(quantity),
          price: parseFloat(orderPrice),
          currency,
          stop_loss: stopLoss ? parseFloat(stopLoss) : null,
          take_profit: takeProfit ? parseFloat(takeProfit) : null,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Order failed');
      setSuccess(`${side} ${quantity} ${symbol} @ ${currency}${orderPrice}`);
      setBalance(json.balance);
      fetchPositions();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const closePosition = async (tradeId) => {
    if (!price) { setError('No current price available'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/paper/order/${tradeId}/close`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ price: parseFloat(price) }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Close failed');
      const pnlStr = json.pnl >= 0 ? `+${currency}${json.pnl}` : `-${currency}${Math.abs(json.pnl)}`;
      setSuccess(`Closed ${json.symbol}: ${pnlStr} (${json.pnl_pct}%)`);
      setBalance(json.balance);
      fetchPositions();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const resetAccount = async () => {
    if (!confirm('Reset paper trading account? All trades will be deleted.')) return;
    try {
      const res = await fetch(`${API_BASE}/api/paper/reset`, { method: 'POST', headers });
      const json = await res.json();
      if (json.success) {
        setSuccess('Account reset to $100,000');
        setBalance(json.balance);
        setPositions([]);
        setHistory([]);
        setStats(null);
      }
    } catch (e) {
      setError(e.message);
    }
  };

  if (!token) {
    return (
      <div className="bg-gray-800/60 rounded-lg p-6 text-center">
        <span className="text-3xl block mb-3">&#36;</span>
        <p className="text-gray-300 text-sm">Login to start paper trading with $100K virtual cash</p>
      </div>
    );
  }

  const orderCost = (parseFloat(quantity) || 0) * (parseFloat(orderPrice) || 0);

  return (
    <div className="bg-gray-800/60 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-cyan-400">$</span>
          Paper Trading
        </h3>
        <div className="flex gap-1">
          {['trade', 'positions', 'history', 'stats'].map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-3 py-1 text-xs rounded ${view === v ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600'}`}>
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Balance Bar */}
      {balance && (
        <div className="grid grid-cols-4 gap-2 mb-4 text-center">
          <div className="bg-gray-900/50 rounded p-2">
            <div className="text-[10px] text-gray-500">Cash</div>
            <div className="text-sm font-mono text-white">${balance.available_cash?.toLocaleString()}</div>
          </div>
          <div className="bg-gray-900/50 rounded p-2">
            <div className="text-[10px] text-gray-500">In Positions</div>
            <div className="text-sm font-mono text-yellow-400">${balance.locked_in_positions?.toLocaleString()}</div>
          </div>
          <div className="bg-gray-900/50 rounded p-2">
            <div className="text-[10px] text-gray-500">Realized P&L</div>
            <div className={`text-sm font-mono ${balance.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {balance.realized_pnl >= 0 ? '+' : ''}{currency}{balance.realized_pnl?.toLocaleString()}
            </div>
          </div>
          <div className="bg-gray-900/50 rounded p-2">
            <div className="text-[10px] text-gray-500">Total Equity</div>
            <div className="text-sm font-mono text-cyan-400">${balance.total_equity?.toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Messages */}
      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-xs p-2 rounded mb-3">{error}</div>}
      {success && <div className="bg-green-900/30 border border-green-700 text-green-300 text-xs p-2 rounded mb-3">{success}</div>}

      {/* Trade View */}
      {view === 'trade' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            {['BUY', 'SELL', 'SHORT'].map(s => (
              <button key={s} onClick={() => setSide(s)}
                className={`flex-1 py-2 text-sm font-semibold rounded ${
                  side === s
                    ? s === 'BUY' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}>
                {s}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-gray-500">Symbol</label>
              <div className="bg-gray-900 rounded px-3 py-2 text-white text-sm font-mono">{symbol || 'AAPL'}</div>
            </div>
            <div>
              <label className="text-[10px] text-gray-500">Quantity</label>
              <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-white text-sm" min="1" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-[10px] text-gray-500">Price</label>
              <input type="number" value={orderPrice} onChange={e => setOrderPrice(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-white text-sm" step="0.01" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500">Stop Loss</label>
              <input type="number" value={stopLoss} onChange={e => setStopLoss(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-gray-400 text-sm" step="0.01" placeholder="Optional" />
            </div>
            <div>
              <label className="text-[10px] text-gray-500">Take Profit</label>
              <input type="number" value={takeProfit} onChange={e => setTakeProfit(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-gray-400 text-sm" step="0.01" placeholder="Optional" />
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-gray-500 px-1">
            <span>Order Cost: {currency}{orderCost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            <span>Available: {currency}{balance?.available_cash?.toLocaleString() || '100,000'}</span>
          </div>

          <button onClick={placeOrder} disabled={loading || !orderPrice || !quantity}
            className={`w-full py-3 rounded font-semibold text-sm ${
              side === 'BUY'
                ? 'bg-green-600 hover:bg-green-500 text-white'
                : 'bg-red-600 hover:bg-red-500 text-white'
            } disabled:opacity-50`}>
            {loading ? 'Placing...' : `${side} ${quantity} ${symbol || 'AAPL'}`}
          </button>
        </div>
      )}

      {/* Positions View */}
      {view === 'positions' && (
        <div className="space-y-2">
          {positions.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No open positions</p>
          ) : positions.map(p => (
            <div key={p.id} className="bg-gray-900/50 rounded p-3 flex items-center justify-between">
              <div>
                <span className="text-white font-semibold cursor-pointer hover:text-cyan-400"
                  onClick={() => onSymbolSelect?.(p.symbol)}>
                  {p.symbol}
                </span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded ${p.side === 'BUY' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                  {p.side}
                </span>
                <div className="text-xs text-gray-500 mt-1">
                  {p.quantity} shares @ {p.currency}{p.entry_price?.toFixed(2)}
                  {p.stop_loss && <span className="ml-2">SL: {p.currency}{p.stop_loss}</span>}
                  {p.take_profit && <span className="ml-2">TP: {p.currency}{p.take_profit}</span>}
                </div>
              </div>
              <button onClick={() => closePosition(p.id)} disabled={loading}
                className="bg-gray-700 hover:bg-red-600 text-gray-300 hover:text-white px-3 py-1 rounded text-xs transition-colors">
                Close
              </button>
            </div>
          ))}
          <div className="text-center pt-2">
            <button onClick={fetchPositions} className="text-xs text-gray-500 hover:text-cyan-400">
              &#8635; Refresh
            </button>
          </div>
        </div>
      )}

      {/* History View */}
      {view === 'history' && (
        <div className="space-y-2">
          {history.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No closed trades yet</p>
          ) : history.map(t => (
            <div key={t.id} className="bg-gray-900/50 rounded p-3 flex items-center justify-between">
              <div>
                <span className="text-white font-semibold">{t.symbol}</span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded ${t.side === 'BUY' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                  {t.side}
                </span>
                <div className="text-xs text-gray-500 mt-1">
                  {t.quantity} @ {t.currency}{t.entry_price?.toFixed(2)} → {t.currency}{t.exit_price?.toFixed(2)}
                </div>
              </div>
              <div className="text-right">
                <div className={`font-mono text-sm ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {t.pnl >= 0 ? '+' : ''}{t.currency}{t.pnl?.toFixed(2)}
                </div>
                <div className={`text-xs ${t.pnl_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct?.toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stats View */}
      {view === 'stats' && (
        <div className="space-y-3">
          {!stats || stats.total_trades === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">Complete some trades to see stats</p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-2">
                <StatCard label="Win Rate" value={`${stats.win_rate}%`}
                  color={stats.win_rate >= 55 ? 'text-green-400' : stats.win_rate >= 45 ? 'text-yellow-400' : 'text-red-400'} />
                <StatCard label="Total Trades" value={stats.total_trades} color="text-white" />
                <StatCard label="Profit Factor" value={stats.profit_factor}
                  color={stats.profit_factor >= 1.5 ? 'text-green-400' : stats.profit_factor >= 1 ? 'text-yellow-400' : 'text-red-400'} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <StatCard label="Total P&L" value={`${stats.total_pnl >= 0 ? '+' : ''}$${stats.total_pnl?.toLocaleString()}`}
                  color={stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'} />
                <StatCard label="Best Trade" value={`+$${stats.best_trade?.toLocaleString()}`} color="text-green-400" />
                <StatCard label="Worst Trade" value={`$${stats.worst_trade?.toLocaleString()}`} color="text-red-400" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <StatCard label="Wins / Losses" value={`${stats.wins}W / ${stats.losses}L`} color="text-white" />
                <StatCard label="Avg P&L" value={`${stats.avg_pnl >= 0 ? '+' : ''}$${stats.avg_pnl}`}
                  color={stats.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400'} />
              </div>
            </>
          )}
          <div className="text-center pt-2">
            <button onClick={resetAccount} className="text-xs text-red-500 hover:text-red-400">
              Reset Account to $100K
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-900/50 rounded p-2 text-center">
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className={`text-sm font-mono font-semibold ${color}`}>{value}</div>
    </div>
  );
}

export default memo(PaperTradingPanel);
