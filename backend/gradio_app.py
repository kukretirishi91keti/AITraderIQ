# ============================================
# TRADINGAI PRO v4.3 - GRADIO INTERFACE
# Fixed: API endpoints + Top Movers + Market mapping
# ============================================
import gradio as gr
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# ============================================
# CONFIGURATION
# ============================================
API_BASE = "http://localhost:8000"

# Market codes must match backend market_symbols keys exactly
MARKETS = [
    ("🇺🇸 US", "US"), 
    ("🇮🇳 India", "India"),
    ("🇬🇧 UK", "UK"), 
    ("🇩🇪 Germany", "Germany"), 
    ("🇫🇷 France", "France"),
    ("🇯🇵 Japan", "Japan"),
    ("🇭🇰 Hong Kong", "HongKong"), 
    ("🇨🇳 China", "China"),
    ("🇦🇺 Australia", "Australia"), 
    ("🇨🇦 Canada", "Canada"),
    ("🇧🇷 Brazil", "Brazil"),
    ("🪙 Crypto", "Crypto"), 
    ("🛢️ Commodities", "Commodities"),
    ("💱 Forex", "Forex"),
    ("📊 ETFs", "ETF")
]

TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d", "1w", "1M"]

# ============================================
# API FUNCTIONS
# ============================================
def check_api_health():
    """Check API health status"""
    try:
        start = time.time()
        resp = requests.get(f"{API_BASE}/api/health", timeout=5)
        latency = int((time.time() - start) * 1000)
        
        if resp.ok:
            data = resp.json()
            return f"🟢 Connected ({latency}ms) | v{data.get('version', '?')} | Uptime: {data.get('uptime_formatted', '?')}"
        return f"🟡 Degraded ({resp.status_code})"
    except Exception as e:
        return f"🔴 Offline: {str(e)[:30]}"

def fetch_stock_v4(ticker: str, timeframe: str = "1d"):
    """Fetch stock data by combining multiple v4 endpoints"""
    try:
        data = {'_fetch_time': datetime.now().isoformat()}
        
        # 1. Fetch quote (price, change, etc.)
        try:
            resp = requests.get(f"{API_BASE}/api/v4/quote/{ticker}", timeout=10)
            if resp.ok:
                quote = resp.json()
                data['price'] = quote.get('price', 0)
                data['change'] = quote.get('change', 0)
                data['changePct'] = quote.get('changePercent', quote.get('changePct', 0))
                data['open'] = quote.get('open', data['price'] * 0.99)
                data['high'] = quote.get('dayHigh', quote.get('high', data['price'] * 1.02))
                data['low'] = quote.get('dayLow', quote.get('low', data['price'] * 0.98))
                data['volume'] = quote.get('volume', 1000000)
                data['currency'] = quote.get('currency', '$')
        except Exception as e:
            print(f"Quote error: {e}")
        
        # 2. Fetch history (chart data)
        try:
            resp = requests.get(f"{API_BASE}/api/v4/history/{ticker}?interval={timeframe}", timeout=10)
            if resp.ok:
                history = resp.json()
                candles = history.get('candles', history.get('chart', []))
                # Convert to format expected by chart
                chart_data = []
                for c in candles:
                    chart_data.append({
                        'time': c.get('date', c.get('time', '')),
                        'price': c.get('close', c.get('price', 0)),
                        'volume': c.get('volume', 0)
                    })
                data['chart'] = chart_data
        except Exception as e:
            print(f"History error: {e}")
        
        # 3. Fetch signals (RSI, MACD, etc.)
        try:
            resp = requests.get(f"{API_BASE}/api/v4/signals/{ticker}", timeout=10)
            if resp.ok:
                signals = resp.json()
                data['rsi'] = signals.get('rsi', 50)
                data['macd'] = signals.get('macd', 0)
                data['signal'] = signals.get('signal', 'HOLD')
                data['bbUpper'] = signals.get('bb_upper', signals.get('bbUpper', 0))
                data['bbLower'] = signals.get('bb_lower', signals.get('bbLower', 0))
        except Exception as e:
            print(f"Signals error: {e}")
        
        # 4. Fetch financials (optional, for extra stats)
        try:
            resp = requests.get(f"{API_BASE}/api/v4/financials/{ticker}", timeout=10)
            if resp.ok:
                fin = resp.json()
                data['marketCap'] = fin.get('market_cap', fin.get('marketCap', '--'))
                data['pe'] = fin.get('pe_ratio', fin.get('pe', '--'))
                data['beta'] = fin.get('beta', '--')
                data['high52'] = fin.get('52_week_high', fin.get('high52', data.get('high', 0) * 1.2))
                data['low52'] = fin.get('52_week_low', fin.get('low52', data.get('low', 0) * 0.8))
                data['sector'] = fin.get('sector', '--')
        except Exception as e:
            print(f"Financials error: {e}")
        
        # Return data if we got at least price
        if data.get('price'):
            return data
        return None
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def fetch_top_movers(market: str = "US"):
    """Fetch top movers for a market"""
    try:
        resp = requests.get(f"{API_BASE}/api/v4/top-movers/{market}", timeout=15)
        if resp.ok:
            return resp.json()
        return None
    except Exception as e:
        print(f"Error fetching top movers: {e}")
        return None

