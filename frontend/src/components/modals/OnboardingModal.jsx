/**
 * OnboardingModal.jsx
 *
 * 3-step first-login wizard:
 *   Step 1 — Welcome
 *   Step 2 — Investor Profile (risk, horizon, experience, goals)
 *   Step 3 — Risk Disclosure acceptance
 *
 * On completion: saves profile to localStorage, syncs to backend, and sets
 * localStorage 'onboardingComplete' so it doesn't show again.
 */
import React, { useState } from 'react';
import { authFetch } from '../../services/auth';
import { API_BASE } from '../../constants/appConfig';

const RISK_LEVELS = ['conservative', 'moderate', 'aggressive'];
const HORIZONS = [
  { value: 'short', label: 'Short', sub: '< 1 year' },
  { value: 'medium', label: 'Medium', sub: '1 – 5 years' },
  { value: 'long', label: 'Long', sub: '5+ years' },
];
const GOALS = ['income', 'growth', 'preservation', 'speculation'];
const GOAL_ICONS = { income: '💰', growth: '📈', preservation: '🛡️', speculation: '🎲' };

const RISK_COLORS = {
  conservative: 'bg-green-500/20 text-green-400 border-green-500/40',
  moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  aggressive: 'bg-red-500/20 text-red-400 border-red-500/40',
};

