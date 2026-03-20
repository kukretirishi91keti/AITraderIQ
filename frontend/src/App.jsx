import React, { useState, useEffect, useCallback, useRef, useMemo, lazy, Suspense } from 'react';
import { useAuth } from './context/AuthContext';
import ConnectionStatus from './components/ConnectionStatus';
import BacktestPanel from './components/BacktestPanel';
import SentimentDashboard from './components/SentimentDashboard';
import MarketCommentary from './components/MarketCommentary';
import AIScanner from './components/AIScanner';
import ChartPanel from './components/ChartPanel';
import PaperTradingPanel from './components/PaperTradingPanel';
import StrategyBuilder from './components/StrategyBuilder';
import { getPriceStream } from './services/websocket';

// Constants
import { MARKETS, STATIC_UNIVERSE } from './constants/markets';
import {
  API_BASE, APP_VERSION, POLLING_INTERVALS,
  TRADING_STYLES, AI_PROMPTS, KEYBOARD_SHORTCUTS,
} from './constants/appConfig';

// Utils
import {
  formatLargeNumber, formatPrice, getSignalValue,
  getSignalColor, getRsiColor, getFlagForSymbol,
} from './utils/formatters';
import { fetchTopMovers, generateDemoMovers } from './utils/movers';

// Lazy-loaded modals (code-split)
const UserGuideModal = lazy(() => import('./components/modals/UserGuideModal'));
const WhatsNextModal = lazy(() => import('./components/modals/WhatsNextModal'));
const KeyboardShortcutsModal = lazy(() => import('./components/modals/KeyboardShortcutsModal'));
const WatchlistEditModal = lazy(() => import('./components/modals/WatchlistEditModal'));
const ScreenerModal = lazy(() => import('./components/modals/ScreenerModal'));
const PortfolioModal = lazy(() => import('./components/modals/PortfolioModal'));
const AlertsModal = lazy(() => import('./components/modals/AlertsModal'));
const AddToPortfolioModal = lazy(() => import('./components/modals/AddToPortfolioModal'));
const CreditsModal = lazy(() => import('./components/modals/CreditsModal'));

// ============================================================
// MAIN APP COMPONENT
// ============================================================

