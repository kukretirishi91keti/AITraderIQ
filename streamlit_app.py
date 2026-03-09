"""
TraderAI Pro - Standalone Streamlit Dashboard
============================================
Deploy to Streamlit Cloud for instant live demo link!

This version is self-contained and doesn't need a separate backend.
Perfect for quick academic demonstrations.

Deploy: https://share.streamlit.io
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random
import hashlib

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="TraderAI Pro - AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main {background-color: #0e1117;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #1f2937;
        border-radius: 4px;
        padding: 10px 20px;
    }
    .metric-card {
        background-color: #1f2937;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #374151;
    }
    .signal-buy {
        background-color: #065f46;
        color: #34d399;
        padding: 5px 10px;
        border-radius: 4px;
    }
    .signal-sell {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 5px 10px;
        border-radius: 4px;
    }
    .header-banner {
        background: linear-gradient(90deg, #0891b2 0%, #6366f1 100%);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MARKET DATA
# ============================================================
MARKETS = {
    "🇺🇸 US": {"currency": "$", "suffix": "", "stocks": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "AMD", "NFLX", "INTC"]},
    "🇮🇳 India": {"currency": "₹", "suffix": ".NS", "stocks": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK"]},
    "🇬🇧 UK": {"currency": "£", "suffix": ".L", "stocks": ["SHEL", "AZN", "HSBA", "ULVR", "BP", "GSK", "RIO", "BARC", "LLOY", "VOD"]},
    "🇩🇪 Germany": {"currency": "€", "suffix": ".DE", "stocks": ["SAP", "SIE", "ALV", "BAS", "DTE", "BMW", "MRK", "VOW3", "ADS", "MUV2"]},
    "🇯🇵 Japan": {"currency": "¥", "suffix": ".T", "stocks": ["7203", "6758", "9984", "6861", "8306", "9432", "6501", "7267", "8035", "6902"]},
    "🪙 Crypto": {"currency": "$", "suffix": "", "stocks": ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD", "ADA-USD", "DOGE-USD", "DOT-USD"]},
    "📊 ETF": {"currency": "$", "suffix": "", "stocks": ["SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "ARKK", "XLF", "XLK", "XLE"]},
}

# ============================================================
# DEMO DATA GENERATOR (Deterministic)
# ============================================================
def generate_demo_price(symbol: str, base_price: float = None) -> dict:
    """Generate realistic demo price data for a symbol."""
    # Use symbol hash for deterministic but varied data
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    random.seed(seed + datetime.now().hour)  # Changes hourly
    
    if base_price is None:
        # Generate base price based on symbol
        if "BTC" in symbol:
            base_price = random.uniform(40000, 50000)
        elif "ETH" in symbol:
            base_price = random.uniform(2000, 3000)
        elif ".NS" in symbol:
            base_price = random.uniform(500, 5000)
        elif ".L" in symbol:
            base_price = random.uniform(500, 3000)
        else:
            base_price = random.uniform(50, 500)
    
    change_pct = random.uniform(-3, 3)
    price = base_price * (1 + change_pct / 100)
    prev_close = base_price
    
    return {
        "symbol": symbol,
        "price": round(price, 2),
        "change": round(price - prev_close, 2),
        "change_percent": round(change_pct, 2),
        "open": round(prev_close * random.uniform(0.99, 1.01), 2),
        "high": round(price * random.uniform(1.01, 1.03), 2),
        "low": round(price * random.uniform(0.97, 0.99), 2),
        "volume": random.randint(1000000, 50000000),
        "prev_close": round(prev_close, 2),
        "market_cap": random.randint(10, 3000) * 1e9,
    }


def generate_historical_data(symbol: str, days: int = 60) -> pd.DataFrame:
    """Generate historical OHLCV data."""
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    np.random.seed(seed)
    
    # Starting price
    if "BTC" in symbol:
        start_price = 45000
    elif "ETH" in symbol:
        start_price = 2500
    elif ".NS" in symbol:
        start_price = random.uniform(500, 3000)
    else:
        start_price = random.uniform(100, 400)
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate price series with random walk
    returns = np.random.normal(0.001, 0.02, days)
    prices = start_price * np.cumprod(1 + returns)
    
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        volatility = abs(np.random.normal(0, 0.015))
        open_price = close * (1 + np.random.normal(0, 0.005))
        high = max(open_price, close) * (1 + volatility)
        low = min(open_price, close) * (1 - volatility)
        volume = int(np.random.uniform(1e6, 5e7))
        
        data.append({
            "Date": date,
            "Open": round(open_price, 2),
            "High": round(high, 2),
            "Low": round(low, 2),
            "Close": round(close, 2),
            "Volume": volume
        })
    
    df = pd.DataFrame(data)
    
    # Add technical indicators
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    
    return df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_ai_analysis(symbol: str, price_data: dict) -> str:
    """Generate AI-style analysis."""
    rsi = random.uniform(25, 75)
    
    if rsi < 30:
        signal = "OVERSOLD - Potential Buy"
        analysis = f"""
        **📊 AI Analysis for {symbol}**
        
        The RSI is currently at {rsi:.1f}, indicating **oversold** conditions. 
        This could present a buying opportunity for swing traders.
        
        **Key Levels:**
        - Support: ${price_data['low']:.2f}
        - Resistance: ${price_data['high']:.2f}
        - Entry Zone: ${price_data['price'] * 0.98:.2f} - ${price_data['price']:.2f}
        
        **Recommendation:** Consider accumulating on dips with proper risk management.
        Stop loss suggested at ${price_data['low'] * 0.95:.2f}
        """
    elif rsi > 70:
        signal = "OVERBOUGHT - Consider Taking Profits"
        analysis = f"""
        **📊 AI Analysis for {symbol}**
        
        The RSI is at {rsi:.1f}, indicating **overbought** conditions.
        Consider taking partial profits or tightening stop losses.
        
        **Key Levels:**
        - Support: ${price_data['low']:.2f}
        - Resistance: ${price_data['high']:.2f}
        
        **Recommendation:** Scale out positions or wait for pullback before adding.
        """
    else:
        signal = "NEUTRAL - Wait for Clear Signal"
        analysis = f"""
        **📊 AI Analysis for {symbol}**
        
        RSI at {rsi:.1f} - **neutral zone**. No strong directional bias.
        
        **Key Levels:**
        - Support: ${price_data['low']:.2f}
        - Resistance: ${price_data['high']:.2f}
        
        **Recommendation:** Wait for breakout above resistance or breakdown below support.
        """
    
    return analysis


# ============================================================
# CHARTS
# ============================================================
def create_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create interactive candlestick chart with indicators."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f'{symbol} Price', 'Volume', 'RSI')
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # SMAs
    if 'SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['SMA_20'], name='SMA 20',
                      line=dict(color='orange', width=1)),
            row=1, col=1
        )
    
    if 'SMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['SMA_50'], name='SMA 50',
                      line=dict(color='blue', width=1)),
            row=1, col=1
        )
    
    # Volume
    colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' 
              for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=df['Date'], y=df['Volume'], name='Volume',
               marker_color=colors, opacity=0.7),
        row=2, col=1
    )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=df['RSI'], name='RSI',
                      line=dict(color='purple', width=2)),
            row=3, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    fig.update_layout(
        template='plotly_dark',
        height=700,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )
    
    return fig


# ============================================================
# MAIN APP
# ============================================================
def main():
    # Header
    st.markdown("""
    <div class="header-banner">
        <h1 style="color: white; margin: 0;">📈 TraderAI Pro</h1>
        <p style="color: #e0e0e0; margin: 5px 0 0 0;">
            AI-Powered Trading Dashboard | 22 Global Markets | Real-Time Analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🎛️ Dashboard Controls")
    
    # Market Selection
    selected_market = st.sidebar.selectbox(
        "Select Market",
        list(MARKETS.keys()),
        index=0
    )
    
    market_data = MARKETS[selected_market]
    currency = market_data["currency"]
    
    # Symbol Selection
    available_symbols = market_data["stocks"]
    selected_symbol = st.sidebar.selectbox(
        "Select Symbol",
        available_symbols,
        index=0
    )
    
    # Add suffix if needed
    full_symbol = selected_symbol + market_data["suffix"] if market_data["suffix"] and market_data["suffix"] not in selected_symbol else selected_symbol
    
    # Timeframe
    timeframe = st.sidebar.selectbox(
        "Timeframe",
        ["1D", "1W", "1M", "3M"],
        index=2
    )
    
    days_map = {"1D": 1, "1W": 7, "1M": 30, "3M": 90}
    
    st.sidebar.markdown("---")
    
    # Watchlist
    st.sidebar.subheader("⭐ Watchlist")
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ["AAPL", "NVDA", "RELIANCE.NS"]
    
    for item in st.session_state.watchlist[:5]:
        price_data = generate_demo_price(item)
        color = "🟢" if price_data['change_percent'] > 0 else "🔴"
        st.sidebar.text(f"{color} {item}: {currency}{price_data['price']:.2f} ({price_data['change_percent']:+.2f}%)")
    
    if st.sidebar.button("➕ Add to Watchlist"):
        if full_symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(full_symbol)
            st.sidebar.success(f"Added {full_symbol}!")
    
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **TraderAI Pro v5.8.6**  
    TalentSprint AIML Program  
    Stage 2 Final Project
    
    *Demo Mode - Simulated Data*
    """)
    
    # Main Content
    col1, col2, col3, col4 = st.columns(4)
    
    # Get price data
    price_data = generate_demo_price(full_symbol)
    
    with col1:
        st.metric(
            label=f"{full_symbol} Price",
            value=f"{currency}{price_data['price']:,.2f}",
            delta=f"{price_data['change_percent']:+.2f}%"
        )
    
    with col2:
        st.metric(
            label="Day High",
            value=f"{currency}{price_data['high']:,.2f}"
        )
    
    with col3:
        st.metric(
            label="Day Low",
            value=f"{currency}{price_data['low']:,.2f}"
        )
    
    with col4:
        st.metric(
            label="Volume",
            value=f"{price_data['volume']:,.0f}"
        )
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Chart", "🤖 AI Analysis", "📰 News", "📈 Screener", "ℹ️ About"])
    
    with tab1:
        st.subheader(f"{full_symbol} Technical Chart")
        
        # Generate and display chart
        historical_df = generate_historical_data(full_symbol, days_map.get(timeframe, 30))
        fig = create_candlestick_chart(historical_df, full_symbol)
        st.plotly_chart(fig, use_container_width=True)
        
        # Technical Signals
        st.subheader("📊 Technical Signals")
        sig_col1, sig_col2, sig_col3, sig_col4 = st.columns(4)
        
        rsi_val = historical_df['RSI'].iloc[-1] if not pd.isna(historical_df['RSI'].iloc[-1]) else 50
        
        with sig_col1:
            rsi_signal = "Oversold 🟢" if rsi_val < 30 else ("Overbought 🔴" if rsi_val > 70 else "Neutral ⚪")
            st.info(f"**RSI ({rsi_val:.1f}):** {rsi_signal}")
        
        with sig_col2:
            trend = "Bullish 🟢" if historical_df['Close'].iloc[-1] > historical_df['SMA_20'].iloc[-1] else "Bearish 🔴"
            st.info(f"**Trend:** {trend}")
        
        with sig_col3:
            volatility = "High" if (historical_df['High'].iloc[-1] - historical_df['Low'].iloc[-1]) / historical_df['Close'].iloc[-1] > 0.03 else "Normal"
            st.info(f"**Volatility:** {volatility}")
        
        with sig_col4:
            momentum = "Strong" if abs(price_data['change_percent']) > 2 else "Weak"
            st.info(f"**Momentum:** {momentum}")
    
    with tab2:
        st.subheader("🤖 AI Trading Assistant")
        
        # AI Analysis
        analysis = get_ai_analysis(full_symbol, price_data)
        st.markdown(analysis)
        
        st.markdown("---")
        
        # Chat interface
        st.subheader("💬 Ask AI")
        user_question = st.text_input("Ask about this stock:", placeholder="What's a good entry point?")
        
        if user_question:
            with st.spinner("Analyzing..."):
                import time
                time.sleep(1)  # Simulate API delay
                
                st.markdown(f"""
                **AI Response:**
                
                Based on current technical analysis for {full_symbol}:
                
                - Current price: {currency}{price_data['price']:.2f}
                - Suggested entry zone: {currency}{price_data['price'] * 0.97:.2f} - {currency}{price_data['price'] * 0.99:.2f}
                - Stop loss: {currency}{price_data['low'] * 0.95:.2f}
                - Target 1: {currency}{price_data['high'] * 1.05:.2f}
                - Target 2: {currency}{price_data['high'] * 1.10:.2f}
                
                *Note: This is simulated AI analysis for demonstration purposes.*
                """)
    
    with tab3:
        st.subheader("📰 Market News & Sentiment")
        
        # Simulated news
        news_items = [
            {"title": f"{selected_symbol} Reports Strong Q4 Earnings", "sentiment": "Positive", "source": "Reuters", "time": "2h ago"},
            {"title": f"Analysts Upgrade {selected_symbol} to Buy", "sentiment": "Positive", "source": "Bloomberg", "time": "4h ago"},
            {"title": f"Market Volatility Impacts {selected_symbol}", "sentiment": "Neutral", "source": "CNBC", "time": "6h ago"},
            {"title": f"Sector Rotation Benefits {selected_symbol}", "sentiment": "Positive", "source": "WSJ", "time": "8h ago"},
        ]
        
        for news in news_items:
            sentiment_color = "🟢" if news['sentiment'] == "Positive" else ("🔴" if news['sentiment'] == "Negative" else "⚪")
            st.markdown(f"""
            **{news['title']}**  
            {sentiment_color} {news['sentiment']} | {news['source']} | {news['time']}
            """)
            st.markdown("---")
        
        # Sentiment gauge
        st.subheader("📊 Overall Sentiment")
        sentiment_score = random.uniform(0.4, 0.8)
        st.progress(sentiment_score)
        st.write(f"Sentiment Score: {sentiment_score:.1%} Bullish")
    
    with tab4:
        st.subheader("📈 Stock Screener")
        
        screener_market = st.selectbox("Filter by Market", list(MARKETS.keys()))
        
        # Generate screener data
        screener_data = []
        for sym in MARKETS[screener_market]["stocks"]:
            full_sym = sym + MARKETS[screener_market]["suffix"] if MARKETS[screener_market]["suffix"] else sym
            data = generate_demo_price(full_sym)
            historical = generate_historical_data(full_sym, 30)
            rsi = historical['RSI'].iloc[-1] if not pd.isna(historical['RSI'].iloc[-1]) else 50
            
            signal = "BUY" if rsi < 30 else ("SELL" if rsi > 70 else "HOLD")
            
            screener_data.append({
                "Symbol": sym,
                "Price": f"{MARKETS[screener_market]['currency']}{data['price']:.2f}",
                "Change %": f"{data['change_percent']:+.2f}%",
                "RSI": f"{rsi:.1f}",
                "Signal": signal,
                "Volume": f"{data['volume']:,.0f}"
            })
        
        df_screener = pd.DataFrame(screener_data)
        
        # Color code the signals
        st.dataframe(
            df_screener,
            use_container_width=True,
            hide_index=True
        )
        
        # Summary
        buy_count = len([s for s in screener_data if s['Signal'] == 'BUY'])
        sell_count = len([s for s in screener_data if s['Signal'] == 'SELL'])
        st.info(f"**Summary:** {buy_count} Buy signals | {sell_count} Sell signals")
    
    with tab5:
        st.subheader("ℹ️ About TraderAI Pro")
        
        st.markdown("""
        ### 🎯 Project Overview
        
        **TraderAI Pro** is an AI-powered trading dashboard developed as the final project 
        for the TalentSprint AIML Program (Stage 2).
        
        ### ✨ Key Features
        
        - **22 Global Markets**: US, India, UK, Germany, Japan, Crypto, ETF, and more
        - **Technical Analysis**: RSI, MACD, SMA, Bollinger Bands
        - **AI Assistant**: Intelligent trading recommendations
        - **Stock Screener**: Filter by RSI signals
        - **Real-time Updates**: Live market data visualization
        - **Multi-currency Support**: $, ₹, £, €, ¥
        
        ### 🛠️ Technology Stack
        
        | Component | Technology |
        |-----------|------------|
        | Frontend | React 18, Vite, TailwindCSS |
        | Backend | FastAPI, Python 3.11 |
        | Data | Yahoo Finance API |
        | AI | Groq/LLaMA 3 |
        | Testing | Cypress (180+ tests) |
        
        ### 📊 Data Sources
        
        - **Stock Prices**: Yahoo Finance (yfinance)
        - **Technical Indicators**: Calculated locally
        - **Sentiment**: Reddit, StockTwits (simulated in demo)
        - **AI Analysis**: Groq LLM API
        
        ### ⚠️ Disclaimer
        
        This is an **academic demonstration project**. The data shown may be simulated. 
        This is NOT financial advice. Always consult a qualified financial advisor 
        before making investment decisions.
        
        ---
        
        **Version:** 5.8.6  
        **Author:** Rishi  
        **Program:** TalentSprint AIML - Stage 2  
        **Project:** Database and GenAI-Powered Visualization Tool for Day Traders
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>📈 TraderAI Pro v5.8.6 | TalentSprint AIML Program | Stage 2 Final Project</p>
        <p>⚠️ Demo Mode - Simulated Data | Not Financial Advice</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
