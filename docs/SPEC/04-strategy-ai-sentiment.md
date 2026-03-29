# Module 6: Strategy Intelligence | Module 7: AI Assistant | Module 8: Sentiment & News

---

## Module 6: Strategy Intelligence

### User Story
> As a user, I can get AI-ranked strategy recommendations for any stock based on my capital, risk tolerance, time horizon, and trader style. I can then apply a strategy to create a paper trade, or analyze my entire portfolio with strategy recommendations per holding.

### Available Strategies (5)

| Key | Name | Style | Risk | Typical Hold | Best Market |
|-----|------|-------|------|-------------|-------------|
| `momentum_breakout` | Momentum Breakout | Day | High | Hours-Days | Trending/volatile |
| `mean_reversion` | Mean Reversion | Swing | Moderate | Days-Weeks | Range-bound |
| `trend_following` | Trend Following | Position | Moderate | Weeks-Months | Strong trend |
| `swing_pattern` | Swing Pattern | Swing | Moderate | Days-Weeks | Choppy |
| `scalping` | Scalping | Scalp | High | Minutes-Hours | High volume |

### Endpoints

#### Get Strategy Recommendations
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| POST | `/api/strategy/intelligence` | No | `{symbol, market?, capital (100-100M), growth_target_pct (1-500), risk_tolerance (conservative/moderate/aggressive), time_horizon (short/medium/long), trader_style (scalp/day/swing/position)}` | Ranked strategy recommendations |
| GET | `/api/strategy/intelligence/{symbol}` | No | Query params same as POST body | Same (convenience GET) |

**Response includes per strategy**:
- `rank`, `name`, `confidence` (0-100)
- `entry_price`, `exit_price`, `stop_loss`
- `growth_projection_pct`, `risk_level`
- `indicators_used`, `entry_rules`, `exit_rules`
- `edge_explanation`

#### Apply Strategy to Trade
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| POST | `/api/strategy/apply` | **Yes** | `{symbol, strategy_name, capital, risk_tolerance}` | Paper trade created |

**How it works**:
1. Validates strategy_name exists in STRATEGIES dict
2. Fetches current market price
3. Calculates position size based on risk tolerance:
   - Conservative: 2% of capital
   - Moderate: 5% of capital
   - Aggressive: 10% of capital
4. `quantity = position_capital / current_price`
5. Creates PaperTrade record with strategy name in notes
6. Returns trade details + strategy exit rules

#### Apply Strategy Across Portfolio
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| POST | `/api/strategy/apply-portfolio` | **Yes** | `{strategy_name: "auto" or specific, risk_tolerance, market?: filter}` | Per-holding analysis |

**How it works**:
1. Fetches all user's portfolio holdings from DB
2. Optionally filters by market
3. For each holding:
   - Gets current price + indicators
   - If `strategy_name="auto"`: scores all 5 strategies, picks best
   - Calculates unrealized P&L
   - Determines suggested action:
     - `hold_or_add`: Oversold + P&L < -5%
     - `consider_taking_profit`: Overbought + P&L > 10%
     - `hold`: Bullish momentum
     - `monitor`: Neutral conditions
4. Returns sorted by confidence (highest first)

**Response per holding**:
```json
{
  "symbol": "AAPL",
  "shares": 10, "avg_price": 150,
  "current_price": 238.50,
  "unrealized_pnl": 885.00,
  "unrealized_pnl_pct": 59.0,
  "market_condition": {"trend": "bullish", "momentum": "bullish", "volatility": "moderate", "rsi": 55},
  "recommended_strategy": "trend_following",
  "confidence": 78.5,
  "suggested_action": "hold",
  "action_reason": "Bullish momentum supports continued holding",
  "entry_rules": [...], "exit_rules": [...]
}
```

