import React from 'react';

const WhatsNextModal = ({ onClose }) => {
  const upcomingFeatures = [
    { name: 'Real-time WebSocket Streaming', description: 'Live price updates without polling', eta: 'Q1 2026', priority: 'High', icon: '⚡' },
    { name: 'Advanced Charting', description: 'TradingView-style drawing tools & indicators', eta: 'Q1 2026', priority: 'High', icon: '📈' },
    { name: 'Pattern Recognition AI', description: 'Automatic detection of head & shoulders, double tops, etc.', eta: 'Q2 2026', priority: 'Medium', icon: '🔍' },
    { name: 'Portfolio Analytics', description: 'Track P&L, risk metrics, and performance', eta: 'Q1 2026', priority: 'High', icon: '💼' },
    { name: 'Broker Integration', description: 'One-click trading with Zerodha, Alpaca, IBKR', eta: 'Q2 2026', priority: 'High', icon: '🔗' },
    { name: 'Mobile App', description: 'React Native app for iOS and Android', eta: 'Q3 2026', priority: 'Medium', icon: '📱' },
  ];

  const recentUpdates = [
    { version: '5.8.0', date: 'Dec 2025', changes: 'Fixed chart timestamps, fundamentals, screener data' },
    { version: '5.7.0', date: 'Dec 2025', changes: 'Keyboard shortcuts, Watchlist editing, Roadmap modal' },
    { version: '5.5.0', date: 'Dec 2025', changes: 'Demo mode, circuit breaker, sentiment APIs' },
  ];

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-gray-800 rounded-lg max-w-3xl w-full max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-cyan-400">🚀 What&apos;s Next</h2>
            <p className="text-sm text-gray-400">TraderAI Pro Roadmap</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">&times;</button>
        </div>

        <div className="p-4 space-y-6">
          <section>
            <h3 className="text-lg font-semibold text-green-400 mb-3">✅ Recent Updates</h3>
            <div className="space-y-2">
              {recentUpdates.map((update, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-gray-700/50 rounded-lg">
                  <span className="px-2 py-0.5 bg-green-600/30 text-green-400 text-xs rounded font-mono">
                    v{update.version}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-white">{update.changes}</p>
                    <p className="text-xs text-gray-500">{update.date}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-lg font-semibold text-cyan-400 mb-3">🔮 Coming Soon</h3>
            <div className="grid gap-3">
              {upcomingFeatures.map((feature, i) => (
                <div key={i} className="p-4 bg-gray-700/50 rounded-lg border border-gray-600 hover:border-cyan-500/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{feature.icon}</span>
                      <div>
                        <h4 className="font-medium text-white">{feature.name}</h4>
                        <p className="text-sm text-gray-400">{feature.description}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        feature.priority === 'High' ? 'bg-red-600/30 text-red-400' :
                        feature.priority === 'Medium' ? 'bg-yellow-600/30 text-yellow-400' :
                        'bg-gray-600/30 text-gray-400'
                      }`}>
                        {feature.priority}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">ETA: {feature.eta}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="p-4 bg-cyan-600/10 rounded-lg border border-cyan-600/30">
            <h3 className="text-lg font-semibold text-cyan-400 mb-2">💡 Have a Feature Request?</h3>
            <p className="text-sm text-gray-300">
              We&apos;re building TraderAI Pro with your feedback. Connect with us on kukretirishi91@gmail.com.
            </p>
          </section>
        </div>

        <div className="sticky bottom-0 bg-gray-800 p-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default WhatsNextModal;
