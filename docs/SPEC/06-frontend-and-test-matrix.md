# Module 14: Frontend UI | Test Coverage Matrix | Health & Deployment

---

## Module 14: Frontend UI

### User Story
> As a user, I interact with a single-page dashboard that shows live prices, charts, technical indicators, AI chat, sentiment, and more. I can manage my watchlist, portfolio, and alerts. I can switch between 22 markets. Keyboard shortcuts let me work fast.

### Main Layout (App.jsx)

```
+-----------------------------------------------------+
| Header: Logo | Market Selector | Search | Auth      |
+-----+-----------------------------------------------+
| Left|  Main Content Area                             |
| Bar |  +-------------------------------------------+ |
|     |  | Chart Panel (OHLCV line chart)            | |
| W   |  +-------------------------------------------+ |
| a   |  | Tab Bar: Technicals | Fundamentals |      | |
| t   |  |          Sentiment | News | AI |          | |
| c   |  |          Backtest | Scanner               | |
| h   |  +-------------------------------------------+ |
| l   |  | Tab Content                               | |
| i   |  | (signals / financials / sentiment /        | |
| s   |  |  news / AI chat / backtest / scanner)      | |
| t   |  +-------------------------------------------+ |
|     |  | Top Movers | Market Commentary             | |
+-----+-----------------------------------------------+
```

### Components

| Component | File | What It Renders |
|-----------|------|----------------|
| ChartPanel | `components/ChartPanel.jsx` | SVG price chart with area gradient, min/max labels, responsive |
| TopMovers | (inline in App.jsx) | Gainers/losers for selected market, 30s refresh |
| SentimentDashboard | `components/SentimentDashboard.jsx` | Composite score, source breakdown, sample posts |
| FinancialSummary | (inline in App.jsx) | Market cap, P/E, revenue, EPS, dividend, beta, 52w range |
| BacktestPanel | `components/BacktestPanel.jsx` | Win rate, Sharpe, signal breakdown, strategy comparison |
| AIScanner | `components/AIScanner.jsx` | Ranked symbols by AI score, filter by direction |
| MarketCommentary | `components/MarketCommentary.jsx` | AI digest, per-stock commentary by severity |
| StrategyIntelligence | `components/StrategyIntelligence.jsx` | 3-step wizard: input -> analyze -> results |
| InvestorProfile | `components/InvestorProfile.jsx` | Risk tolerance, horizon, experience (saved to localStorage) |
| DataStatusBadge | `components/DataStatusBadge.jsx` | LIVE/CACHED/SIMULATED badge with expandable details |
| ConnectionStatus | `components/ConnectionStatus.jsx` | Green dot = connected, shows WS state |
| ErrorBoundary | `components/ErrorBoundary.jsx` | Catches crashes, shows reload button |

### Modals

| Modal | Trigger | Purpose |
|-------|---------|---------|
| ScreenerModal | Press `S` | Browse stock universe, filter by RSI/signal |
| PortfolioModal | Press `P` | View holdings, P&L, remove positions |
| AlertsModal | Press `A` | Create/delete price alerts |
| WatchlistEditModal | Click "Edit" on watchlist | Add/remove/reorder watchlist, drag-to-sort |
| AddToPortfolioModal | Click "+ Portfolio" | Enter shares + avg price for a stock |
| UserGuideModal | Click "?" help | Feature guide for all major features |
| KeyboardShortcutsModal | Press `?` | Shows all keyboard shortcuts |
| WhatsNextModal | (varies) | Guidance for next trading actions |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search bar |
| `1` | Set chart to 1-minute interval |
| `2` | Set chart to 5-minute interval |
| `3` | Set chart to 15-minute interval |
| `4` | Set chart to 1-hour interval |
| `5` | Set chart to 1-day interval |
| `6` | Set chart to 1-week interval |
| `W` | Toggle current symbol in watchlist |
| `P` | Open portfolio modal |
| `S` | Open screener modal |
| `A` | Open alerts modal |
| `?` | Show keyboard shortcuts help |
| `Esc` | Close any open modal |