def get_data_status(data: dict) -> str:
    """Get data freshness status badge"""
    if not data:
        return "🔴 ERROR"
    
    cache_age = data.get('cache_age', 0)
    source = data.get('source', 'cache')
    
    if source == 'live' or cache_age < 30:
        return f"🟢 LIVE ({cache_age}s)"
    elif cache_age < 120:
        return f"🔵 CACHED ({cache_age}s)"
    elif cache_age < 300:
        return f"🟡 STALE ({cache_age}s)"
    else:
        return f"🟠 EXPIRED ({cache_age}s)"

# ============================================
# CHART FUNCTIONS
# ============================================
def create_price_chart(data: dict) -> go.Figure:
    """Create interactive price chart with technical indicators"""
    if not data or 'chart' not in data:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        return fig
    
    chart = data['chart']
    if not chart:
        fig = go.Figure()
        fig.add_annotation(text="No chart data", x=0.5, y=0.5, showarrow=False)
        return fig
    
    df = pd.DataFrame(chart)
    
    # Create figure with subplots
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    # Price line
    change_pct = data.get('changePct', 0)
    color = '#00E599' if change_pct >= 0 else '#FF4757'
    
    fig.add_trace(
        go.Scatter(
            x=df['time'], y=df['price'],
            mode='lines',
            name='Price',
            line=dict(color=color, width=2),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) + (0.1,)}'
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    bb_upper = data.get('bbUpper', 0)
    bb_lower = data.get('bbLower', 0)
    if bb_upper and bb_lower:
        fig.add_hline(y=bb_upper, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=1, col=1)
        fig.add_hline(y=bb_lower, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=1, col=1)
    
    # Volume bars
    if 'volume' in df.columns:
        colors = ['#00E599' if i == 0 or df['price'].iloc[i] >= df['price'].iloc[i-1] else '#FF4757' 
                  for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['time'], y=df['volume'], name='Volume', marker_color=colors, opacity=0.5),
            row=2, col=1
        )
    
    # Layout
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=50, r=50, t=30, b=30),
        showlegend=False,
        xaxis_rangeslider_visible=False,
        height=400
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

def create_rsi_gauge(rsi: float) -> go.Figure:
    """Create RSI gauge chart"""
    color = '#00E599' if rsi < 30 else '#FF4757' if rsi > 70 else '#FFB800'
    signal = 'Oversold (BUY)' if rsi < 30 else 'Overbought (SELL)' if rsi > 70 else 'Neutral'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"RSI (14)<br><span style='font-size:12px;color:{color}'>{signal}</span>"},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': 'white'},
            'bar': {'color': color},
            'bgcolor': 'rgba(255,255,255,0.1)',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 30], 'color': 'rgba(0,229,153,0.2)'},
                {'range': [30, 70], 'color': 'rgba(255,184,0,0.2)'},
                {'range': [70, 100], 'color': 'rgba(255,71,87,0.2)'}
            ],
            'threshold': {
                'line': {'color': 'white', 'width': 2},
                'thickness': 0.75,
                'value': rsi
            }
        }
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=200,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

