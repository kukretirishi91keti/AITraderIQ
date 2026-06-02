import React, { useState, useEffect } from 'react';

const NUM_FMT = (n) => (n == null || n === 0 ? '—' : Number(n).toLocaleString('en-IN'));
const PRICE_FMT = (n) => (n == null || n === 0 ? '—' : `₹${Number(n).toFixed(2)}`);

function OIBar({ value, max, isCall }) {
  if (!max || !value) return null;
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="h-1 rounded overflow-hidden bg-gray-700 w-16 inline-block align-middle">
      <div
        className={`h-full rounded ${isCall ? 'bg-blue-500' : 'bg-orange-500'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function OptionChainTab({ symbol, apiBase }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedExpiry, setSelectedExpiry] = useState(null);

  // Determine which underlying to query
  const underlying = symbol ? symbol.replace('.NS', '').replace('.BO', '').toUpperCase() : 'NIFTY';

  useEffect(() => {
    setLoading(true);
    setData(null);
    fetch(`${apiBase}/api/v4/option-chain/${underlying}`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setSelectedExpiry(d.expiryDate || null);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [underlying, apiBase]);

  if (loading)
    return <p className="text-gray-400 text-sm text-center py-6">Loading option chain…</p>;

  if (!data || !data.success)
    return (
      <div className="text-center py-6 space-y-2">
        <p className="text-gray-400 text-sm">
          {data?.error || 'Option chain unavailable for this symbol.'}
        </p>
        <p className="text-xs text-gray-600">
          Option chains are available for NIFTY, BANKNIFTY, and NSE-listed equities during market
          hours.
        </p>
      </div>
    );

  const rows = data.rows || [];
  const maxCeOI = Math.max(...rows.map((r) => r.CE?.oi || 0), 1);
  const maxPeOI = Math.max(...rows.map((r) => r.PE?.oi || 0), 1);

  // PCR (Put-Call Ratio)
  const totalCeOI = rows.reduce((s, r) => s + (r.CE?.oi || 0), 0);
  const totalPeOI = rows.reduce((s, r) => s + (r.PE?.oi || 0), 0);
  const pcr = totalCeOI > 0 ? (totalPeOI / totalCeOI).toFixed(2) : '—';
  const pcrColor =
    pcr === '—'
      ? 'text-gray-400'
      : Number(pcr) > 1.2
        ? 'text-green-400'
        : Number(pcr) < 0.8
          ? 'text-red-400'
          : 'text-yellow-400';

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h4 className="text-sm font-semibold text-white">{data.underlying} Option Chain</h4>
          <p className="text-xs text-gray-400">
            Spot: {PRICE_FMT(data.underlyingValue)} · ATM: {NUM_FMT(data.atmStrike)} · Expiry:{' '}
            {selectedExpiry}
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-gray-400">PCR </span>
            <span className={`font-bold ${pcrColor}`}>{pcr}</span>
            <span className="text-gray-600 ml-1">
              {pcr !== '—' && Number(pcr) > 1.2
                ? '(Bullish)'
                : pcr !== '—' && Number(pcr) < 0.8
                  ? '(Bearish)'
                  : '(Neutral)'}
            </span>
          </div>
          {data.cached && <span className="text-gray-600">cached</span>}
        </div>
      </div>

      {/* Expiry selector */}
      {data.expiryDates?.length > 1 && (
        <div className="flex gap-1 flex-wrap">
          {data.expiryDates.map((d) => (
            <button
              key={d}
              onClick={() => setSelectedExpiry(d)}
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                selectedExpiry === d
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-700/60 text-gray-400">
              <th className="px-2 py-2 text-right text-blue-400" colSpan={3}>
                CALL (CE)
              </th>
              <th className="px-3 py-2 text-center font-bold text-white">Strike</th>
              <th className="px-2 py-2 text-left text-orange-400" colSpan={3}>
                PUT (PE)
              </th>
            </tr>
            <tr className="bg-gray-700/40 text-gray-500 text-center">
              <th className="px-2 py-1 text-right">OI</th>
              <th className="px-2 py-1 text-right">IV%</th>
              <th className="px-2 py-1 text-right">LTP</th>
              <th className="px-3 py-1"></th>
              <th className="px-2 py-1 text-left">LTP</th>
              <th className="px-2 py-1 text-left">IV%</th>
              <th className="px-2 py-1 text-left">OI</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isATM = row.isATM;
              const rowBg = isATM
                ? 'bg-cyan-900/30 border-y border-cyan-700/40'
                : 'hover:bg-gray-700/20';
              return (
                <tr key={row.strikePrice} className={`border-b border-gray-700/30 ${rowBg}`}>
                  {/* CE side */}
                  <td className="px-2 py-1.5 text-right text-gray-300">
                    <span className="mr-1">{NUM_FMT(row.CE.oi)}</span>
                    <OIBar value={row.CE.oi} max={maxCeOI} isCall />
                  </td>
                  <td className="px-2 py-1.5 text-right text-blue-300">
                    {row.CE.iv ? `${row.CE.iv}%` : '—'}
                  </td>
                  <td className="px-2 py-1.5 text-right font-medium text-blue-400">
                    {PRICE_FMT(row.CE.ltp)}
                  </td>

                  {/* Strike */}
                  <td
                    className={`px-3 py-1.5 text-center font-bold ${isATM ? 'text-cyan-300' : 'text-white'}`}
                  >
                    {NUM_FMT(row.strikePrice)}
                    {isATM && <span className="ml-1 text-cyan-500 text-xs font-normal">ATM</span>}
                  </td>

                  {/* PE side */}
                  <td className="px-2 py-1.5 text-left font-medium text-orange-400">
                    {PRICE_FMT(row.PE.ltp)}
                  </td>
                  <td className="px-2 py-1.5 text-left text-orange-300">
                    {row.PE.iv ? `${row.PE.iv}%` : '—'}
                  </td>
                  <td className="px-2 py-1.5 text-left text-gray-300">
                    <OIBar value={row.PE.oi} max={maxPeOI} isCall={false} />
                    <span className="ml-1">{NUM_FMT(row.PE.oi)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="p-3 bg-gray-700/20 rounded text-xs text-gray-500">
        <p>
          <span className="text-blue-400 font-medium">CE OI</span> = open interest in call
          contracts. High CE OI at a strike = resistance.{' '}
          <span className="text-orange-400 font-medium">PE OI</span> = put open interest. High PE OI
          = support. PCR &gt; 1.2 is broadly bullish; &lt; 0.8 bearish.
        </p>
        <p className="mt-1 text-gray-600">Source: NSE · {data.cached ? 'cached' : 'live'}</p>
      </div>
    </div>
  );
}
