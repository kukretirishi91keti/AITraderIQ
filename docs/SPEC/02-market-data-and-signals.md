# Module 2: Market Data & Module 3: Technical Signals

---

## Module 2: Market Data

### User Story
> As a user, I can view real-time quotes, historical price charts, financial metrics, and top market movers for any symbol across 22 global markets. Data shows quality indicators (LIVE/CACHED/SIMULATED) so I know what I'm looking at.

### Data Quality Tiers

| Tier | Label | Source | When Used |
|------|-------|--------|-----------|
| 1 | LIVE | yfinance real-time | Primary - fresh API call succeeds |
| 2 | CACHED | File cache (< 5 min old) | yfinance rate-limited or slow |
| 3 | LKG | File cache (5 min - 1 hr old) | Last Known Good, stale but usable |
| 4 | SIMULATED | Deterministic algorithm | All sources fail, or DEMO_MODE=true |

### Fallback Hierarchy
```
yfinance API call (15s timeout)
  |-- Success --> Return LIVE data, update cache
  |-- Timeout/Error --> Check file cache
        |-- Fresh (< 5 min) --> Return CACHED
        |-- Stale (< 1 hr) --> Return LKG with warning
        |-- Expired/Missing --> Generate SIMULATED data
```

### Endpoints

#### Single Quote
| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/v4/quote/{symbol}` | No | `{success, symbol, price, currency, change, change_pct, volume, market, dayOpen, dayHigh, dayLow, companyName, timestamp, dataQuality, source}` |

**Example**: `GET /api/v4/quote/AAPL`
```json
{
  "success": true,
  "symbol": "AAPL",
  "price": 238.50,
  "currency": "$",
  "change": 1.50,
  "change_pct": 0.63,
  "volume": 45000000,
  "market": "US",
  "dataQuality": "LIVE",
  "source": "Yahoo Finance"
}
```

#### Batch Quotes
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| GET | `/api/v4/quotes` | No | Query: `symbols=AAPL,MSFT` | `{success, results: {AAPL: {...}, MSFT: {...}}}` |
| POST | `/api/v4/quotes` | No | `{symbols: [...], include_candles: bool}` | Same + optional miniChart |

#### Historical Data / Candles
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| GET | `/api/v4/history/{symbol}` | No | Query: `period=1mo` (1d/5d/1mo/3mo/6mo/1y/max) | `{symbol, period, prices: [{date, open, high, low, close, volume}]}` |
| GET | `/api/v4/candles/{symbol}` | No | Query: `interval=1d` (1m/5m/15m/30m/1h/4h/1d), `lookback=100` (5-500) | `{success, symbol, interval, count, results: [{timestamp, open, high, low, close, volume}], source, dataQuality}` |

#### Financials
| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/v4/financials/{symbol}` | No | `{symbol, marketCap, peRatio, revenue, eps, dividendYield, beta, high52w, low52w, source}` |

#### Market Overview & Top Movers
| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/v4/market-overview` | No | `{indices: [...], market_status, timestamp}` |
| GET | `/api/v4/top-movers/{market}` | No | `{market, movers: [{symbol, price, change_pct, rank}], timestamp}` |

#### Stock Info
| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/v4/stock/{symbol}` | No | Company info (name, sector, market cap, dividend) |
| GET | `/api/v4/watchlist` | No | Query: `symbols=...` - batch response for dashboard |

### Service: market_data_service.py
- **Caching**: Check-Lock-Check-Write pattern (prevents thundering herd)
- **Timeouts**: Quote fetch = 15s, History fetch = 30s
- **Circuit breaker**: Auto-fallback after consecutive failures
- **Currency mapping**: Auto-detects currency from market suffix

---

## Module 3: Technical Signals

### User Story
> As a user, when I view a stock's technicals tab, I see real RSI, MACD, Bollinger Bands, ATR, VWAP, SMA, and EMA computed from actual OHLCV history data. The signal recommendation (BUY/SELL/HOLD) is based on real indicator thresholds, not random data.

### How Signals Are Computed (Real Data Pipeline)

