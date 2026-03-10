import React, { memo } from 'react';
import { formatTimestamp } from '../utils/formatters';

function ChartPanel({ history, selectedSymbol, chartInterval, currency }) {
  if (!history || !Array.isArray(history)) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-gray-500">
        <svg className="w-12 h-12 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p>Loading chart for {selectedSymbol}...</p>
        <p className="text-xs text-gray-600 mt-1">Initializing chart data...</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-gray-500">
        <svg className="w-12 h-12 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p>Loading chart for {selectedSymbol}...</p>
        <p className="text-xs text-gray-600 mt-1">
          Waiting for historical data... ({chartInterval} interval)
        </p>
      </div>
    );
  }

  try {
    const prices = history.map(h => h.close || h.price || 0).filter(p => p > 0);

    if (prices.length === 0) {
      return (
        <div className="h-64 flex items-center justify-center text-gray-500">
          <p>No valid price data for chart.</p>
        </div>
      );
    }

    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const range = maxPrice - minPrice || 1;

    const width = 700;
    const height = 200;
    const padding = 40;

    const points = history.map((h, i) => {
      const x = padding + (i / (history.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((h.close || h.price || 0) - minPrice) / range * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`;

    const firstCandle = history[0];
    const lastCandle = history[history.length - 1];
    const firstTimestamp = firstCandle?.timestamp || firstCandle?.date;
    const lastTimestamp = lastCandle?.timestamp || lastCandle?.date;

    const startLabel = formatTimestamp(firstTimestamp, chartInterval);
    const endLabel = formatTimestamp(lastTimestamp, chartInterval);

    const displayStartLabel = startLabel || (chartInterval.includes('m') || chartInterval.includes('h')
      ? new Date(Date.now() - history.length * 60000).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})
      : new Date(Date.now() - history.length * 86400000).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}));
    const displayEndLabel = endLabel || 'Now';

    return (
      <svg viewBox={`0 0 ${width} ${height + 20}`} className="w-full h-64">
        <defs>
          <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3"/>
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0"/>
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75].map(pct => (
          <line
            key={pct}
            x1={padding}
            y1={padding + pct * (height - 2 * padding)}
            x2={width - padding}
            y2={padding + pct * (height - 2 * padding)}
            stroke="#374151"
            strokeDasharray="4"
          />
        ))}

        <polygon points={areaPoints} fill="url(#chartGradient)" />
        <polyline points={points} fill="none" stroke="#06b6d4" strokeWidth="2" />

        <text x={padding - 5} y={padding + 5} fill="#9ca3af" fontSize="10" textAnchor="end">
          {currency}{maxPrice.toFixed(2)}
        </text>
        <text x={padding - 5} y={height - padding + 5} fill="#9ca3af" fontSize="10" textAnchor="end">
          {currency}{minPrice.toFixed(2)}
        </text>

        <text x={padding} y={height - padding + 20} fill="#9ca3af" fontSize="10">
          {displayStartLabel}
        </text>
        <text x={width - padding} y={height - padding + 20} fill="#9ca3af" fontSize="10" textAnchor="end">
          {displayEndLabel}
        </text>
      </svg>
    );
  } catch (error) {
    return (
      <div className="h-64 flex items-center justify-center text-red-400">
        <p>Error rendering chart: {error.message}</p>
      </div>
    );
  }
}

export default memo(ChartPanel);
