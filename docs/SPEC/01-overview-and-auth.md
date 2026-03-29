# AITraderIQ - Project Specification

## 1. Project Overview

### What It Is
AITraderIQ is a full-stack AI-powered trading intelligence dashboard. Users can track stocks across 22 global markets, get real technical analysis signals, manage watchlists and portfolios, simulate trades via paper trading, and receive AI-driven strategy recommendations.

### Architecture
```
Frontend (React/Vite)          Backend (FastAPI/Python)
-------------------------      ---------------------------
  App.jsx                        main.py
  Components/Modals              Routers (15+ endpoint groups)
  Services (auth, websocket)     Services (9 business logic modules)
  Context (Auth, Stock)          Database (SQLAlchemy async)
  Constants (markets, config)    Middleware (rate limit, logging)
                                 Auth (JWT/bcrypt)
        |                              |
        +--- REST API (HTTP) ----------+
        +--- WebSocket (ws/prices) ----+
        +--- localStorage (offline) ---+
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, vanilla CSS |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Database | SQLite (dev) / PostgreSQL (prod), SQLAlchemy async, Alembic migrations |
| Auth | JWT (python-jose), bcrypt password hashing |
| Market Data | yfinance (primary), file cache (fallback), simulator (demo) |
| AI | Groq LLM (Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2 9B) |
| Real-time | WebSocket (FastAPI native) |
| Payments | Stripe (international), Razorpay (India) |

### Supported Markets (22)

| Market | Currency | Symbol Suffix | Example |
|--------|----------|---------------|---------|
| US | $ | (none) | AAPL, MSFT |
| India | INR | .NS | RELIANCE.NS |
| UK | GBP | .L | HSBA.L |
| Germany | EUR | .DE | SAP.DE |
| France | EUR | .PA | MC.PA |
| Japan | JPY | .T | 7203.T |
| China | CNY | .SS | 600519.SS |
| Hong Kong | HKD | .HK | 0700.HK |
| Taiwan | TWD | .TW | 2330.TW |
| Australia | AUD | .AX | BHP.AX |
| Canada | CAD | .TO | SHOP.TO |
| Brazil | BRL | .SA | VALE3.SA |
| Korea | KRW | .KS | 005930.KS |
| Singapore | SGD | .SI | D05.SI |
| Switzerland | CHF | .SW | NESN.SW |
| Netherlands | EUR | .AS | ASML.AS |
| Spain | EUR | .MC | ITX.MC |
| Italy | EUR | .MI | ENEL.MI |
| Sweden | SEK | .ST | VOLV-B.ST |
| Crypto | USD | -USD | BTC-USD |
| ETF | USD | (none) | SPY, QQQ |
| Forex | USD | =X | EURUSD=X |
| Commodities | USD | =F | GC=F |

---

## 2. Environment Variables

| Variable | Default | Required (prod) | Purpose |
|----------|---------|:---:|---------|
| `DEMO_MODE` | `true` | No | Use simulated data when `true` |
| `JWT_SECRET_KEY` | `CHANGE-THIS-...` | **Yes** | JWT signing key (min 32 chars). Generate: `openssl rand -hex 32` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./traderai.db` | **Yes** (PostgreSQL) | DB connection string |
| `GROQ_API_KEY` | `""` | No | Groq LLM API key (AI features fall back to rule-based without it) |
| `NEWSAPI_KEY` | `""` | No | NewsAPI.org key for real news |
| `STRIPE_SECRET_KEY` | `""` | No | Stripe payment gateway |
| `STRIPE_WEBHOOK_SECRET` | `""` | No | Stripe webhook verification |
| `RAZORPAY_KEY_ID` | `""` | No | Razorpay payment (India) |
| `RAZORPAY_KEY_SECRET` | `""` | No | Razorpay auth |
| `CORS_ORIGINS` | `localhost:5173,...` | No | Comma-separated allowed origins |
| `JWT_EXPIRE_MINUTES` | `1440` (24h) | No | Token TTL |
| `RATE_LIMIT_DEFAULT` | `60/minute` | No | General rate limit |
| `RATE_LIMIT_AI` | `10/minute` | No | AI endpoint rate limit |
| `PORT` | `8000` | No | Server port |