### Frontend Services

#### auth.js
| Function | Purpose |
|----------|---------|
| `register({email, username, password, fullName, traderStyle})` | Create account |
| `login(username, password)` | Login, store token |
| `logout()` | Clear credentials |
| `getProfile()` | GET `/api/auth/me` |
| `updateProfile(updates)` | PUT `/api/auth/me` |
| `authFetch(url, options)` | Fetch with Bearer token, auto-logout on 401 |
| `getUserWatchlist()` | GET `/api/user/watchlist` |
| `addToWatchlist(symbol, market)` | POST `/api/user/watchlist` |
| `removeFromWatchlist(symbol)` | DELETE `/api/user/watchlist/{symbol}` |
| `getUserPortfolio()` | GET `/api/user/portfolio` |
| `addToPortfolio({...})` | POST `/api/user/portfolio` |
| `removeFromPortfolio(itemId)` | DELETE `/api/user/portfolio/{id}` |
| `getUserAlerts()` | GET `/api/user/alerts` |
| `createAlert({symbol, condition, targetValue})` | POST `/api/user/alerts` |
| `deleteAlert(alertId)` | DELETE `/api/user/alerts/{id}` |

#### websocket.js (PriceStream class)
| Method | Purpose |
|--------|---------|
| `connect()` | Connect to `/ws/prices`, handle reconnect |
| `subscribe(symbols)` | Subscribe to price updates |
| `unsubscribe(symbols)` | Unsubscribe from symbols |
| `disconnect()` | Close connection |
| `onQuote(callback)` | Register quote listener |
| `onConnectionChange(callback)` | Register connection state listener |

### Context Providers

#### AuthContext
```javascript
{user, isLoggedIn, showAuthModal, login, register, logout, setShowAuthModal, token}
```

#### StockContext
```javascript
{symbol, setSymbol, quote, candles, health, isLoading, error, chartInterval,
 setChartInterval, dataQuality, dataSource, dataAge, isAnchored, refreshAll}
```

### localStorage Keys
- `traderai_token` - JWT token
- `traderai_user` - User object JSON
- `investorProfile` - Investor profile settings

---

## Complete Test Coverage Matrix

### Backend Tests (19 files, 171+ tests)

| File | Tests | Module Coverage |
|------|:-----:|----------------|
| `test_auth.py` | 5 | Auth: register, login, duplicate, wrong password |
| `test_auth_complete.py` | 15 | Auth: validation, profile, expired tokens |
| `test_security.py` | 4 | Auth: password hashing, JWT creation |
| `test_health.py` | 6 | Health: ping, root, status, K8s probes |
| `test_health_and_infra.py` | 8 | Health: loaded routers, exception handler, injection |
| `test_market_data.py` | 10 | Market Data: quotes, history, financials, batch, movers |
| `test_data_provenance.py` | 10 | Market Data: dataQuality, source, timestamps |
| `test_signals_and_backtest.py` | 11 | Signals + Backtest: RSI range, recommendations, win rate |
| `test_market_strategy.py` | 10 | Strategy: intelligence, overview, catalog, validation |
| `test_trader_level_matrix.py` | 16 | Cross-cutting: styles x plans x risk levels |
| `test_ai_correctness.py` | 10 | AI: context, fallback, models, health |
| `test_sentiment_and_news.py` | 7 | Sentiment: scoring, heatmap, commentary |
| `test_user_data_crud.py` | 17 | User Data: watchlist/portfolio/alerts CRUD + isolation |
| `test_user_journeys.py` | 12 | E2E: full user workflows (register -> trade decision) |
| `test_subscription_and_credits.py` | 7 | Subscriptions: plans, credits, checkout |
| `test_websocket.py` | 6 | WebSocket: connect, subscribe, ping, unsubscribe |
| `test_validation.py` | 1 | Env validation |
| `test_smoke_50_users.py` | 3 | Load: 50 concurrent users |
| `test_smoke_1000_users.py` | 6 | Load: 1000 concurrent users (production) |

### Frontend Tests (5 files, 63 tests)

