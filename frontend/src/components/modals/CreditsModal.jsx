import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const CREDIT_PACKS = [
  { id: 'pack_100', credits: 100, price: '$0.99', label: '100 Credits' },
  { id: 'pack_500', credits: 500, price: '$3.99', label: '500 Credits', popular: true, savings: '20% off' },
  { id: 'pack_2000', credits: 2000, price: '$12.99', label: '2,000 Credits', savings: '35% off' },
  { id: 'pack_10000', credits: 10000, price: '$49.99', label: '10,000 Credits', savings: '50% off' },
];

const TIERS = [
  { id: 'free', name: 'Free', price: '$0', daily: 50, features: ['50 AI queries/day', 'All 15 markets', 'Real-time charts', 'Technical signals'] },
  { id: 'starter', name: 'Starter', price: '$4.99/mo', daily: 200, features: ['200 AI queries/day', 'Credit rollover (500)', 'Advanced backtesting', 'Priority data'] },
  { id: 'pro', name: 'Pro', price: '$14.99/mo', daily: 1000, popular: true, features: ['1000 AI queries/day', 'Credit rollover (3000)', 'AI Scanner', 'Export reports'] },
  { id: 'unlimited', name: 'Unlimited', price: '$29.99/mo', daily: '∞', features: ['Unlimited queries', 'All features', 'API access', 'White-label'] },
];

const AI_COSTS = [
  { model: 'Llama 3.1 8B (Groq)', cost: 1, speed: 'Fastest' },
  { model: 'Llama 3.3 70B (Groq)', cost: 2, speed: 'Fast' },
  { model: 'GPT-4o Mini (OpenAI)', cost: 3, speed: 'Fast' },
  { model: 'Claude Haiku (Anthropic)', cost: 2, speed: 'Fast' },
  { model: 'Claude Sonnet (Anthropic)', cost: 4, speed: 'Smart' },
  { model: 'GPT-4o (OpenAI)', cost: 5, speed: 'Smartest' },
  { model: 'Rule-based Analysis', cost: 0, speed: 'Instant (free)' },
];

