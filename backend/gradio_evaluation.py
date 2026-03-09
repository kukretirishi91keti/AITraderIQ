"""
TraderAI Pro - Signal Evaluation Dashboard
===========================================
Gradio-based dashboard for evaluating trading signal accuracy

Features:
- 30-day simulated historical signals
- Signal accuracy metrics (precision, recall, F1)
- RSI distribution analysis
- Confusion matrix visualization
- Backtest P&L simulation
- Multi-symbol comparison

Run: python gradio_evaluation.py
Access: http://localhost:7860
"""

import gradio as gr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random
import hashlib
from typing import List, Dict, Any, Tuple

# ============================================================
# CONFIGURATION
# ============================================================

STATIC_UNIVERSE = [
    # US Tech
    'AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD', 'NFLX',
    # India
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
    # Crypto
    'BTC-USD', 'ETH-USD', 'SOL-USD',
    # ETFs
    'SPY', 'QQQ', 'IWM',
]

SIGNAL_LABELS = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']

# Base prices for simulation
BASE_PRICES = {
    'AAPL': 250, 'MSFT': 430, 'GOOGL': 175, 'AMZN': 225, 'NVDA': 140,
    'TSLA': 250, 'META': 580, 'AMD': 130, 'NFLX': 700,
    'RELIANCE.NS': 2500, 'TCS.NS': 4200, 'INFY.NS': 1800,
    'HDFCBANK.NS': 1700, 'ICICIBANK.NS': 1200,
    'BTC-USD': 105000, 'ETH-USD': 3900, 'SOL-USD': 220,
    'SPY': 590, 'QQQ': 520, 'IWM': 230,
}


# ============================================================
# SIGNAL GENERATION (matches backend logic)
# ============================================================

