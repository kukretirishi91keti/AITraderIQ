# Module 4: Watchlist, Portfolio & Alerts | Module 5: Paper Trading

---

## Module 4: User Data Management

### User Story
> As a logged-in user, my watchlist, portfolio, and alerts are saved to the database. When I log in on any device, my data is there. When I'm not logged in, I can still use local state but nothing persists.

### 4A: Watchlist

#### Endpoints (all require auth)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/user/watchlist` | - | `{count, watchlist: [{id, symbol, market, notes, added_at}]}` |
| POST | `/api/user/watchlist` | `{symbol, market: "US", notes: ""}` | `201: {id, symbol, market, notes, added_at}` |
| DELETE | `/api/user/watchlist/{symbol}` | - | `{success: true}` |

#### Behavior
- Adding a duplicate symbol returns 400
- Watchlist is ordered by `sort_order`, then `added_at`
- Notes are sanitized (HTML/script tags stripped)
- User A cannot see User B's watchlist (data isolation)

#### Frontend Sync (App.jsx)
```
On login:
  -> refreshWatchlistFromApi() fetches GET /api/user/watchlist
  -> Maps response to local state: setWatchlist(data.watchlist.map(i => i.symbol))

On add (press W or click):
  -> Updates local state immediately (optimistic)
  -> Calls apiAddToWatchlist(symbol, market) in background
  -> On failure: silently keeps local state

On remove:
  -> Updates local state immediately
  -> Calls apiRemoveFromWatchlist(symbol) in background

WatchlistEditModal:
  -> Uses callback props (onAdd, onRemove, onClear, onReorder, onAddAlert)
  -> All callbacks call API when logged in, update local state always
```

#### Watchlist Items Table

| Column | Type | Constraints |
|--------|------|------------|
| id | Integer | PK |
| user_id | Integer | FK -> users.id, not null |
| symbol | String(20) | Not null |
| market | String(20) | Default "US" |
| notes | Text | Default "" |
| sort_order | Integer | Default 0 |
| added_at | DateTime | Auto UTC |

---

### 4B: Portfolio

#### Endpoints (all require auth)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/user/portfolio` | - | `{count, holdings: [{id, symbol, shares, avg_price, currency, market, notes, updated_at}]}` |
| POST | `/api/user/portfolio` | `{symbol, shares (>0), avg_price (>0), currency: "$", market: "US", notes: ""}` | `201: portfolio item` |
| PUT | `/api/user/portfolio/{id}` | `{shares?, avg_price?, notes?}` | Updated item |
| DELETE | `/api/user/portfolio/{id}` | - | `{success: true}` |

#### Behavior
- Negative shares rejected (422)
- Zero avg_price rejected (422)
- Update nonexistent ID returns 404
- User isolation enforced (can't access other user's portfolio)
- Notes are sanitized

#### Frontend Sync
```
On login:
  -> refreshPortfolioFromApi() fetches GET /api/user/portfolio
  -> Maps to local: setPortfolio(data.holdings.map(i => ({id, symbol, shares, avgPrice: i.avg_price, ...})))

AddToPortfolioModal:
  -> Shows current price, shares input, avg price input
  -> On submit: calls apiAddToPortfolio() then refreshPortfolioFromApi()

PortfolioModal:
  -> Displays table: Symbol, Shares, Avg Price, Current Price, Value, P&L, P&L%
  -> P&L = (currentPrice - avgPrice) * shares
  -> Remove calls apiRemoveFromPortfolio(id)
```

#### Portfolio Items Table

| Column | Type | Constraints |
|--------|------|------------|
| id | Integer | PK |
| user_id | Integer | FK -> users.id, not null |
| symbol | String(20) | Not null |
| shares | Float | Not null, >0 |
| avg_price | Float | Not null, >0 |
| currency | String(10) | Default "$" |
| market | String(20) | Default "US" |
| notes | Text | Default "" |
| added_at | DateTime | Auto UTC |
| updated_at | DateTime | Auto UTC, on update |

---

### 4C: Alerts

#### Endpoints (all require auth)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/api/user/alerts` | - | `{count, alerts: [{id, symbol, condition, target_value, is_active, is_triggered, triggered_at, created_at}]}` |
| POST | `/api/user/alerts` | `{symbol, condition, target_value}` | `201: alert object` |
| DELETE | `/api/user/alerts/{id}` | - | `{success: true}` |

#### Conditions
- `above` - trigger when price >= target
- `below` - trigger when price <= target
- `rsi_above` - trigger when RSI >= target
- `rsi_below` - trigger when RSI <= target

#### Alerts Table

| Column | Type | Constraints |
|--------|------|------------|
| id | Integer | PK |
| user_id | Integer | FK -> users.id, not null |
| symbol | String(20) | Not null |
| condition | String(20) | Not null |
| target_value | Float | Not null |
| is_triggered | Boolean | Default false |
| is_active | Boolean | Default true |
| triggered_at | DateTime | Nullable |
| created_at | DateTime | Auto UTC |

---

## Module 5: Paper Trading

