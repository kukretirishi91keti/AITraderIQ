/**
 * WebSocket service for real-time price streaming.
 *
 * Usage:
 *   import { PriceStream } from './services/websocket';
 *
 *   const stream = new PriceStream();
 *   stream.onQuote((data) => console.log(data));
 *   stream.connect();
 *   stream.subscribe(['AAPL', 'MSFT']);
 */

const WS_BASE = import.meta.env.VITE_WS_BASE_URL ||
  (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
  (import.meta.env.VITE_API_BASE_URL || 'localhost:8000').replace(/^https?:\/\//, '');

export class PriceStream {
  constructor() {
    this._ws = null;
    this._listeners = { quote: [], status: [], error: [], connected: [] };
    this._subscriptions = new Set();
    this._reconnectDelay = 1000;
    this._maxReconnectDelay = 30000;
    this._shouldReconnect = true;
    this._pingInterval = null;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect() {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) return;

    try {
      this._ws = new WebSocket(`${WS_BASE}/ws/prices`);

      this._ws.onopen = () => {
        console.log('[WS] Connected');
        this._reconnectDelay = 1000;
        this._emit('connected', { connected: true });

        // Re-subscribe to any symbols
        if (this._subscriptions.size > 0) {
          this.subscribe([...this._subscriptions]);
        }

        // Keepalive ping every 30s
        this._pingInterval = setInterval(() => {
          this._send({ action: 'ping' });
        }, 30000);
      };

      this._ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'quote') {
            this._emit('quote', data);
          } else if (data.type === 'status') {
            this._emit('status', data);
          } else if (data.type === 'error') {
            this._emit('error', data);
          }
        } catch (e) {
          console.warn('[WS] Parse error:', e);
        }
      };

      this._ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code);
        clearInterval(this._pingInterval);
        this._emit('connected', { connected: false });

        if (this._shouldReconnect) {
          console.log(`[WS] Reconnecting in ${this._reconnectDelay}ms...`);
          setTimeout(() => this.connect(), this._reconnectDelay);
          this._reconnectDelay = Math.min(this._reconnectDelay * 2, this._maxReconnectDelay);
        }
      };

      this._ws.onerror = (error) => {
        console.warn('[WS] Error:', error);
        this._emit('error', { message: 'WebSocket error' });
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
    }
  }

  /**
   * Subscribe to price updates for symbols.
   */
  subscribe(symbols) {
    symbols.forEach(s => this._subscriptions.add(s.toUpperCase()));
    this._send({ action: 'subscribe', symbols });
  }

  /**
   * Unsubscribe from symbols.
   */
  unsubscribe(symbols) {
    symbols.forEach(s => this._subscriptions.delete(s.toUpperCase()));
    this._send({ action: 'unsubscribe', symbols });
  }

  /**
   * Register a listener for quote updates.
   */
  onQuote(callback) {
    this._listeners.quote.push(callback);
    return () => {
      this._listeners.quote = this._listeners.quote.filter(cb => cb !== callback);
    };
  }

  /**
   * Register a listener for connection state changes.
   */
  onConnectionChange(callback) {
    this._listeners.connected.push(callback);
    return () => {
      this._listeners.connected = this._listeners.connected.filter(cb => cb !== callback);
    };
  }

  /**
   * Disconnect and stop reconnecting.
   */
  disconnect() {
    this._shouldReconnect = false;
    clearInterval(this._pingInterval);
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  get isConnected() {
    return this._ws && this._ws.readyState === WebSocket.OPEN;
  }

  _send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data));
    }
  }

  _emit(type, data) {
    (this._listeners[type] || []).forEach(cb => {
      try { cb(data); } catch (e) { console.error('[WS] Listener error:', e); }
    });
  }
}

// Singleton instance
let _instance = null;

export function getPriceStream() {
  if (!_instance) {
    _instance = new PriceStream();
  }
  return _instance;
}

export default { PriceStream, getPriceStream };