def generate_price_series(symbol: str, days: int = 60, seed_date: str = None) -> List[float]:
    """Generate realistic price series for a symbol."""
    base = BASE_PRICES.get(symbol.upper(), 100)
    
    seed = f"{symbol}:{seed_date or datetime.now().strftime('%Y%m%d')}"
    rng = random.Random(hashlib.md5(seed.encode()).hexdigest())
    
    prices = []
    current = base * 0.95
    for i in range(days):
        change = (rng.random() - 0.48) * 0.025  # Slight upward bias
        current = current * (1 + change)
        prices.append(current)
    
    return prices


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI."""
    if len(prices) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 1)


def calculate_macd(prices: List[float]) -> Dict[str, float]:
    """Calculate MACD."""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}
    
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]
        for price in data[1:]:
            ema_values.append((price * multiplier) + (ema_values[-1] * (1 - multiplier)))
        return ema_values
    
    ema_12 = ema(prices, 12)
    ema_26 = ema(prices, 26)
    
    macd_line = [a - b for a, b in zip(ema_12, ema_26)]
    signal_line = ema(macd_line[-9:], 9) if len(macd_line) >= 9 else [0]
    
    return {
        "macd": round(macd_line[-1], 2),
        "signal": round(signal_line[-1], 2),
        "histogram": round(macd_line[-1] - signal_line[-1], 2)
    }


def generate_signal(rsi: float, macd_hist: float) -> str:
    """Generate signal based on RSI and MACD."""
    score = 0
    
    # RSI contribution
    if rsi < 30:
        score += 2
    elif rsi < 40:
        score += 1
    elif rsi > 70:
        score -= 2
    elif rsi > 60:
        score -= 1
    
    # MACD contribution
    if macd_hist > 0.5:
        score += 2
    elif macd_hist > 0:
        score += 1
    elif macd_hist < -0.5:
        score -= 2
    elif macd_hist < 0:
        score -= 1
    
    if score >= 3:
        return 'STRONG_BUY'
    elif score >= 1:
        return 'BUY'
    elif score <= -3:
        return 'STRONG_SELL'
    elif score <= -1:
        return 'SELL'
    else:
        return 'HOLD'


def determine_actual_outcome(price_before: float, price_after: float, threshold: float = 0.02) -> str:
    """Determine what the 'correct' signal should have been based on actual price movement."""
    pct_change = (price_after - price_before) / price_before
    
    if pct_change > threshold * 1.5:
        return 'STRONG_BUY'
    elif pct_change > threshold * 0.5:
        return 'BUY'
    elif pct_change < -threshold * 1.5:
        return 'STRONG_SELL'
    elif pct_change < -threshold * 0.5:
        return 'SELL'
    else:
        return 'HOLD'


# ============================================================
# EVALUATION FUNCTIONS
# ============================================================

def generate_historical_signals(symbols: List[str], days: int = 30) -> pd.DataFrame:
    """Generate historical signals for evaluation."""
    records = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 30)  # Extra buffer for calculations
    
    for symbol in symbols:
        # Generate full price series
        full_prices = generate_price_series(symbol, days + 60, start_date.strftime('%Y%m%d'))
        
        for day in range(30, 30 + days):
            date = start_date + timedelta(days=day)
            
            # Get prices up to this day
            prices_to_date = full_prices[:day+1]
            
            # Calculate indicators
            rsi = calculate_rsi(prices_to_date)
            macd = calculate_macd(prices_to_date)
            
            # Generate signal
            signal = generate_signal(rsi, macd['histogram'])
            
            # Calculate actual outcome (5-day forward return)
            if day + 5 < len(full_prices):
                actual = determine_actual_outcome(full_prices[day], full_prices[day + 5])
                future_return = (full_prices[day + 5] - full_prices[day]) / full_prices[day] * 100
            else:
                actual = 'HOLD'
                future_return = 0
            
            records.append({
                'date': date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'price': round(full_prices[day], 2),
                'rsi': rsi,
                'macd': macd['macd'],
                'signal': signal,
                'actual': actual,
                'future_return_pct': round(future_return, 2),
                'signal_correct': 1 if signal == actual else 0,
                'signal_profitable': 1 if (
                    (signal in ['BUY', 'STRONG_BUY'] and future_return > 0) or
                    (signal in ['SELL', 'STRONG_SELL'] and future_return < 0) or
                    (signal == 'HOLD' and abs(future_return) < 2)
                ) else 0
            })
    
    return pd.DataFrame(records)


def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate accuracy metrics."""
    total = len(df)
    correct = df['signal_correct'].sum()
    profitable = df['signal_profitable'].sum()
    
    # Signal distribution
    signal_counts = df['signal'].value_counts().to_dict()
    
    # By signal type accuracy
    signal_accuracy = {}
    for signal in SIGNAL_LABELS:
        mask = df['signal'] == signal
        if mask.sum() > 0:
            signal_accuracy[signal] = {
                'count': int(mask.sum()),
                'profitable': int(df.loc[mask, 'signal_profitable'].sum()),
                'accuracy': round(df.loc[mask, 'signal_profitable'].mean() * 100, 1)
            }
    
    # Confusion matrix data
    confusion = pd.crosstab(df['signal'], df['actual'])
    
    return {
        'total_signals': total,
        'exact_accuracy': round(correct / total * 100, 1),
        'profitable_accuracy': round(profitable / total * 100, 1),
        'signal_counts': signal_counts,
        'signal_accuracy': signal_accuracy,
        'confusion_matrix': confusion,
        'avg_return': round(df['future_return_pct'].mean(), 2),
        'rsi_mean': round(df['rsi'].mean(), 1),
        'rsi_std': round(df['rsi'].std(), 1),
    }


def simulate_backtest(df: pd.DataFrame, initial_capital: float = 10000) -> pd.DataFrame:
    """Simulate backtest with signals."""
    capital = initial_capital
    position = 0
    position_price = 0
    trades = []
    
    # Sort by date
    df_sorted = df.sort_values('date')
    
    for _, row in df_sorted.iterrows():
        signal = row['signal']
        price = row['price']
        symbol = row['symbol']
        
        # Only trade first symbol for simplicity
        if symbol != df_sorted['symbol'].iloc[0]:
            continue
        
        if signal in ['BUY', 'STRONG_BUY'] and position == 0:
            # Enter long position
            shares = capital / price
            position = shares
            position_price = price
            capital = 0
            trades.append({
                'date': row['date'],
                'action': 'BUY',
                'price': price,
                'shares': round(shares, 4),
                'capital': 0
            })
        
        elif signal in ['SELL', 'STRONG_SELL'] and position > 0:
            # Exit position
            capital = position * price
            pnl = (price - position_price) / position_price * 100
            trades.append({
                'date': row['date'],
                'action': 'SELL',
                'price': price,
                'shares': round(position, 4),
                'capital': round(capital, 2),
                'pnl_pct': round(pnl, 2)
            })
            position = 0
            position_price = 0
    
    # Final value
    final_value = capital if position == 0 else position * df_sorted['price'].iloc[-1]
    
    return pd.DataFrame(trades), final_value, initial_capital