### Startup Validation Rules
- **Fatal in production** (DEMO_MODE=false): Default JWT secret, SQLite database
- **Warning only** (DEMO_MODE=true): All of the above just log warnings

---

## 3. Module 1: Authentication & User Management

### User Story
> As a user, I can register, log in, and manage my profile. My session persists via JWT token stored in the browser. Protected features (watchlist, portfolio, alerts, paper trading) require authentication.

### Endpoints

| Method | Path | Auth | Request Body | Response |
|--------|------|:----:|-------------|----------|
| POST | `/api/auth/register` | No | `{email, username (3-100 chars), password (8-128 chars), full_name, trader_style}` | `201: {access_token, token_type: "bearer", user: {id, email, username, full_name, trader_style}}` |
| POST | `/api/auth/login` | No | Form: `username` (accepts email too), `password` | `200: {access_token, token_type: "bearer", user: {id, email, username, ...}}` |
| GET | `/api/auth/me` | **Yes** | - | `200: {id, email, username, full_name, trader_style, risk_tolerance, created_at}` |
| PUT | `/api/auth/me` | **Yes** | `{full_name?, trader_style?, risk_tolerance?}` | `200: updated user object` |

### JWT Token Flow
```
1. Register/Login -> Server creates JWT {sub: user_id, exp: now+24h}
2. Client stores token in localStorage key "traderai_token"
3. Client sends: Authorization: Bearer <token>
4. Server decodes, fetches User from DB, injects into endpoint
5. 401 returned if: missing token, expired, invalid, user inactive
```

### Security Details
- Password hashing: bcrypt with auto-salt
- Token algorithm: HS256
- Input sanitization: HTML/script tags stripped from `full_name` on register and profile update
- Duplicate email/username: returns 400

### Users Table Schema

| Column | Type | Constraints |
|--------|------|------------|
| id | Integer | PK, auto-increment |
| email | String(255) | Unique, indexed, not null |
| username | String(100) | Unique, indexed, not null |
| hashed_password | String(255) | Not null |
| full_name | String(255) | Default "" |
| trader_style | String(50) | Default "swing" |
| risk_tolerance | String(50) | Default "moderate" |
| is_active | Boolean | Default true |
| plan | String(20) | Default "free" |
| stripe_customer_id | String(255) | Nullable |
| plan_expires_at | DateTime | Nullable |
| ai_queries_today | Integer | Default 0 |
| ai_queries_reset_at | DateTime | Nullable |
| created_at | DateTime | Auto UTC |
| updated_at | DateTime | Auto UTC, on update |

### Test Checkpoints

| # | Test | How to Verify | Expected |
|---|------|--------------|----------|
| 1.1 | Register new user | POST `/api/auth/register` with valid data | 201, returns access_token + user object (no hashed_password exposed) |
| 1.2 | Duplicate email | Register same email twice | 400 error |
| 1.3 | Duplicate username | Register same username twice | 400 error |
| 1.4 | Short password | Password < 8 chars | 422 validation error |
| 1.5 | Login valid | POST `/api/auth/login` with correct credentials | 200, returns token |
| 1.6 | Login wrong password | Wrong password | 401 |
| 1.7 | Login nonexistent user | Unknown username | 401 |
| 1.8 | Get profile (auth) | GET `/api/auth/me` with valid Bearer token | 200, user data |
| 1.9 | Get profile (no auth) | GET `/api/auth/me` without token | 401 |
| 1.10 | Get profile (expired token) | Use expired JWT | 401 |
| 1.11 | Update profile | PUT `/api/auth/me` with `{trader_style: "day"}` | 200, updated value |
| 1.12 | XSS in full_name | Register with `<script>alert(1)</script>` in full_name | Stored without script tags |

### Existing Test Files
- `tests/test_auth.py` (5 tests) - Basic auth flows
- `tests/test_auth_complete.py` (15 tests) - Comprehensive auth with validation
- `tests/test_security.py` (4 tests) - Password hashing + JWT unit tests
