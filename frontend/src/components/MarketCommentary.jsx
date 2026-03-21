/**
 * MarketCommentary - AI-generated market digest.
 * Shows auto-commentary on significant market moves.
 */
import React, { useState, useEffect, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const SEVERITY_STYLES = {
  high: 'border-l-red-500 bg-red-900/10',
  medium: 'border-l-yellow-500 bg-yellow-900/10',
  normal: 'border-l-gray-600 bg-gray-800/50',
};

function MarketCommentary() {
  const [digest, setDigest] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDigest();
    const interval = setInterval(fetchDigest, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, []);

  const fetchDigest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/commentary/market/digest`);
      const json = await res.json();
      if (json.success) setDigest(json);
    } catch (e) {
      console.error('Commentary fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  if (!digest) {
    return loading ? (
      <div className="p-4 text-center text-gray-400">Loading market commentary...</div>
    ) : null;
  }

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-gray-800/50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-cyan-400">Market Digest</h3>
          <span className="text-[10px] text-gray-500">
            {digest.significant_moves}/{digest.total_monitored} active
          </span>
        </div>
        <p className="text-sm text-gray-300">{digest.summary}</p>
      </div>

      {/* Individual Commentaries */}
      {(digest.items || []).map((item, i) => (
        <div
          key={i}
          className={`border-l-2 rounded-r-lg p-3 ${SEVERITY_STYLES[item.severity] || SEVERITY_STYLES.normal}`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-cyan-400 text-sm">{item.symbol}</span>
            <span className={`text-xs font-medium ${
              item.price_change_pct > 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {item.price_change_pct > 0 ? '+' : ''}{item.price_change_pct}%
            </span>
            {item.severity === 'high' && (
              <span className="text-[10px] px-1.5 py-0.5 bg-red-900/50 text-red-400 rounded">
                ALERT
              </span>
            )}
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{item.commentary}</p>
        </div>
      ))}

      {(digest.items || []).length === 0 && (
        <div className="text-center text-gray-500 text-sm py-4">
          No significant moves detected. Markets are quiet.
        </div>
      )}
    </div>
  );
}

export default memo(MarketCommentary);
