import { useState, useEffect, useCallback, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const OPERATOR_LABELS = { '<': '<', '<=': '\u2264', '>': '>', '>=': '\u2265', '==': '=', '!=': '\u2260' };

function StrategyBuilder({ onSymbolSelect }) {
  const [view, setView] = useState('list');           // list | create | scan-results
  const [strategies, setStrategies] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [universes, setUniverses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [scanResults, setScanResults] = useState(null);
  const [maxAllowed, setMaxAllowed] = useState(2);
  const [expandedId, setExpandedId] = useState(null);

  // Create form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [action, setAction] = useState('BUY');
  const [universe, setUniverse] = useState('US_TECH');
  const [conditions, setConditions] = useState([
    { indicator: 'rsi', operator: '<', value: '30' },
  ]);

  const token = localStorage.getItem('auth_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };

  const fetchStrategies = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/strategy/list`, { headers });
      const json = await res.json();
      if (json.success) {
        setStrategies(json.strategies);
        setMaxAllowed(json.max_allowed);
      }
    } catch (e) {
      console.error('Fetch strategies error:', e);
    }
  }, [token]);

  const fetchIndicators = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/strategy/indicators`);
      const json = await res.json();
      setIndicators(json.indicators || []);
      setUniverses(json.universes || []);
    } catch (e) {
      console.error('Fetch indicators error:', e);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
    fetchIndicators();
  }, [fetchStrategies, fetchIndicators]);

  const addCondition = () => {
    if (conditions.length >= 10) return;
    setConditions([...conditions, { indicator: 'rsi', operator: '<', value: '30' }]);
  };

  const removeCondition = (idx) => {
    setConditions(conditions.filter((_, i) => i !== idx));
  };

  const updateCondition = (idx, field, val) => {
    const updated = [...conditions];
    updated[idx] = { ...updated[idx], [field]: val };
    setConditions(updated);
  };

  const createStrategy = async () => {
    if (!token) { setError('Login required'); return; }
    if (!name.trim()) { setError('Name is required'); return; }
    setLoading(true);
    setError('');
    try {
      const payload = {
        name: name.trim(),
        description: description.trim(),
        action,
        universe,
        conditions: conditions.map(c => ({
          indicator: c.indicator,
          operator: c.operator,
          value: isNaN(c.value) ? c.value : parseFloat(c.value),
        })),
      };
      const res = await fetch(`${API_BASE}/api/strategy/create`, {
        method: 'POST', headers, body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Failed to create');
      setSuccess(`Strategy "${name}" created!`);
      setView('list');
      setName('');
      setDescription('');
      setConditions([{ indicator: 'rsi', operator: '<', value: '30' }]);
      fetchStrategies();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteStrategy = async (id) => {
    if (!confirm('Delete this strategy?')) return;
    try {
      await fetch(`${API_BASE}/api/strategy/${id}`, { method: 'DELETE', headers });
      fetchStrategies();
    } catch (e) {
      setError(e.message);
    }
  };

  const toggleActive = async (id, currentActive) => {
    try {
      await fetch(`${API_BASE}/api/strategy/${id}`, {
        method: 'PUT', headers,
        body: JSON.stringify({ is_active: !currentActive }),
      });
      fetchStrategies();
    } catch (e) {
      setError(e.message);
    }
  };

  const runScan = async (id) => {
    setLoading(true);
    setError('');
    setScanResults(null);
    try {
      const res = await fetch(`${API_BASE}/api/strategy/${id}/scan`, {
        method: 'POST', headers,
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Scan failed');
      setScanResults(json);
      setView('scan-results');
      fetchStrategies(); // refresh match count
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="bg-gray-800/60 rounded-lg p-6 text-center">
        <span className="text-3xl block mb-3">&#9881;</span>
        <p className="text-gray-300 text-sm">Login to build no-code trading strategies</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/60 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-purple-400">&#9881;</span>
          Strategy Builder
        </h3>
        <div className="flex gap-1">
          <button onClick={() => setView('list')}
            className={`px-3 py-1 text-xs rounded ${view === 'list' ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            My Strategies
          </button>
          <button onClick={() => setView('create')}
            className={`px-3 py-1 text-xs rounded ${view === 'create' ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-400'}`}>
            + New
          </button>
        </div>
      </div>

      {error && <div className="bg-red-900/30 border border-red-700 text-red-300 text-xs p-2 rounded mb-3">{error}</div>}
      {success && <div className="bg-green-900/30 border border-green-700 text-green-300 text-xs p-2 rounded mb-3">{success}</div>}

      {/* List View */}
      {view === 'list' && (
        <div className="space-y-2">
          <div className="text-xs text-gray-500 mb-2">
            {strategies.length} / {maxAllowed} strategies used
          </div>
          {strategies.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-500 text-sm mb-3">No strategies yet</p>
              <button onClick={() => setView('create')}
                className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded text-sm">
                + Create First Strategy
              </button>
            </div>
          ) : strategies.map(s => (
            <div key={s.id} className="bg-gray-900/50 rounded p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleActive(s.id, s.is_active)} title={s.is_active ? 'Active' : 'Paused'}>
                    {s.is_active
                      ? <span className="text-green-400 text-lg leading-none">&#9679;</span>
                      : <span className="text-gray-600 text-lg leading-none">&#9675;</span>}
                  </button>
                  <div>
                    <span className="text-white font-semibold text-sm">{s.name}</span>
                    <span className={`ml-2 text-xs px-2 py-0.5 rounded ${s.action === 'BUY' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                      {s.action}
                    </span>
                    <span className="ml-2 text-xs text-gray-500">{s.universe?.replace(/,/g, ', ')}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {s.matches_count > 0 && (
                    <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded">
                      {s.matches_count} matches
                    </span>
                  )}
                  <button onClick={() => runScan(s.id)} disabled={loading}
                    className="bg-purple-700 hover:bg-purple-600 text-white px-2 py-1 rounded text-xs" title="Scan Now">
                    &#9654; Scan
                  </button>
                  <button onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}
                    className="text-gray-500 hover:text-white p-1">
                    {expandedId === s.id ? '\u25B2' : '\u25BC'}
                  </button>
                  <button onClick={() => deleteStrategy(s.id)} className="text-gray-600 hover:text-red-400 p-1">
                    &#10005;
                  </button>
                </div>
              </div>

              {/* Expanded rules */}
              {expandedId === s.id && (
                <div className="mt-3 border-t border-gray-700 pt-2">
                  {s.description && <p className="text-xs text-gray-400 mb-2">{s.description}</p>}
                  <div className="space-y-1">
                    {(s.conditions || []).map((c, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="text-purple-400 font-mono">{c.indicator}</span>
                        <span className="text-gray-500">{OPERATOR_LABELS[c.operator] || c.operator}</span>
                        <span className="text-white font-mono">{String(c.value)}</span>
                      </div>
                    ))}
                  </div>
                  {s.last_scan_at && (
                    <div className="text-[10px] text-gray-600 mt-2">
                      Last scan: {new Date(s.last_scan_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create View */}
      {view === 'create' && (
        <div className="space-y-3">
          <div>
            <label className="text-[10px] text-gray-500">Strategy Name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. RSI Oversold Bounce"
              className="w-full bg-gray-900 rounded px-3 py-2 text-white text-sm" maxLength={100} />
          </div>

          <div>
            <label className="text-[10px] text-gray-500">Description (optional)</label>
            <input value={description} onChange={e => setDescription(e.target.value)} placeholder="What this strategy does..."
              className="w-full bg-gray-900 rounded px-3 py-2 text-gray-400 text-sm" maxLength={500} />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-gray-500">Action</label>
              <select value={action} onChange={e => setAction(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-white text-sm">
                <option value="BUY">BUY Signal</option>
                <option value="SELL">SELL Signal</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500">Market Universe</label>
              <select value={universe} onChange={e => setUniverse(e.target.value)}
                className="w-full bg-gray-900 rounded px-3 py-2 text-white text-sm">
                {universes.map(u => (
                  <option key={u.id} value={u.id}>{u.name} ({u.symbols})</option>
                ))}
              </select>
            </div>
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] text-gray-500">Rules (all must match)</label>
              <button onClick={addCondition} disabled={conditions.length >= 10}
                className="text-xs text-purple-400 hover:text-purple-300 disabled:text-gray-600">
                + Add Rule
              </button>
            </div>

            <div className="space-y-2">
              {conditions.map((cond, i) => {
                const indicatorMeta = indicators.find(ind => ind.id === cond.indicator);
                const isEnum = indicatorMeta?.type === 'enum';

                return (
                  <div key={i} className="flex items-center gap-2 bg-gray-900/50 rounded p-2">
                    <select value={cond.indicator} onChange={e => updateCondition(i, 'indicator', e.target.value)}
                      className="bg-gray-800 rounded px-2 py-1 text-purple-400 text-xs flex-1">
                      {indicators.map(ind => (
                        <option key={ind.id} value={ind.id}>{ind.name}</option>
                      ))}
                    </select>

                    <select value={cond.operator} onChange={e => updateCondition(i, 'operator', e.target.value)}
                      className="bg-gray-800 rounded px-2 py-1 text-gray-300 text-xs w-14">
                      {isEnum
                        ? ['==', '!='].map(op => <option key={op} value={op}>{OPERATOR_LABELS[op]}</option>)
                        : Object.entries(OPERATOR_LABELS).map(([op, label]) => (
                            <option key={op} value={op}>{label}</option>
                          ))
                      }
                    </select>

                    {isEnum ? (
                      <select value={cond.value} onChange={e => updateCondition(i, 'value', e.target.value)}
                        className="bg-gray-800 rounded px-2 py-1 text-white text-xs flex-1">
                        {(indicatorMeta.values || []).map(v => (
                          <option key={v} value={v}>{v}</option>
                        ))}
                      </select>
                    ) : (
                      <input type="number" value={cond.value} onChange={e => updateCondition(i, 'value', e.target.value)}
                        className="bg-gray-800 rounded px-2 py-1 text-white text-xs w-20" step="any" />
                    )}

                    {conditions.length > 1 && (
                      <button onClick={() => removeCondition(i)} className="text-gray-600 hover:text-red-400">
                        &#10005;
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Preview */}
          <div className="bg-gray-900/30 rounded p-3 border border-gray-700">
            <div className="text-[10px] text-gray-500 mb-1">Strategy Preview</div>
            <div className="text-xs text-gray-300">
              <span className={action === 'BUY' ? 'text-green-400' : 'text-red-400'}>{action}</span>
              {' when '}
              {conditions.map((c, i) => (
                <span key={i}>
                  {i > 0 && <span className="text-purple-400"> AND </span>}
                  <span className="text-white">{c.indicator}</span>
                  <span className="text-gray-500"> {OPERATOR_LABELS[c.operator]} </span>
                  <span className="text-cyan-400">{c.value}</span>
                </span>
              ))}
              <span className="text-gray-500"> in {universe.replace(/_/g, ' ')}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={() => setView('list')} className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-300 py-2 rounded text-sm">
              Cancel
            </button>
            <button onClick={createStrategy} disabled={loading || !name.trim()}
              className="flex-1 bg-purple-600 hover:bg-purple-500 text-white py-2 rounded text-sm font-semibold disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Strategy'}
            </button>
          </div>
        </div>
      )}

      {/* Scan Results View */}
      {view === 'scan-results' && scanResults && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-white font-semibold text-sm">{scanResults.strategy_name}</h4>
              <div className="text-xs text-gray-500">
                Scanned {scanResults.scanned} symbols &mdash; {scanResults.match_count} matches
              </div>
            </div>
            <button onClick={() => setView('list')} className="text-xs text-gray-500 hover:text-white">
              Back
            </button>
          </div>

          {scanResults.matches.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">
              No symbols match your strategy right now. Try adjusting conditions.
            </p>
          ) : (
            <div className="space-y-2">
              {scanResults.matches.map((m, i) => (
                <div key={i} className="bg-gray-900/50 rounded p-3 flex items-center justify-between cursor-pointer hover:bg-gray-900/80"
                  onClick={() => onSymbolSelect?.(m.symbol)}>
                  <div>
                    <span className="text-white font-semibold">{m.symbol}</span>
                    <span className={`ml-2 text-xs px-2 py-0.5 rounded ${
                      scanResults.action === 'BUY' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                    }`}>
                      {scanResults.action}
                    </span>
                    <div className="flex gap-3 mt-1 text-xs text-gray-500">
                      <span>Price: ${m.price?.toFixed(2)}</span>
                      <span>RSI: {m.rsi?.toFixed(1)}</span>
                      <span className={m.change_pct >= 0 ? 'text-green-500' : 'text-red-500'}>
                        {m.change_pct >= 0 ? '+' : ''}{m.change_pct?.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                  <span className="text-purple-400">&#9889;</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(StrategyBuilder);