export default function App() {
  const { user, isLoggedIn, setShowAuthModal, logout } = useAuth();

  // Core state
  const [selectedMarket, setSelectedMarket] = useState('US');
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [searchQuery, setSearchQuery] = useState('');
  const [traderStyle, setTraderStyle] = useState('Swing');
  const [chartInterval, setChartInterval] = useState('1d');

  // Data state
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]);
  const [signals, setSignals] = useState(null);
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState(null);
  const [movers, setMovers] = useState([]);
  const [screenerData, setScreenerData] = useState({});

  // UI state
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('technicals');
  const [financials, setFinancials] = useState(null);
  const [financialsLoading, setFinancialsLoading] = useState(false);
  const [showScreener, setShowScreener] = useState(false);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showUserGuide, setShowUserGuide] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [showWhatsNext, setShowWhatsNext] = useState(false);
  const [showWatchlistEdit, setShowWatchlistEdit] = useState(false);
  const [showAddToPortfolio, setShowAddToPortfolio] = useState(false);
  const [portfolioShares, setPortfolioShares] = useState('');
  const [portfolioAvgPrice, setPortfolioAvgPrice] = useState('');
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

  // Screener filters
  const [screenerFilter, setScreenerFilter] = useState('all');
  const [screenerCategory, setScreenerCategory] = useState('all');
  const [screenerLoading, setScreenerLoading] = useState(false);
  const [screenerCategories, setScreenerCategories] = useState([]);

  // Watchlist & Alerts
  const [watchlist, setWatchlist] = useState(['AAPL', 'NVDA', 'TSLA', 'BTC-USD', 'SPY']);
  const [alerts, setAlerts] = useState([
    { symbol: 'AAPL', condition: 'above', price: 250 },
    { symbol: 'BTC-USD', condition: 'above', price: 110000 }
  ]);
  const [newAlertPrice, setNewAlertPrice] = useState('');
  const [newAlertCondition, setNewAlertCondition] = useState('above');

  // Portfolio
  const [portfolio, setPortfolio] = useState([
    { symbol: 'AAPL', shares: 10, avgPrice: 150 },
    { symbol: 'NVDA', shares: 5, avgPrice: 450 },
    { symbol: 'MSFT', shares: 8, avgPrice: 380 },
  ]);

  // Investor Profile
  const [investorProfile, setInvestorProfile] = useState(() => {
    const saved = localStorage.getItem('investorProfile');
    return saved ? JSON.parse(saved) : {
      name: '', riskTolerance: 'moderate', investmentHorizon: 'medium',
      experience: 'intermediate', capitalRange: 'medium', goals: []
    };
  });
  const [showInvestorProfile, setShowInvestorProfile] = useState(false);

  // AI Chat
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiSettings, setShowAiSettings] = useState(false);
  const [llmProvider, setLlmProvider] = useState(() => localStorage.getItem('llm_provider') || '');
  const [llmModel, setLlmModel] = useState(() => localStorage.getItem('llm_model') || '');
  const [llmApiKey, setLlmApiKey] = useState(() => localStorage.getItem('llm_api_key') || '');

  // Credits
  const [credits, setCredits] = useState({ balance: 50, tier: 'free', daily_grant: 50 });
  const [showCreditsModal, setShowCreditsModal] = useState(false);

  // Health monitoring
  const [healthStatus, setHealthStatus] = useState('HEALTHY');
  const [pollingInterval, setPollingInterval] = useState(POLLING_INTERVALS.HEALTHY);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // Refs
  const intervalRef = useRef(null);
  const searchInputRef = useRef(null);

  // WebSocket real-time price updates
  useEffect(() => {
    const stream = getPriceStream();
    stream.connect();
    const cleanup = stream.onQuote((data) => {
      if (data.symbol === selectedSymbol) {
        setQuote(prev => prev ? { ...prev, price: data.price, change: data.change, changePercent: data.changePercent, volume: data.volume, dataQuality: data.dataQuality } : prev);
      }
    });
    const allSymbols = [...new Set([selectedSymbol, ...watchlist])];
    stream.subscribe(allSymbols);
    return () => { cleanup(); };
  }, [selectedSymbol, watchlist]);

  const currentMarket = useMemo(() =>
    MARKETS.find(m => m.id === selectedMarket) || MARKETS[0],
    [selectedMarket]
  );

  // ============================================================
  // KEYBOARD SHORTCUTS
  // ============================================================
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') e.target.blur();
        return;
      }
      const anyModalOpen = showScreener || showPortfolio || showAddToPortfolio || showAlerts ||
                          showUserGuide || showWhatsNext || showWatchlistEdit || showKeyboardHelp;
      switch (e.key) {
        case '/': e.preventDefault(); searchInputRef.current?.focus(); break;
        case '1': e.preventDefault(); setChartInterval('1m'); break;
        case '2': e.preventDefault(); setChartInterval('5m'); break;
        case '3': e.preventDefault(); setChartInterval('15m'); break;
        case '4': e.preventDefault(); setChartInterval('1h'); break;
        case '5': e.preventDefault(); setChartInterval('1d'); break;
        case '6': e.preventDefault(); setChartInterval('1wk'); break;
        case 'w': case 'W':
          e.preventDefault();
          if (!watchlist.includes(selectedSymbol)) setWatchlist(prev => [...prev, selectedSymbol]);
          else setWatchlist(prev => prev.filter(s => s !== selectedSymbol));
          break;
        case 'p': case 'P': e.preventDefault(); if (!anyModalOpen) setShowPortfolio(true); break;
        case 's': case 'S': e.preventDefault(); if (!anyModalOpen) { setShowScreener(true); fetchScreenerData(); } break;
        case 'a': case 'A': e.preventDefault(); if (!anyModalOpen) setShowAlerts(true); break;
        case '?': e.preventDefault(); if (!anyModalOpen) setShowKeyboardHelp(true); break;
        case 'Escape':
          setShowScreener(false); setShowPortfolio(false); setShowAddToPortfolio(false);
          setShowAlerts(false); setShowUserGuide(false); setShowWhatsNext(false);
          setShowWatchlistEdit(false); setShowKeyboardHelp(false); setShowDebug(false);
          break;
        default: break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedSymbol, watchlist, showScreener, showPortfolio, showAlerts,
      showUserGuide, showWhatsNext, showWatchlistEdit, showAddToPortfolio, showKeyboardHelp]);

  // ============================================================
  // SYMBOL & MARKET HANDLERS
  // ============================================================
  const handleSymbolSelect = useCallback((symbol) => {
    const upperSymbol = symbol.toUpperCase();
    setSelectedSymbol(upperSymbol);
    setSearchQuery('');
    setAiMessages([]);
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) setSelectedMarket('India');
    else if (upperSymbol.endsWith('.L')) setSelectedMarket('UK');
    else if (upperSymbol.endsWith('.DE')) setSelectedMarket('Germany');
    else if (upperSymbol.endsWith('.T')) setSelectedMarket('Japan');
    else if (upperSymbol.endsWith('.AX')) setSelectedMarket('Australia');
    else if (upperSymbol.includes('-USD') || upperSymbol === 'BTC' || upperSymbol === 'ETH') setSelectedMarket('Crypto');
    else if (upperSymbol.includes('=X')) setSelectedMarket('Forex');
    else if (upperSymbol.includes('=F')) setSelectedMarket('Commodities');
    else if (['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'GLD'].includes(upperSymbol)) setSelectedMarket('ETF');
  }, []);

  const handleMarketChange = useCallback(async (marketId) => {
    const fallbackMovers = generateDemoMovers(marketId);
    setMovers(fallbackMovers);
    setSelectedMarket(marketId);
    const market = MARKETS.find(m => m.id === marketId);
    if (market) {
      setSelectedSymbol(market.defaultSymbol);
      setAiMessages([]);
      try {
        const freshMovers = await fetchTopMovers(marketId);
        if (freshMovers && freshMovers.length > 0) setMovers(freshMovers);
      } catch (err) { /* fallback already set */ }
    }
  }, []);

  // ============================================================
  // DATA FETCHING
  // ============================================================
  const fetchAllData = useCallback(async (signal = null) => {
    if (!selectedSymbol) return;
    setLoading(true);
    setFinancialsLoading(true);
    try {
      const [quoteRes, historyRes, signalsRes, newsRes, sentimentRes, financialsRes, healthRes] =
        await Promise.allSettled([
          fetch(`${API_BASE}/api/v4/quote/${selectedSymbol}`, { signal }),
          fetch(`${API_BASE}/api/v4/history/${selectedSymbol}?interval=${chartInterval}`, { signal }),
          fetch(`${API_BASE}/api/v4/signals/${selectedSymbol}`, { signal }),
          fetch(`${API_BASE}/api/news/${selectedSymbol}`, { signal }),
          fetch(`${API_BASE}/api/sentiment/reddit/${selectedSymbol}`, { signal }),
          fetch(`${API_BASE}/api/v4/financials/${selectedSymbol}`, { signal }),
          fetch(`${API_BASE}/api/health`, { signal }),
        ]);
      if (signal?.aborted) return;

      if (quoteRes.status === 'fulfilled' && quoteRes.value.ok) {
        setQuote(await quoteRes.value.json());
      }
      if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
        const historyData = await historyRes.value.json();
        const chartData = historyData.candles || historyData.history || historyData.data || historyData.prices || [];
        setHistory(Array.isArray(chartData) ? chartData : []);
      } else if (historyRes.status === 'fulfilled') {
        setHistory([]);
      }
      if (signalsRes.status === 'fulfilled' && signalsRes.value.ok) {
        setSignals(await signalsRes.value.json());
      }
      if (newsRes.status === 'fulfilled' && newsRes.value.ok) {
        const newsData = await newsRes.value.json();
        setNews(newsData.articles || []);
      }
      if (sentimentRes.status === 'fulfilled' && sentimentRes.value.ok) {
        setSentiment(await sentimentRes.value.json());
      }
      if (financialsRes.status === 'fulfilled' && financialsRes.value.ok) {
        try {
          const data = await financialsRes.value.json();
          if (data.success && data.financials) {
            const f = data.financials;
            setFinancials({
              symbol: data.symbol, name: data.name, currency: data.currency,
              sector: f.sector || 'Technology', industry: f.industry || 'Software',
              marketCap: f.market_cap_formatted || formatLargeNumber(f.market_cap),
              peRatio: f.pe_ratio ? f.pe_ratio.toFixed(2) : 'N/A',
              revenue: f.revenue_formatted || formatLargeNumber(f.revenue),
              eps: f.eps ? `$${f.eps.toFixed(2)}` : 'N/A',
              dividendYield: f.dividend_yield ? `${f.dividend_yield.toFixed(2)}%` : '0%',
              beta: f.beta ? f.beta.toFixed(2) : 'N/A',
              fiftyTwoWeekHigh: f['52_week_high'] || f.fiftyTwoWeekHigh,
              fiftyTwoWeekLow: f['52_week_low'] || f.fiftyTwoWeekLow,
              profitMargin: f.profit_margin ? `${f.profit_margin.toFixed(1)}%` : 'N/A',
              dataQuality: data.source || 'DEMO',
            });
          } else if (data.marketCap || data.peRatio) {
            setFinancials(data);
          } else {
            setFinancials(null);
          }
        } catch { setFinancials(null); }
      } else {
        setFinancials(null);
      }
      setFinancialsLoading(false);

      if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
        const healthData = await healthRes.value.json();
        setHealthStatus(healthData.status?.toUpperCase() || 'HEALTHY');
        if (healthData.polling_recommendation) setPollingInterval(healthData.polling_recommendation * 1000);
      }
      setLastFetchTime(new Date());
      setLoading(false);
    } catch (err) {
      if (err.name === 'AbortError') return;
      setHealthStatus('ERROR');
      setPollingInterval(POLLING_INTERVALS.ERROR);
      setLoading(false);
      setFinancialsLoading(false);
    }
  }, [selectedSymbol, chartInterval, selectedMarket]);

  // ============================================================
  // SCREENER
  // ============================================================
  const fetchScreenerData = useCallback(async () => {
    setScreenerLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/screener/universe`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const metaKeys = ['timestamp', 'categories', 'total_stocks', 'source', 'category_counts', 'signal_counts', 'all', 'total_count', 'demoMode', 'refresh_interval', 'message'];
      const categoryKeys = Object.keys(data).filter(k => !metaKeys.includes(k));
      if (categoryKeys.length > 0) setScreenerCategories(categoryKeys);
      const processed = {};
      categoryKeys.forEach(category => {
        const stocks = data[category];
        if (Array.isArray(stocks) && stocks.length > 0) {
          processed[category] = stocks.map(s => ({
            symbol: s.symbol, name: s.name || s.symbol.split('.')[0],
            price: s.price, changePct: s.change_percent || s.changePct || 0,
            rsi: s.rsi, signal: s.signal, currency: s.currency || '$',
            flag: getFlagForSymbol(s.symbol), dataQuality: s.dataQuality || 'DEMO'
          }));
        }
      });
      if (Object.keys(processed).length === 0) {
        Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
          processed[category] = stocks.map(s => ({
            ...s, rsi: Math.random() * 100, signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
            price: 100 + Math.random() * 500, changePct: (Math.random() * 10 - 5).toFixed(2),
            flag: s.flag || getFlagForSymbol(s.symbol), dataQuality: 'DEMO'
          }));
        });
        setScreenerCategories(Object.keys(STATIC_UNIVERSE));
      }
      setScreenerData(processed);
    } catch {
      const demo = {};
      Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
        demo[category] = stocks.map(s => ({
          ...s, rsi: Math.random() * 100, signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
          price: 100 + Math.random() * 500, changePct: (Math.random() * 10 - 5).toFixed(2),
          flag: s.flag || getFlagForSymbol(s.symbol), dataQuality: 'DEMO'
        }));
      });
      setScreenerData(demo);
      setScreenerCategories(Object.keys(STATIC_UNIVERSE));
    } finally {
      setScreenerLoading(false);
    }
  }, []);

  // ============================================================
  // AI CHAT
  // ============================================================
  const handleAiSubmit = async (customPrompt = null) => {
    const prompt = customPrompt || aiInput.trim();
    if (!prompt || aiLoading) return;
    setAiMessages(prev => [...prev, { role: 'user', content: prompt }]);
    setAiInput('');
    setAiLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/genai/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: prompt, symbol: selectedSymbol, price: quote?.price,
          currency: currentMarket.currency, market: currentMarket.name,
          trader_style: traderStyle.toLowerCase(),
          rsi: getSignalValue(signals?.rsi), signal: signals?.signal || signals?.overall_signal,
          ...(llmProvider && { llm_provider: llmProvider }),
          ...(llmModel && { llm_model: llmModel }),
          ...(llmApiKey && { llm_api_key: llmApiKey }),
        })
      });
      const data = await response.json();
      const sourceLabel = data.source === 'fallback' ? 'AI Analysis (free)' : data.provider || data.source || 'AI';
      setAiMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || data.response || 'Unable to generate response',
        source: sourceLabel,
      }]);
      // Refresh credits after AI query
      try {
        const token = localStorage.getItem('traderai_token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const credRes = await fetch(`${API_BASE}/api/credits/balance`, { headers });
        if (credRes.ok) setCredits(await credRes.json());
      } catch { /* non-critical */ }
    } catch (err) {
      setAiMessages(prev => [...prev, { role: 'assistant', content: `AI service temporarily unavailable. Error: ${err.message}`, source: 'error' }]);
    } finally {
      setAiLoading(false);
    }
  };

  // ============================================================
  // WATCHLIST / PORTFOLIO / ALERT HANDLERS
  // ============================================================
  const addToWatchlist = useCallback(() => {
    if (selectedSymbol && !watchlist.includes(selectedSymbol)) setWatchlist(prev => [...prev, selectedSymbol]);
  }, [selectedSymbol, watchlist]);

  const isInWatchlist = useMemo(() => watchlist.includes(selectedSymbol), [watchlist, selectedSymbol]);
  const isInPortfolio = useMemo(() => portfolio.some(p => p.symbol === selectedSymbol), [portfolio, selectedSymbol]);

  const addToPortfolio = useCallback(() => {
    const shares = parseFloat(portfolioShares);
    const avgPrice = parseFloat(portfolioAvgPrice);
    if (isNaN(shares) || shares <= 0 || isNaN(avgPrice) || avgPrice <= 0) return;
    setPortfolio(prev => {
      const existing = prev.find(p => p.symbol === selectedSymbol);
      if (existing) {
        const totalShares = existing.shares + shares;
        const newAvgPrice = ((existing.shares * existing.avgPrice) + (shares * avgPrice)) / totalShares;
        return prev.map(p => p.symbol === selectedSymbol ? { ...p, shares: totalShares, avgPrice: newAvgPrice } : p);
      }
      return [...prev, { symbol: selectedSymbol, shares, avgPrice }];
    });
    setPortfolioShares(''); setPortfolioAvgPrice(''); setShowAddToPortfolio(false);
  }, [selectedSymbol, portfolioShares, portfolioAvgPrice]);

  const removeFromPortfolio = useCallback((symbol) => {
    setPortfolio(prev => prev.filter(p => p.symbol !== symbol));
  }, []);

  const addAlert = useCallback(() => {
    const price = parseFloat(newAlertPrice);
    if (isNaN(price) || price <= 0) return;
    const newAlert = { symbol: selectedSymbol, condition: newAlertCondition, price };
    if (!alerts.some(a => a.symbol === newAlert.symbol && a.condition === newAlert.condition && a.price === newAlert.price)) {
      setAlerts(prev => [...prev, newAlert]);
      setNewAlertPrice('');
    }
  }, [selectedSymbol, newAlertCondition, newAlertPrice, alerts]);

  const removeAlert = useCallback((index) => {
    setAlerts(prev => prev.filter((_, i) => i !== index));
  }, []);

  // ============================================================
  // EFFECTS
  // ============================================================
  useEffect(() => {
    const loadMovers = async () => {
      try {
        const freshMovers = await fetchTopMovers(selectedMarket);
        if (freshMovers && freshMovers.length > 0) setMovers(freshMovers);
        else setMovers(generateDemoMovers(selectedMarket));
      } catch { setMovers(generateDemoMovers(selectedMarket)); }
    };
    loadMovers();
  }, [selectedMarket]);

  useEffect(() => {
    // Clear stale chart data immediately when interval changes
    setHistory([]);
    setLoading(true);

    const controller = new AbortController();
    fetchAllData(controller.signal);
    intervalRef.current = setInterval(() => fetchAllData(null), pollingInterval);
    return () => { controller.abort(); if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchAllData, pollingInterval]);

  // Fetch credits balance
  useEffect(() => {
    const fetchCredits = async () => {
      try {
        const token = localStorage.getItem('traderai_token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch(`${API_BASE}/api/credits/balance`, { headers });
        if (res.ok) setCredits(await res.json());
      } catch { /* credits display is non-critical */ }
    };
    fetchCredits();
    const creditsInterval = setInterval(fetchCredits, 60000); // refresh every minute
    return () => clearInterval(creditsInterval);
  }, [isLoggedIn]);

  // Filtered screener data
  const filteredScreenerData = useMemo(() => {
    let data = { ...screenerData };
    if (screenerCategory !== 'all') data = { [screenerCategory]: screenerData[screenerCategory] || [] };
    if (screenerFilter !== 'all') {
      const filtered = {};
      Object.entries(data).forEach(([cat, stocks]) => {
        if (!Array.isArray(stocks)) return;
        const filteredStocks = stocks.filter(stock => {
          const rsi = stock.rsi || 50;
          if (screenerFilter === 'oversold') return rsi < 30;
          if (screenerFilter === 'overbought') return rsi > 70;
          if (screenerFilter === 'buy') { const sig = (stock.signal || '').toUpperCase(); return sig === 'BUY' || sig === 'STRONG BUY' || sig === 'STRONG_BUY'; }
          return true;
        });
        if (filteredStocks.length > 0) filtered[cat] = filteredStocks;
      });
      data = filtered;
    }
    return data;
  }, [screenerData, screenerCategory, screenerFilter]);

  // ============================================================
  // RENDER
  // ============================================================
  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Status Bar */}
      <div className="bg-gray-950 px-4 py-1 flex items-center justify-between text-xs text-gray-500 border-b border-gray-800">
        <span>
          {healthStatus === 'HEALTHY' ? '🟢' : healthStatus === 'DEGRADED' ? '🟡' : '🔴'}
          {healthStatus === 'HEALTHY' ? ' System healthy' : ` Status: ${healthStatus}`}
          {' • Polling: '}{pollingInterval / 1000}s{' • Press ? for shortcuts'}
        </span>
        <a href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">API Docs</a>
      </div>

      {/* Header */}
      <header className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-cyan-400">TraderAI Pro</h1>
            <span className="text-xs text-gray-500">v{APP_VERSION}</span>
            <div className="relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) handleSymbolSelect(searchQuery.trim().toUpperCase());
                  if (e.key === 'Escape') { e.target.blur(); setSearchQuery(''); }
                }}
                placeholder="Search symbols... (press /)"
                className="bg-gray-700 px-4 py-2 rounded-lg text-sm w-56 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => { setShowScreener(true); fetchScreenerData(); }} className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm font-medium">Screener</button>
            <button onClick={() => setShowPortfolio(true)} className="px-3 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium">💰 Portfolio</button>
            <button onClick={() => setShowAlerts(true)} className="px-3 py-2 bg-orange-600 hover:bg-orange-500 rounded-lg text-sm font-medium relative">
              🔔 Alerts
              {alerts.length > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-xs w-5 h-5 rounded-full flex items-center justify-center">{alerts.length}</span>}
            </button>
            <button onClick={() => setShowWhatsNext(true)} className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">🚀 What&apos;s Next</button>
            <button onClick={() => setShowUserGuide(true)} className="px-3 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium">📖 Guide</button>
            <button onClick={() => setShowDebug(!showDebug)} className="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg text-sm font-medium">🔧</button>
            <ConnectionStatus />
            <button onClick={() => setShowCreditsModal(true)} className="px-3 py-2 bg-yellow-600/80 hover:bg-yellow-500 rounded-lg text-sm font-medium flex items-center gap-1" title="Credits & Pricing">
              <span>{credits.balance ?? 50}</span>
              <span className="text-yellow-200 text-xs">credits</span>
            </button>
            {isLoggedIn ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-cyan-400">{user?.username}</span>
                <span className="text-xs text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded">{credits.tier || 'free'}</span>
                <button onClick={logout} className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">Logout</button>
              </div>
            ) : (
              <button onClick={() => setShowAuthModal(true)} className="px-3 py-2 bg-cyan-700 hover:bg-cyan-600 rounded-lg text-sm font-medium">Login</button>
            )}
          </div>
        </div>

        {/* Market Selector */}
        <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-2">
          {MARKETS.map(market => (
            <button
              key={market.id}
              onClick={() => handleMarketChange(market.id)}
              className={`px-3 py-1 rounded text-sm whitespace-nowrap transition-colors ${
                selectedMarket === market.id ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {market.flag} {market.name}
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
        {/* Left Sidebar */}
        <aside className="w-full md:w-56 bg-gray-800 border-r border-gray-700 p-4 space-y-6 overflow-y-auto md:block hidden">
          {/* Trading Style */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Trading Style</h3>
            <select value={traderStyle} onChange={(e) => setTraderStyle(e.target.value)} className="w-full bg-gray-700 text-white px-3 py-2 rounded text-sm">
              {Object.keys(TRADING_STYLES).map(style => <option key={style} value={style}>{style}</option>)}
            </select>
          </div>

          {/* Investor Profile - Collapsible */}
          <div className="bg-gray-700/50 rounded-lg border border-gray-600/50 overflow-hidden">
            <button onClick={() => setShowInvestorProfile(!showInvestorProfile)} className="w-full p-3 flex items-center justify-between hover:bg-gray-700/30 transition-colors">
              <div className="flex items-center gap-2">
                <span>👤</span>
                <span className="font-medium text-sm">Investor Profile</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded border ${
                  investorProfile.riskTolerance === 'conservative' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  investorProfile.riskTolerance === 'aggressive' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                }`}>{investorProfile.riskTolerance?.toUpperCase() || 'MODERATE'}</span>
                <span className={`transform transition-transform text-xs ${showInvestorProfile ? 'rotate-180' : ''}`}>▼</span>
              </div>
            </button>
            {showInvestorProfile && (
              <div className="p-3 border-t border-gray-600/50 space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Display Name</label>
                  <input type="text" value={investorProfile.name} onChange={(e) => setInvestorProfile(prev => ({ ...prev, name: e.target.value }))} placeholder="Your name" className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Risk Tolerance</label>
                  <div className="grid grid-cols-3 gap-1">
                    {['conservative', 'moderate', 'aggressive'].map(level => (
                      <button key={level} onClick={() => setInvestorProfile(prev => ({ ...prev, riskTolerance: level }))}
                        className={`py-1.5 px-1 rounded text-xs font-medium transition-all border ${
                          investorProfile.riskTolerance === level
                            ? level === 'conservative' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                              level === 'aggressive' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                              'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                            : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                        }`}>
                        {level === 'conservative' ? '🛡️' : level === 'aggressive' ? '🔥' : '⚖️'}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Horizon</label>
                  <select value={investorProfile.investmentHorizon} onChange={(e) => setInvestorProfile(prev => ({ ...prev, investmentHorizon: e.target.value }))} className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500">
                    <option value="short">Short (&lt;1 year)</option>
                    <option value="medium">Medium (1-5 years)</option>
                    <option value="long">Long (5+ years)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Experience</label>
                  <select value={investorProfile.experience} onChange={(e) => setInvestorProfile(prev => ({ ...prev, experience: e.target.value }))} className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500">
                    <option value="beginner">🌱 Beginner</option>
                    <option value="intermediate">📈 Intermediate</option>
                    <option value="advanced">🎯 Advanced</option>
                    <option value="expert">🏆 Expert</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Capital Range</label>
                  <select value={investorProfile.capitalRange} onChange={(e) => setInvestorProfile(prev => ({ ...prev, capitalRange: e.target.value }))} className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500">
                    <option value="small">$1K - $10K</option>
                    <option value="medium">$10K - $100K</option>
                    <option value="large">$100K - $1M</option>
                    <option value="institutional">$1M+</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Goals</label>
                  <div className="flex flex-wrap gap-1">
                    {['income', 'growth', 'preservation', 'speculation'].map(goal => (
                      <button key={goal} onClick={() => {
                        const goals = investorProfile.goals || [];
                        const newGoals = goals.includes(goal) ? goals.filter(g => g !== goal) : [...goals, goal];
                        setInvestorProfile(prev => ({ ...prev, goals: newGoals }));
                      }} className={`py-1 px-2 rounded text-xs transition-all border ${
                        (investorProfile.goals || []).includes(goal)
                          ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                          : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                      }`}>
                        {goal === 'income' ? '💰' : goal === 'growth' ? '📈' : goal === 'preservation' ? '🛡️' : '🎲'}
                      </button>
                    ))}
                  </div>
                </div>
                <button onClick={() => { localStorage.setItem('investorProfile', JSON.stringify(investorProfile)); setShowInvestorProfile(false); }}
                  className="w-full py-2 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium rounded hover:opacity-90 transition-opacity">
                  Save Profile
                </button>
                {investorProfile.name && (
                  <div className="p-2 bg-gray-700/30 rounded text-xs text-gray-400">
                    <span className="text-white font-medium">{investorProfile.name}</span> • {investorProfile.experience} • {investorProfile.riskTolerance} risk
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Top Movers */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Movers</h3>
            <div className="space-y-1">
              {movers.slice(0, 4).map(mover => (
                <button key={mover.symbol} onClick={() => handleSymbolSelect(mover.fullSymbol || mover.symbol)} className="w-full flex items-center justify-between p-2 rounded text-sm hover:bg-gray-700 transition-colors">
                  <span className="text-cyan-400">{mover.symbol}</span>
                  <span className={`text-sm ${parseFloat(mover.change) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {parseFloat(mover.change) >= 0 ? '+' : ''}{mover.change}%
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Watchlist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs text-gray-400 uppercase tracking-wide">Watchlist</h3>
              <button onClick={() => setShowWatchlistEdit(true)} className="text-xs text-cyan-400 hover:underline">Edit</button>
            </div>
            <div className="space-y-1">
              {watchlist.slice(0, 5).map(symbol => (
                <button key={symbol} onClick={() => handleSymbolSelect(symbol)} className={`w-full text-left p-2 rounded text-sm transition-colors ${selectedSymbol === symbol ? 'bg-cyan-600/30 text-cyan-400' : 'hover:bg-gray-700'}`}>
                  {symbol}
                </button>
              ))}
              {watchlist.length > 5 && (
                <button onClick={() => setShowWatchlistEdit(true)} className="w-full text-center text-xs text-gray-500 hover:text-cyan-400 py-1">+{watchlist.length - 5} more</button>
              )}
            </div>
          </div>
        </aside>

        {/* Main Panel */}
        <main className="flex-1 p-4 overflow-y-auto">
          {/* Symbol Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold">{selectedSymbol}</h2>
                <span className="px-2 py-0.5 bg-cyan-600/30 text-cyan-400 text-xs rounded">DEMO</span>
                <span className="text-2xl font-bold">{currentMarket.currency}{quote?.price?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span>{currentMarket.flag} {currentMarket.name}</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-400">{currentMarket.currencyName}</span>
                {quote?.changePercent !== undefined && (
                  <span className={quote.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {quote.changePercent >= 0 ? '+' : ''}{quote.changePercent.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={addToWatchlist} className={`px-4 py-2 rounded text-sm font-medium transition-colors ${isInWatchlist ? 'bg-yellow-600/30 text-yellow-400 border border-yellow-600' : 'bg-gray-700 hover:bg-gray-600'}`}>
                {isInWatchlist ? '★ Watching' : '+ Watchlist'}
              </button>
              <button onClick={() => {
                if (isInPortfolio) { removeFromPortfolio(selectedSymbol); }
                else { setPortfolioShares(''); setPortfolioAvgPrice(quote?.price?.toFixed(2) || ''); setShowAddToPortfolio(true); }
              }} className={`px-4 py-2 rounded text-sm font-medium transition-colors ${isInPortfolio ? 'bg-green-600/30 text-green-400 border border-green-600' : 'bg-gray-700 hover:bg-gray-600'}`}>
                {isInPortfolio ? '💰 In Portfolio' : '+ Portfolio'}
              </button>
              <button onClick={() => setShowAlerts(true)} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium">Set Alert</button>
            </div>
          </div>

          {/* Time Interval Buttons */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {['1m', '5m', '15m', '1h', '1d', '1wk'].map((interval, idx) => (
              <button key={interval} onClick={() => setChartInterval(interval)} className={`px-3 py-1 rounded text-sm ${chartInterval === interval ? 'bg-cyan-600 text-white' : 'bg-gray-700 hover:bg-gray-600'}`}>
                {interval.toUpperCase()}<span className="ml-1 text-xs text-gray-500">({idx + 1})</span>
              </button>
            ))}
            <span className="ml-auto text-sm text-gray-400">Last: {lastFetchTime?.toLocaleTimeString() || '-'} • Poll: {pollingInterval / 1000}s</span>
          </div>

          {/* Chart */}
          <div key={`chart-${selectedSymbol}-${chartInterval}`} className="bg-gray-800 rounded-lg p-4 mb-4">
            <ChartPanel history={history} selectedSymbol={selectedSymbol} chartInterval={chartInterval} currency={currentMarket.currency} />
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
            {['technicals', 'backtest', 'sentiment', 'fundamentals', 'news', 'AI scanner', 'paper trade', 'strategies'].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 rounded text-sm font-medium capitalize whitespace-nowrap ${activeTab === tab ? 'bg-cyan-600 text-white' : 'bg-gray-700 hover:bg-gray-600'}`}>
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="bg-gray-800 rounded-lg p-4">
            {activeTab === 'technicals' && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">RSI (14)</h4>
                  <div className={`text-2xl font-bold ${getRsiColor(getSignalValue(signals?.rsi))}`}>{getSignalValue(signals?.rsi)?.toFixed(1) || '-'}</div>
                  <p className="text-xs text-gray-500 mt-1">{getSignalValue(signals?.rsi) < 30 ? 'Oversold' : getSignalValue(signals?.rsi) > 70 ? 'Overbought' : 'Neutral'}</p>
                </div>
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">Signal</h4>
                  <div className={`text-2xl font-bold ${getSignalColor(signals?.signal || signals?.overall_signal)}`}>{signals?.signal || signals?.overall_signal || '-'}</div>
                  <p className="text-xs text-gray-500 mt-1">AI recommendation</p>
                </div>
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">SMA 20</h4>
                  <div className="text-2xl font-bold text-cyan-400">{formatPrice(getSignalValue(signals?.sma_20 || signals?.sma20), currentMarket.currency)}</div>
                  <p className="text-xs text-gray-500 mt-1">Moving average</p>
                </div>
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">EMA 12</h4>
                  <div className="text-2xl font-bold text-cyan-400">{formatPrice(getSignalValue(signals?.ema_12 || signals?.ema12), currentMarket.currency)}</div>
                  <p className="text-xs text-gray-500 mt-1">Exponential MA</p>
                </div>
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">VWAP</h4>
                  <div className="text-2xl font-bold text-cyan-400">{formatPrice(getSignalValue(signals?.vwap), currentMarket.currency)}</div>
                  <p className="text-xs text-gray-500 mt-1">Volume weighted</p>
                </div>
                <div className="p-3 bg-gray-700/50 rounded-lg">
                  <h4 className="text-sm text-gray-400 mb-1">ATR</h4>
                  <div className="text-2xl font-bold text-orange-400">{formatPrice(getSignalValue(signals?.atr), currentMarket.currency)}</div>
                  <p className="text-xs text-gray-500 mt-1">Volatility</p>
                </div>
              </div>
            )}

            {activeTab === 'fundamentals' && (
              <div>
                {financialsLoading ? (
                  <div className="text-center py-8 text-gray-400">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3"></div>
                    <p>Loading financial data...</p>
                  </div>
                ) : !financials ? (
                  <div className="text-center py-8 text-gray-400"><p>Financial data not available for {selectedSymbol}</p></div>
                ) : (
                  <div className="space-y-4">
                    <div className="bg-gray-700/50 rounded-lg p-4">
                      <h4 className="text-sm font-semibold text-cyan-400 mb-3">Company Overview</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div><p className="text-xs text-gray-400">Sector</p><p className="text-sm text-white">{financials.sector || 'N/A'}</p></div>
                        <div><p className="text-xs text-gray-400">Industry</p><p className="text-sm text-white">{financials.industry || 'N/A'}</p></div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        ['Market Cap', financials.marketCap], ['P/E Ratio', financials.peRatio],
                        ['Revenue', financials.revenue], ['EPS', financials.eps],
                        ['Div Yield', financials.dividendYield], ['52W High', financials.fiftyTwoWeekHigh ? `${currentMarket.currency}${financials.fiftyTwoWeekHigh}` : 'N/A'],
                        ['52W Low', financials.fiftyTwoWeekLow ? `${currentMarket.currency}${financials.fiftyTwoWeekLow}` : 'N/A'], ['Beta', financials.beta],
                      ].map(([label, value]) => (
                        <div key={label} className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-xs text-gray-400 mb-1">{label}</p>
                          <p className="text-lg font-semibold text-white">{value || 'N/A'}</p>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 text-center">
                      Data Quality: <span className={`px-2 py-0.5 rounded ${financials.dataQuality === 'LIVE' ? 'bg-green-600' : financials.dataQuality === 'CACHED' ? 'bg-blue-600' : 'bg-orange-600'} text-white`}>{financials.dataQuality || 'DEMO'}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'news' && (
              <div className="space-y-3">
                {news.length === 0 ? (
                  <p className="text-gray-400 text-center py-4">No recent news available</p>
                ) : news.slice(0, 5).map((item, i) => (
                  <div key={i} className="p-3 bg-gray-700/50 rounded-lg">
                    <h4 className="font-medium text-sm mb-1">{item.title || item.headline}</h4>
                    <p className="text-xs text-gray-400">
                      {item.source} • {item.time_ago || item.time || item.date || 'Recent'}
                      {item.sentiment && <span className={`ml-2 ${item.sentiment === 'positive' ? 'text-green-400' : item.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'}`}>• {item.sentiment}</span>}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'backtest' && <BacktestPanel symbol={selectedSymbol} traderStyle={traderStyle?.toLowerCase()} />}
            {activeTab === 'sentiment' && <SentimentDashboard symbol={selectedSymbol} />}
            {activeTab === 'AI scanner' && <AIScanner traderStyle={traderStyle?.toLowerCase()} onSymbolSelect={handleSymbolSelect} />}
            {activeTab === 'paper trade' && <PaperTradingPanel symbol={selectedSymbol} price={quote?.price} currency={quote?.currency || '$'} onSymbolSelect={handleSymbolSelect} />}
            {activeTab === 'strategies' && <StrategyBuilder onSymbolSelect={handleSymbolSelect} />}
          </div>
        </main>

        {/* Right Sidebar - AI Chat */}
        <aside className="w-full md:w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-cyan-400">AI Assistant</h3>
              <div className="flex items-center gap-2">
                {llmProvider && <span className="text-xs text-cyan-300 bg-cyan-900/40 px-1.5 py-0.5 rounded">{llmProvider}</span>}
                <button onClick={() => setShowAiSettings(s => !s)} className="text-xs text-gray-400 hover:text-cyan-400 transition-colors" title="AI Settings">⚙</button>
                <span className="text-xs text-green-400">● Active</span>
              </div>
            </div>
            {showAiSettings && (
              <div className="mt-3 p-3 bg-gray-900/60 rounded-lg border border-gray-700 space-y-2">
                <p className="text-xs text-gray-400 font-medium">LLM Provider</p>
                <select value={llmProvider} onChange={e => { setLlmProvider(e.target.value); localStorage.setItem('llm_provider', e.target.value); setLlmModel(''); localStorage.setItem('llm_model', ''); }} className="w-full bg-gray-700 text-sm px-2 py-1.5 rounded border border-gray-600 focus:border-cyan-500 focus:outline-none">
                  <option value="">Auto (server default)</option>
                  <option value="groq">Groq (Llama 3.3)</option>
                  <option value="openai">OpenAI (GPT-4o)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                </select>
                {llmProvider && (
                  <>
                    <p className="text-xs text-gray-400 font-medium">Model</p>
                    <select value={llmModel} onChange={e => { setLlmModel(e.target.value); localStorage.setItem('llm_model', e.target.value); }} className="w-full bg-gray-700 text-sm px-2 py-1.5 rounded border border-gray-600 focus:border-cyan-500 focus:outline-none">
                      <option value="">Default</option>
                      {llmProvider === 'groq' && <><option value="llama-3.3-70b-versatile">Llama 3.3 70B</option><option value="llama-3.1-8b-instant">Llama 3.1 8B (fast)</option></>}
                      {llmProvider === 'openai' && <><option value="gpt-4o">GPT-4o</option><option value="gpt-4o-mini">GPT-4o Mini</option><option value="gpt-3.5-turbo">GPT-3.5 Turbo</option></>}
                      {llmProvider === 'anthropic' && <><option value="claude-sonnet-4-20250514">Claude Sonnet 4</option><option value="claude-haiku-4-20250414">Claude Haiku 4</option></>}
                    </select>
                  </>
                )}
                <p className="text-xs text-gray-400 font-medium">API Key <span className="text-gray-600">(stored locally)</span></p>
                <input type="password" value={llmApiKey} onChange={e => { setLlmApiKey(e.target.value); localStorage.setItem('llm_api_key', e.target.value); }} placeholder={llmProvider === 'groq' ? 'gsk_...' : llmProvider === 'anthropic' ? 'sk-ant-...' : llmProvider === 'openai' ? 'sk-...' : 'Enter API key'} className="w-full bg-gray-700 text-sm px-2 py-1.5 rounded border border-gray-600 focus:border-cyan-500 focus:outline-none" />
                <p className="text-xs text-gray-500">Key stays in your browser. Never sent to our servers.</p>
                {llmApiKey && <button onClick={() => { setLlmApiKey(''); localStorage.removeItem('llm_api_key'); }} className="text-xs text-red-400 hover:text-red-300">Clear key</button>}
              </div>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {aiMessages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-3">🤖</div>
                <p className="text-sm mb-2">Ask me about {selectedSymbol}</p>
                <p className="text-xs text-gray-600 mb-4">Style: {traderStyle} ({TRADING_STYLES[traderStyle]?.focus})</p>
                <div className="space-y-2">
                  {AI_PROMPTS.map((prompt, i) => (
                    <button key={i} onClick={() => handleAiSubmit(prompt)} className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-xs text-left transition-colors">{prompt}</button>
                  ))}
                </div>
              </div>
            ) : aiMessages.map((msg, i) => (
              <div key={i} className={`p-3 rounded-lg text-sm ${msg.role === 'user' ? 'bg-cyan-600/30 ml-8' : 'bg-gray-700/50 mr-8'}`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.source && msg.role === 'assistant' && <p className="text-xs text-gray-500 mt-1">via {msg.source}</p>}
              </div>
            ))}
            {aiLoading && (
              <div className="p-3 bg-gray-700/50 rounded-lg mr-8">
                <div className="flex items-center gap-2">
                  <div className="animate-spin h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
                  <span className="text-sm text-gray-400">Thinking...</span>
                </div>
              </div>
            )}
          </div>
          <div className="p-4 border-t border-gray-700">
            <div className="flex gap-2">
              <input type="text" value={aiInput} onChange={(e) => setAiInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAiSubmit()} placeholder="Ask about this stock..." className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" />
              <button onClick={() => handleAiSubmit()} disabled={aiLoading || !aiInput.trim()} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium">Send</button>
            </div>
          </div>
          <div className="border-t border-gray-700 p-3 overflow-y-auto max-h-60">
            <MarketCommentary />
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 px-4 py-2 border-t border-gray-700 text-xs text-gray-500 flex justify-between">
        <span>TraderAI Pro v{APP_VERSION} • Press ? for keyboard shortcuts</span>
        <span>Data: DEMO • Watchlist: {watchlist.length} • Alerts: {alerts.length}</span>
      </footer>

      {/* Lazy-loaded Modals */}
      <Suspense fallback={null}>
        {showUserGuide && <UserGuideModal onClose={() => setShowUserGuide(false)} />}
        {showWhatsNext && <WhatsNextModal onClose={() => setShowWhatsNext(false)} />}
        {showKeyboardHelp && <KeyboardShortcutsModal onClose={() => setShowKeyboardHelp(false)} />}
        {showWatchlistEdit && (
          <WatchlistEditModal onClose={() => setShowWatchlistEdit(false)} watchlist={watchlist} setWatchlist={setWatchlist} onSelectSymbol={handleSymbolSelect} setAlerts={setAlerts} currentSymbol={selectedSymbol} />
        )}
        {showScreener && (
          <ScreenerModal onClose={() => setShowScreener(false)} screenerCategory={screenerCategory} setScreenerCategory={setScreenerCategory} screenerCategories={screenerCategories} screenerFilter={screenerFilter} setScreenerFilter={setScreenerFilter} screenerLoading={screenerLoading} filteredScreenerData={filteredScreenerData} onSymbolSelect={handleSymbolSelect} />
        )}
        {showPortfolio && (
          <PortfolioModal onClose={() => setShowPortfolio(false)} portfolio={portfolio} quote={quote} onSymbolSelect={handleSymbolSelect} onRemove={removeFromPortfolio} />
        )}
        {showAlerts && (
          <AlertsModal onClose={() => setShowAlerts(false)} alerts={alerts} newAlertPrice={newAlertPrice} setNewAlertPrice={setNewAlertPrice} newAlertCondition={newAlertCondition} setNewAlertCondition={setNewAlertCondition} onAddAlert={addAlert} onRemoveAlert={removeAlert} />
        )}
        {showAddToPortfolio && (
          <AddToPortfolioModal onClose={() => setShowAddToPortfolio(false)} selectedSymbol={selectedSymbol} quote={quote} portfolioShares={portfolioShares} setPortfolioShares={setPortfolioShares} portfolioAvgPrice={portfolioAvgPrice} setPortfolioAvgPrice={setPortfolioAvgPrice} onAdd={addToPortfolio} isInPortfolio={isInPortfolio} />
        )}
        {showCreditsModal && (
          <CreditsModal onClose={() => setShowCreditsModal(false)} credits={credits} setCredits={setCredits} isLoggedIn={isLoggedIn} />
        )}
      </Suspense>

      {/* Debug Panel */}
      {showDebug && (
        <div className="fixed bottom-0 right-0 w-96 max-h-64 bg-gray-900 border border-gray-700 rounded-tl-lg overflow-auto text-xs font-mono p-2 z-50">
          <div className="flex justify-between items-center mb-2">
            <span className="text-cyan-400">Debug Info</span>
            <button onClick={() => setShowDebug(false)} className="text-gray-400">×</button>
          </div>
          <pre className="text-gray-300 whitespace-pre-wrap">
            {JSON.stringify({
              version: APP_VERSION, market: selectedMarket, symbol: selectedSymbol,
              chartInterval, healthStatus, pollingInterval,
              historyLength: history?.length || 0, screenerCategories: screenerCategories.length,
              watchlistCount: watchlist.length, alertsCount: alerts.length,
              financials: financials ? { marketCap: financials.marketCap, peRatio: financials.peRatio, dataQuality: financials.dataQuality } : null,
              signals: signals ? { rsi: getSignalValue(signals.rsi), signal: signals.signal || signals.overall_signal } : null
            }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