#### List All Strategies
| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/strategy/strategies` | No | `{count, strategies: [{key, name, description, style, risk_level, typical_hold, indicators_used, entry_rules, exit_rules, best_market_conditions}]}` |

#### Market Overview
| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| POST | `/api/strategy/market-overview` | No | `{symbols?, market: "US", risk_tolerance}` | Per-symbol trend/momentum analysis, top opportunities |

---

## Module 7: AI Assistant

### User Story
> As a user, I can chat with an AI trading assistant that knows my current stock, its technical indicators, sentiment, and my trader style. I can pick from 4 AI models. If the AI service is down, I get rule-based fallback responses.

### AI Models Available

| ID | Label | Tag |
|----|-------|-----|
| `llama-3.3-70b-versatile` | Llama 3.3 70B | Best |
| `llama-3.1-8b-instant` | Llama 3.1 8B | Fast |
| `mixtral-8x7b-32768` | Mixtral 8x7B | - |
| `gemma2-9b-it` | Gemma 2 9B | - |

### Endpoints

| Method | Path | Auth | Request | Response |
|--------|------|:----:|---------|----------|
| POST | `/api/genai/ask` | No | `{question, symbol, price?, rsi?, signal?, trader_style, vwap?, macd?, model?}` | `{answer, source: "GROQ\|FALLBACK", model, timestamp}` |
| GET | `/api/genai/health` | No | - | `{status, available_models}` |
| GET | `/api/genai/models` | No | - | List of available models |

### Context Injection
The AI receives a system prompt with:
- Stock symbol + current price
- Technical indicators (RSI, MACD, VWAP, signal)
- Market sentiment score
- Trader style (adjusts advice accordingly)
- Time of day / market session

### Fallback Behavior
When `GROQ_API_KEY` is not set or Groq API fails:
- Source field = "FALLBACK" or "rule-based"
- Template responses based on RSI + signal:
  - RSI < 30 + BUY: "Stock appears oversold..."
  - RSI > 70 + SELL: "Stock appears overbought..."
  - Default: General advice based on trader style

### Rate Limiting
- AI endpoint: 10 requests/minute (per user if logged in, per IP if not)
- Timeout: 15 seconds per Groq call

---

## Module 8: Sentiment & News

### User Story
> As a user, I can see aggregated sentiment for any stock from Reddit, StockTwits, and news sources. A composite score from -100 (very bearish) to +100 (very bullish) helps me gauge market mood. I can also view a sentiment heatmap across multiple stocks.

### Sentiment Scoring

| Score Range | Label | Color |
|-------------|-------|-------|
| +51 to +100 | VERY_BULLISH | Dark green |
| +21 to +50 | BULLISH | Green |
| -20 to +20 | NEUTRAL | Yellow |
| -50 to -21 | BEARISH | Red |
| -100 to -51 | VERY_BEARISH | Dark red |

### Source Weights
- StockTwits: 35%
- Reddit: 30%
- News: 35%

### Endpoints

| Method | Path | Auth | Response |
|--------|------|:----:|----------|
| GET | `/api/sentiment/combined/{symbol}` | No | `{composite_score, recommendation: "BUY\|HOLD\|SELL", reddit: {score, posts}, stocktwits: {score, messages}, news: {score, articles}, sources_used}` |
| GET | `/api/sentiment/reddit/{symbol}` | No | `{symbol, bullish_pct, bearish_pct, mentions_24h, trending}` |
| GET | `/api/sentiment/heatmap` | No | `{symbols, heatmap: [{symbol, sentiment_score, rank}], market_mood}` |
| GET | `/api/news/{symbol}` | No | `{symbol, count, news: [{headline, summary, url, source, datetime, sentiment_score}]}` |
| GET | `/api/news/market/latest` | No | Trending market-wide news |

### Test Checkpoints

| # | Test | How to Verify | Expected |
|---|------|--------------|----------|
| 6.1 | Strategy for symbol | POST `/api/strategy/intelligence` with AAPL | 200, returns ranked strategies |
| 6.2 | Strategy has rules | Check each strategy | Has entry_rules + exit_rules |
| 6.3 | Confidence range | Check confidence values | 0-100 |
| 6.4 | Capital < 100 rejected | POST with capital: 50 | 422 |
| 6.5 | Invalid trader style | POST with trader_style: "invalid" | 422 |
| 6.6 | Apply strategy | POST `/api/strategy/apply` (auth) | 201, paper trade created |
| 6.7 | Apply unknown strategy | POST with strategy_name: "nonexistent" | 400 |
| 6.8 | Apply portfolio (auto) | POST `/api/strategy/apply-portfolio` (auth, with holdings) | Per-holding analysis |
| 6.9 | Apply portfolio (empty) | POST with no holdings | 404 |
| 6.10 | List strategies | GET `/api/strategy/strategies` | count + strategies array |
| 7.1 | AI answers question | POST `/api/genai/ask` with question + symbol | answer field non-empty |
| 7.2 | AI source field | Check response | "GROQ" or "FALLBACK" |
| 7.3 | AI model field | Check response | Matches requested model |
| 7.4 | All 4 models accepted | Test each model ID | 200 for all |
| 7.5 | AI fallback works | With no GROQ_API_KEY | Returns rule-based answer |
| 7.6 | AI health endpoint | GET `/api/genai/health` | status field present |
| 8.1 | Combined sentiment | GET `/api/sentiment/combined/AAPL` | composite_score -100 to +100 |
| 8.2 | Sentiment score range | Check composite_score | Within bounds |
| 8.3 | Different symbols work | Test AAPL and TSLA | Both return 200 |
| 8.4 | Heatmap | GET `/api/sentiment/heatmap` | Array of symbols with scores |
| 8.5 | Unknown symbol fallback | GET with ZZZZ | 200 in demo mode (not 500) |
| 8.6 | News for symbol | GET `/api/news/AAPL` | Array of news items |

### Existing Test Files
- `tests/test_market_strategy.py` (10 tests) - Strategy intelligence
- `tests/test_ai_correctness.py` (10 tests) - AI responses and fallback
- `tests/test_sentiment_and_news.py` (7 tests) - Sentiment scoring and commentary
- `tests/test_trader_level_matrix.py` (16 tests) - Trader styles x plans x features
