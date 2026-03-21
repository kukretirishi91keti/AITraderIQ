import React, { useState, useCallback, useMemo } from 'react';
import { API_BASE } from '../config';

// =============================================================================
// STRATEGY INTELLIGENCE WIZARD + DASHBOARD
// =============================================================================
// 3-step guided flow:
//   Step 1: "How much do you want to grow?" (capital, target, risk)
//   Step 2: "How is the market playing?" (live analysis results)
//   Step 3: "What's the best strategy?" (ranked recommendations)

const RISK_OPTIONS = [
  { value: 'conservative', label: 'Conservative', icon: '🛡️', desc: 'Preserve capital, steady growth' },
  { value: 'moderate', label: 'Moderate', icon: '⚖️', desc: 'Balanced risk and reward' },
  { value: 'aggressive', label: 'Aggressive', icon: '🔥', desc: 'Higher risk for higher returns' },
];

const HORIZON_OPTIONS = [
  { value: 'short', label: 'Short (< 1 month)', months: 1 },
  { value: 'medium', label: 'Medium (1-6 months)', months: 3 },
  { value: 'long', label: 'Long (6+ months)', months: 12 },
];

const STYLE_OPTIONS = [
  { value: 'scalp', label: 'Scalper', desc: 'Minutes-level trades' },
  { value: 'day', label: 'Day Trader', desc: 'Intraday positions' },
  { value: 'swing', label: 'Swing Trader', desc: 'Days to weeks' },
  { value: 'position', label: 'Position Trader', desc: 'Weeks to months' },
];

const SCORE_COLOR = (score) => {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
};

const RISK_COLOR = {
  low: 'bg-green-500/20 text-green-400 border-green-500/30',
  moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  very_high: 'bg-red-500/20 text-red-400 border-red-500/30',
};

