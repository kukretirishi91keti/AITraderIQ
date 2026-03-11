import React from 'react';

const PortfolioModal = ({ onClose, portfolio, quote, onSymbolSelect, onRemove }) => (
  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div
      className="bg-gray-800 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-hidden"
      onClick={e => e.stopPropagation()}
    >
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-green-400">💰 Portfolio</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
      </div>
      <div className="p-4 overflow-y-auto max-h-[60vh]">
        {portfolio.length === 0 ? (
          <p className="text-gray-400 text-center py-8">Your portfolio is empty. Add stocks using the &quot;+ Portfolio&quot; button.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-gray-400 text-sm border-b border-gray-700">
                <th className="text-left py-2">Symbol</th>
                <th className="text-right py-2">Shares</th>
                <th className="text-right py-2">Avg Price</th>
                <th className="text-right py-2">Current</th>
                <th className="text-right py-2">Value</th>
                <th className="text-right py-2">P&L</th>
                <th className="text-right py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map((pos, i) => {
                const currentPrice = quote?.symbol === pos.symbol ? quote.price : pos.avgPrice * (1 + (Math.random() - 0.5) * 0.1);
                const value = pos.shares * currentPrice;
                const cost = pos.shares * pos.avgPrice;
                const pnl = value - cost;
                const pnlPercent = ((currentPrice / pos.avgPrice) - 1) * 100;

                return (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-3">
                      <button
                        onClick={() => { onSymbolSelect(pos.symbol); onClose(); }}
                        className="text-cyan-400 font-medium hover:underline"
                      >
                        {pos.symbol}
                      </button>
                    </td>
                    <td className="py-3 text-right">{pos.shares}</td>
                    <td className="py-3 text-right">${pos.avgPrice.toFixed(2)}</td>
                    <td className="py-3 text-right">${currentPrice.toFixed(2)}</td>
                    <td className="py-3 text-right">${value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td className={`py-3 text-right font-medium ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)} ({pnlPercent >= 0 ? '+' : ''}{pnlPercent.toFixed(1)}%)
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => onRemove(pos.symbol)}
                        className="text-red-400 hover:text-red-300 text-sm px-2 py-1 hover:bg-red-900/30 rounded"
                      >
                        ✕ Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="font-bold border-t border-gray-600">
                <td className="py-3">Total</td>
                <td></td><td></td><td></td>
                <td className="py-3 text-right text-green-400">
                  ${portfolio.reduce((sum, p) => sum + p.shares * p.avgPrice, 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
                <td></td><td></td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>
      <div className="p-4 border-t border-gray-700 flex justify-between items-center">
        <span className="text-gray-400 text-sm">{portfolio.length} position{portfolio.length !== 1 ? 's' : ''}</span>
        <button onClick={onClose} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">Close</button>
      </div>
    </div>
  </div>
);

export default PortfolioModal;
