/**
 * WhatsNext.jsx - Enhanced Roadmap Component
 * ==========================================
 * 
 * Features:
 *   - Current capabilities (what's done)
 *   - Upcoming features with ETAs
 *   - Provider upgrade options with COSTS
 *   - Important caveats (transparency)
 *   - Collapsible sections
 * 
 * Usage:
 *   import WhatsNext from './components/WhatsNext';
 *   <WhatsNext />
 *   <WhatsNext defaultExpanded={false} />
 */

import React, { useState, useEffect } from 'react';

// =============================================================================
// ROADMAP DATA (Hardcoded for demo, can be fetched from /api/v4/roadmap)
// =============================================================================

const ROADMAP_DATA = {
  version: "3.0.0",
  lastUpdated: "December 2024",
  
  // What's already built
  currentCapabilities: [
    {
      name: "Resilient Market Data Engine",
      description: "Live data with intelligent fallback. Dashboard never breaks even when APIs fail.",
      status: "done",
      icon: "🛡️",
      technical: "yfinance → LKG Cache → Anchored MME → Default MME",
    },
    {
      name: "Multi-Market Support",
      description: "US, India, Crypto, Forex, Commodities, ETFs - 18 markets from single API.",
      status: "done",
      icon: "🌍",
      markets: 18,
    },
    {
      name: "Technical Indicators",
      description: "RSI, MACD, Moving Averages, Bollinger Bands powered by pandas-ta.",
      status: "done",
      icon: "📈",
    },
    {
      name: "AI-Powered Signals",
      description: "Buy/Sell/Hold recommendations with natural language explanations.",
      status: "done",
      icon: "🤖",
    },
    {
      name: "Interactive Charts",
      description: "Candlestick, line, and area charts with zoom and pan.",
      status: "done",
      icon: "📊",
    },
    {
      name: "Watchlist Management",
      description: "Custom watchlists with real-time updates and mini-charts.",
      status: "done",
      icon: "⭐",
    },
  ],
  
  // Coming soon
  upcomingFeatures: [
    {
      name: "WebSocket Streaming",
      description: "Push updates to UI without polling. Lower latency, fewer API calls.",
      status: "next",
      eta: "Q1 2025",
      effort: "Medium",
      icon: "⚡",
    },
    {
      name: "Price Alerts",
      description: "Get notified when stocks hit key technical levels.",
      status: "planned",
      eta: "Q1 2025",
      effort: "Low",
      icon: "🔔",
    },
    {
      name: "Portfolio Tracking",
      description: "Track holdings, P&L, and performance over time.",
      status: "planned",
      eta: "Q1 2025",
      effort: "Medium",
      icon: "💼",
    },
    {
      name: "News Sentiment",
      description: "AI-powered news impact scoring for market events.",
      status: "planned",
      eta: "Q2 2025",
      effort: "High",
      icon: "📰",
    },
    {
      name: "Pattern Recognition",
      description: "Auto-detect chart patterns (Head & Shoulders, Double Top, etc.).",
      status: "planned",
      eta: "Q2 2025",
      effort: "High",
      icon: "🔍",
    },
    {
      name: "Broker Integration",
      description: "Connect to Zerodha, Alpaca for live trading.",
      status: "planned",
      eta: "Q2 2025",
      effort: "High",
      icon: "🔗",
    },
    {
      name: "Strategy Builder",
      description: "Visual strategy creation without code.",
      status: "planned",
      eta: "Q3 2025",
      effort: "High",
      icon: "🎯",
    },
  ],
  
  // API provider options with costs
  providerUpgrade: {
    title: "Global Live Data Coverage",
    description: "Upgrade from yfinance (free but unreliable) to professional market data.",
    currentProvider: {
      name: "yfinance",
      cost: "Free",
      pros: ["No cost", "Easy to use"],
      cons: ["Can be blocked anytime", "Rate limited", "US-focused"],
    },
    options: [
      {
        name: "Twelve Data",
        cost: "$29-79/month",
        coverage: "50+ exchanges, stocks + FX + crypto",
        url: "https://twelvedata.com",
        recommended: true,
        pros: ["Global coverage", "Unified API", "Built-in indicators"],
        cons: ["Cost varies by plan", "Some exchanges delayed"],
      },
      {
        name: "Polygon.io",
        cost: "$29-199/month",
        coverage: "US stocks (excellent), limited international",
        url: "https://polygon.io",
        recommended: false,
        pros: ["Excellent US data", "WebSocket included"],
        cons: ["US-focused", "Higher tiers expensive"],
      },
      {
        name: "Alpaca",
        cost: "$0-99/month",
        coverage: "US stocks + paper trading",
        url: "https://alpaca.markets",
        recommended: false,
        pros: ["Paper trading built-in", "Good for US"],
        cons: ["IEX only on free tier", "US only"],
      },
      {
        name: "EODHD",
        cost: "$20-80/month",
        coverage: "Historical + fundamentals, global",
        url: "https://eodhd.com",
        recommended: false,
        pros: ["Good historical data", "Affordable"],
        cons: ["Real-time costs extra", "Less polished"],
      },
    ],
  },
  
  // Important caveats for transparency
  caveats: [
    {
      type: "Data Source",
      icon: "⚠️",
      message: "yfinance is unofficial and may be rate-limited or blocked. Our LKG + MME fallback ensures graceful degradation.",
    },
    {
      type: "Simulation Notice",
      icon: "🎮",
      message: "When showing 'SIMULATED' data quality, prices are mathematically modeled (GBM) but not actual market data.",
    },
    {
      type: "Not Financial Advice",
      icon: "📋",
      message: "This platform is for educational and informational purposes only. Always consult a qualified financial advisor before making investment decisions.",
    },
    {
      type: "Demo Limitations",
      icon: "🔧",
      message: "For production deployment with multiple workers, you'll need Redis-based rate limiting instead of the in-process semaphore.",
    },
  ],
};


