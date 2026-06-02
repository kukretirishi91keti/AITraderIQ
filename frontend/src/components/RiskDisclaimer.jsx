/**
 * RiskDisclaimer.jsx
 *
 * Persistent slim banner fixed to the bottom of the screen.
 * Dismissed per browser session (sessionStorage) — reappears on each new tab/session.
 */
import React, { useState } from 'react';

export default function RiskDisclaimer() {
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem('disclaimerDismissed') === 'true'
  );

  if (dismissed) return null;

  const handleDismiss = () => {
    sessionStorage.setItem('disclaimerDismissed', 'true');
    setDismissed(true);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 border-t border-yellow-700/40 px-4 py-2 flex items-center justify-between gap-4">
      <p className="text-xs text-gray-400 leading-snug">
        <span className="text-yellow-400 font-medium">Disclaimer: </span>
        AITraderIQ provides simulated or delayed market data for{' '}
        <strong>educational purposes only</strong>. This is <strong>not financial advice</strong>.
        Not registered with SEBI as an investment advisor. Trading in equities and derivatives
        involves risk of loss. Past performance does not guarantee future results. Verify all data
        independently before trading.
      </p>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss disclaimer"
        className="shrink-0 text-gray-500 hover:text-gray-300 text-lg leading-none px-1"
      >
        &times;
      </button>
    </div>
  );
}
