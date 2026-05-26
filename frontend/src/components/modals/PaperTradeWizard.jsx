import React, { useState } from 'react';
import { API_BASE } from '../../config';

function StepIndicator({ step }) {
  const steps = ['Direction', 'Size', 'Confirm'];
  return (
    <div className="flex items-center justify-center gap-3 mb-6">
      {steps.map((label, i) => (
        <React.Fragment key={label}>
          <div className="flex flex-col items-center gap-1">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
                i < step
                  ? 'bg-cyan-600 border-cyan-600 text-white'
                  : i === step
                    ? 'bg-transparent border-cyan-400 text-cyan-400'
                    : 'bg-transparent border-gray-600 text-gray-600'
              }`}
            >
              {i < step ? '✓' : i + 1}
            </div>
            <span className={`text-xs ${i === step ? 'text-cyan-400' : 'text-gray-500'}`}>
              {label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-px ${i < step ? 'bg-cyan-600' : 'bg-gray-700'} mt-[-12px]`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function PaperTradeWizard({ onClose, symbol, prefill, token, onSuccess }) {
  const [step, setStep] = useState(0);
  const [side, setSide] = useState(prefill?.side || null);
  const [shares, setShares] = useState(prefill?.shares || 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);

  const entry = prefill?.entry || null;
  const stop = prefill?.stop || null;
  const target = prefill?.target || null;
  const currency = /\.(NS|BO)$/i.test(symbol) ? '₹' : '$';

  const gain = entry && target ? ((target - entry) * shares).toFixed(2) : null;
  const loss = entry && stop ? ((entry - stop) * shares).toFixed(2) : null;

  async function confirmTrade() {
    setLoading(true);
    setError(null);
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_BASE}/api/paper-trade`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ symbol, side, quantity: shares }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Error ${res.status}`);
      }
      setDone(true);
      if (onSuccess) setTimeout(onSuccess, 1500);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-xl max-w-md w-full shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-white">Paper Trade</h2>
            <p className="text-sm text-gray-400">{symbol} · No real money</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl leading-none">
            &times;
          </button>
        </div>

        <div className="p-5">
          {done ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-3">✅</div>
              <p className="text-green-400 font-semibold text-lg">Trade placed!</p>
              <p className="text-gray-400 text-sm mt-1">
                {side?.toUpperCase()} {shares} × {symbol} — check Paper Trades to track it.
              </p>
            </div>
          ) : (
            <>
              <StepIndicator step={step} />

              {/* Step 0: Direction */}
              {step === 0 && (
                <div>
                  <p className="text-center text-gray-300 mb-5">
                    What direction do you expect <span className="text-white font-medium">{symbol}</span> to move?
                  </p>
                  <div className="flex gap-4">
                    <button
                      onClick={() => { setSide('buy'); setStep(1); }}
                      className="flex-1 py-6 rounded-xl bg-green-900/40 border-2 border-green-600 hover:bg-green-900/70 flex flex-col items-center gap-2 transition-colors"
                    >
                      <span className="text-3xl">↑</span>
                      <span className="text-green-400 font-bold text-lg">BUY</span>
                      <span className="text-xs text-gray-400 text-center">Price will rise</span>
                    </button>
                    <button
                      onClick={() => { setSide('sell'); setStep(1); }}
                      className="flex-1 py-6 rounded-xl bg-red-900/40 border-2 border-red-600 hover:bg-red-900/70 flex flex-col items-center gap-2 transition-colors"
                    >
                      <span className="text-3xl">↓</span>
                      <span className="text-red-400 font-bold text-lg">SELL</span>
                      <span className="text-xs text-gray-400 text-center">Price will fall</span>
                    </button>
                  </div>
                  <p className="text-center text-xs text-gray-500 mt-4">
                    BUY if you think price will rise. SELL (short) if you expect it to fall.
                  </p>
                </div>
              )}

              {/* Step 1: Quantity */}
              {step === 1 && (
                <div>
                  <p className="text-gray-300 mb-5 text-center">
                    How many shares of <span className="text-white font-medium">{symbol}</span>?
                    <span
                      className={`ml-2 px-2 py-0.5 rounded text-xs font-bold ${side === 'buy' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}
                    >
                      {side?.toUpperCase()}
                    </span>
                  </p>
                  <div className="flex items-center justify-center gap-4 mb-5">
                    <button
                      onClick={() => setShares((s) => Math.max(1, s - 1))}
                      className="w-10 h-10 rounded-full bg-gray-700 hover:bg-gray-600 text-xl font-bold"
                    >
                      −
                    </button>
                    <input
                      type="number"
                      min="1"
                      value={shares}
                      onChange={(e) => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-24 text-center text-2xl font-bold bg-gray-700 rounded-lg py-2 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    />
                    <button
                      onClick={() => setShares((s) => s + 1)}
                      className="w-10 h-10 rounded-full bg-gray-700 hover:bg-gray-600 text-xl font-bold"
                    >
                      +
                    </button>
                  </div>
                  {entry && (
                    <div className="bg-gray-700/50 rounded-lg p-3 text-sm space-y-1 mb-5">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Investment</span>
                        <span className="text-white font-medium">
                          {currency}{(entry * shares).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                      </div>
                      {loss && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Max loss (if stop hit)</span>
                          <span className="text-red-400">−{currency}{Math.abs(loss)}</span>
                        </div>
                      )}
                      {gain && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Potential gain (if target hit)</span>
                          <span className="text-green-400">+{currency}{gain}</span>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="flex gap-3">
                    <button
                      onClick={() => setStep(0)}
                      className="flex-1 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm"
                    >
                      ← Back
                    </button>
                    <button
                      onClick={() => setStep(2)}
                      className="flex-1 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-sm font-medium"
                    >
                      Continue →
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Confirm */}
              {step === 2 && (
                <div>
                  <p className="text-gray-300 mb-4 text-center text-sm">Review your trade before placing</p>
                  <div className="bg-gray-700/50 rounded-xl p-4 mb-4 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-400 text-sm">Direction</span>
                      <span
                        className={`font-bold text-sm px-2 py-0.5 rounded ${side === 'buy' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}
                      >
                        {side?.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Symbol</span>
                      <span className="text-white font-medium text-sm">{symbol}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Quantity</span>
                      <span className="text-white font-medium text-sm">{shares} shares</span>
                    </div>
                    {entry && (
                      <div className="flex justify-between">
                        <span className="text-gray-400 text-sm">Entry</span>
                        <span className="text-white text-sm">{currency}{entry.toFixed(2)}</span>
                      </div>
                    )}
                    {stop && (
                      <div className="flex justify-between">
                        <span className="text-gray-400 text-sm">Stop Loss</span>
                        <span className="text-red-400 text-sm">{currency}{stop.toFixed(2)}</span>
                      </div>
                    )}
                    {target && (
                      <div className="flex justify-between">
                        <span className="text-gray-400 text-sm">Target</span>
                        <span className="text-green-400 text-sm">{currency}{target.toFixed(2)}</span>
                      </div>
                    )}
                    {gain && (
                      <div className="flex justify-between border-t border-gray-600 pt-2 mt-2">
                        <span className="text-gray-400 text-sm">If target hit</span>
                        <span className="text-green-400 font-semibold text-sm">+{currency}{gain}</span>
                      </div>
                    )}
                  </div>

                  {error && (
                    <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-red-400 text-sm">
                      {error}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button
                      onClick={() => setStep(1)}
                      disabled={loading}
                      className="flex-1 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm disabled:opacity-50"
                    >
                      ← Back
                    </button>
                    <button
                      onClick={confirmTrade}
                      disabled={loading}
                      className="flex-1 py-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                          </svg>
                          Placing…
                        </>
                      ) : (
                        'Confirm Trade ✓'
                      )}
                    </button>
                  </div>
                  <p className="text-center text-xs text-gray-500 mt-3">
                    Paper trade only — no real money involved
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
