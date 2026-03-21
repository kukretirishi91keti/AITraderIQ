import React, { useState } from 'react';

const WatchlistEditModal = ({
  onClose,
  watchlist,
  setWatchlist,
  onSelectSymbol,
  setAlerts,
  currentSymbol,
}) => {
  const [newSymbol, setNewSymbol] = useState('');
  const [draggedIndex, setDraggedIndex] = useState(null);

  const handleAdd = () => {
    const symbol = newSymbol.trim().toUpperCase();
    if (symbol && !watchlist.includes(symbol)) {
      setWatchlist((prev) => [...prev, symbol]);
      setNewSymbol('');
    }
  };

  const handleRemove = (symbol) => {
    setWatchlist((prev) => prev.filter((s) => s !== symbol));
  };

  const handleAddAlert = (symbol) => {
    setAlerts((prev) => [...prev, { symbol, condition: 'above', price: 0 }]);
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newWatchlist = [...watchlist];
    const draggedItem = newWatchlist[draggedIndex];
    newWatchlist.splice(draggedIndex, 1);
    newWatchlist.splice(index, 0, draggedItem);

    setWatchlist(newWatchlist);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg max-w-md w-full max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-yellow-400">⭐ Edit Watchlist</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
            &times;
          </button>
        </div>

        <div className="p-4 border-b border-gray-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="Add symbol (e.g., AAPL)"
              className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
            <button
              onClick={handleAdd}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
            >
              Add
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">Drag items to reorder • Click symbol to view</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {watchlist.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Your watchlist is empty</p>
          ) : (
            watchlist.map((symbol, index) => (
              <div
                key={symbol}
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                className={`flex items-center justify-between p-3 bg-gray-700/50 rounded-lg cursor-move hover:bg-gray-700 transition-colors ${
                  draggedIndex === index ? 'opacity-50 border-2 border-cyan-500' : ''
                } ${symbol === currentSymbol ? 'border border-cyan-500' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 cursor-grab">⋮⋮</span>
                  <button
                    onClick={() => {
                      onSelectSymbol(symbol);
                      onClose();
                    }}
                    className="text-cyan-400 font-medium hover:underline"
                  >
                    {symbol}
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleAddAlert(symbol)}
                    className="px-2 py-1 text-xs bg-orange-600/30 text-orange-400 rounded hover:bg-orange-600/50"
                    title="Add alert"
                  >
                    🔔
                  </button>
                  <button
                    onClick={() => handleRemove(symbol)}
                    className="px-2 py-1 text-xs bg-red-600/30 text-red-400 rounded hover:bg-red-600/50"
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-gray-700 flex gap-2">
          <button
            onClick={() => setWatchlist([])}
            className="flex-1 py-2 bg-red-600/30 hover:bg-red-600/50 text-red-400 rounded text-sm font-medium"
          >
            Clear All
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default WatchlistEditModal;
