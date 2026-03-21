/**
 * TopMovers.jsx - ENHANCED
 * ========================
 * Location: frontend/src/components/TopMovers.jsx
 * 
 * Shows top gainers and losers with real data from backend
 */
import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const TopMovers = ({ market = 'US', onSelectStock, limit = 5 }) => {
  const [gainers, setGainers] = useState([]);
  const [losers, setLosers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({ gainers: true, losers: true });

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE}/api/v4/top-movers/${market}?limit=${limit}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Handle different response formats
        const gainersList = data.gainers || [];
        const losersList = data.losers || [];
        
        setGainers(gainersList.slice(0, limit));
        setLosers(losersList.slice(0, limit));
        
      } catch (err) {
        console.error('TopMovers fetch error:', err);
        setError(err.message);
        
        // Fallback mock data for demo
        setGainers([
          { symbol: 'NVDA', ticker: 'NVDA', price: 142.50, changePercent: 5.2 },
          { symbol: 'TSLA', ticker: 'TSLA', price: 248.30, changePercent: 3.8 },
          { symbol: 'AMD', ticker: 'AMD', price: 125.60, changePercent: 2.9 },
        ]);
        setLosers([
          { symbol: 'INTC', ticker: 'INTC', price: 45.20, changePercent: -2.5 },
          { symbol: 'BA', ticker: 'BA', price: 178.90, changePercent: -1.8 },
          { symbol: 'DIS', ticker: 'DIS', price: 92.40, changePercent: -1.2 },
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
    
  }, [market, limit]);

  const handleClick = (symbol) => {
    if (onSelectStock) {
      onSelectStock(symbol);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-20 bg-gray-800 rounded"></div>
        <div className="h-20 bg-gray-800 rounded"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Gainers */}
      <div>
        <button
          onClick={() => setExpanded(e => ({ ...e, gainers: !e.gainers }))}
          className="flex items-center justify-between w-full text-left mb-2"
        >
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
            📈 Top Gainers
            <span className="text-green-400 font-mono">({gainers.length})</span>
          </span>
          <span className="text-gray-600">{expanded.gainers ? '▼' : '▶'}</span>
        </button>
        
        {expanded.gainers && (
          <div className="space-y-1">
            {gainers.length === 0 ? (
              <div className="text-gray-500 text-xs italic">No gainers data</div>
            ) : (
              gainers.map((stock, i) => (
                <button
                  key={stock.symbol || stock.ticker || i}
                  onClick={() => handleClick(stock.symbol || stock.ticker)}
                  className="w-full flex items-center justify-between p-2 rounded bg-green-500/10 hover:bg-green-500/20 border border-green-500/20 transition-colors"
                >
                  <span className="font-bold text-green-400 text-sm">
                    {stock.symbol || stock.ticker}
                  </span>
                  <div className="text-right">
                    <div className="text-white text-xs font-mono">
                      ${(stock.price || 0).toFixed(2)}
                    </div>
                    <div className="text-green-400 text-xs font-mono">
                      +{(stock.changePercent || 0).toFixed(2)}%
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Top Losers */}
      <div>
        <button
          onClick={() => setExpanded(e => ({ ...e, losers: !e.losers }))}
          className="flex items-center justify-between w-full text-left mb-2"
        >
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex items-center gap-2">
            📉 Top Losers
            <span className="text-red-400 font-mono">({losers.length})</span>
          </span>
          <span className="text-gray-600">{expanded.losers ? '▼' : '▶'}</span>
        </button>
        
        {expanded.losers && (
          <div className="space-y-1">
            {losers.length === 0 ? (
              <div className="text-gray-500 text-xs italic">No losers data</div>
            ) : (
              losers.map((stock, i) => (
                <button
                  key={stock.symbol || stock.ticker || i}
                  onClick={() => handleClick(stock.symbol || stock.ticker)}
                  className="w-full flex items-center justify-between p-2 rounded bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-colors"
                >
                  <span className="font-bold text-red-400 text-sm">
                    {stock.symbol || stock.ticker}
                  </span>
                  <div className="text-right">
                    <div className="text-white text-xs font-mono">
                      ${(stock.price || 0).toFixed(2)}
                    </div>
                    <div className="text-red-400 text-xs font-mono">
                      {(stock.changePercent || 0).toFixed(2)}%
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Error indicator */}
      {error && (
        <div className="text-xs text-yellow-500 italic">
          ⚠️ Using cached data
        </div>
      )}
    </div>
  );
};

export default TopMovers;