# ============================================
# MAIN INTERFACE FUNCTIONS
# ============================================
def analyze_stock(ticker: str, timeframe: str):
    """Main analysis function"""
    if not ticker:
        return "Enter a ticker", None, None, "", "", "", "", ""
    
    ticker = ticker.upper().strip()
    data = fetch_stock_v4(ticker, timeframe)
    
    if not data:
        return f"❌ Failed to fetch {ticker}", None, None, "", "", "", "", ""
    
    # Data status
    status = get_data_status(data)
    
    # Price info
    price = data.get('price', 0)
    change = data.get('change', 0)
    change_pct = data.get('changePct', 0)
    arrow = '▲' if change_pct >= 0 else '▼'
    color = 'green' if change_pct >= 0 else 'red'
    
    price_html = f"""
    <div style='text-align:center; padding:20px;'>
        <h1 style='margin:0; font-size:2.5em;'>{ticker}</h1>
        <h2 style='margin:10px 0; font-size:2em;'>${price:.2f}</h2>
        <span style='color:{color}; font-size:1.2em;'>{arrow} {change:+.2f} ({change_pct:+.2f}%)</span>
        <br><br>
        <span style='font-size:0.9em;'>{status}</span>
    </div>
    """
    
    # Charts
    price_chart = create_price_chart(data)
    rsi_gauge = create_rsi_gauge(data.get('rsi', 50))
    
    # Technical Analysis
    rsi = data.get('rsi', 50)
    macd = data.get('macd', 0)
    signal = data.get('signal', 'HOLD')
    
    signal_color = '#00E599' if 'BUY' in signal else '#FF4757' if 'SELL' in signal else '#FFB800'
    
    tech_html = f"""
    <div style='padding:15px;'>
        <h3>📊 Technical Indicators</h3>
        <table style='width:100%; border-collapse:collapse;'>
            <tr><td>RSI (14)</td><td style='text-align:right;'><b>{rsi:.1f}</b></td></tr>
            <tr><td>MACD</td><td style='text-align:right;'><b>{macd:.4f}</b></td></tr>
            <tr><td>BB Upper</td><td style='text-align:right;'>${data.get('bbUpper', 0):.2f}</td></tr>
            <tr><td>BB Lower</td><td style='text-align:right;'>${data.get('bbLower', 0):.2f}</td></tr>
        </table>
        <br>
        <div style='text-align:center; padding:15px; background:{signal_color}30; border-radius:8px;'>
            <span style='font-size:1.5em; color:{signal_color};'><b>{signal}</b></span>
        </div>
    </div>
    """
    
    # Stats
    stats_html = f"""
    <div style='padding:15px;'>
        <h3>📈 Stock Stats</h3>
        <table style='width:100%; border-collapse:collapse;'>
            <tr><td>Open</td><td style='text-align:right;'>${data.get('open', 0):.2f}</td></tr>
            <tr><td>High</td><td style='text-align:right;'>${data.get('high', 0):.2f}</td></tr>
            <tr><td>Low</td><td style='text-align:right;'>${data.get('low', 0):.2f}</td></tr>
            <tr><td>Volume</td><td style='text-align:right;'>{data.get('volume', 0):,.0f}</td></tr>
            <tr><td>Market Cap</td><td style='text-align:right;'>{data.get('marketCap', '--')}</td></tr>
            <tr><td>52W High</td><td style='text-align:right;'>${data.get('high52', 0):.2f}</td></tr>
            <tr><td>52W Low</td><td style='text-align:right;'>${data.get('low52', 0):.2f}</td></tr>
            <tr><td>P/E</td><td style='text-align:right;'>{data.get('pe', '--')}</td></tr>
            <tr><td>Beta</td><td style='text-align:right;'>{data.get('beta', '--')}</td></tr>
            <tr><td>Sector</td><td style='text-align:right;'>{data.get('sector', '--')}</td></tr>
        </table>
    </div>
    """
    
    return price_html, price_chart, rsi_gauge, tech_html, stats_html

def get_top_movers_display(market: str):
    """Get top movers for display"""
    data = fetch_top_movers(market)
    
    if not data:
        return "❌ Failed to fetch top movers"
    
    # Backend returns {"movers": [...]} with "symbol" and "change"/"changePercent"
    movers = data.get('movers', [])
    
    # Split into gainers and losers based on change
    gainers = [m for m in movers if m.get('change', m.get('changePercent', 0)) > 0]
    losers = [m for m in movers if m.get('change', m.get('changePercent', 0)) < 0]
    
    # Sort gainers by change descending, losers by change ascending
    gainers.sort(key=lambda x: x.get('change', x.get('changePercent', 0)), reverse=True)
    losers.sort(key=lambda x: x.get('change', x.get('changePercent', 0)))
    
    html = "<div style='display:grid; grid-template-columns:1fr 1fr; gap:20px;'>"
    
    # Gainers
    html += "<div style='background:rgba(0,229,153,0.1); padding:15px; border-radius:8px;'>"
    html += "<h3>📈 Top Gainers</h3>"
    if gainers:
        for g in gainers[:5]:
            ticker = g.get('symbol', g.get('ticker', '???'))
            change = g.get('change', g.get('changePercent', g.get('changePct', 0)))
            html += f"<div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.1);'>"
            html += f"<span><b>{ticker}</b></span>"
            html += f"<span style='color:#00E599;'>+{change:.2f}%</span>"
            html += "</div>"
    else:
        html += "<div style='opacity:0.5;'>No gainers today</div>"
    html += "</div>"
    
    # Losers
    html += "<div style='background:rgba(255,71,87,0.1); padding:15px; border-radius:8px;'>"
    html += "<h3>📉 Top Losers</h3>"
    if losers:
        for l in losers[:5]:
            ticker = l.get('symbol', l.get('ticker', '???'))
            change = l.get('change', l.get('changePercent', l.get('changePct', 0)))
            html += f"<div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.1);'>"
            html += f"<span><b>{ticker}</b></span>"
            html += f"<span style='color:#FF4757;'>{change:.2f}%</span>"
            html += "</div>"
    else:
        html += "<div style='opacity:0.5;'>No losers today</div>"
    html += "</div>"
    
    html += "</div>"
    
    # Market info
    html += f"<div style='margin-top:15px; text-align:center; opacity:0.7;'>"
    html += f"📊 Market: {data.get('market', market)} | Source: {data.get('source', 'API')}"
    html += "</div>"
    
    return html