| File | Tests | Coverage |
|------|:-----:|---------|
| `auth.test.js` | 8 | Auth service: login, logout, register, authFetch |
| `api.test.js` | 9 | API service: getQuote, getCandles, batch, health |
| `websocket.test.js` | 7 | WebSocket: connect, subscribe, reconnect, ping |
| `config.test.js` | 4 | Config: API_BASE, endpoints, intervals, thresholds |
| `formatters.test.js` | 30 | Utils: formatPrice, formatLargeNumber, RSI/signal colors |

### Test Commands

```bash
# Backend (from /backend directory)
python -m pytest tests/ -q                          # All tests
python -m pytest tests/test_auth.py -q              # Auth only
python -m pytest tests/test_market_data.py -q       # Market data only
python -m pytest tests/test_user_data_crud.py -q    # CRUD only
python -m pytest tests/ -q --ignore=tests/test_smoke_1000_users.py  # Skip load test

# Frontend (from /frontend directory)
npx vitest run                                      # All tests
npx vitest run src/services/auth.test.js            # Auth service only
npx vitest run src/utils/formatters.test.js         # Formatters only
```

---

## Health & Deployment

### Health Endpoints

| Endpoint | Purpose | Use For |
|----------|---------|---------|
| GET `/ping` | Simple ping | Basic connectivity |
| GET `/` | API info | Version, loaded routers |
| GET `/status` | Detailed status | Demo mode, router list |
| GET `/api/health` | System health | Cache metrics, yfinance status, uptime |
| GET `/api/health/detailed` | Extended health | Upstream service status |
| GET `/api/health/ready` | K8s readiness | Load balancer |
| GET `/api/health/live` | K8s liveness | Process alive check |

### Health Status Levels
- **HEALTHY**: All systems operational, polling every 60s
- **DEGRADED**: Some failures, polling every 120s
- **CRITICAL**: Major failures, polling every 300s
- **ERROR**: System down, polling every 180s

### Dev vs Production Checklist

| Check | Dev | Production |
|-------|-----|-----------|
| DEMO_MODE | `true` | `false` |
| JWT_SECRET_KEY | Default OK | **Must change** (32+ chars) |
| DATABASE_URL | SQLite OK | **Must be PostgreSQL** |
| GROQ_API_KEY | Optional | Recommended |
| Rate limiting | Optional | Enable with Redis |
| CORS_ORIGINS | localhost | Specific domains only |
| Alembic migrations | Optional (create_all OK) | **Required** |

### Middleware Stack
1. **CORS**: Configurable origins, credentials allowed
2. **Rate Limiting**: Per-user (JWT) or per-IP, configurable per endpoint category
3. **Request Logging**: Method, path, status, duration, request ID
4. **Global Exception Handler**: Never leaks stack traces to client

### Starting the Application

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your keys
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend
npm install
npm run dev  # Starts on localhost:5173
```

---

## Quick Reference: All API Endpoint Groups

| Prefix | Router | Endpoints | Auth Required |
|--------|--------|:---------:|:-------------:|
| `/api/auth` | auth.py | 4 | Mixed |
| `/api/user` | user_data.py | 9 | All |
| `/api/v4` | stock.py | 10 | None |
| `/api/signals` | signals.py | 2 | None |
| `/api/screener` | screener.py | 3 | None |
| `/api/backtest` | backtest.py | 3 | None |
| `/api/scanner` | scanner.py | 1 | None |
| `/api/genai` | genai.py | 3 | None |
| `/api/sentiment` | sentiment.py | 4 | None |
| `/api/news` | news.py | 2 | None |
| `/api/commentary` | commentary.py | 2 | None |
| `/api/strategy` | strategy.py | 5 | Mixed |
| `/api/paper-trade` | paper_trade.py | 5 | All |
| `/api/subscription` | subscription.py | 5 | Mixed |
| `/api/health` | health.py | 4 | None |
| `/ws/prices` | websocket.py | 1 (WS) | Optional |
| `/`, `/ping`, `/status` | main.py | 3 | None |
| **Total** | | **66** | |
