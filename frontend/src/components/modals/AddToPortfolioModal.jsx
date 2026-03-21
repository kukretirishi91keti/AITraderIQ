import React from 'react';

const AddToPortfolioModal = ({
  onClose,
  selectedSymbol,
  quote,
  portfolioShares,
  setPortfolioShares,
  portfolioAvgPrice,
  setPortfolioAvgPrice,
  onAdd,
  isInPortfolio,
}) => (
  <div
    className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
    onClick={onClose}
  >
    <div className="bg-gray-800 rounded-lg max-w-md w-full" onClick={(e) => e.stopPropagation()}>
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-green-400">💰 Add to Portfolio</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">
          &times;
        </button>
      </div>
      <div className="p-4">
        <div className="mb-4">
          <p className="text-lg font-medium text-cyan-400 mb-2">{selectedSymbol}</p>
          {quote && <p className="text-gray-400">Current Price: ${quote.price?.toFixed(2)}</p>}
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Number of Shares</label>
            <input
              type="number"
              value={portfolioShares}
              onChange={(e) => setPortfolioShares(e.target.value)}
              placeholder="e.g., 10"
              className="w-full bg-gray-700 px-3 py-2 rounded text-white"
              min="0"
              step="any"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Average Price per Share ($)</label>
            <input
              type="number"
              value={portfolioAvgPrice}
              onChange={(e) => setPortfolioAvgPrice(e.target.value)}
              placeholder="e.g., 150.00"
              className="w-full bg-gray-700 px-3 py-2 rounded text-white"
              min="0"
              step="any"
            />
          </div>

          {portfolioShares && portfolioAvgPrice && (
            <div className="p-3 bg-gray-700/50 rounded">
              <p className="text-sm text-gray-400">
                Total Cost:{' '}
                <span className="text-white font-medium">
                  $
                  {(parseFloat(portfolioShares) * parseFloat(portfolioAvgPrice)).toLocaleString(
                    undefined,
                    { minimumFractionDigits: 2, maximumFractionDigits: 2 }
                  )}
                </span>
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-2 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onAdd}
            disabled={!portfolioShares || !portfolioAvgPrice}
            className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-medium"
          >
            {isInPortfolio ? 'Update Position' : 'Add to Portfolio'}
          </button>
        </div>
      </div>
    </div>
  </div>
);

export default AddToPortfolioModal;