### User Story
> As a logged-in user, I can place simulated (paper) trades at the current market price, track open positions, close them at the current price to see my P&L, and view my overall win rate and total P&L. This lets me test strategies without risking real money.

### Endpoints (all require auth)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/paper-trade` | `{symbol, side: "buy\|sell", quantity (>0), strategy?, notes?}` | `201: {id, symbol, side, quantity, entry_price, currency, status: "open", message}` |
| GET | `/api/paper-trade` | Query: `status=open\|closed` (optional) | `{count, trades: [{id, symbol, side, quantity, entry_price, exit_price, status, strategy, market, currency, pnl, pnl_percent, notes, opened_at, closed_at}]}` |
| POST | `/api/paper-trade/{id}/close` | - | `{id, symbol, side, entry_price, exit_price, quantity, pnl, pnl_percent, currency, status: "closed", message}` |
| DELETE | `/api/paper-trade/{id}` | - | `{message: "Paper trade deleted"}` |
| GET | `/api/paper-trade/summary` | - | `{total_trades, open_positions, closed_trades, wins, losses, win_rate, total_pnl}` |

### How It Works

#### Place Trade
1. User submits symbol + side (buy/sell) + quantity
2. Backend fetches current market price via `market_data_service.get_quote(symbol)`
3. Creates PaperTrade record with entry_price = current price
4. Returns trade confirmation with entry price

#### Close Trade
1. User clicks "Close" on an open trade
2. Backend fetches current price as exit_price
3. Calculates P&L:
   - Buy trade: `pnl = (exit_price - entry_price) * quantity`
   - Sell trade: `pnl = (entry_price - exit_price) * quantity`
   - `pnl_percent = pnl / (entry_price * quantity) * 100`
4. Updates trade status to "closed", sets `closed_at`

#### Summary Stats
- `win_rate = wins / closed_trades * 100`
- `total_pnl = sum of all closed trade pnl`

### Paper Trades Table

| Column | Type | Constraints |
|--------|------|------------|
| id | Integer | PK |
| user_id | Integer | FK -> users.id, not null |
| symbol | String(20) | Not null |
| side | String(10) | Not null ("buy" or "sell") |
| quantity | Float | Not null, >0 |
| entry_price | Float | Not null |
| exit_price | Float | Nullable |
| status | String(20) | Default "open" |
| strategy | String(50) | Nullable |
| market | String(20) | Default "US" |
| currency | String(10) | Default "$" |
| pnl | Float | Nullable |
| pnl_percent | Float | Nullable |
| notes | Text | Default "" |
| opened_at | DateTime | Auto UTC |
| closed_at | DateTime | Nullable |

### Test Checkpoints

| # | Test | How to Verify | Expected |
|---|------|--------------|----------|
| 4.1 | Watchlist starts empty | GET `/api/user/watchlist` (new user) | `{count: 0, watchlist: []}` |
| 4.2 | Add to watchlist | POST `{symbol: "AAPL", market: "US"}` | 201 |
| 4.3 | Duplicate watchlist add | POST same symbol again | 400 |
| 4.4 | Remove from watchlist | DELETE `/api/user/watchlist/AAPL` | 200 |
| 4.5 | Remove nonexistent | DELETE unknown symbol | 404 |
| 4.6 | Watchlist isolation | User A adds AAPL, User B queries | User B doesn't see it |
| 4.7 | Portfolio add | POST `{symbol: "AAPL", shares: 10, avg_price: 150}` | 201 |
| 4.8 | Portfolio negative shares | POST `{shares: -5}` | 422 |
| 4.9 | Portfolio zero price | POST `{avg_price: 0}` | 422 |
| 4.10 | Portfolio update | PUT with new shares/price | 200, values updated |
| 4.11 | Portfolio delete | DELETE `/api/user/portfolio/{id}` | 200 |
| 4.12 | Alerts create | POST `{symbol: "AAPL", condition: "above", target_value: 250}` | 201 |
| 4.13 | Invalid alert condition | POST `{condition: "invalid"}` | 422 |
| 4.14 | Alert delete | DELETE `/api/user/alerts/{id}` | 200 |
| 4.15 | All CRUD requires auth | All endpoints without token | 401 |
| 5.1 | Place paper trade | POST `/api/paper-trade` with buy order | 201, entry_price is current market price |
| 5.2 | List open trades | GET `/api/paper-trade?status=open` | Trade appears |
| 5.3 | Close trade | POST `/api/paper-trade/{id}/close` | Returns pnl and pnl_percent |
| 5.4 | Delete trade | DELETE `/api/paper-trade/{id}` | 200 |
| 5.5 | Summary stats | GET `/api/paper-trade/summary` | Correct win_rate and total_pnl |
| 5.6 | Cannot close already closed | Close same trade twice | 400 |
| 5.7 | Trade not found | Close nonexistent ID | 404 |

### Existing Test Files
- `tests/test_user_data_crud.py` (17 tests) - Watchlist, portfolio, alerts CRUD + isolation
- `tests/test_user_journeys.py` (12 tests) - End-to-end user workflows
