import React, { useState, useEffect } from 'react';

function FlowBar({ label, net, maxAbs }) {
  const pct = maxAbs > 0 ? Math.abs(net) / maxAbs : 0;
  const width = `${Math.round(pct * 100)}%`;
  const isPositive = net >= 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-300 font-medium">{label}</span>
        <span className={`font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}₹{Math.abs(net).toLocaleString('en-IN')} Cr
        </span>
      </div>
      <div className="h-2 bg-gray-700 rounded overflow-hidden">
        <div
          className={`h-full rounded ${isPositive ? 'bg-green-500' : 'bg-red-500'}`}
          style={{ width }}
        />
      </div>
    </div>
  );
}

export default function FiiDiiTab({ apiBase }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${apiBase}/api/v4/fii-dii`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [apiBase]);

  if (loading)
    return <p className="text-gray-400 text-sm text-center py-4">Loading FII/DII data…</p>;
  if (!data || !data.success)
    return <p className="text-gray-400 text-sm text-center py-4">FII/DII data unavailable</p>;

  const maxAbs = Math.max(Math.abs(data.fii.net), Math.abs(data.dii.net), 1);
  const totalNet = data.fii.net + data.dii.net;
  const marketSentiment = totalNet > 500 ? 'Bullish' : totalNet < -500 ? 'Bearish' : 'Neutral';
  const sentimentColor =
    totalNet > 500 ? 'text-green-400' : totalNet < -500 ? 'text-red-400' : 'text-yellow-400';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-white">Institutional Flows</h4>
          <p className="text-xs text-gray-400">{data.date}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-400">Market Sentiment</p>
          <p className={`text-sm font-bold ${sentimentColor}`}>{marketSentiment}</p>
        </div>
      </div>

      <div className="space-y-3 p-4 bg-gray-700/40 rounded-lg">
        <FlowBar label="FII / FPI (Foreign)" net={data.fii.net} maxAbs={maxAbs} />
        <FlowBar label="DII (Domestic)" net={data.dii.net} maxAbs={maxAbs} />
      </div>

      {(data.fii.buy > 0 || data.dii.buy > 0) && (
        <div className="grid grid-cols-2 gap-3 text-xs">
          {[
            { label: 'FII Buy', val: data.fii.buy, color: 'text-green-400' },
            { label: 'FII Sell', val: data.fii.sell, color: 'text-red-400' },
            { label: 'DII Buy', val: data.dii.buy, color: 'text-green-400' },
            { label: 'DII Sell', val: data.dii.sell, color: 'text-red-400' },
          ].map(({ label, val, color }) => (
            <div key={label} className="p-2 bg-gray-700/30 rounded">
              <p className="text-gray-400">{label}</p>
              <p className={`font-semibold ${color}`}>₹{val.toLocaleString('en-IN')} Cr</p>
            </div>
          ))}
        </div>
      )}

      <div className="p-3 bg-gray-700/30 rounded-lg text-xs text-gray-400">
        <p className="font-medium text-gray-300 mb-1">How to read this:</p>
        <p>
          • <span className="text-green-400">FII buying</span> = foreign capital flowing into India
          = bullish signal
        </p>
        <p>
          • <span className="text-red-400">FII selling</span> = capital outflow = bearish pressure
          on index
        </p>
        <p>• DII often buys when FII sells — provides market support</p>
      </div>

      <p className="text-xs text-gray-600 text-right">
        Source: {data.source}
        {data.cached ? ' (cached)' : ''}
      </p>
    </div>
  );
}
