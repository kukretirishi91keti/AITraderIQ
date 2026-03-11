import React from 'react';
import { getSignalColor } from '../../utils/formatters';

const ScreenerModal = ({
  onClose,
  screenerCategory,
  setScreenerCategory,
  screenerCategories,
  screenerFilter,
  setScreenerFilter,
  screenerLoading,
  filteredScreenerData,
  onSymbolSelect,
}) => (
  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div
      className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[80vh] flex flex-col"
      onClick={e => e.stopPropagation()}
    >
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-cyan-400">📊 Stock Screener</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
      </div>

      <div className="p-4 border-b border-gray-700 flex gap-4 flex-wrap">
        <select
          value={screenerCategory}
          onChange={(e) => setScreenerCategory(e.target.value)}
          className="bg-gray-700 text-white px-3 py-1 rounded text-sm"
        >
          <option value="all">All Categories</option>
          {screenerCategories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <div className="flex gap-2">
          {['all', 'oversold', 'overbought', 'buy'].map(filter => (
            <button
              key={filter}
              onClick={() => setScreenerFilter(filter)}
              className={`px-3 py-1 rounded text-sm ${
                screenerFilter === filter ? 'bg-cyan-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              {filter === 'all' ? 'All' :
               filter === 'oversold' ? 'RSI < 30' :
               filter === 'overbought' ? 'RSI > 70' : 'Buy Signal'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {screenerLoading ? (
          <div className="text-center py-8 text-gray-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3"></div>
            <p>Loading screener data...</p>
          </div>
        ) : Object.keys(filteredScreenerData).length === 0 ? (
          <div className="text-center py-8 text-gray-400">No stocks match your filters</div>
        ) : (
          <div className="space-y-6">
            {Object.entries(filteredScreenerData).map(([category, stocks]) => {
              if (!Array.isArray(stocks) || stocks.length === 0) return null;

              return (
                <div key={category}>
                  <h3 className="text-cyan-400 font-medium mb-2">{category}</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                    {stocks.map(stock => {
                      const rsi = stock.rsi;
                      const rsiColor = rsi < 30 ? 'text-green-400' : rsi > 70 ? 'text-red-400' : 'text-yellow-400';

                      return (
                        <button
                          key={stock.symbol}
                          onClick={() => { onSymbolSelect(stock.symbol); onClose(); }}
                          className="p-3 bg-gray-700/50 rounded text-left hover:bg-gray-700 transition-colors border border-transparent hover:border-cyan-500/50"
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-cyan-400 font-bold text-sm">
                              {stock.symbol.replace('.NS', '').replace('.KS', '').replace('.AS', '')}
                            </span>
                            <span className="text-xs">{stock.flag}</span>
                          </div>
                          <div className="text-sm text-white">{stock.currency}{stock.price?.toFixed(2) || '-'}</div>
                          <div className="flex justify-between text-xs mt-1">
                            <span className={rsiColor}>RSI: {rsi?.toFixed(0) || '-'}</span>
                            <span className={getSignalColor(stock.signal)}>{stock.signal}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  </div>
);

export default ScreenerModal;
