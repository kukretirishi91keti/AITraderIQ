/**
 * UserGuide.jsx
 *
 * A comprehensive help modal that explains all features of TraderAI Pro.
 * Includes keyboard shortcuts, feature explanations, and tips.
 *
 * Usage: <UserGuide isOpen={showGuide} onClose={() => setShowGuide(false)} />
 */

import React, { useState } from 'react';

const UserGuide = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('overview');

  if (!isOpen) return null;

  const tabs = [
    { id: 'overview', label: '📖 Overview', icon: '📖' },
    { id: 'signals', label: '📊 Signals', icon: '📊' },
    { id: 'indicators', label: '📈 Indicators', icon: '📈' },
    { id: 'sentiment', label: '💬 Sentiment', icon: '💬' },
    { id: 'shortcuts', label: '⌨️ Shortcuts', icon: '⌨️' },
    { id: 'faq', label: '❓ FAQ', icon: '❓' },
  ];

  const content = {
    overview: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Welcome to TraderAI Pro</h3>
        <p className="text-gray-300 text-sm leading-relaxed">
          TraderAI Pro is an AI-powered decision support dashboard designed to help day traders
          process market data, sentiment signals, and technical indicators into actionable insights.
        </p>

        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="bg-gray-700/30 p-3 rounded">
            <div className="text-cyan-400 font-medium mb-1">🌍 22 Markets</div>
            <div className="text-xs text-gray-400">US, India, Europe, Asia, Crypto & more</div>
          </div>
          <div className="bg-gray-700/30 p-3 rounded">
            <div className="text-green-400 font-medium mb-1">📊 Real-Time Signals</div>
            <div className="text-xs text-gray-400">BUY/SELL/HOLD with confidence scores</div>
          </div>
          <div className="bg-gray-700/30 p-3 rounded">
            <div className="text-purple-400 font-medium mb-1">🤖 AI Assistant</div>
            <div className="text-xs text-gray-400">Ask questions, get explanations</div>
          </div>
          <div className="bg-gray-700/30 p-3 rounded">
            <div className="text-yellow-400 font-medium mb-1">⚠️ Risk Scores</div>
            <div className="text-xs text-gray-400">LOW/MEDIUM/HIGH assessment</div>
          </div>
        </div>

        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
          <div className="text-yellow-400 text-sm font-medium">⚠️ Disclaimer</div>
          <div className="text-xs text-gray-400 mt-1">
            TraderAI Pro is for educational purposes only. All signals are simulated and do not
            constitute financial advice. Always consult a qualified financial advisor.
          </div>
        </div>
      </div>
    ),

    signals: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Understanding Signals</h3>

        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 bg-green-500/10 border border-green-500/30 rounded">
            <span className="text-2xl">🟢</span>
            <div>
              <div className="text-green-400 font-medium">BUY / STRONG_BUY</div>
              <div className="text-xs text-gray-400 mt-1">
                Technical indicators suggest bullish momentum. RSI may be oversold, MACD showing
                positive crossover, sentiment favorable.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
            <span className="text-2xl">🟡</span>
            <div>
              <div className="text-yellow-400 font-medium">HOLD / BUY_THE_DIP</div>
              <div className="text-xs text-gray-400 mt-1">
                Mixed signals. Consider waiting for clearer direction or accumulating on pullbacks
                if fundamentally bullish.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 bg-red-500/10 border border-red-500/30 rounded">
            <span className="text-2xl">🔴</span>
            <div>
              <div className="text-red-400 font-medium">SELL / STRONG_SELL</div>
              <div className="text-xs text-gray-400 mt-1">
                Technical indicators suggest bearish momentum. RSI may be overbought, MACD showing
                negative crossover, sentiment unfavorable.
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <div className="text-white font-medium mb-2">Confidence Score</div>
          <div className="text-xs text-gray-400">
            Ranges from 0-100%. Higher scores indicate stronger alignment between technical
            indicators and sentiment. Scores below 50% suggest conflicting signals.
          </div>
        </div>
      </div>
    ),

    indicators: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Technical Indicators</h3>

        <div className="space-y-4">
          <div className="border-b border-gray-700 pb-4">
            <div className="text-cyan-400 font-medium mb-2">📊 RSI (Relative Strength Index)</div>
            <div className="text-xs text-gray-400 space-y-1">
              <p>Momentum oscillator measuring speed of price changes (0-100).</p>
              <div className="flex gap-4 mt-2">
                <span className="text-green-400">• Below 30: Oversold (Buy signal)</span>
                <span className="text-red-400">• Above 70: Overbought (Sell signal)</span>
              </div>
            </div>
          </div>

          <div className="border-b border-gray-700 pb-4">
            <div className="text-purple-400 font-medium mb-2">
              📈 MACD (Moving Average Convergence Divergence)
            </div>
            <div className="text-xs text-gray-400 space-y-1">
              <p>Trend-following momentum indicator showing relationship between two EMAs.</p>
              <div className="flex gap-4 mt-2">
                <span className="text-green-400">• Positive: Bullish momentum</span>
                <span className="text-red-400">• Negative: Bearish momentum</span>
              </div>
            </div>
          </div>

          <div className="pb-4">
            <div className="text-yellow-400 font-medium mb-2">📉 Bollinger Bands (20,2)</div>
            <div className="text-xs text-gray-400 space-y-1">
              <p>Volatility bands placed above and below a moving average.</p>
              <div className="mt-2 space-y-1">
                <p>
                  <span className="text-white">Upper Band:</span> Potential resistance / overbought
                </p>
                <p>
                  <span className="text-white">Middle (SMA):</span> 20-period simple moving average
                </p>
                <p>
                  <span className="text-white">Lower Band:</span> Potential support / oversold
                </p>
                <p>
                  <span className="text-orange-400">🔔 Squeeze Alert:</span> Low bandwidth indicates
                  consolidation, breakout imminent
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    ),

    sentiment: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Sentiment Analysis</h3>

        <div className="space-y-4">
          <div className="bg-gray-700/30 p-4 rounded">
            <div className="text-blue-400 font-medium mb-2">📰 News Sentiment</div>
            <div className="text-xs text-gray-400">
              <p>Headlines are analyzed and classified as:</p>
              <div className="flex gap-3 mt-2">
                <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded">BULLISH</span>
                <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded">NEUTRAL</span>
                <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded">BEARISH</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-700/30 p-4 rounded">
            <div className="text-orange-400 font-medium mb-2">🤖 Reddit Sentiment</div>
            <div className="text-xs text-gray-400">
              <p>Aggregated from r/wallstreetbets, r/stocks, r/investing:</p>
              <div className="mt-2 space-y-1">
                <p>
                  <span className="text-white">Mentions:</span> Total ticker mentions in 24h
                </p>
                <p>
                  <span className="text-white">Trend:</span> Change vs previous period
                </p>
                <p>
                  <span className="text-white">Sentiment Bar:</span> Bullish vs Bearish ratio
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded">
            <div className="text-purple-400 text-sm font-medium">🔥 HOT Badge</div>
            <div className="text-xs text-gray-400 mt-1">
              Appears when a stock is trending with high mention volume and significant sentiment
              movement. Use caution — high attention can mean volatility.
            </div>
          </div>
        </div>
      </div>
    ),

    shortcuts: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Keyboard Shortcuts</h3>

        <div className="space-y-2">
          {[
            { keys: ['/', 'Ctrl+K'], action: 'Focus search bar' },
            { keys: ['1-7'], action: 'Switch timeframe (1M, 5M, 15M, 1H, 1D, 1W)' },
            { keys: ['A'], action: 'Open Alerts modal' },
            { keys: ['S'], action: 'Open Screener' },
            { keys: ['?'], action: 'Open this Help guide' },
            { keys: ['Esc'], action: 'Close modals' },
            { keys: ['←', '→'], action: 'Navigate markets' },
            { keys: ['↑', '↓'], action: 'Navigate stock list' },
            { keys: ['Enter'], action: 'Select highlighted stock' },
          ].map(({ keys, action }) => (
            <div
              key={action}
              className="flex items-center justify-between p-2 bg-gray-700/30 rounded"
            >
              <span className="text-sm text-gray-300">{action}</span>
              <div className="flex gap-1">
                {keys.map((key) => (
                  <kbd
                    key={key}
                    className="px-2 py-1 bg-gray-800 border border-gray-600 rounded text-xs text-gray-300 font-mono"
                  >
                    {key}
                  </kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    ),

    faq: (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-white">Frequently Asked Questions</h3>

        <div className="space-y-3">
          {[
            {
              q: "Why does it say 'SIMULATED' on some data?",
              a: 'Financial summary data (P/E, Market Cap, etc.) is simulated for academic demonstration. Real integration would require SEC/Bloomberg API access.',
            },
            {
              q: 'How often does data refresh?',
              a: 'Price data refreshes every 60 seconds. News and Reddit sentiment update every 5 minutes. Technical indicators recalculate on each price update.',
            },
            {
              q: "Why don't I see real-time prices?",
              a: 'We use Yahoo Finance public API which provides near-real-time data (15-20 min delay for some markets). For true real-time, paid data feeds are required.',
            },
            {
              q: 'Should I trade based on these signals?',
              a: 'No! TraderAI Pro is for educational purposes only. Always do your own research and consult a financial advisor before making investment decisions.',
            },
            {
              q: 'Why are some markets showing different stocks than expected?',
              a: "We maintain a 'Static Universe' of highly liquid stocks per market to ensure reliable data. The full market isn't scanned to avoid rate limits.",
            },
            {
              q: 'How is the AI Assistant different from ChatGPT?',
              a: 'Our AI is context-aware — it knows the current stock, indicators, and sentiment. It provides trading-specific insights rather than general information.',
            },
          ].map(({ q, a }) => (
            <details key={q} className="bg-gray-700/30 rounded group">
              <summary className="p-3 cursor-pointer text-sm font-medium text-white hover:bg-gray-700/50 rounded">
                {q}
              </summary>
              <div className="px-3 pb-3 text-xs text-gray-400">{a}</div>
            </details>
          ))}
        </div>
      </div>
    ),
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-gray-800 border border-gray-700 rounded-xl w-full max-w-3xl max-h-[85vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-2xl">📚</span>
            <h2 className="text-xl font-bold text-white">User Guide</h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-700 rounded-lg transition-colors">
            <span className="text-gray-400 text-xl">✕</span>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-500/10'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">{content[activeTab]}</div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-800/50 flex justify-between items-center">
          <span className="text-xs text-gray-500">TraderAI Pro v4.6 • Educational Use Only</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 transition-colors text-sm font-medium"
          >
            Got it!
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserGuide;
