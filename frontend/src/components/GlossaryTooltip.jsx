/**
 * GlossaryTooltip — Wraps a term in a dotted underline that shows a
 * rich popup on hover explaining the financial concept.
 *
 * Props:
 *   term     {string}  Key into the GLOSSARY dictionary (case-insensitive lookup)
 *   children {node}    The visible label text
 *
 * Usage:
 *   <GlossaryTooltip term="RSI">RSI</GlossaryTooltip>
 *   <GlossaryTooltip term="Stop Loss">Stop Loss</GlossaryTooltip>
 */
import React, { useState, useRef, useEffect } from 'react';

// ── Glossary dictionary ───────────────────────────────────────────────────────
const GLOSSARY = {
  RSI: {
    full: 'Relative Strength Index',
    what: 'Measures if a stock is overbought or oversold on a 0-100 scale.',
    howToUse: 'Below 30 = oversold (potential buy). Above 70 = overbought (potential sell).',
    range: '0-100 · Sweet spot: 30-70',
  },
  ATR: {
    full: 'Average True Range',
    what: 'How much the stock typically moves per day in price.',
    howToUse: 'Use it to set stop-loss: stop = entry − 1.5×ATR.',
    range: 'Higher ATR = more volatile stock',
  },
  VWAP: {
    full: 'Volume-Weighted Average Price',
    what: 'The average price weighted by trading volume during the day.',
    howToUse: 'Price above VWAP = institutions buying. Below = selling pressure.',
    range: 'Intraday benchmark',
  },
  MACD: {
    full: 'Moving Average Convergence Divergence',
    what: 'Shows momentum by comparing two moving averages.',
    howToUse: 'MACD line crossing above signal line = bullish. Below = bearish.',
    range: 'No fixed range',
  },
  SMA: {
    full: 'Simple Moving Average',
    what: 'The average closing price over N days.',
    howToUse: 'Price above SMA = uptrend. Below = downtrend.',
    range: 'Common: 20-day, 50-day, 200-day',
  },
  EMA: {
    full: 'Exponential Moving Average',
    what: 'Like SMA but gives more weight to recent prices, reacts faster.',
    howToUse: 'EMA12 crossing above EMA26 = bullish signal.',
    range: 'Faster than SMA at detecting trends',
  },
  'STOP LOSS': {
    full: 'Stop Loss Order',
    what: 'An automatic sell order triggered if price drops to a set level.',
    howToUse: 'Set 1.5×ATR below your entry price to limit losses.',
    range: 'Rule of thumb: risk max 2% of capital per trade',
  },
  'TAKE PROFIT': {
    full: 'Take Profit / Target Price',
    what: 'The price level where you plan to sell and lock in gains.',
    howToUse: 'Set at 2-3×ATR above entry for a good risk:reward ratio.',
    range: 'Aim for Risk:Reward of 1:2 or better',
  },
  'RISK:REWARD': {
    full: 'Risk to Reward Ratio',
    what: 'How much you stand to gain vs how much you risk losing.',
    howToUse: '1:2 means risk ₹100 to potentially gain ₹200. Always aim for 1:2+.',
    range: 'Good: 1:2+. Great: 1:3+',
  },
  BOLLINGER: {
    full: 'Bollinger Bands',
    what: 'Bands that show price volatility — upper and lower bounds.',
    howToUse:
      'Price touching lower band = potential bounce. Upper band = potential reversal.',
    range: '20-day SMA ± 2 standard deviations',
  },
};

// Case-insensitive lookup — "Stop Loss", "stop loss", "STOP LOSS" all work.
function lookupTerm(term) {
  if (!term) return null;
  const key = term.toUpperCase().replace(/\s+/g, ' ').trim();
  return GLOSSARY[key] || null;
}

