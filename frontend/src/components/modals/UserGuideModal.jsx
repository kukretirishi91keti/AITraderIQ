import React from 'react';
import { KEYBOARD_SHORTCUTS } from '../../constants/appConfig';

const UserGuideModal = ({ onClose }) => (
  <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
    <div
      className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto"
      onClick={e => e.stopPropagation()}
    >
      <div className="sticky top-0 bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-cyan-400">📖 TraderAI Pro User Guide</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
      </div>

      <div className="p-4 space-y-6">
        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🌍 Markets</h3>
          <p className="text-gray-300 text-sm">
            Click any market flag to switch between 22 global markets. Each market displays prices
            in its native currency (USD, EUR, INR, JPY, etc.).
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">📊 Screener</h3>
          <p className="text-gray-300 text-sm">
            The screener scans stocks across categories. Filter by RSI conditions:
          </p>
          <ul className="text-gray-300 text-sm mt-2 space-y-1 list-disc list-inside">
            <li><span className="text-green-400">Oversold (RSI &lt; 30)</span> - Potential buy opportunities</li>
            <li><span className="text-red-400">Overbought (RSI &gt; 70)</span> - Potential sell signals</li>
            <li><span className="text-yellow-400">Neutral (30-70)</span> - No extreme conditions</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🤖 AI Assistant</h3>
          <p className="text-gray-300 text-sm">
            Ask questions about any stock. The AI considers your trading style and provides
            tailored advice. Try suggested prompts or type your own questions.
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">📈 Technical Indicators</h3>
          <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
            <li><strong>RSI (14)</strong> - Momentum oscillator (0-100)</li>
            <li><strong>SMA 20</strong> - 20-period Simple Moving Average</li>
            <li><strong>EMA 12</strong> - 12-period Exponential Moving Average</li>
            <li><strong>VWAP</strong> - Volume Weighted Average Price</li>
            <li><strong>ATR</strong> - Average True Range (volatility)</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">⭐ Watchlist & Alerts</h3>
          <p className="text-gray-300 text-sm">
            Click "+ Watchlist" to track stocks. Set price alerts with "Set Alert" -
            you'll be notified when conditions are met.
          </p>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">🎯 Trading Styles</h3>
          <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
            <li><strong>Day</strong> - Intraday focus, quick trades</li>
            <li><strong>Swing</strong> - Multi-day trends, support/resistance</li>
            <li><strong>Position</strong> - Long-term, fundamental analysis</li>
            <li><strong>Scalper</strong> - Micro-movements, rapid execution</li>
          </ul>
        </section>

        <section>
          <h3 className="text-lg font-semibold text-cyan-400 mb-2">⌨️ Keyboard Shortcuts</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {KEYBOARD_SHORTCUTS.map(s => (
              <div key={s.key} className="flex justify-between text-gray-300">
                <kbd className="px-2 py-1 bg-gray-700 rounded text-cyan-400">{s.key}</kbd>
                <span>{s.description}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="sticky bottom-0 bg-gray-800 p-4 border-t border-gray-700">
        <button
          onClick={onClose}
          className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
        >
          Got it!
        </button>
      </div>
    </div>
  </div>
);

export default UserGuideModal;