# ============================================================
# VISUALIZATION FUNCTIONS
# ============================================================

def create_accuracy_gauge(accuracy: float, title: str = "Signal Accuracy") -> go.Figure:
    """Create a gauge chart for accuracy."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=accuracy,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 18, 'color': 'white'}},
        delta={'reference': 50, 'increasing': {'color': "#00ff88"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#00ff88" if accuracy >= 60 else "#ffaa00" if accuracy >= 50 else "#ff4444"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': 'rgba(255, 68, 68, 0.3)'},
                {'range': [40, 60], 'color': 'rgba(255, 170, 0, 0.3)'},
                {'range': [60, 100], 'color': 'rgba(0, 255, 136, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': accuracy
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig


def create_rsi_distribution(df: pd.DataFrame) -> go.Figure:
    """Create RSI distribution histogram."""
    fig = go.Figure()
    
    # Overall distribution
    fig.add_trace(go.Histogram(
        x=df['rsi'],
        nbinsx=20,
        name='RSI Distribution',
        marker_color='#00d4ff',
        opacity=0.7
    ))
    
    # Add vertical lines for zones
    fig.add_vline(x=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    fig.add_vline(x=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    
    fig.update_layout(
        title="RSI Distribution (All Signals)",
        xaxis_title="RSI Value",
        yaxis_title="Frequency",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,30,30,1)',
        font={'color': 'white'},
        height=300,
        showlegend=False,
        xaxis=dict(gridcolor='rgba(100,100,100,0.3)'),
        yaxis=dict(gridcolor='rgba(100,100,100,0.3)')
    )
    
    return fig


def create_confusion_matrix(confusion: pd.DataFrame) -> go.Figure:
    """Create confusion matrix heatmap."""
    # Ensure all labels are present
    all_labels = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']
    
    # Reindex to include all labels
    confusion_full = confusion.reindex(index=all_labels, columns=all_labels, fill_value=0)
    
    fig = go.Figure(data=go.Heatmap(
        z=confusion_full.values,
        x=all_labels,
        y=all_labels,
        colorscale='Blues',
        text=confusion_full.values,
        texttemplate='%{text}',
        textfont={'size': 12, 'color': 'white'},
        hoverongaps=False,
        showscale=True
    ))
    
    fig.update_layout(
        title="Confusion Matrix: Predicted vs Actual",
        xaxis_title="Actual Outcome",
        yaxis_title="Predicted Signal",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,30,30,1)',
        font={'color': 'white'},
        height=400,
        xaxis={'side': 'bottom'},
        yaxis={'autorange': 'reversed'}
    )
    
    return fig


def create_signal_breakdown(signal_accuracy: Dict) -> go.Figure:
    """Create signal accuracy breakdown bar chart."""
    signals = list(signal_accuracy.keys())
    accuracies = [signal_accuracy[s]['accuracy'] for s in signals]
    counts = [signal_accuracy[s]['count'] for s in signals]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=signals,
        y=accuracies,
        text=[f"{a}%<br>({c} signals)" for a, c in zip(accuracies, counts)],
        textposition='outside',
        marker_color=['#00ff88' if a >= 60 else '#ffaa00' if a >= 50 else '#ff4444' for a in accuracies],
        name='Accuracy %'
    ))
    
    fig.update_layout(
        title="Accuracy by Signal Type",
        xaxis_title="Signal",
        yaxis_title="Profitable Accuracy (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,30,30,1)',
        font={'color': 'white'},
        height=350,
        yaxis=dict(range=[0, 100], gridcolor='rgba(100,100,100,0.3)'),
        xaxis=dict(gridcolor='rgba(100,100,100,0.3)')
    )
    
    return fig


def create_pnl_chart(trades_df: pd.DataFrame, final_value: float, initial: float) -> go.Figure:
    """Create P&L chart from backtest."""
    if trades_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No trades executed", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': 'white'}, height=300)
        return fig
    
    # Calculate cumulative returns
    trades_df['cumulative_capital'] = initial
    capital = initial
    cumulative = []
    
    for i, row in trades_df.iterrows():
        if 'capital' in row and row['capital'] > 0:
            capital = row['capital']
        cumulative.append(capital)
    
    trades_df['cumulative_capital'] = cumulative
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trades_df['date'],
        y=trades_df['cumulative_capital'],
        mode='lines+markers',
        name='Portfolio Value',
        line=dict(color='#00d4ff', width=2),
        marker=dict(size=8)
    ))
    
    # Add horizontal line for initial capital
    fig.add_hline(y=initial, line_dash="dash", line_color="gray", 
                  annotation_text=f"Initial: ${initial:,.0f}")
    
    total_return = (final_value - initial) / initial * 100
    
    fig.update_layout(
        title=f"Backtest Results | Final: ${final_value:,.0f} ({total_return:+.1f}%)",
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,30,30,1)',
        font={'color': 'white'},
        height=300,
        xaxis=dict(gridcolor='rgba(100,100,100,0.3)'),
        yaxis=dict(gridcolor='rgba(100,100,100,0.3)')
    )
    
    return fig


def create_symbol_comparison(df: pd.DataFrame) -> go.Figure:
    """Create symbol-wise accuracy comparison."""
    symbol_stats = df.groupby('symbol').agg({
        'signal_profitable': 'mean',
        'future_return_pct': 'mean',
        'rsi': 'mean'
    }).reset_index()
    
    symbol_stats['accuracy'] = symbol_stats['signal_profitable'] * 100
    symbol_stats = symbol_stats.sort_values('accuracy', ascending=True)
    
    fig = go.Figure()
    
    colors = ['#00ff88' if a >= 60 else '#ffaa00' if a >= 50 else '#ff4444' 
              for a in symbol_stats['accuracy']]
    
    fig.add_trace(go.Bar(
        y=symbol_stats['symbol'],
        x=symbol_stats['accuracy'],
        orientation='h',
        marker_color=colors,
        text=[f"{a:.1f}%" for a in symbol_stats['accuracy']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Signal Accuracy by Symbol",
        xaxis_title="Profitable Accuracy (%)",
        yaxis_title="Symbol",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30,30,30,1)',
        font={'color': 'white'},
        height=400,
        xaxis=dict(range=[0, 100], gridcolor='rgba(100,100,100,0.3)'),
        yaxis=dict(gridcolor='rgba(100,100,100,0.3)')
    )
    
    return fig


# ============================================================
# MAIN EVALUATION FUNCTION
# ============================================================

def run_evaluation(symbols_str: str, days: int, initial_capital: float):
    """Run full evaluation and return all visualizations."""
    
    # Parse symbols
    if symbols_str.strip():
        symbols = [s.strip().upper() for s in symbols_str.split(',')]
    else:
        symbols = STATIC_UNIVERSE[:10]  # Default to first 10
    
    # Generate historical data
    df = generate_historical_signals(symbols, days)
    
    # Calculate metrics
    metrics = calculate_metrics(df)
    
    # Create visualizations
    gauge_fig = create_accuracy_gauge(metrics['profitable_accuracy'], "Profitable Signal Accuracy")
    rsi_fig = create_rsi_distribution(df)
    confusion_fig = create_confusion_matrix(metrics['confusion_matrix'])
    breakdown_fig = create_signal_breakdown(metrics['signal_accuracy'])
    symbol_fig = create_symbol_comparison(df)
    
    # Run backtest on first symbol
    trades_df, final_value, initial = simulate_backtest(df, initial_capital)
    pnl_fig = create_pnl_chart(trades_df, final_value, initial)
    
    # Summary text
    summary = f"""
