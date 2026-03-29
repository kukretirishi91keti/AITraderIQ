import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PriceStream } from './websocket';

class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 1; // OPEN
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    this.sent = [];
    MockWebSocket.instances.push(this);
    MockWebSocket.instance = this;
    // Fire onopen asynchronously
    setTimeout(() => this.onopen && this.onopen(), 0);
  }
  send(data) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.readyState = 3;
    this.onclose && this.onclose({ code: 1000 });
  }
}
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSED = 3;
MockWebSocket.instances = [];
MockWebSocket.instance = null;

globalThis.WebSocket = MockWebSocket;

describe('PriceStream', () => {
  let stream;

  beforeEach(() => {
    MockWebSocket.instances = [];
    MockWebSocket.instance = null;
    stream = new PriceStream();
  });

  afterEach(() => {
    stream.disconnect();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('connects to correct URL', () => {
    stream.connect();
    expect(MockWebSocket.instance.url).toContain('/ws/prices');
  });

  it('subscribe sends message', async () => {
    vi.useFakeTimers();
    stream.connect();
    // Trigger onopen
    vi.advanceTimersByTime(1);
    stream.subscribe(['AAPL']);
    const subMsg = MockWebSocket.instance.sent.find((m) => m.action === 'subscribe');
    expect(subMsg).toBeDefined();
    expect(subMsg.symbols).toEqual(['AAPL']);
  });

  it('onQuote fires callback', async () => {
    vi.useFakeTimers();
    const callback = vi.fn();
    stream.onQuote(callback);
    stream.connect();
    vi.advanceTimersByTime(1);

    // Simulate incoming quote message
    const ws = MockWebSocket.instance;
    ws.onmessage({ data: JSON.stringify({ type: 'quote', symbol: 'AAPL', price: 150 }) });

    expect(callback).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'quote', symbol: 'AAPL', price: 150 })
    );
  });

  it('reconnects on close', () => {
    vi.useFakeTimers();
    stream.connect();
    // Fire onopen setTimeout(0)
    vi.advanceTimersByTime(10);

    const initialCount = MockWebSocket.instances.length;

    // Simulate unexpected close (not via disconnect)
    const ws = MockWebSocket.instance;
    ws.readyState = 3;
    ws.onclose({ code: 1006 });

    // Advance past reconnect delay (1000ms) + new constructor onopen
    vi.advanceTimersByTime(1200);

    expect(MockWebSocket.instances.length).toBeGreaterThan(initialCount);
  });

  it('ping keepalive sent', () => {
    vi.useFakeTimers();
    stream.connect();
    vi.advanceTimersByTime(1); // trigger onopen

    vi.advanceTimersByTime(30000); // advance 30s for ping

    const pingMsg = MockWebSocket.instance.sent.find((m) => m.action === 'ping');
    expect(pingMsg).toBeDefined();
  });

  it('disconnect stops reconnect', () => {
    vi.useFakeTimers();
    stream.connect();
    vi.advanceTimersByTime(1);

    const countBefore = MockWebSocket.instances.length;
    stream.disconnect();

    // Advance well past any reconnect delay
    vi.advanceTimersByTime(60000);

    expect(MockWebSocket.instances.length).toBe(countBefore);
  });
});