// ── Popup card ────────────────────────────────────────────────────────────────
function GlossaryPopup({ term, entry, position }) {
  const isAbove = position !== 'below';

  return (
    <span
      className={`
        absolute z-50 left-1/2 -translate-x-1/2
        ${isAbove ? 'bottom-full mb-2.5' : 'top-full mt-2.5'}
        w-64 bg-gray-800 border border-gray-600 rounded-xl
        shadow-2xl shadow-black/70 p-3.5 text-left pointer-events-none
      `}
      role="tooltip"
    >
      {/* Arrow — points toward the term */}
      {isAbove ? (
        <>
          <span className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0
            border-l-[6px] border-l-transparent
            border-r-[6px] border-r-transparent
            border-t-[6px] border-t-gray-600" />
          <span className="absolute left-1/2 -translate-x-1/2 top-full mt-[-1px] w-0 h-0
            border-l-[5px] border-l-transparent
            border-r-[5px] border-r-transparent
            border-t-[5px] border-t-gray-800" />
        </>
      ) : (
        <>
          <span className="absolute left-1/2 -translate-x-1/2 bottom-full w-0 h-0
            border-l-[6px] border-l-transparent
            border-r-[6px] border-r-transparent
            border-b-[6px] border-b-gray-600" />
          <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-[-1px] w-0 h-0
            border-l-[5px] border-l-transparent
            border-r-[5px] border-r-transparent
            border-b-[5px] border-b-gray-800" />
        </>
      )}

      {/* Term identifier */}
      <span className="block text-[10px] font-semibold uppercase tracking-widest text-cyan-500 mb-0.5">
        {term}
      </span>

      {/* Full name */}
      <span className="block text-white font-semibold text-xs leading-tight mb-2">
        {entry.full}
      </span>

      <span className="block h-px bg-gray-700 mb-2" />

      {/* What it is */}
      <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-0.5">
        What it is
      </span>
      <span className="block text-gray-300 text-xs leading-relaxed mb-2">
        {entry.what}
      </span>

      {/* How to use */}
      <span className="block text-[10px] uppercase tracking-wider text-gray-500 font-medium mb-0.5">
        How to use
      </span>
      <span className="block text-gray-300 text-xs leading-relaxed mb-2">
        {entry.howToUse}
      </span>

      {/* Range / note chip */}
      <span className="block bg-gray-700/60 rounded-lg px-2.5 py-1.5 text-[10px] text-cyan-400/80 font-medium">
        {entry.range}
      </span>
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function GlossaryTooltip({ term, children }) {
  const [visible,  setVisible]  = useState(false);
  const [position, setPosition] = useState('above');
  const wrapRef                 = useRef(null);
  const hideTimer               = useRef(null);

  // Cleanup timer on unmount
  useEffect(() => () => clearTimeout(hideTimer.current), []);

  const entry = lookupTerm(term);

  // If no glossary entry, render plain text
  if (!entry) return <span>{children}</span>;

  function handleShow() {
    clearTimeout(hideTimer.current);
    // Decide popup position based on available space above the element
    if (wrapRef.current) {
      const rect = wrapRef.current.getBoundingClientRect();
      setPosition(rect.top > 170 ? 'above' : 'below');
    }
    setVisible(true);
  }

  function handleHide() {
    // Short delay prevents flicker when mouse briefly leaves the span
    hideTimer.current = setTimeout(() => setVisible(false), 100);
  }

  return (
    <span
      ref={wrapRef}
      className="relative inline-block border-b border-dotted border-gray-400 hover:border-cyan-400 cursor-help transition-colors duration-150"
      onMouseEnter={handleShow}
      onMouseLeave={handleHide}
      onFocus={handleShow}
      onBlur={handleHide}
      tabIndex={0}
      role="button"
      aria-describedby={`glossary-${(term || '').replace(/\s+/g, '-').toLowerCase()}`}
    >
      {children}
      {visible && (
        <GlossaryPopup
          term={term}
          entry={entry}
          position={position}
        />
      )}
    </span>
  );
}