# ============================================
# GRADIO INTERFACE
# ============================================
def create_interface():
    with gr.Blocks(
        title="TradingAI Pro v4.3",
        theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate"),
        css="""
            .gradio-container { max-width: 1400px !important; }
            .gr-button { background: linear-gradient(135deg, #00E599, #00B4D8) !important; }
        """
    ) as demo:
        
        # Header
        gr.Markdown("""
        # 📊 TradingAI Pro v4.3
        ### AI-Powered Global Trading Platform with Real-Time Data Status
        """)
        
        # API Health Status
        with gr.Row():
            health_status = gr.Textbox(label="API Status", value=check_api_health(), interactive=False)
            refresh_health = gr.Button("🔄 Refresh", scale=0)
            refresh_health.click(check_api_health, outputs=health_status)
        
        with gr.Tabs():
            # Tab 1: Stock Analysis
            with gr.TabItem("📈 Stock Analysis"):
                with gr.Row():
                    with gr.Column(scale=2):
                        ticker_input = gr.Textbox(
                            label="Ticker Symbol",
                            placeholder="NVDA, AAPL, RELIANCE.NS, BTC-USD...",
                            value="NVDA"
                        )
                    with gr.Column(scale=1):
                        timeframe_select = gr.Dropdown(
                            choices=TIMEFRAMES,
                            value="1d",
                            label="Timeframe"
                        )
                    with gr.Column(scale=1):
                        analyze_btn = gr.Button("🔍 Analyze", variant="primary")
                
                with gr.Row():
                    price_display = gr.HTML(label="Price")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        price_chart = gr.Plot(label="Price Chart")
                    with gr.Column(scale=1):
                        rsi_gauge = gr.Plot(label="RSI Gauge")
                
                with gr.Row():
                    with gr.Column():
                        tech_analysis = gr.HTML(label="Technical Analysis")
                    with gr.Column():
                        stock_stats = gr.HTML(label="Stock Stats")
                
                analyze_btn.click(
                    analyze_stock,
                    inputs=[ticker_input, timeframe_select],
                    outputs=[price_display, price_chart, rsi_gauge, tech_analysis, stock_stats]
                )
            
            # Tab 2: Top Movers
            with gr.TabItem("🔥 Top Movers"):
                with gr.Row():
                    market_select = gr.Dropdown(
                        choices=MARKETS,  # Shows "🇺🇸 US" but submits "US"
                        value="US",
                        label="Select Market"
                    )
                    movers_btn = gr.Button("🔄 Load Top Movers", variant="primary")
                
                movers_display = gr.HTML(label="Top Movers")
                
                movers_btn.click(
                    get_top_movers_display,
                    inputs=[market_select],
                    outputs=[movers_display]
                )
            
            # Tab 3: About
            with gr.TabItem("ℹ️ About"):
                gr.Markdown("""
                ## TradingAI Pro v4.3 Features
                
                ### 🚀 What's New in v4.3
                - **Fixed Market Mapping**: Top Movers now correctly changes per market
                - **Fixed Top Movers**: Properly parses backend movers response
                - **Fixed Backend Integration**: Uses correct v4 API endpoints
                - **Multi-Endpoint Fetching**: Combines quote, history, signals, financials
                - **15 Global Markets**: US, India, UK, Germany, France, Japan, HK, China, Australia, Canada, Brazil, Crypto, Forex, Commodities, ETFs
                
                ### 📊 Technical Indicators
                - RSI (14) with Oversold/Overbought signals
                - MACD with Signal Line
                - Bollinger Bands
                - Volume Analysis
                
                ### 🌍 Supported Markets
                US, India, UK, Germany, France, Japan, Hong Kong, China, Australia, Canada, Brazil, Crypto, Forex, Commodities, ETFs
                
                ---
                **TradingAI Pro | TalentSprint Project 5 | December 2025**
                """)
        
        # Footer
        gr.Markdown("""
        ---
        <center>
        TradingAI Pro v4.3 | Not Financial Advice | DYOR
        </center>
        """)
    
    return demo

# ============================================
# LAUNCH
# ============================================
if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,  # Creates public shareable link (72h validity)
        show_error=True
    )
