import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChartPanel from './ChartPanel';

const makeCandle = (price, ts = '2024-01-15T09:15:00') => ({
  close: price,
  timestamp: ts,
  open: price,
  high: price + 1,
  low: price - 1,
  volume: 1000,
});

describe('ChartPanel', () => {
  it('shows loading state when history is null', () => {
    render(<ChartPanel history={null} selectedSymbol="AAPL" chartInterval="1d" currency="$" />);
    expect(screen.getByText(/Loading chart/)).toBeTruthy();
  });

  it('shows loading state when history is empty', () => {
    render(<ChartPanel history={[]} selectedSymbol="AAPL" chartInterval="1d" currency="$" />);
    expect(screen.getByText(/Loading chart/)).toBeTruthy();
  });

  it('renders SVG for normal multi-candle history', () => {
    const history = Array.from({ length: 20 }, (_, i) =>
      makeCandle(100 + i, `2024-01-${String(i + 1).padStart(2, '0')}T09:00:00`)
    );
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="AAPL" chartInterval="1d" currency="$" />
    );
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelector('polyline')).toBeTruthy();
  });

  it('renders SVG without Infinity/NaN when history has exactly 1 candle', () => {
    const history = [makeCandle(150)];
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="AAPL" chartInterval="1d" currency="$" />
    );
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
    // Points must not contain Infinity or NaN
    const polyline = container.querySelector('polyline');
    expect(polyline).toBeTruthy();
    const pts = polyline.getAttribute('points') || '';
    expect(pts).not.toContain('Infinity');
    expect(pts).not.toContain('NaN');
  });

  it('renders SVG when all candles have the same price (zero range)', () => {
    const history = Array.from({ length: 5 }, () => makeCandle(200));
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="FLAT" chartInterval="1d" currency="$" />
    );
    expect(container.querySelector('svg')).toBeTruthy();
    const polyline = container.querySelector('polyline');
    const pts = polyline.getAttribute('points') || '';
    expect(pts).not.toContain('Infinity');
    expect(pts).not.toContain('NaN');
  });

  it('shows date labels for daily interval', () => {
    const history = [
      makeCandle(100, '2024-01-10T00:00:00'),
      makeCandle(105, '2024-01-15T00:00:00'),
    ];
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="AAPL" chartInterval="1d" currency="$" />
    );
    const texts = [...container.querySelectorAll('text')].map((t) => t.textContent);
    // Should have start and end date labels (not blank)
    const dateLabels = texts.filter((t) => t.includes('Jan'));
    expect(dateLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('shows date+time for intraday interval spanning multiple days', () => {
    const history = [
      makeCandle(100, '2024-01-10T09:15:00'),
      makeCandle(105, '2024-01-15T15:30:00'),
    ];
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="AAPL" chartInterval="15m" currency="$" />
    );
    const texts = [...container.querySelectorAll('text')].map((t) => t.textContent);
    // Multi-day span with intraday interval should include month name, not just time
    const hasDate = texts.some((t) => t.includes('Jan'));
    expect(hasDate).toBe(true);
  });

  it('handles Twelve Data space-separated timestamps', () => {
    const history = [
      makeCandle(100, '2024-01-10 09:15:00'),
      makeCandle(110, '2024-01-15 15:30:00'),
    ];
    // Should not throw and should render SVG
    const { container } = render(
      <ChartPanel history={history} selectedSymbol="RELIANCE.NS" chartInterval="1d" currency="₹" />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });
});
