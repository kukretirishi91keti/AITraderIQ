/**
 * ConnectionStatus - Shows WebSocket connection state in the UI.
 */
import React, { useState, useEffect } from 'react';
import { getPriceStream } from '../services/websocket';

export default function ConnectionStatus() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const stream = getPriceStream();

    const cleanup = stream.onConnectionChange(({ connected: isConnected }) => {
      setConnected(isConnected);
    });

    // Auto-connect on mount
    stream.connect();
    setConnected(stream.isConnected);

    return cleanup;
  }, []);

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded ${
        connected ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'
      }`}
      title={connected ? 'Real-time stream connected' : 'Connecting to real-time stream...'}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          connected ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'
        }`}
      />
      {connected ? 'LIVE' : 'CONNECTING'}
    </span>
  );
}
