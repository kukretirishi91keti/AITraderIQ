import React, { useState, useEffect } from 'react';

export default function EarningsTab({ symbol, apiBase }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    fetch(`${apiBase}/api/v4/earnings/${symbol}`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [symbol, apiBase]);

  if (loading) return <p className="text-gray-400 text-sm text-center py-4">Loading earnings…</p>;
  if (!data || !data.success)
    return <p className="text-gray-400 text-sm text-center py-4">Earnings data unavailable</p>;
  if (!data.earnings?.length)
    return (
      <p className="text-gray-400 text-sm text-center py-4">
        No upcoming earnings found for {symbol}
      </p>
    );

  const upcoming = data.earnings.filter((e) => !e.epsActual);
  const past = data.earnings.filter((e) => e.epsActual != null);

  return (
    <div className="space-y-4">
      {upcoming.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-cyan-400 uppercase mb-2">Upcoming Results</h4>
          <div className="space-y-2">
            {upcoming.map((e, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 bg-yellow-900/20 border border-yellow-700/40 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-white">{e.date}</p>
                  <p className="text-xs text-gray-400">
                    Q{e.quarter} {e.year}
                  </p>
                </div>
                {e.epsEstimate != null && (
                  <div className="text-right">
                    <p className="text-xs text-gray-400">EPS Est.</p>
                    <p className="text-sm text-white">{e.epsEstimate}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Recent Results</h4>
          <div className="space-y-2">
            {past.slice(0, 4).map((e, i) => {
              const beat =
                e.epsActual != null && e.epsEstimate != null && e.epsActual >= e.epsEstimate;
              const miss =
                e.epsActual != null && e.epsEstimate != null && e.epsActual < e.epsEstimate;
              return (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 bg-gray-700/40 rounded-lg"
                >
                  <div>
                    <p className="text-sm font-medium text-white">{e.date}</p>
                    <p className="text-xs text-gray-400">
                      Q{e.quarter} {e.year}
                    </p>
                  </div>
                  <div className="flex gap-4 text-right">
                    {e.epsEstimate != null && (
                      <div>
                        <p className="text-xs text-gray-400">Est.</p>
                        <p className="text-sm text-gray-300">{e.epsEstimate}</p>
                      </div>
                    )}
                    <div>
                      <p className="text-xs text-gray-400">Actual</p>
                      <p
                        className={`text-sm font-semibold ${beat ? 'text-green-400' : miss ? 'text-red-400' : 'text-white'}`}
                      >
                        {e.epsActual} {beat ? '✓' : miss ? '✗' : ''}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-600 text-right">Source: Finnhub</p>
    </div>
  );
}
