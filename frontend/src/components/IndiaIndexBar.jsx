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
        {sign}{index.changePercent?.toFixed(2)}%
      </span>
      {index.dataQuality === 'SIMULATED' && (
        <span className="text-yellow-600 text-xs">~</span>
      )}
    </div>
  );
}

export default function IndiaIndexBar() {
  const [indices, setIndices] = useState([]);
  const intervalRef = useRef(null);

  const fetchIndices = () => {
    fetch(`${API_BASE}/api/v4/indices`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.indices)) setIndices(d.indices);
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchIndices();
    intervalRef.current = setInterval(fetchIndices, 5000);
    return () => clearInterval(intervalRef.current);
  }, []);

  if (!indices.length) return null;

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-4 py-1 flex items-center gap-3 overflow-x-auto">
      <span className="text-gray-500 text-xs font-medium whitespace-nowrap">NSE</span>
      {indices.map((idx) => (
        <IndexTile key={idx.symbol} index={idx} />
      ))}
    </div>
  );
}
