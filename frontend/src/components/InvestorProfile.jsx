/**
 * InvestorProfile.jsx
 * 
 * A collapsible investor profile panel that allows users to set their
 * trading preferences, risk tolerance, and investment goals.
 * 
 * Add this to your App.jsx imports and render in the sidebar.
 */

import React, { useState, useEffect } from 'react';

const InvestorProfile = ({ onProfileChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    riskTolerance: 'moderate',
    investmentHorizon: 'medium',
    tradingStyle: 'swing',
    preferredMarkets: ['US'],
    capitalRange: 'medium',
    experience: 'intermediate',
    goals: []
  });

  // Load saved profile on mount
  useEffect(() => {
    const saved = localStorage.getItem('investorProfile');
    if (saved) {
      setProfile(JSON.parse(saved));
    }
  }, []);

  // Save profile changes
  const handleSave = () => {
    localStorage.setItem('investorProfile', JSON.stringify(profile));
    onProfileChange?.(profile);
    setIsExpanded(false);
  };

  const updateProfile = (key, value) => {
    setProfile(prev => ({ ...prev, [key]: value }));
  };

  const riskColors = {
    conservative: 'bg-green-500/20 text-green-400 border-green-500/30',
    moderate: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    aggressive: 'bg-red-500/20 text-red-400 border-red-500/30'
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">👤</span>
          <span className="font-medium text-white">Investor Profile</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded border ${riskColors[profile.riskTolerance]}`}>
            {profile.riskTolerance.toUpperCase()}
          </span>
          <span className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 border-t border-gray-700/50 space-y-4">
          {/* Name Input */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Display Name</label>
            <input
              type="text"
              value={profile.name}
              onChange={(e) => updateProfile('name', e.target.value)}
              placeholder="Enter your name"
              className="w-full bg-gray-700/50 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Risk Tolerance */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Risk Tolerance</label>
            <div className="grid grid-cols-3 gap-2">
              {['conservative', 'moderate', 'aggressive'].map(level => (
                <button
                  key={level}
                  onClick={() => updateProfile('riskTolerance', level)}
                  className={`py-2 px-3 rounded text-xs font-medium transition-all border ${
                    profile.riskTolerance === level
                      ? riskColors[level]
                      : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                  }`}
                >
                  {level === 'conservative' && '🛡️ '}
                  {level === 'moderate' && '⚖️ '}
                  {level === 'aggressive' && '🔥 '}
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Investment Horizon */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Investment Horizon</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { key: 'short', label: 'Short', desc: '< 1 year' },
                { key: 'medium', label: 'Medium', desc: '1-5 years' },
                { key: 'long', label: 'Long', desc: '5+ years' }
              ].map(({ key, label, desc }) => (
                <button
                  key={key}
                  onClick={() => updateProfile('investmentHorizon', key)}
                  className={`py-2 px-3 rounded text-xs transition-all border ${
                    profile.investmentHorizon === key
                      ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                      : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                  }`}
                >
                  <div className="font-medium">{label}</div>
                  <div className="text-[10px] opacity-60">{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Experience Level */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Experience Level</label>
            <select
              value={profile.experience}
              onChange={(e) => updateProfile('experience', e.target.value)}
              className="w-full bg-gray-700/50 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="beginner">🌱 Beginner (0-1 years)</option>
              <option value="intermediate">📈 Intermediate (1-3 years)</option>
              <option value="advanced">🎯 Advanced (3-5 years)</option>
              <option value="expert">🏆 Expert (5+ years)</option>
            </select>
          </div>

          {/* Capital Range */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Capital Range</label>
            <select
              value={profile.capitalRange}
              onChange={(e) => updateProfile('capitalRange', e.target.value)}
              className="w-full bg-gray-700/50 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="small">$1K - $10K</option>
              <option value="medium">$10K - $100K</option>
              <option value="large">$100K - $1M</option>
              <option value="institutional">$1M+</option>
            </select>
          </div>

          {/* Investment Goals */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Investment Goals</label>
            <div className="flex flex-wrap gap-2">
              {[
                { key: 'income', label: '💰 Income', icon: '💰' },
                { key: 'growth', label: '📈 Growth', icon: '📈' },
                { key: 'preservation', label: '🛡️ Preservation', icon: '🛡️' },
                { key: 'speculation', label: '🎲 Speculation', icon: '🎲' }
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => {
                    const goals = profile.goals.includes(key)
                      ? profile.goals.filter(g => g !== key)
                      : [...profile.goals, key];
                    updateProfile('goals', goals);
                  }}
                  className={`py-1.5 px-3 rounded text-xs transition-all border ${
                    profile.goals.includes(key)
                      ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                      : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            className="w-full py-2.5 bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-medium rounded hover:opacity-90 transition-opacity"
          >
            Save Profile
          </button>

          {/* Profile Summary */}
          {profile.name && (
            <div className="p-3 bg-gray-700/30 rounded text-xs text-gray-400">
              <strong className="text-white">{profile.name}</strong> • {profile.experience} trader • 
              {profile.riskTolerance} risk • {profile.investmentHorizon}-term horizon
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default InvestorProfile;