// =============================================================================
// SUB-COMPONENTS
// =============================================================================

const StatusBadge = ({ status }) => {
  const styles = {
    done: { bg: 'bg-green-100', text: 'text-green-800', label: '✓ Done' },
    next: { bg: 'bg-blue-100', text: 'text-blue-800', label: '🚀 Next Up' },
    planned: { bg: 'bg-gray-100', text: 'text-gray-600', label: '📋 Planned' },
  };
  const style = styles[status] || styles.planned;
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
};

const EffortBadge = ({ effort }) => {
  const colors = {
    Low: 'bg-green-50 text-green-700',
    Medium: 'bg-yellow-50 text-yellow-700',
    High: 'bg-red-50 text-red-700',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[effort] || colors.Medium}`}>
      {effort} effort
    </span>
  );
};

const CapabilityCard = ({ item }) => (
  <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
    <div className="flex items-start gap-3">
      <span className="text-2xl">{item.icon}</span>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-gray-800">{item.name}</h4>
          <StatusBadge status={item.status} />
        </div>
        <p className="text-sm text-gray-500 mt-1">{item.description}</p>
        {item.technical && (
          <p className="text-xs text-gray-400 mt-2 font-mono">{item.technical}</p>
        )}
      </div>
    </div>
  </div>
);

const UpcomingCard = ({ item }) => (
  <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-blue-400">
    <div className="flex items-start gap-3">
      <span className="text-2xl">{item.icon}</span>
      <div className="flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h4 className="font-semibold text-gray-800">{item.name}</h4>
          <StatusBadge status={item.status} />
          <EffortBadge effort={item.effort} />
        </div>
        <p className="text-sm text-gray-500 mt-1">{item.description}</p>
        <p className="text-xs text-blue-600 mt-2 font-medium">ETA: {item.eta}</p>
      </div>
    </div>
  </div>
);

const ProviderCard = ({ provider, isRecommended }) => (
  <div className={`bg-white rounded-lg p-4 border-2 ${isRecommended ? 'border-green-400 ring-2 ring-green-100' : 'border-gray-200'}`}>
    {isRecommended && (
      <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full mb-2 inline-block">
        ⭐ Recommended
      </span>
    )}
    <h4 className="font-bold text-gray-800">{provider.name}</h4>
    <p className="text-2xl font-bold text-blue-600 mt-1">{provider.cost}</p>
    <p className="text-sm text-gray-500 mt-2">{provider.coverage}</p>
    
    <div className="mt-3 space-y-2">
      <div>
        <span className="text-xs font-medium text-green-600">✓ Pros:</span>
        <ul className="text-xs text-gray-600 ml-2">
          {provider.pros.map((pro, i) => <li key={i}>• {pro}</li>)}
        </ul>
      </div>
      <div>
        <span className="text-xs font-medium text-red-600">✗ Cons:</span>
        <ul className="text-xs text-gray-600 ml-2">
          {provider.cons.map((con, i) => <li key={i}>• {con}</li>)}
        </ul>
      </div>
    </div>
    
    <a 
      href={provider.url} 
      target="_blank" 
      rel="noopener noreferrer"
      className="mt-3 inline-block text-sm text-blue-600 hover:underline"
    >
      Learn more →
    </a>
  </div>
);

const CaveatCard = ({ caveat }) => (
  <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
    <div className="flex items-start gap-2">
      <span className="text-lg">{caveat.icon}</span>
      <div>
        <h5 className="font-medium text-amber-800 text-sm">{caveat.type}</h5>
        <p className="text-xs text-amber-700 mt-1">{caveat.message}</p>
      </div>
    </div>
  </div>
);

const CollapsibleSection = ({ title, emoji, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div className="mb-6">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full text-left mb-3 hover:opacity-80"
      >
        <span className="text-xl">{emoji}</span>
        <h3 className="text-lg font-semibold text-gray-700">{title}</h3>
        <span className="text-gray-400 ml-auto">{isOpen ? '▼' : '▶'}</span>
      </button>
      {isOpen && children}
    </div>
  );
};


// =============================================================================
// MAIN COMPONENT
// =============================================================================

const WhatsNext = ({ defaultExpanded = true, showCosts = true }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [roadmap, setRoadmap] = useState(ROADMAP_DATA);
  
  // Optionally fetch from API
  useEffect(() => {
    // Uncomment to fetch from backend:
    // fetch('/api/v4/roadmap')
    //   .then(res => res.json())
    //   .then(data => setRoadmap(data))
    //   .catch(err => console.log('Using hardcoded roadmap'));
  }, []);
  
  return (
    <div className="bg-gradient-to-br from-slate-50 to-blue-50 rounded-2xl p-6 shadow-lg">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            🚀 What's Next
          </h2>
          <p className="text-gray-500 mt-1">
            Building the ultimate trading intelligence platform
          </p>
          <p className="text-xs text-gray-400 mt-1">
            v{roadmap.version} • Updated {roadmap.lastUpdated}
          </p>
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-white/50"
        >
          {isCollapsed ? '➕' : '➖'}
        </button>
      </div>
      
      {!isCollapsed && (
        <>
          {/* Current Capabilities */}
          <CollapsibleSection title="What's Already Built" emoji="✅" defaultOpen={defaultExpanded}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {roadmap.currentCapabilities.map((item, idx) => (
                <CapabilityCard key={idx} item={item} />
              ))}
            </div>
          </CollapsibleSection>
          
          {/* Upcoming Features */}
          <CollapsibleSection title="Coming Soon" emoji="⚡" defaultOpen={defaultExpanded}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {roadmap.upcomingFeatures.map((item, idx) => (
                <UpcomingCard key={idx} item={item} />
              ))}
            </div>
          </CollapsibleSection>
          
          {/* Provider Upgrade Options (with costs) */}
          {showCosts && (
            <CollapsibleSection title="Data Provider Upgrade Options" emoji="💰" defaultOpen={false}>
              <div className="bg-white rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-gray-800">Current: yfinance (Free)</h4>
                <p className="text-sm text-gray-500 mt-1">
                  Free but unofficial. Can be blocked anytime. Our fallback system ensures continuity.
                </p>
              </div>
              
              <p className="text-sm text-gray-600 mb-4">
                For production with guaranteed uptime and global coverage, consider these providers:
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {roadmap.providerUpgrade.options.map((provider, idx) => (
                  <ProviderCard 
                    key={idx} 
                    provider={provider} 
                    isRecommended={provider.recommended}
                  />
                ))}
              </div>
            </CollapsibleSection>
          )}
          
          {/* Important Caveats */}
          <CollapsibleSection title="Important Notes" emoji="⚠️" defaultOpen={false}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {roadmap.caveats.map((caveat, idx) => (
                <CaveatCard key={idx} caveat={caveat} />
              ))}
            </div>
          </CollapsibleSection>
          
          {/* Feedback CTA */}
          <div className="mt-6 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-4 text-white">
            <div className="flex items-center gap-3">
              <span className="text-2xl">💡</span>
              <div className="flex-1">
                <h4 className="font-semibold">Have a Feature Request?</h4>
                <p className="text-blue-100 text-sm mt-1">
                  We're building this platform for traders like you. Let us know what would help!
                </p>
              </div>
              <button className="bg-white text-blue-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors whitespace-nowrap">
                Submit Feedback
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default WhatsNext;

// Also export the data for use elsewhere
export { ROADMAP_DATA };