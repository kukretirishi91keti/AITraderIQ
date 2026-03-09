import React from 'react';

const ArchitectureDiagram = () => {
  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 p-8 min-h-screen flex items-center justify-center">
      <div className="w-full max-w-5xl">
        {/* Title */}
        <h1 className="text-3xl font-bold text-white text-center mb-2">TraderAI Pro</h1>
        <p className="text-cyan-400 text-center mb-8 text-lg">System Architecture</p>
        
        <svg viewBox="0 0 900 600" className="w-full h-auto">
          {/* Background grid pattern */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#334155" strokeWidth="0.5" opacity="0.3"/>
            </pattern>
            {/* Gradients */}
            <linearGradient id="dataGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0ea5e9"/>
              <stop offset="100%" stopColor="#0284c7"/>
            </linearGradient>
            <linearGradient id="backendGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8b5cf6"/>
              <stop offset="100%" stopColor="#7c3aed"/>
            </linearGradient>
            <linearGradient id="frontendGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#22c55e"/>
              <stop offset="100%" stopColor="#16a34a"/>
            </linearGradient>
            <linearGradient id="aiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f59e0b"/>
              <stop offset="100%" stopColor="#d97706"/>
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          
          <rect width="900" height="600" fill="url(#grid)"/>
          
          {/* Section Labels */}
          <text x="100" y="50" fill="#94a3b8" fontSize="14" fontWeight="bold">DATA SOURCES</text>
          <text x="380" y="50" fill="#94a3b8" fontSize="14" fontWeight="bold">BACKEND SERVICES</text>
          <text x="700" y="50" fill="#94a3b8" fontSize="14" fontWeight="bold">FRONTEND</text>
          
          {/* Data Sources Column */}
          <g transform="translate(40, 80)">
            {/* Yahoo Finance */}
            <rect x="0" y="0" width="160" height="70" rx="8" fill="url(#dataGrad)" filter="url(#glow)"/>
            <text x="80" y="30" fill="white" fontSize="13" fontWeight="bold" textAnchor="middle">Yahoo Finance</text>
            <text x="80" y="50" fill="#bae6fd" fontSize="11" textAnchor="middle">fast_info API</text>
            
            {/* Reddit */}
            <rect x="0" y="90" width="160" height="70" rx="8" fill="url(#dataGrad)" filter="url(#glow)"/>
            <text x="80" y="120" fill="white" fontSize="13" fontWeight="bold" textAnchor="middle">Reddit API</text>
            <text x="80" y="140" fill="#bae6fd" fontSize="11" textAnchor="middle">r/wallstreetbets</text>
            
            {/* StockTwits */}
            <rect x="0" y="180" width="160" height="70" rx="8" fill="url(#dataGrad)" filter="url(#glow)"/>
            <text x="80" y="210" fill="white" fontSize="13" fontWeight="bold" textAnchor="middle">StockTwits</text>
            <text x="80" y="230" fill="#bae6fd" fontSize="11" textAnchor="middle">Sentiment Stream</text>
            
            {/* News APIs */}
            <rect x="0" y="270" width="160" height="70" rx="8" fill="url(#dataGrad)" filter="url(#glow)"/>
            <text x="80" y="300" fill="white" fontSize="13" fontWeight="bold" textAnchor="middle">News APIs</text>
            <text x="80" y="320" fill="#bae6fd" fontSize="11" textAnchor="middle">Market Headlines</text>
          </g>
          
          {/* Connection Lines - Data to Backend */}
          <g stroke="#0ea5e9" strokeWidth="2" opacity="0.6">
            <path d="M200 115 L300 200" fill="none" markerEnd="url(#arrowBlue)"/>
            <path d="M200 205 L300 220" fill="none"/>
            <path d="M200 295 L300 240" fill="none"/>
            <path d="M200 385 L300 260" fill="none"/>
          </g>
          
          {/* Backend Column */}
          <g transform="translate(300, 100)">
            {/* Main Backend Box */}
            <rect x="0" y="0" width="240" height="380" rx="12" fill="#1e293b" stroke="#475569" strokeWidth="2"/>
            <text x="120" y="30" fill="white" fontSize="15" fontWeight="bold" textAnchor="middle">FastAPI Backend</text>
            <text x="120" y="50" fill="#a78bfa" fontSize="11" textAnchor="middle">Python 3.11 • Uvicorn</text>
            
            {/* Services inside backend */}
            {/* Market Data Service */}
            <rect x="15" y="70" width="210" height="55" rx="6" fill="url(#backendGrad)" opacity="0.9"/>
            <text x="120" y="95" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">Market Data Service</text>
            <text x="120" y="112" fill="#c4b5fd" fontSize="10" textAnchor="middle">Singleflight • Cache • Circuit Breaker</text>
            
            {/* RSI Engine */}
            <rect x="15" y="135" width="210" height="55" rx="6" fill="url(#backendGrad)" opacity="0.9"/>
            <text x="120" y="160" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">Technical Analysis Engine</text>
            <text x="120" y="177" fill="#c4b5fd" fontSize="10" textAnchor="middle">RSI • MACD • SMA • Bollinger</text>
            
            {/* Sentiment Service */}
            <rect x="15" y="200" width="210" height="55" rx="6" fill="url(#backendGrad)" opacity="0.9"/>
            <text x="120" y="225" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">Sentiment Aggregator</text>
            <text x="120" y="242" fill="#c4b5fd" fontSize="10" textAnchor="middle">Reddit • StockTwits • News</text>
            
            {/* Screener */}
            <rect x="15" y="265" width="210" height="55" rx="6" fill="url(#backendGrad)" opacity="0.9"/>
            <text x="120" y="290" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">Static Universe Screener</text>
            <text x="120" y="307" fill="#c4b5fd" fontSize="10" textAnchor="middle">22 Markets • 200+ Symbols</text>
            
            {/* GenAI Service */}
            <rect x="15" y="330" width="210" height="45" rx="6" fill="url(#aiGrad)" opacity="0.9"/>
            <text x="120" y="355" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">Groq / LLaMA AI</text>
            <text x="120" y="368" fill="#fef3c7" fontSize="10" textAnchor="middle">Contextual Trading Signals</text>
          </g>
          
          {/* Connection Lines - Backend to Frontend */}
          <g stroke="#22c55e" strokeWidth="2" opacity="0.6">
            <path d="M540 290 L620 180" fill="none"/>
            <path d="M540 290 L620 290" fill="none"/>
            <path d="M540 290 L620 400" fill="none"/>
          </g>
          
          {/* Frontend Column */}
          <g transform="translate(620, 80)">
            {/* React Dashboard */}
            <rect x="0" y="0" width="240" height="140" rx="8" fill="url(#frontendGrad)" filter="url(#glow)"/>
            <text x="120" y="30" fill="white" fontSize="14" fontWeight="bold" textAnchor="middle">React 18 Dashboard</text>
            <text x="120" y="50" fill="#bbf7d0" fontSize="11" textAnchor="middle">Vite • TailwindCSS • Recharts</text>
            <line x1="20" y1="65" x2="220" y2="65" stroke="#16a34a" strokeWidth="1"/>
            <text x="30" y="85" fill="#dcfce7" fontSize="10">• Multi-Market Charts</text>
            <text x="30" y="100" fill="#dcfce7" fontSize="10">• Real-time Watchlist</text>
            <text x="30" y="115" fill="#dcfce7" fontSize="10">• Portfolio Tracker</text>
            <text x="30" y="130" fill="#dcfce7" fontSize="10">• Keyboard Shortcuts</text>
            
            {/* AI Assistant */}
            <rect x="0" y="160" width="240" height="100" rx="8" fill="url(#aiGrad)" filter="url(#glow)"/>
            <text x="120" y="190" fill="white" fontSize="14" fontWeight="bold" textAnchor="middle">AI Trading Assistant</text>
            <text x="120" y="210" fill="#fef3c7" fontSize="11" textAnchor="middle">Natural Language Queries</text>
            <line x1="20" y1="225" x2="220" y2="225" stroke="#b45309" strokeWidth="1"/>
            <text x="30" y="245" fill="#fef9c3" fontSize="10">• Explainable Signals</text>
            
            {/* Stock Screener UI */}
            <rect x="0" y="280" width="240" height="100" rx="8" fill="url(#frontendGrad)" filter="url(#glow)"/>
            <text x="120" y="310" fill="white" fontSize="14" fontWeight="bold" textAnchor="middle">Stock Screener</text>
            <text x="120" y="330" fill="#bbf7d0" fontSize="11" textAnchor="middle">RSI Filters • Buy/Sell Tags</text>
            <line x1="20" y1="345" x2="220" y2="345" stroke="#16a34a" strokeWidth="1"/>
            <text x="30" y="365" fill="#dcfce7" fontSize="10">• Oversold (RSI {'<'} 30)</text>
            
            {/* User */}
            <rect x="60" y="400" width="120" height="50" rx="25" fill="#475569" stroke="#22c55e" strokeWidth="2"/>
            <text x="120" y="430" fill="white" fontSize="12" fontWeight="bold" textAnchor="middle">👤 Day Trader</text>
          </g>
          
          {/* Arrow Markers */}
          <defs>
            <marker id="arrowBlue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#0ea5e9"/>
            </marker>
            <marker id="arrowGreen" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <path d="M0,0 L0,6 L9,3 z" fill="#22c55e"/>
            </marker>
          </defs>
          
          {/* Bottom Stats Bar */}
          <g transform="translate(0, 520)">
            <rect x="40" y="0" width="820" height="60" rx="8" fill="#1e293b" stroke="#334155" strokeWidth="1"/>
            
            <text x="120" y="25" fill="#94a3b8" fontSize="11" textAnchor="middle">MARKETS</text>
            <text x="120" y="45" fill="#22c55e" fontSize="18" fontWeight="bold" textAnchor="middle">22</text>
            
            <line x1="220" y1="10" x2="220" y2="50" stroke="#334155" strokeWidth="1"/>
            
            <text x="320" y="25" fill="#94a3b8" fontSize="11" textAnchor="middle">SYMBOLS</text>
            <text x="320" y="45" fill="#22c55e" fontSize="18" fontWeight="bold" textAnchor="middle">200+</text>
            
            <line x1="420" y1="10" x2="420" y2="50" stroke="#334155" strokeWidth="1"/>
            
            <text x="520" y="25" fill="#94a3b8" fontSize="11" textAnchor="middle">CYPRESS TESTS</text>
            <text x="520" y="45" fill="#22c55e" fontSize="18" fontWeight="bold" textAnchor="middle">125</text>
            
            <line x1="620" y1="10" x2="620" y2="50" stroke="#334155" strokeWidth="1"/>
            
            <text x="720" y="25" fill="#94a3b8" fontSize="11" textAnchor="middle">PASS RATE</text>
            <text x="720" y="45" fill="#22c55e" fontSize="18" fontWeight="bold" textAnchor="middle">100%</text>
            
            <line x1="820" y1="10" x2="820" y2="50" stroke="#334155" strokeWidth="1"/>
          </g>
        </svg>
        
        {/* Footer */}
        <p className="text-slate-500 text-center mt-6 text-sm">
          TalentSprint AIML Program • Stage 2 Final Project • January 2026
                  </p>
      </div>
    </div>
  );
};

export default ArchitectureDiagram;