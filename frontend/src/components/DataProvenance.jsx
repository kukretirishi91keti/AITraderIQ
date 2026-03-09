/**
 * DataProvenance.jsx
 * 
 * A footer component that displays data source attribution.
 * Crucial for academic submission to show transparency.
 * 
 * Usage: <DataProvenance />
 */

import React, { useState } from 'react';

const DataProvenance = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  const sources = [
    {
      type: 'Stock Prices',
      source: 'Yahoo Finance (yfinance)',
      status: 'live',
      icon: '📈',
      note: 'Near real-time via fast_info API'
    },
    {
      type: 'News Headlines',
      source: 'News APIs',
      status: 'live',
      icon: '📰',
      note: 'Sentiment classified in real-time'
    },
    {
      type: 'Social Sentiment',
      source: 'Reddit API',
      status: 'live',
      icon: '🤖',
      note: 'r/wallstreetbets, r/stocks aggregation'
    },
    {
      type: 'Financial Metrics',
      source: 'Simulated/Derived',
      status: 'simulated',
      icon: '💰',
      note: 'Demo mode - real requires SEC/Bloomberg'
    },
    {
      type: 'Technical Indicators',
      source: 'Calculated',
      status: 'live',
      icon: '📊',
      note: 'RSI, MACD, Bollinger computed locally'
    },
    {
      type: 'AI Analysis',
      source: 'Groq LLM',
      status: 'live',
      icon: '🧠',
      note: 'Context-aware financial reasoning'
    }
  ];

  const statusColors = {
    live: 'bg-green-500/20 text-green-400',
    simulated: 'bg-yellow-500/20 text-yellow-400',
    cached: 'bg-blue-500/20 text-blue-400'
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      {/* Expandable Panel */}
      {isExpanded && (
        <div className="bg-gray-900/95 backdrop-blur border-t border-gray-700 p-4">
          <div className="max-w-6xl mx-auto">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
              <span>🔍</span> Data Sources & Attribution
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {sources.map(({ type, source, status, icon, note }) => (
                <div key={type} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
                  <div className="flex items-center gap-2 mb-2">
                    <span>{icon}</span>
                    <span className="text-xs font-medium text-white">{type}</span>
                  </div>
                  <div className="text-[10px] text-gray-400 mb-2">{source}</div>
                  <div className={`text-[10px] px-2 py-0.5 rounded inline-block ${statusColors[status]}`}>
                    {status.toUpperCase()}
                  </div>
                  <div className="text-[9px] text-gray-500 mt-2">{note}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded text-xs text-yellow-400/80">
              ⚠️ <strong>Academic Demonstration:</strong> This dashboard is for educational purposes only. 
              Financial data may be simulated or delayed. Do not use for actual trading decisions.
            </div>
          </div>
        </div>
      )}

      {/* Collapsed Footer Bar */}
      <div 
        className="bg-gray-900/95 backdrop-blur border-t border-gray-700 px-4 py-2 cursor-pointer hover:bg-gray-800/95 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="max-w-6xl mx-auto flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <span className="text-gray-500">
              TraderAI Pro v4.6 • {isExpanded ? '▼' : '▲'} Data Sources
            </span>
            <div className="hidden sm:flex items-center gap-2">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-gray-400">Live</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                <span className="text-gray-400">Simulated</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-gray-500">
            <span>📈 Yahoo Finance</span>
            <span className="hidden md:inline">📰 News APIs</span>
            <span className="hidden md:inline">🤖 Reddit</span>
            <span className="hidden lg:inline">🧠 Groq LLM</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataProvenance;