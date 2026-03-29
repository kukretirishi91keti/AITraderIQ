# Module 9: Backtesting & Scanner | Module 10: Commentary | Module 11: Screener | Module 12: Subscriptions | Module 13: WebSocket

---

## Module 9: Backtesting & AI Scanner

### User Story (Backtest)
> As a user, I can backtest signal accuracy for any stock across 4 trader types. I see win rate, average return, Sharpe ratio, and signal breakdown. I can compare all 4 strategies side-by-side to see which is recommended.

### User Story (Scanner)
> As a user, I can view AI-ranked trading opportunities. Each stock gets a composite score (0-100) based on technical strength, backtest accuracy, sentiment, and risk-adjusted returns.

### Backtest Endpoints

| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| GET | `/api/backtest/run/{symbol}` | No | Query: `trader_type` (scalp/day/swing/position), `periods` (50-500, default 150) | `{win_rate, avg_return_pct, sharpe_ratio, total_signals, signal_breakdown: {BUY, SELL, HOLD}, recent_signals}` |
| GET | `/api/backtest/compare` | No | Query: `symbol, periods` | `{strategies: {scalp: {...}, day: {...}, swing: {...}, position: {...}}, recommended, reason}` |
| GET | `/api/backtest/leaderboard` | No | Query: `trader_type` | `{leaderboard: [{symbol, win_rate, avg_return, sharpe_ratio}]}` |

### Evaluation Periods by Trader Type

| Type | Look-ahead Periods | Approximate Time |
|------|-------------------|-----------------|
| Scalp | 1 period | ~15 minutes |
| Day | 4 periods | ~1 hour |
| Swing | 20 periods | ~1 week |
| Position | 60 periods | ~3 months |

### Backtest Metrics
- **win_rate** (0-100%): % of signals that resulted in profit
- **avg_return_pct**: Mean return per signal
- **sharpe_ratio**: Risk-adjusted return (return / volatility)
- **total_signals**: Number of signals evaluated
- **signal_breakdown**: Count of BUY, SELL, HOLD signals
- **recent_signals**: Last 10 signals with entry price, confidence, RSI

### AI Scanner Endpoint

| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| GET | `/api/scanner/opportunities` | No | Query: `trader_type?`, `symbols?` (comma list) | `{opportunities: [{symbol, ai_score, direction, signal, confidence, sentiment_score, win_rate, ranked}]}` |

### AI Score Formula (0-100)
```
ai_score = (0.40 * signal_confidence)     // Technical strength
         + (0.25 * backtest_win_rate)      // Historical accuracy
         + (0.20 * normalized_sentiment)   // Market mood
         + (0.15 * risk_adjusted_score)    // Sharpe * 30 + 50
```

---

## Module 10: Market Commentary

### User Story
> As a user, I see AI-generated market commentary highlighting significant moves. Only stocks with notable activity (>3% price move, extreme RSI, volume spikes, Bollinger breakouts) get commentary, reducing noise.

### Endpoints

| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/commentary/{symbol}` | No | `{symbol, commentary, triggered_by, severity: "normal\|medium\|high", timestamp}` |
| GET | `/api/commentary/market/digest` | No | `{digest, symbols_analyzed, significant_moves: [{symbol, commentary, severity}]}` |

### Trigger Conditions
- Price move > 5% -> severity: high
- Price move > 3% -> severity: medium
- RSI < 25 or > 75 -> oversold/overbought alert
- Volume > 2x average -> volume spike
- Price outside Bollinger Bands -> breakout

### AI Generation
- Uses Groq LLM with context about the move
- Falls back to rule-based templates if API unavailable
- Commentary refreshes every 5 minutes on the frontend

---

## Module 11: Screener

### User Story
> As a user, I can browse all tradable symbols organized by market. I can filter by RSI oversold (<30), overbought (>70), or buy signal. Each stock card shows symbol, price, change%, RSI, and signal direction.

### Endpoints

| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/screener/universe` | No | `{US_Tech: [{symbol, ...}], India: [...], UK: [...], ...}` grouped by market |
| GET | `/api/screener/movers` | No | Query: `market, limit` -> Top movers |
| GET | `/api/screener/signals` | No | Query: `symbols` -> Bulk signals |

### Frontend Filters
- **All**: Show everything
- **RSI < 30**: Oversold stocks (potential buys)
- **RSI > 70**: Overbought stocks (potential sells)
- **Buy Signal**: Only stocks with BUY/STRONG_BUY recommendation

---

## Module 12: Subscriptions & Billing

### User Story
> As a user, I start on the Free plan with limited AI queries. I can upgrade to Pro or Premium for more features. Payments are handled via Stripe (international) or Razorpay (India).

### Plan Tiers

| Feature | Free | Pro ($9.99/mo) | Premium ($29.99/mo) |
|---------|------|----------------|---------------------|
| AI queries/day | 5 | 100 | Unlimited |
| Watchlist symbols | 10 | Unlimited | Unlimited |
| Number of watchlists | 1 | 10 | Unlimited |
| Alerts | 3 | 50 | Unlimited |
| Paper trading | - | Yes | Yes |
| Strategy intelligence | Basic | Full | Full |
| Real-time data | - | - | Yes |
| Support | Community | Priority | 1-on-1 |
| Price (INR) | Free | Rs799/mo | Rs2,499/mo |

### Endpoints

| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| GET | `/api/subscription/plans` | No | - | `{plans: [{id, name, price_usd, price_inr, limits}]}` |
| GET | `/api/subscription/my-plan` | **Yes** | - | `{plan, expires_at, ai_queries_today, ai_queries_remaining}` |
| POST | `/api/subscription/checkout` | **Yes** | `{plan: "pro\|premium", gateway: "stripe\|razorpay"}` | `{checkout_url}` or demo upgrade |
| POST | `/api/subscription/webhook/stripe` | No | Stripe webhook payload | Payment confirmation |
| POST | `/api/subscription/webhook/razorpay` | No | Razorpay webhook payload | Payment confirmation |

### Credit System
- `ai_queries_today` increments on each AI query
- Resets daily (checked via `ai_queries_reset_at`)
- Free: 5/day, Pro: 100/day, Premium: unlimited (-1)

---

## Module 13: WebSocket Real-Time Prices

### User Story
> As a user, I see live price updates without refreshing the page. The connection status shows as a green dot when connected. If the connection drops, it auto-reconnects with exponential backoff.

### Protocol

**Endpoint**: `ws://host:8000/ws/prices?token=<jwt>` (token optional for auth)

```
Client -> Server: Subscribe
{"action": "subscribe", "symbols": ["AAPL", "MSFT"]}

Server -> Client: Confirmation
{"type": "subscribed", "symbols": ["AAPL", "MSFT"]}

Server -> Client: Price Update (streaming)
{"type": "quote", "symbol": "AAPL", "price": 238.50, "change": 1.50, "changePercent": 0.63, "volume": 45000000, "dataQuality": "LIVE"}

Client -> Server: Unsubscribe
{"action": "unsubscribe", "symbols": ["AAPL"]}

Client -> Server: Ping (keepalive every 30s)
{"action": "ping"}

Server -> Client: Pong
{"type": "pong"}

Client -> Server: Status
{"action": "status"}

Server -> Client: Stats
{"type": "stats", "connections": 150, "symbols_tracked": 45}
```

### Reconnection
- Auto-reconnect on close with exponential backoff: 1s, 2s, 4s, 8s... up to 30s max
- Re-subscribes to all previous symbols on reconnect
- Frontend shows "CONNECTING" state during reconnect

### Test Checkpoints

| # | Test | How to Verify | Expected |
|---|------|--------------|----------|
| 9.1 | Backtest returns metrics | GET `/api/backtest/run/AAPL?trader_type=swing` | win_rate (0-100), sharpe_ratio present |
| 9.2 | Win rate range | Check win_rate | 0-100 |
| 9.3 | Compare 4 strategies | GET `/api/backtest/compare?symbol=AAPL` | All 4 trader types present + recommended |
| 9.4 | Period validation | periods=10 (below 50) | 422 |
| 9.5 | Leaderboard | GET `/api/backtest/leaderboard` | Ranked list |
| 9.6 | Scanner ranking | GET `/api/scanner/opportunities` | ai_score 0-100 per symbol |
| 10.1 | Commentary for symbol | GET `/api/commentary/AAPL` | Has commentary text |
| 10.2 | Market digest | GET `/api/commentary/market/digest` | digest field present |
| 11.1 | Screener universe | GET `/api/screener/universe` | Grouped by market |
| 12.1 | Plans list | GET `/api/subscription/plans` | 3 plans with USD + INR prices |
| 12.2 | My plan (auth) | GET `/api/subscription/my-plan` | Current tier |
| 12.3 | My plan (no auth) | Without token | 401 |
| 12.4 | Checkout invalid plan | POST with plan: "invalid" | 422 |
| 13.1 | WS connect | Connect to `/ws/prices` | Receives type=connected |
| 13.2 | WS subscribe | Send subscribe action | Receives confirmation |
| 13.3 | WS ping/pong | Send ping | Receives pong |
| 13.4 | WS invalid action | Send unknown action | Error message |

### Existing Test Files
- `tests/test_signals_and_backtest.py` (11 tests) - Backtest metrics + signals
- `tests/test_sentiment_and_news.py` (7 tests) - Commentary + sentiment
- `tests/test_subscription_and_credits.py` (7 tests) - Plans, credits, checkout
- `tests/test_websocket.py` (6 tests) - WS protocol
