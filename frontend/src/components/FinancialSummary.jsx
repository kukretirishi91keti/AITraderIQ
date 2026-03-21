/**
 * Financial Summary Component v4.9
 * ================================
 * Location: frontend/src/components/FinancialSummary.jsx
 * 
 * Displays company financial data including:
 * - Key metrics (Market Cap, P/E, Revenue)
 * - AI-generated summary
 * - Data provenance indicator
 */

import React, { useState, useEffect } from 'react';
import { Building2, TrendingUp, DollarSign, PieChart, AlertCircle, Loader2, RefreshCw } from 'lucide-react';

// API Configuration
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Fetch company financials from API
 */
async function fetchFinancials(symbol) {
  try {
    const response = await fetch(`${API_BASE}/api/v4/financials/${symbol}`);
    if (!response.ok) throw new Error('Failed to fetch financials');
    return await response.json();
  } catch (error) {
    console.error('Financials fetch error:', error);
    return null;
  }
}

/**
 * Data Quality Badge
 */
function DataBadge({ quality }) {
  const badges = {
    LIVE: { color: 'bg-green-500', text: 'Live' },
    CACHED: { color: 'bg-blue-500', text: 'Cached' },
    LKG: { color: 'bg-yellow-500', text: 'Last Known' },
    SIMULATED: { color: 'bg-orange-500', text: 'Demo' },
    FALLBACK: { color: 'bg-orange-500', text: 'Fallback' }
  };
  
  const badge = badges[quality] || badges.SIMULATED;
  
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full ${badge.color} text-white`}>
      {badge.text}
    </span>
  );
}

/**
 * Metric Card Component
 */
function MetricCard({ label, value, icon: Icon, subValue }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
      <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
        {Icon && <Icon className="w-3.5 h-3.5" />}
        {label}
      </div>
      <div className="text-lg font-semibold text-white">
        {value || 'N/A'}
      </div>
      {subValue && (
        <div className="text-xs text-gray-500 mt-0.5">{subValue}</div>
      )}
    </div>
  );
}

/**
 * Main Financial Summary Component
 */
export default function FinancialSummary({ symbol, onError }) {
  const [financials, setFinancials] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  
  // Fetch financials when symbol changes
  useEffect(() => {
    if (!symbol) return;
    
    let cancelled = false;
    
    async function load() {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchFinancials(symbol);
        
        if (cancelled) return;
        
        if (data) {
          setFinancials(data);
        } else {
          setError('Unable to load financial data');
          if (onError) onError('Financials unavailable');
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message);
          if (onError) onError(e.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    
    load();
    
    return () => { cancelled = true; };
  }, [symbol, onError]);
  
  // Refresh handler
  const handleRefresh = async () => {
    if (!symbol) return;
    setLoading(true);
    const data = await fetchFinancials(symbol);
    if (data) setFinancials(data);
    setLoading(false);
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading financials for {symbol}...
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      </div>
    );
  }
  
  // No data state
  if (!financials) {
    return (
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="text-gray-400">No financial data available</div>
      </div>
    );
  }
  
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-400" />
          <h3 className="font-semibold text-white">
            {financials.name || symbol}
          </h3>
          <DataBadge quality={financials.dataQuality || financials.source} />
        </div>
        <button
          onClick={handleRefresh}
          className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>
      
      {/* Sector/Industry */}
      {(financials.sector || financials.industry) && (
        <div className="px-4 py-2 text-sm text-gray-400 border-b border-gray-800">
          {financials.sector}
          {financials.industry && financials.sector && ' • '}
          {financials.industry}
        </div>
      )}
      
      {/* Key Metrics Grid */}
      <div className="p-4 grid grid-cols-2 gap-3">
        <MetricCard
          label="Market Cap"
          value={financials.marketCapFormatted}
          icon={DollarSign}
        />
        <MetricCard
          label="P/E Ratio"
          value={financials.peFormatted}
          icon={PieChart}
          subValue={financials.forwardPe ? `Forward: ${financials.forwardPeFormatted}` : null}
        />
        <MetricCard
          label="Revenue"
          value={financials.revenueFormatted}
          icon={TrendingUp}
          subValue={financials.revenueGrowthFormatted ? `Growth: ${financials.revenueGrowthFormatted}` : null}
        />
        <MetricCard
          label="Profit Margin"
          value={financials.profitMarginFormatted}
          icon={TrendingUp}
        />
      </div>
      
      {/* Expandable Details */}
      {expanded && (
        <div className="px-4 pb-4 grid grid-cols-2 gap-3 border-t border-gray-800 pt-3">
          <MetricCard label="EPS" value={financials.epsFormatted} />
          <MetricCard label="Book Value" value={financials.bookValueFormatted} />
          <MetricCard label="Dividend Yield" value={financials.dividendYieldFormatted} />
          <MetricCard label="Debt/Equity" value={financials.debtToEquity?.toFixed(2)} />
          <MetricCard label="Target Price" value={financials.targetPriceFormatted} />
          <MetricCard label="Recommendation" value={financials.recommendation?.toUpperCase()} />
        </div>
      )}
      
      {/* AI Summary */}
      {financials.summary && (
        <div className="px-4 py-3 bg-gray-800/30 border-t border-gray-800">
          <div className="text-xs text-gray-500 mb-1 flex items-center gap-1">
            🤖 AI Analysis
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">
            {financials.summary}
          </p>
        </div>
      )}
      
      {/* Expand/Collapse Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors border-t border-gray-800"
      >
        {expanded ? 'Show Less' : 'Show More Details'}
      </button>
      
      {/* Source Attribution */}
      <div className="px-4 py-2 text-xs text-gray-600 border-t border-gray-800">
        Data: {financials.source || 'TraderAI'} • 
        {financials.cached ? ' Cached' : ' Fresh'} • 
        {new Date(financials.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

/**
 * Compact version for sidebar
 */
export function FinancialSummaryCompact({ symbol }) {
  const [financials, setFinancials] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (!symbol) return;
    
    fetchFinancials(symbol).then(data => {
      setFinancials(data);
      setLoading(false);
    });
  }, [symbol]);
  
  if (loading) {
    return (
      <div className="text-gray-400 text-sm py-2">
        Loading financials...
      </div>
    );
  }
  
  if (!financials) return null;
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Market Cap</span>
        <span className="text-white">{financials.marketCapFormatted || 'N/A'}</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">P/E Ratio</span>
        <span className="text-white">{financials.peFormatted || 'N/A'}</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">Revenue</span>
        <span className="text-white">{financials.revenueFormatted || 'N/A'}</span>
      </div>
      {financials.recommendation && (
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Analyst</span>
          <span className={`uppercase ${
            financials.recommendation === 'buy' ? 'text-green-400' :
            financials.recommendation === 'sell' ? 'text-red-400' : 'text-yellow-400'
          }`}>
            {financials.recommendation}
          </span>
        </div>
      )}
    </div>
  );
}