export default function StrategyIntelligence({ symbol = 'AAPL', onClose }) {
  // Wizard state
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // User inputs (Step 1)
  const [capital, setCapital] = useState(10000);
  const [growthTarget, setGrowthTarget] = useState(15);
  const [riskTolerance, setRiskTolerance] = useState('moderate');
  const [timeHorizon, setTimeHorizon] = useState('medium');
  const [traderStyle, setTraderStyle] = useState('swing');

  // Expanded strategy detail
  const [expandedStrategy, setExpandedStrategy] = useState(null);

  const targetAmount = useMemo(() => capital * (1 + growthTarget / 100), [capital, growthTarget]);

  // ============================================================
  // API CALL
  // ============================================================
  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/strategy/intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          capital,
          growth_target_pct: growthTarget,
          risk_tolerance: riskTolerance,
          time_horizon: timeHorizon,
          trader_style: traderStyle,
        }),
      });
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const data = await response.json();
      setResult(data);
      setStep(2);
    } catch (err) {
      setError(err.message || 'Analysis failed. Check your connection.');
    } finally {
      setLoading(false);
    }
  }, [symbol, capital, growthTarget, riskTolerance, timeHorizon, traderStyle]);

  // ============================================================
  // STEP 1: USER INPUT FORM
  // ============================================================
  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-white">Strategy Intelligence</h2>
        <p className="text-gray-400 mt-1">Tell us your goals — we'll find the winning strategy for <span className="text-cyan-400 font-semibold">{symbol}</span></p>
      </div>

      {/* Capital Input */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          How much capital are you investing?
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-lg">$</span>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Math.max(100, Number(e.target.value)))}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-8 py-3 text-white text-lg focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
            min={100}
            step={1000}
          />
        </div>
        <div className="flex gap-2 mt-2">
          {[1000, 5000, 10000, 25000, 50000, 100000].map(amt => (
            <button
              key={amt}
              onClick={() => setCapital(amt)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                capital === amt
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              ${amt >= 1000 ? `${amt / 1000}K` : amt}
            </button>
          ))}
        </div>
      </div>

      {/* Growth Target */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          How much do you want to grow? <span className="text-cyan-400 font-bold">{growthTarget}%</span>
          <span className="text-gray-500 ml-2">(${capital.toLocaleString()} → ${targetAmount.toLocaleString(undefined, { maximumFractionDigits: 0 })})</span>
        </label>
        <input
          type="range"
          min={2}
          max={100}
          value={growthTarget}
          onChange={(e) => setGrowthTarget(Number(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>2% (Safe)</span>
          <span>25% (Moderate)</span>
          <span>50% (Ambitious)</span>
          <span>100% (Double)</span>
        </div>
      </div>

      {/* Risk Tolerance */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Risk tolerance</label>
        <div className="grid grid-cols-3 gap-3">
          {RISK_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setRiskTolerance(opt.value)}
              className={`p-3 rounded-lg border text-center transition-all ${
                riskTolerance === opt.value
                  ? 'border-cyan-500 bg-cyan-500/10 ring-1 ring-cyan-500/50'
                  : 'border-gray-600 bg-gray-800 hover:border-gray-500'
              }`}
            >
              <div className="text-2xl">{opt.icon}</div>
              <div className="text-sm font-medium text-white mt-1">{opt.label}</div>
              <div className="text-xs text-gray-400 mt-1">{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Time Horizon & Style */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Time horizon</label>
          <select
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2.5 text-white focus:border-cyan-500 outline-none"
          >
            {HORIZON_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Trading style</label>
          <select
            value={traderStyle}
            onChange={(e) => setTraderStyle(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2.5 text-white focus:border-cyan-500 outline-none"
          >
            {STYLE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label} — {opt.desc}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={runAnalysis}
        disabled={loading}
        className="w-full py-3 px-6 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Analyzing market intelligence...
          </>
        ) : (
          'Analyze & Find Best Strategy'
        )}
      </button>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}
    </div>
  );

  // ============================================================
  // STEP 2: MARKET ANALYSIS RESULTS
  // ============================================================
  const renderStep2 = () => {
    if (!result) return null;
    const { market_analysis, recommendation, growth_plan } = result;
    const ma = market_analysis;

    return (
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Market Intelligence: {symbol}</h2>
            <p className="text-gray-400 text-sm">{ma.summary}</p>
          </div>
          <button
            onClick={() => setStep(1)}
            className="text-sm text-gray-400 hover:text-white underline"
          >
            Change inputs
          </button>
        </div>

        {/* Market Condition Cards */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 uppercase">Trend</div>
            <div className={`text-lg font-bold ${
              ma.trend === 'trending_up' ? 'text-green-400' :
              ma.trend === 'trending_down' ? 'text-red-400' : 'text-yellow-400'
            }`}>
              {ma.trend.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </div>
            <div className="text-xs text-gray-500">Strength: {ma.trend_strength}%</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 uppercase">RSI</div>
            <div className={`text-lg font-bold ${
              ma.rsi > 70 ? 'text-red-400' : ma.rsi < 30 ? 'text-green-400' : 'text-white'
            }`}>
              {ma.rsi}
            </div>
            <div className="text-xs text-gray-500">{ma.momentum}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 uppercase">Volatility</div>
            <div className="text-lg font-bold text-white">{ma.atr_pct}%</div>
            <div className="text-xs text-gray-500">{ma.volatility.replace(/_/g, ' ')}</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="text-xs text-gray-400 uppercase">Confidence</div>
            <div className={`text-lg font-bold ${SCORE_COLOR(recommendation.confidence_score)}`}>
              {recommendation.confidence_score}%
            </div>
            <div className="text-xs text-gray-500">Strategy fit</div>
          </div>
        </div>

        {/* AI Recommendation Card */}
        <div className="bg-gradient-to-r from-cyan-900/30 to-blue-900/30 border border-cyan-700/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-cyan-400 font-bold text-sm uppercase">AI Recommendation</span>
            <span className="bg-cyan-500/20 text-cyan-300 text-xs px-2 py-0.5 rounded-full">
              {recommendation.strategy_name}
            </span>
          </div>
          <p className="text-gray-200 text-sm leading-relaxed">{recommendation.ai_narrative}</p>
        </div>

        {/* Growth Projection */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 uppercase mb-3">Growth Projection</h3>
          <div className="grid grid-cols-3 gap-4 mb-3">
            <div className="text-center">
              <div className="text-xs text-gray-500">Worst Case</div>
              <div className="text-lg font-bold text-red-400">
                ${growth_plan.projections.worst_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-500">Expected</div>
              <div className="text-lg font-bold text-green-400">
                ${growth_plan.projections.expected.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-500">Best Case</div>
              <div className="text-lg font-bold text-cyan-400">
                ${growth_plan.projections.best_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">
              ${growth_plan.initial_capital.toLocaleString()} → ${growth_plan.target_amount.toLocaleString()} ({growth_plan.growth_target_pct}% target)
            </span>
            {growth_plan.best_strategy_months_to_target && (
              <span className="text-cyan-400 font-semibold">
                ~{Math.ceil(growth_plan.best_strategy_months_to_target)} months to target
              </span>
            )}
          </div>
          {/* Risk bar */}
          <div className="mt-3 flex items-center gap-3">
            <span className="text-xs text-gray-500">Risk:</span>
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  growth_plan.risk_metrics.max_drawdown_pct > 10 ? 'bg-red-500' :
                  growth_plan.risk_metrics.max_drawdown_pct > 5 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(100, growth_plan.risk_metrics.max_drawdown_pct * 5)}%` }}
              />
            </div>
            <span className="text-xs text-gray-400">{growth_plan.risk_metrics.max_drawdown_pct}% max drawdown</span>
          </div>
        </div>

        <button
          onClick={() => setStep(3)}
          className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold rounded-lg transition-all"
        >
          View All Strategy Rankings →
        </button>
      </div>
    );
  };

  // ============================================================
  // STEP 3: RANKED STRATEGIES
  // ============================================================
  const renderStep3 = () => {
    if (!result) return null;
    const { ranked_strategies, action_items } = result;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Strategy Rankings for {symbol}</h2>
          <button onClick={() => setStep(2)} className="text-sm text-gray-400 hover:text-white underline">
            Back to overview
          </button>
        </div>

        {/* Strategy Cards */}
        <div className="space-y-3">
          {ranked_strategies.map((s) => (
            <div
              key={s.key}
              className={`bg-gray-800/50 rounded-lg border transition-all cursor-pointer ${
                s.rank === 1 ? 'border-cyan-500/50 ring-1 ring-cyan-500/20' : 'border-gray-700 hover:border-gray-600'
              }`}
              onClick={() => setExpandedStrategy(expandedStrategy === s.key ? null : s.key)}
            >
              {/* Card Header */}
              <div className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    s.rank === 1 ? 'bg-cyan-500/20 text-cyan-400' :
                    s.rank === 2 ? 'bg-yellow-500/20 text-yellow-400' :
                    s.rank === 3 ? 'bg-orange-500/20 text-orange-400' :
                    'bg-gray-700 text-gray-400'
                  }`}>
                    #{s.rank}
                  </div>
                  <div>
                    <div className="font-semibold text-white flex items-center gap-2">
                      {s.name}
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${RISK_COLOR[s.risk_level] || RISK_COLOR.moderate}`}>
                        {s.risk_level}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400">{s.description}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-xl font-bold ${SCORE_COLOR(s.score)}`}>{s.score}</div>
                  <div className="text-xs text-gray-500">score</div>
                </div>
              </div>

              {/* Quick Stats Row */}
              <div className="px-4 pb-3 flex gap-4 text-xs">
                <span className="text-gray-400">Win: <span className="text-white font-medium">{s.historical_win_rate}%</span></span>
                <span className="text-gray-400">Avg Return: <span className="text-white font-medium">{s.historical_avg_return}%</span></span>
                <span className="text-gray-400">Monthly: <span className="text-green-400 font-medium">{s.projected_monthly_return}%</span></span>
                <span className="text-gray-400">Hold: <span className="text-white font-medium">{s.typical_hold}</span></span>
                {s.months_to_target && (
                  <span className="text-gray-400">Target in: <span className="text-cyan-400 font-medium">~{Math.ceil(s.months_to_target)}mo</span></span>
                )}
              </div>

              {/* Expanded Details */}
              {expandedStrategy === s.key && (
                <div className="px-4 pb-4 border-t border-gray-700 pt-3 space-y-3">
                  {/* Indicators */}
                  <div>
                    <div className="text-xs text-gray-500 uppercase mb-1">Indicators Used</div>
                    <div className="flex flex-wrap gap-1">
                      {s.indicators_used.map(ind => (
                        <span key={ind} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{ind}</span>
                      ))}
                    </div>
                  </div>

                  {/* Entry/Exit Rules */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs text-green-400 uppercase mb-1">Entry Rules</div>
                      <ul className="space-y-1">
                        {s.entry_rules.map((rule, i) => (
                          <li key={i} className="text-xs text-gray-300 flex gap-1">
                            <span className="text-green-500 mt-0.5">▸</span>
                            {rule}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="text-xs text-red-400 uppercase mb-1">Exit Rules</div>
                      <ul className="space-y-1">
                        {s.exit_rules.map((rule, i) => (
                          <li key={i} className="text-xs text-gray-300 flex gap-1">
                            <span className="text-red-500 mt-0.5">▸</span>
                            {rule}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Monthly Returns Mini Chart */}
                  <div>
                    <div className="text-xs text-gray-500 uppercase mb-1">Monthly Returns (Last 6 months)</div>
                    <div className="flex items-end gap-1 h-12">
                      {s.monthly_returns_history.map((ret, i) => (
                        <div
                          key={i}
                          className={`flex-1 rounded-t ${ret >= 0 ? 'bg-green-500/60' : 'bg-red-500/60'}`}
                          style={{
                            height: `${Math.min(100, Math.abs(ret) * 10 + 10)}%`,
                            minHeight: '4px',
                          }}
                          title={`Month ${i + 1}: ${ret > 0 ? '+' : ''}${ret}%`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Sharpe Ratio: {s.sharpe_ratio} | Cumulative: {s.monthly_returns_history.reduce((a, b) => a + b, 0).toFixed(1)}%
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Action Items */}
        <div className="bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-700/30 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-green-400 uppercase mb-2">Your Action Plan</h3>
          <ul className="space-y-2">
            {action_items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-green-500 font-bold">{i + 1}.</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Restart */}
        <div className="flex gap-3">
          <button
            onClick={() => { setStep(1); setResult(null); }}
            className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Start Over
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            Apply to Trading
          </button>
        </div>
      </div>
    );
  };

  // ============================================================
  // RENDER
  // ============================================================
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-gray-900 rounded-xl shadow-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Progress Bar */}
        <div className="flex items-center gap-0 px-6 pt-4 pb-2">
          {[1, 2, 3].map(s => (
            <React.Fragment key={s}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  step >= s ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-400'
                }`}
              >
                {step > s ? '✓' : s}
              </div>
              {s < 3 && (
                <div className={`flex-1 h-0.5 mx-1 transition-all ${step > s ? 'bg-cyan-600' : 'bg-gray-700'}`} />
              )}
            </React.Fragment>
          ))}
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-white text-xl"
            title="Close"
          >
            ×
          </button>
        </div>
        <div className="text-center text-xs text-gray-500 mb-2">
          {step === 1 ? 'Set Your Goals' : step === 2 ? 'Market Analysis' : 'Strategy Rankings'}
        </div>

        {/* Content */}
        <div className="px-6 pb-6">
          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step === 3 && renderStep3()}
        </div>
      </div>
    </div>
  );
}
