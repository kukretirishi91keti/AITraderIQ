import React, { useState, useEffect, useRef } from 'react';
import { API_BASE } from '../constants/appConfig';

function IndexTile({ index }) {
  if (!index || index.price == null) {
    return (
      <div className="flex items-center gap-2 px-3 py-1 bg-gray-800 rounded">
        <span className="text-gray-400 text-xs font-medium">{index?.name || '—'}</span>
        <span className="text-gray-500 text-xs">—</span>
      </div>
    );
  }

  const isUp = index.changePercent >= 0;
  const color = isUp ? 'text-green-400' : 'text-red-400';
  const sign = isUp ? '+' : '';

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-gray-800 rounded border border-gray-700">
      <span className="text-gray-300 text-xs font-semibold">{index.name}</span>
      <span className="text-white text-xs font-bold">
        ₹{index.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
      </span>
      <span className={`text-xs font-medium ${color}`}>
        {sign}
        {index.changePercent?.toFixed(2)}%
      </span>
      {index.dataQuality === 'SIMULATED' && <span className="text-yellow-600 text-xs">~</span>}
    </div>
  );
}

function MarketStatusBadge({ status }) {
  if (!status) return null;
  const cfg = {
    OPEN: { dot: 'bg-green-400', text: 'text-green-300', bg: 'bg-green-900/30' },
    PRE_OPEN: { dot: 'bg-yellow-400', text: 'text-yellow-300', bg: 'bg-yellow-900/30' },
    POST_CLOSE: { dot: 'bg-blue-400', text: 'text-blue-300', bg: 'bg-blue-900/30' },
    CLOSED: { dot: 'bg-gray-500', text: 'text-gray-400', bg: 'bg-gray-800' },
  };
  const c = cfg[status.session] || cfg.CLOSED;
  return (
    <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded ${c.bg} border border-gray-700`}>
      <span
        className={`w-1.5 h-1.5 rounded-full ${c.dot} ${status.session === 'OPEN' ? 'animate-pulse' : ''}`}
      />
      <span className={`text-xs font-medium ${c.text} whitespace-nowrap`}>{status.label}</span>
      <span className="text-gray-500 text-xs">{status.ist_time}</span>
    </div>
  );
}

export default function IndiaIndexBar() {
  const [indices, setIndices] = useState([]);
  const [marketStatus, setMarketStatus] = useState(null);
  const indexRef = useRef(null);
  const statusRef = useRef(null);

  const fetchIndices = () => {
    fetch(`${API_BASE}/api/v4/indices`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.indices)) setIndices(d.indices);
      })
      .catch(() => {});
  };

  const fetchStatus = () => {
    fetch(`${API_BASE}/api/v4/market-status`)
      .then((r) => r.json())
      .then((d) => setMarketStatus(d))
      .catch(() => {});
  };

  useEffect(() => {
    fetchIndices();
    fetchStatus();
    indexRef.current = setInterval(fetchIndices, 5000);
    statusRef.current = setInterval(fetchStatus, 30000);
    return () => {
      clearInterval(indexRef.current);
      clearInterval(statusRef.current);
    };
  }, []);

  if (!indices.length && !marketStatus) return null;

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-4 py-1 flex items-center gap-3 overflow-x-auto">
      <span className="text-gray-500 text-xs font-medium whitespace-nowrap">NSE</span>
      <MarketStatusBadge status={marketStatus} />
      {indices.map((idx) => (
        <IndexTile key={idx.symbol} index={idx} />
      ))}
    </div>
  );
}