export default function CreditsModal({ onClose, credits, setCredits, isLoggedIn }) {
  const [tab, setTab] = useState('balance');
  const [buying, setBuying] = useState(false);
  const [message, setMessage] = useState('');

  const authHeaders = () => {
    const token = localStorage.getItem('traderai_token');
    return token ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } : { 'Content-Type': 'application/json' };
  };

  const handleBuyPack = async (packId) => {
    if (!isLoggedIn) {
      setMessage('Please sign in to purchase credits');
      return;
    }
    setBuying(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/api/credits/topup`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ pack_id: packId }),
      });
      const data = await res.json();
      if (data.success) {
        setCredits(prev => ({ ...prev, balance: data.new_balance }));
        setMessage(data.message);
      } else {
        setMessage(data.detail || 'Purchase failed');
      }
    } catch (err) {
      setMessage('Network error. Try again.');
    }
    setBuying(false);
  };

  const handleUpgradeTier = async (tierId) => {
    if (!isLoggedIn) {
      setMessage('Please sign in to change plans');
      return;
    }
    setBuying(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/api/credits/upgrade`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ tier: tierId }),
      });
      const data = await res.json();
      if (data.success) {
        setCredits(prev => ({ ...prev, balance: data.new_balance, tier: tierId, daily_grant: data.plan?.daily_credits }));
        setMessage(data.message);
      } else {
        setMessage(data.detail || 'Upgrade failed');
      }
    } catch (err) {
      setMessage('Network error. Try again.');
    }
    setBuying(false);
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-gray-800 rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-700">
          <div>
            <h2 className="text-lg font-bold text-white">Credits & Pricing</h2>
            <p className="text-sm text-gray-400">Pay only for AI queries. Everything else is free.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-2xl font-bold text-yellow-400">{credits.balance ?? 50}</div>
              <div className="text-xs text-gray-400">credits left</div>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          {['balance', 'buy', 'plans', 'costs'].map(t => (
            <button key={t} onClick={() => setTab(t)} className={`flex-1 px-4 py-3 text-sm font-medium capitalize ${tab === t ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-gray-400 hover:text-gray-200'}`}>
              {t === 'buy' ? 'Buy Credits' : t === 'costs' ? 'AI Costs' : t}
            </button>
          ))}
        </div>

        <div className="p-5">
          {/* Balance Tab */}
          {tab === 'balance' && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-yellow-400">{credits.balance ?? 50}</div>
                  <div className="text-xs text-gray-400 mt-1">Available</div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-cyan-400">{credits.daily_grant ?? 50}</div>
                  <div className="text-xs text-gray-400 mt-1">Daily Grant</div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400 capitalize">{credits.tier ?? 'free'}</div>
                  <div className="text-xs text-gray-400 mt-1">Current Tier</div>
                </div>
              </div>

              <div className="bg-gray-700/30 rounded-lg p-4">
                <h3 className="text-sm font-medium text-white mb-2">How Credits Work</h3>
                <ul className="text-xs text-gray-400 space-y-1">
                  <li>- Charts, quotes, signals, news, alerts = <span className="text-green-400">Always Free</span></li>
                  <li>- AI chat with rule-based analysis = <span className="text-green-400">Free (0 credits)</span></li>
                  <li>- AI chat with LLM (Groq/OpenAI/Anthropic) = <span className="text-yellow-400">1-5 credits per query</span></li>
                  <li>- Free tier gets <span className="text-cyan-400">50 credits daily</span> (resets at midnight UTC)</li>
                  <li>- Bring your own API key = <span className="text-green-400">No credit cost</span> (you pay the provider directly)</li>
                </ul>
              </div>

              {!isLoggedIn && (
                <div className="bg-cyan-900/30 border border-cyan-700/50 rounded-lg p-3 text-sm text-cyan-300">
                  Sign in to track your credits across sessions and buy credit packs.
                </div>
              )}
            </div>
          )}

          {/* Buy Credits Tab */}
          {tab === 'buy' && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400 mb-4">One-time credit packs. No subscription required.</p>
              {CREDIT_PACKS.map(pack => (
                <div key={pack.id} className={`flex items-center justify-between p-4 rounded-lg border ${pack.popular ? 'border-yellow-500/50 bg-yellow-900/10' : 'border-gray-700 bg-gray-700/30'}`}>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{pack.label}</span>
                      {pack.popular && <span className="text-xs bg-yellow-500 text-black px-2 py-0.5 rounded-full font-medium">Popular</span>}
                    </div>
                    {pack.savings && <span className="text-xs text-green-400">{pack.savings}</span>}
                  </div>
                  <button onClick={() => handleBuyPack(pack.id)} disabled={buying} className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-gray-600 rounded-lg text-sm font-medium">
                    {pack.price}
                  </button>
                </div>
              ))}
              {message && <p className={`text-sm mt-2 ${message.includes('Added') ? 'text-green-400' : 'text-yellow-400'}`}>{message}</p>}
              <p className="text-xs text-gray-500 mt-2">Demo mode: credits are granted instantly. In production, integrates with Stripe/Razorpay.</p>
            </div>
          )}

          {/* Plans Tab */}
          {tab === 'plans' && (
            <div className="space-y-3">
              {message && <p className={`text-sm ${message.includes('Upgraded') ? 'text-green-400' : 'text-yellow-400'}`}>{message}</p>}
            <div className="grid grid-cols-2 gap-3">
              {TIERS.map(tier => (
                <div key={tier.id} className={`rounded-lg border p-4 ${tier.popular ? 'border-cyan-500/50 bg-cyan-900/10' : 'border-gray-700 bg-gray-700/30'} ${credits.tier === tier.id ? 'ring-2 ring-cyan-500' : ''}`}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-white">{tier.name}</h3>
                    {tier.popular && <span className="text-xs bg-cyan-500 text-black px-2 py-0.5 rounded-full">Best Value</span>}
                  </div>
                  <div className="text-xl font-bold text-cyan-400 mb-1">{tier.price}</div>
                  <div className="text-xs text-gray-400 mb-3">{tier.daily} credits/day</div>
                  <ul className="text-xs text-gray-300 space-y-1">
                    {tier.features.map((f, i) => <li key={i}>- {f}</li>)}
                  </ul>
                  {credits.tier === tier.id ? (
                    <div className="mt-3 text-xs text-cyan-400 font-medium">Current Plan</div>
                  ) : (
                    <button onClick={() => handleUpgradeTier(tier.id)} disabled={buying} className={`mt-3 w-full px-3 py-1.5 rounded text-xs font-medium ${tier.id === 'free' ? 'bg-gray-600 hover:bg-gray-500' : 'bg-cyan-600 hover:bg-cyan-500'} disabled:bg-gray-600`}>
                      {tier.id === 'free' ? 'Downgrade' : 'Upgrade'}
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">Demo mode: tier changes apply instantly. In production, integrates with Stripe/Razorpay.</p>
            </div>
          )}

          {/* AI Costs Tab */}
          {tab === 'costs' && (
            <div>
              <p className="text-sm text-gray-400 mb-4">Credit cost per AI query by model:</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-700">
                    <th className="text-left py-2">Model</th>
                    <th className="text-center py-2">Cost</th>
                    <th className="text-right py-2">Speed</th>
                  </tr>
                </thead>
                <tbody>
                  {AI_COSTS.map((item, i) => (
                    <tr key={i} className="border-b border-gray-700/50">
                      <td className="py-2 text-white">{item.model}</td>
                      <td className="py-2 text-center">
                        {item.cost === 0 ? (
                          <span className="text-green-400 font-medium">Free</span>
                        ) : (
                          <span className="text-yellow-400 font-medium">{item.cost} cr</span>
                        )}
                      </td>
                      <td className="py-2 text-right text-gray-400">{item.speed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 bg-green-900/20 border border-green-700/30 rounded-lg p-3 text-xs text-green-300">
                Pro tip: Use your own API key (in AI Settings) to bypass credits entirely. You pay the provider directly at their rates.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
