import React, { useState, useRef, useEffect } from "react";
import "./GenAIChat.css";

// API Base URL - Update this for production deployment
// For production: const API_BASE = import.meta.env.VITE_API_BASE || window.location.origin;
const API_BASE = "http://localhost:8000";

// Currency detection based on ticker suffix
const getCurrencySymbol = (ticker) => {
  if (!ticker) return '$';
  if (ticker.includes('.NS') || ticker.includes('.BO')) return '₹';
  if (ticker.includes('.T') || ticker.includes('.SS')) return '¥';
  if (ticker.includes('.L')) return '£';
  if (ticker.includes('.DE') || ticker.includes('.PA')) return '€';
  if (ticker.includes('.HK')) return 'HK$';
  if (ticker.includes('.AX')) return 'A$';
  if (ticker.includes('.TO')) return 'C$';
  if (ticker.includes('.SA')) return 'R$';
  if (ticker.includes('.KS')) return '₩';
  if (ticker.includes('.SI')) return 'S$';
  if (ticker.includes('.SW')) return 'CHF ';
  return '$'; // Default USD
};

// Format price with currency
const formatPrice = (price, ticker) => {
  if (price === null || price === undefined || isNaN(price)) return '--';
  const currency = getCurrencySymbol(ticker);
  return `${currency}${Number(price).toLocaleString(undefined, { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`;
};

export default function GenAIChat({ currentTicker = "AAPL", traderType = "swing", stockData = {}, signal = "" }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // LLM settings from localStorage
  const llmProvider = localStorage.getItem('llm_provider') || '';
  const llmModel = localStorage.getItem('llm_model') || '';
  const llmApiKey = localStorage.getItem('llm_api_key') || '';

  // Get currency for current ticker
  const currency = getCurrencySymbol(currentTicker);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const quickPrompts = [
    `Should I ${signal?.includes('BUY') ? 'buy' : 'hold'} ${currentTicker}?`,
    `Risk analysis for ${currentTicker}`,
    `Entry & exit points`,
    `Technical outlook`,
    `Compare to sector peers`,
    `News sentiment summary`
  ];

  const sendMessage = async (customMessage = null) => {
    const msg = customMessage || input;
    if (!msg.trim() || loading) return;

    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    setInput("");

    try {
      const res = await fetch(`${API_BASE}/api/genai/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: msg,
          symbol: currentTicker,
          trader_style: traderType,
          price: stockData?.price,
          currency: currency,
          rsi: stockData?.rsi,
          signal: signal,
          ...(llmProvider && { llm_provider: llmProvider }),
          ...(llmModel && { llm_model: llmModel }),
          ...(llmApiKey && { llm_api_key: llmApiKey }),
        }),
      });

      const data = await res.json();
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.answer || data.response || "I couldn't process that request."
      }]);
    } catch {
      // Provide contextual fallback with correct currency
      let fallback = `Based on ${traderType} analysis, ${currentTicker} is showing a ${signal || 'HOLD'} signal. `;
      fallback += stockData?.rsi 
        ? `RSI is at ${stockData.rsi.toFixed(1)}, indicating ${stockData.rsi < 30 ? 'oversold' : stockData.rsi > 70 ? 'overbought' : 'neutral'} conditions. `
        : '';
      fallback += `Current price: ${formatPrice(stockData?.price, currentTicker)}. Please ensure backend is running for full AI analysis.`;
      
      setMessages(prev => [...prev, { role: "assistant", content: fallback }]);
    }

    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-avatar">🤖<span className="online-dot" /></div>
          <div>
            <h3>AI Trading Assistant</h3>
            <p>Analyzing <span className="ticker">{currentTicker}</span> • {formatPrice(stockData?.price, currentTicker)}</p>
          </div>
        </div>
        <div className="chat-header-right">
          <span className={`strategy-badge ${traderType}`}>{traderType}</span>
          {messages.length > 0 && <button onClick={() => setMessages([])} className="clear-btn">Clear</button>}
        </div>
      </div>

      <div className="chat-context">
        <span>Signal: <strong className={signal?.includes('BUY') ? 'bullish' : 'neutral'}>{signal || 'N/A'}</strong></span>
        <span>RSI: <strong>{stockData?.rsi?.toFixed(1) || '--'}</strong></span>
        <span>Market: <strong>{stockData?.market || 'US'}</strong></span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">💬</div>
            <h4>Ask about {currentTicker}</h4>
            <p>Get AI-powered analysis, risk assessment, entry/exit points, and trading strategies.</p>
            <div className="quick-prompts">
              {quickPrompts.map((p, i) => (
                <button key={i} onClick={() => sendMessage(p)} className="quick-btn">{p}</button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                <div className="message-bubble">
                  {m.role === "assistant" && <div className="assistant-label">🤖 AI</div>}
                  <p>{m.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-bubble">
                  <div className="typing"><span></span><span></span><span></span></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <div className="chat-input-area">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === "Enter" && sendMessage()}
          placeholder={`Ask about ${currentTicker}...`}
          disabled={loading}
        />
        <button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
      <p className="disclaimer">AI responses are for informational purposes only. Not financial advice.</p>
    </div>
  );
}