```
1. Fetch 1 month daily OHLCV history via market_data_service.get_history()
2. Extract close prices array
3. Compute each indicator from actual prices:

RSI(14):
  - Calculate daily price changes
  - Separate gains and losses
  - Wilder's smoothed average: avg_gain = (prev_avg * 13 + current_gain) / 14
  - RS = avg_gain / avg_loss
  - RSI = 100 - (100 / (1 + RS))

MACD(12, 26, 9):
  - EMA_12 = Exponential Moving Average of close prices (span=12)
  - EMA_26 = Exponential Moving Average of close prices (span=26)
  - MACD line = EMA_12 - EMA_26
  - Signal line = EMA of MACD line (span=9)
  - Histogram = MACD - Signal

Bollinger Bands(20, 2):
  - Middle = SMA(20) of close prices
  - Std = Standard deviation of last 20 closes
  - Upper = Middle + 2 * Std
  - Lower = Middle - 2 * Std

ATR(14):
  - True Range = max(high-low, |high-prev_close|, |low-prev_close|)
  - ATR = SMA of True Range over 14 periods

VWAP:
  - Typical Price = (high + low + close) / 3
  - VWAP = sum(TP * volume) / sum(volume)

SMA(20): Simple moving average of last 20 closes
EMA(12): Exponential moving average (span=12)
```

### Signal Logic
```
IF RSI < 30 AND MACD histogram > 0:
    signal = "STRONG_BUY", confidence = high
ELIF RSI < 40 AND MACD histogram > 0:
    signal = "BUY", confidence = moderate
ELIF RSI > 70 AND MACD histogram < 0:
    signal = "STRONG_SELL", confidence = high
ELIF RSI > 60 AND MACD histogram < 0:
    signal = "SELL", confidence = moderate
ELSE:
    signal = "HOLD", confidence = low-moderate

Support = Bollinger Lower Band
Resistance = Bollinger Upper Band
```

### Endpoints

| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/v4/signals/{symbol}` | No | See response below |

**Response Schema**:
```json
{
  "symbol": "AAPL",
  "signal": "BUY",
  "confidence": 0.72,
  "rsi": 35.4,
  "macd": {"macd": 1.23, "signal": 0.98, "histogram": 0.25},
  "bollinger": {"upper": 245.0, "middle": 238.0, "lower": 231.0},
  "atr": 4.52,
  "vwap": 237.80,
  "sma_20": 238.0,
  "ema_12": 239.1,
  "support": 231.0,
  "resistance": 245.0,
  "source": "LIVE",
  "timestamp": "2026-03-29T10:30:00Z"
}
```

**Fallback**: If history fetch fails, falls back to demo signal generation (source = "SIMULATED")

### Test Checkpoints

| # | Test | How to Verify | Expected |
|---|------|--------------|----------|
| 2.1 | Quote returns price | GET `/api/v4/quote/AAPL` | 200, `price` is a positive number |
| 2.2 | Quote has dataQuality | Check response | `dataQuality` is one of: LIVE, CACHED, LKG, SIMULATED, DEMO |
| 2.3 | Quote has timestamp | Check response | ISO timestamp present |
| 2.4 | History returns data | GET `/api/v4/history/AAPL?period=1mo` | Non-empty array of price objects |
| 2.5 | Candles with intervals | GET `/api/v4/candles/AAPL?interval=1d` | Array of OHLCV candles |
| 2.6 | Candles with intervals | GET `/api/v4/candles/AAPL?interval=1h` | 200 response |
| 2.7 | Financials valid | GET `/api/v4/financials/AAPL` | Non-empty dict with financial metrics |
| 2.8 | Top movers | GET `/api/v4/top-movers/US` | Array of movers with price and change_pct |
| 2.9 | Market overview | GET `/api/v4/market-overview` | 200 response |
| 2.10 | Batch quotes | POST `/api/v4/quotes` with `{symbols: ["AAPL","MSFT"]}` | Both symbols in results |
| 2.11 | Demo mode never errors | All endpoints return 200 when DEMO_MODE=true | No 500 errors |
| 3.1 | Signals has RSI | GET `/api/v4/signals/AAPL` | `rsi` is 0-100 |
| 3.2 | Signal recommendation | Check `signal` field | One of: BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL |
| 3.3 | Confidence range | Check `confidence` | 0 to 100 |
| 3.4 | Bollinger bands present | Check response | Has upper, middle, lower |
| 3.5 | MACD present | Check response | Has macd, signal, histogram |
| 3.6 | Source field | Check `source` | LIVE, CACHED, or SIMULATED |
| 3.7 | Signals for Indian stock | GET `/api/v4/signals/RELIANCE.NS` | 200 with valid indicators |
| 3.8 | Signals for crypto | GET `/api/v4/signals/BTC-USD` | 200 with valid indicators |

### Existing Test Files
- `tests/test_market_data.py` (10 tests) - Quotes, history, financials, batch, movers
- `tests/test_signals_and_backtest.py` (11 tests) - Signal values, ranges, backtest metrics
- `tests/test_data_provenance.py` (10 tests) - Data quality fields, source tracking
