/**
 * TraderContextRibbon — compact playbook strip shown below the price row.
 * Tells the user what to focus on for their selected trading style.
 */
import React from 'react';

const PLAYBOOKS = {
  Scalper: {
    icon: '⚡',
    color: 'border-orange-500/40 bg-orange-500/5',
    labelColor: 'text-orange-400',
    cues: [
      'RSI extremes (<30 / >70) for micro-reversals',
      'VWAP as intraday fair value; enter on reclaim',
      'ATR stop ≤ 0.5×; target 1:1.5 min',
      'Square off before 3:15 PM IST',
    ],
  },
  Day: {
    icon: '📈',
    color: 'border-cyan-500/40 bg-cyan-500/5',
    labelColor: 'text-cyan-400',
    cues: [
      'Trade in direction of Nifty/BankNifty trend',
      'VWAP rejection or breakout = entry trigger',
      'Check FII/DII tab for institutional bias',
      'Close all MIS positions before 3:20 PM IST',
    ],
  },
  Swing: {
    icon: '🌊',
    color: 'border-blue-500/40 bg-blue-500/5',
    labelColor: 'text-blue-400',
    cues: [
      'Daily chart: look for RSI reset + support hold',
      'Check Earnings tab — avoid stocks reporting soon',
      'Backtest tab shows multi-day signal accuracy',
      'Use CNC orders; hold 2–10 days',
    ],
  },
  Position: {
    icon: '🏦',
    color: 'border-purple-500/40 bg-purple-500/5',
    labelColor: 'text-purple-400',
    cues: [
      'Fundamentals tab: P/E, revenue growth, promoter %',
      'FII/DII trend over weeks = smart money direction',
      'Weekly chart: 200-day MA as key support',
      'Sector rotation via Sectors tab',
    ],
  },
};

export default function TraderContextRibbon({ traderStyle }) {
  const pb = PLAYBOOKS[traderStyle];
  if (!pb) return null;

  return (
    <div className={`rounded-lg border px-3 py-2 mb-3 ${pb.color}`}>
      <div className="flex items-start gap-2">
        <span className="text-base leading-none mt-0.5">{pb.icon}</span>
        <div className="min-w-0 flex-1">
          <span className={`text-xs font-semibold uppercase tracking-wide ${pb.labelColor}`}>
            {traderStyle} Playbook
          </span>
          <ul className="mt-1 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-0.5">
            {pb.cues.map((cue) => (
              <li key={cue} className="text-[11px] text-gray-400 flex items-start gap-1">
                <span className="text-gray-600 mt-px">›</span>
                <span>{cue}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