export default function OnboardingModal({ onComplete }) {
  const [step, setStep] = useState(1);
  const [agreed, setAgreed] = useState(false);
  const [saving, setSaving] = useState(false);

  const [profile, setProfile] = useState({
    riskTolerance: 'moderate',
    investmentHorizon: 'medium',
    experience: 'intermediate',
    goals: [],
  });

  const update = (key, value) => setProfile((p) => ({ ...p, [key]: value }));

  const toggleGoal = (goal) => {
    setProfile((p) => ({
      ...p,
      goals: p.goals.includes(goal) ? p.goals.filter((g) => g !== goal) : [...p.goals, goal],
    }));
  };

  const handleFinish = async () => {
    setSaving(true);
    try {
      // Merge with any existing saved profile
      const existing = JSON.parse(localStorage.getItem('investorProfile') || '{}');
      const merged = { ...existing, ...profile };
      localStorage.setItem('investorProfile', JSON.stringify(merged));

      // Sync to backend (best-effort)
      try {
        await authFetch(`${API_BASE}/api/auth/me`, {
          method: 'PUT',
          body: JSON.stringify({
            risk_tolerance:     profile.riskTolerance,
            investment_horizon: profile.investmentHorizon,
            experience_level:   profile.experience,
            goals:              JSON.stringify(profile.goals),
          }),
        });
      } catch {
        // backend sync failure is non-blocking
      }

      localStorage.setItem('onboardingComplete', 'true');
      onComplete(merged);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[100] p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-lg w-full shadow-2xl">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 pt-6">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-2 w-2 rounded-full transition-all ${
                s === step ? 'bg-cyan-400 w-6' : s < step ? 'bg-cyan-600' : 'bg-gray-600'
              }`}
            />
          ))}
        </div>

        <div className="p-8">
          {/* ── Step 1: Welcome ──────────────────────────────────────── */}
          {step === 1 && (
            <div className="text-center space-y-4">
              <div className="text-5xl mb-2">📊</div>
              <h2 className="text-2xl font-bold text-white">Welcome to AITraderIQ</h2>
              <p className="text-gray-400">
                AI-powered insights for smarter trading decisions. Let&apos;s take 60 seconds to
                personalise your experience.
              </p>
              <ul className="text-left text-sm text-gray-300 space-y-2 mt-4">
                {[
                  'Real-time signals tailored to your risk profile',
                  'AI responses that match your experience level',
                  'Strategies filtered to your investment horizon',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="text-cyan-400 mt-0.5">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => setStep(2)}
                className="w-full mt-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold rounded-lg hover:opacity-90 transition-opacity"
              >
                Get Started →
              </button>
            </div>
          )}

          {/* ── Step 2: Investor Profile ─────────────────────────────── */}
          {step === 2 && (
            <div className="space-y-5">
              <h2 className="text-xl font-bold text-white text-center">Your Investor Profile</h2>

              {/* Risk Tolerance */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">Risk Tolerance</label>
                <div className="flex gap-2">
                  {RISK_LEVELS.map((level) => (
                    <button
                      key={level}
                      onClick={() => update('riskTolerance', level)}
                      className={`flex-1 py-2 text-sm rounded border capitalize transition-colors ${
                        profile.riskTolerance === level
                          ? RISK_COLORS[level]
                          : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              {/* Investment Horizon */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">Investment Horizon</label>
                <div className="flex gap-2">
                  {HORIZONS.map(({ value, label, sub }) => (
                    <button
                      key={value}
                      onClick={() => update('investmentHorizon', value)}
                      className={`flex-1 py-2 text-sm rounded border transition-colors ${
                        profile.investmentHorizon === value
                          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40'
                          : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                      }`}
                    >
                      <div className="font-medium">{label}</div>
                      <div className="text-xs opacity-70">{sub}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Experience Level */}
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Experience Level</label>
                <select
                  value={profile.experience}
                  onChange={(e) => update('experience', e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>

              {/* Goals */}
              <div>
                <label className="text-sm text-gray-400 mb-2 block">
                  Investment Goals <span className="text-gray-500">(select all that apply)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {GOALS.map((goal) => (
                    <button
                      key={goal}
                      onClick={() => toggleGoal(goal)}
                      className={`px-3 py-1.5 text-sm rounded border capitalize transition-colors ${
                        profile.goals.includes(goal)
                          ? 'bg-purple-500/20 text-purple-400 border-purple-500/40'
                          : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                      }`}
                    >
                      {GOAL_ICONS[goal]} {goal}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-2.5 border border-gray-600 text-gray-400 rounded-lg hover:bg-gray-700/30 text-sm"
                >
                  ← Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 py-2.5 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold rounded-lg hover:opacity-90 text-sm"
                >
                  Next →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Risk Disclosure ──────────────────────────────── */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white text-center">Important Disclaimer</h2>
              <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-4 text-sm text-gray-300 space-y-3 max-h-48 overflow-y-auto">
                <p>
                  <strong className="text-yellow-400">Educational Use Only.</strong> AITraderIQ is
                  designed to support learning and decision-making. It does{' '}
                  <strong>not</strong> constitute financial, investment, or trading advice.
                </p>
                <p>
                  <strong className="text-yellow-400">No Guarantee of Accuracy.</strong> Market data
                  may be delayed, simulated, or sourced from unofficial providers (yfinance). Always
                  verify data independently before making any decision.
                </p>
                <p>
                  <strong className="text-yellow-400">Risk of Loss.</strong> Trading involves
                  significant risk of loss. Past performance of any signal, strategy, or indicator
                  shown here does not guarantee future results.
                </p>
                <p>
                  <strong className="text-yellow-400">Regulatory Note.</strong> If you are trading
                  in India, ensure compliance with SEBI regulations. This platform does not
                  constitute a SEBI-registered investment advisory service.
                </p>
              </div>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  className="mt-0.5 accent-cyan-500 w-4 h-4 shrink-0"
                />
                <span className="text-sm text-gray-300">
                  I understand that AITraderIQ is for educational purposes only and does not
                  constitute financial advice. I will not make trading decisions based solely on
                  this platform.
                </span>
              </label>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 py-2.5 border border-gray-600 text-gray-400 rounded-lg hover:bg-gray-700/30 text-sm"
                >
                  ← Back
                </button>
                <button
                  onClick={handleFinish}
                  disabled={!agreed || saving}
                  className="flex-1 py-2.5 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold rounded-lg hover:opacity-90 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving…' : 'Start Trading →'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