## 📊 Evaluation Summary

### Overall Performance
- **Total Signals Generated:** {metrics['total_signals']}
- **Exact Match Accuracy:** {metrics['exact_accuracy']}%
- **Profitable Accuracy:** {metrics['profitable_accuracy']}%
- **Average 5-Day Return:** {metrics['avg_return']:+.2f}%

### RSI Statistics
- **Mean RSI:** {metrics['rsi_mean']}
- **RSI Std Dev:** {metrics['rsi_std']}

### Backtest Results ({symbols[0]})
- **Initial Capital:** ${initial_capital:,.0f}
- **Final Value:** ${final_value:,.0f}
- **Total Return:** {(final_value - initial_capital) / initial_capital * 100:+.1f}%
- **Total Trades:** {len(trades_df)}

### Signal Distribution
"""
    for signal, count in metrics['signal_counts'].items():
        summary += f"- **{signal}:** {count} signals\n"
    
    return summary, gauge_fig, rsi_fig, confusion_fig, breakdown_fig, pnl_fig, symbol_fig


# ============================================================
# GRADIO INTERFACE
# ============================================================

def create_interface():
    """Create the Gradio interface."""
    
    with gr.Blocks(
        title="TraderAI Pro - Signal Evaluation Dashboard",
        theme=gr.themes.Soft(
            primary_hue="cyan",
            secondary_hue="purple",
            neutral_hue="gray",
        ),
        css="""
        .gradio-container {background-color: #1a1a2e;}
        .gr-button-primary {background: linear-gradient(90deg, #00d4ff, #7c3aed);}
        """
    ) as demo:
        
        gr.Markdown("""
        # 🚀 TraderAI Pro - Signal Evaluation Dashboard
        
        Evaluate the accuracy of trading signals generated by the RSI + MACD engine.
        This dashboard simulates 30 days of historical signals and compares them to actual price movements.
        
        ---
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                symbols_input = gr.Textbox(
                    label="Symbols (comma-separated)",
                    placeholder="AAPL, NVDA, TSLA, MSFT, BTC-USD",
                    value="AAPL, NVDA, TSLA, RELIANCE.NS, BTC-USD, SPY",
                    info="Enter stock symbols to evaluate"
                )
            with gr.Column(scale=1):
                days_input = gr.Slider(
                    label="Evaluation Period (Days)",
                    minimum=7,
                    maximum=60,
                    value=30,
                    step=1
                )
            with gr.Column(scale=1):
                capital_input = gr.Number(
                    label="Initial Capital ($)",
                    value=10000,
                    minimum=1000,
                    maximum=1000000
                )
        
        run_btn = gr.Button("🔍 Run Evaluation", variant="primary", size="lg")
        
        summary_output = gr.Markdown(label="Summary")
        
        with gr.Row():
            with gr.Column():
                gauge_output = gr.Plot(label="Accuracy Gauge")
            with gr.Column():
                rsi_output = gr.Plot(label="RSI Distribution")
        
        with gr.Row():
            with gr.Column():
                confusion_output = gr.Plot(label="Confusion Matrix")
            with gr.Column():
                breakdown_output = gr.Plot(label="Signal Breakdown")
        
        with gr.Row():
            with gr.Column():
                pnl_output = gr.Plot(label="Backtest P&L")
            with gr.Column():
                symbol_output = gr.Plot(label="Symbol Comparison")
        
        gr.Markdown("""
        ---
        
        ### 📖 How to Interpret Results
        
        | Metric | Good | Average | Poor |
        |--------|------|---------|------|
        | **Profitable Accuracy** | > 60% | 50-60% | < 50% |
        | **Average Return** | > 1% | 0-1% | < 0% |
        
        #### Signal Definitions
        - **STRONG_BUY**: RSI < 30 + Positive MACD → Expect > 3% gain
        - **BUY**: RSI < 40 or Positive MACD → Expect 1-3% gain
        - **HOLD**: Neutral indicators → Expect < 1% movement
        - **SELL**: RSI > 60 or Negative MACD → Expect 1-3% loss
        - **STRONG_SELL**: RSI > 70 + Negative MACD → Expect > 3% loss
        
        ---
        
        **⚠️ Disclaimer:** This is for educational demonstration only. Past simulated performance does not guarantee future results. Not financial advice.
        
        **TraderAI Pro v4.8** | Academic Project
        """)
        
        run_btn.click(
            fn=run_evaluation,
            inputs=[symbols_input, days_input, capital_input],
            outputs=[summary_output, gauge_output, rsi_output, confusion_output, 
                    breakdown_output, pnl_output, symbol_output]
        )
    
    return demo


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("🚀 Starting TraderAI Pro Evaluation Dashboard...")
    print("📊 Access at: http://localhost:7860")
    
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )