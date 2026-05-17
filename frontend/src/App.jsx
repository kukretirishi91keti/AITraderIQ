import React, { useState, useEffect, useCallback, useRef, useMemo, lazy, Suspense } from 'react';
import { useAuth } from './context/AuthContext';
import ConnectionStatus from './components/ConnectionStatus';
import RiskDisclaimer from './components/RiskDisclaimer';
import ToastNotification from './components/ToastNotification';
import BacktestPanel from './components/BacktestPanel';
import SentimentDashboard from './components/SentimentDashboard';
import MarketCommentary from './components/MarketCommentary';
import AIScanner from './components/AIScanner';
import Nifty50Scanner from './components/Nifty50Scanner';
import ChartPanel from './components/ChartPanel';
import { getPriceStream } from './services/websocket';
import {
  getUserWatchlist,
  addToWatchlist as apiAddToWatchlist,
  removeFromWatchlist as apiRemoveFromWatchlist,
  getUserPortfolio,
  addToPortfolio as apiAddToPortfolio,
  removeFromPortfolio as apiRemoveFromPortfolio,
  getUserAlerts,
  createAlert as apiCreateAlert,
  deleteAlert as apiDeleteAlert,
  authFetch,
  getProfile,
} from './services/auth';

// Constants
import { MARKETS, STATIC_UNIVERSE } from './constants/markets';
import { searchSymbols } from './constants/symbolIndex';
import {
  API_BASE,
  APP_VERSION,
  POLLING_INTERVALS,
  TRADING_STYLES,
  AI_PROMPTS,
  KEYBOARD_SHORTCUTS,
  DEFAULT_MARKET,
  DEFAULT_SYMBOL,
  NIFTY_50_WATCHLIST,
  NSE_HOURS,
} from './constants/appConfig';

// Utils
import {
  formatLargeNumber,
  formatPrice,
  getSignalValue,
  getSignalColor,
  getRsiColor,
  getFlagForSymbol,
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
const StrategyIntelligence = lazy(() => import('./components/StrategyIntelligence'));
const PaperTradesModal = lazy(() => import('./components/modals/PaperTradesModal'));
const TradeJournalModal = lazy(() => import('./components/modals/TradeJournalModal'));
const OnboardingModal = lazy(() => import('./components/modals/OnboardingModal'));

const AI_MODEL_OPTIONS = [
  { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B', tag: 'Best' },
  { id: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B', tag: 'Fast' },
  { id: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B', tag: '' },
  { id: 'gemma2-9b-it', label: 'Gemma 2 9B', tag: '' },
];

// ============================================================
// MAIN APP COMPONENT
// ============================================================

export default function App() {
  const { user, isLoggedIn, setShowAuthModal, logout } = useAuth();

  // Core state
  const [selectedMarket, setSelectedMarket] = useState(DEFAULT_MARKET);
  const [selectedSymbol, setSelectedSymbol] = useState(DEFAULT_SYMBOL);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDrop, setShowSearchDrop] = useState(false);
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
  const [showPaperTrades, setShowPaperTrades] = useState(false);
  const [showJournal, setShowJournal] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [showMobileAI, setShowMobileAI] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showUserGuide, setShowUserGuide] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [showWhatsNext, setShowWhatsNext] = useState(false);
  const [showWatchlistEdit, setShowWatchlistEdit] = useState(false);
  const [showAddToPortfolio, setShowAddToPortfolio] = useState(false);
  const [portfolioShares, setPortfolioShares] = useState('');
  const [portfolioAvgPrice, setPortfolioAvgPrice] = useState('');
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);
  const [showStrategyIntelligence, setShowStrategyIntelligence] = useState(false);

  // Screener filters
  const [screenerFilter, setScreenerFilter] = useState('all');
  const [screenerCategory, setScreenerCategory] = useState('all');
  const [screenerLoading, setScreenerLoading] = useState(false);
  const [screenerCategories, setScreenerCategories] = useState([]);

  // Watchlist & Alerts
  const [watchlist, setWatchlist] = useState(NIFTY_50_WATCHLIST);
  const [alerts, setAlerts] = useState([
    { symbol: 'AAPL', condition: 'above', price: 250 },
    { symbol: 'BTC-USD', condition: 'above', price: 110000 },
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
    return saved
      ? JSON.parse(saved)
      : {
          name: '',
          riskTolerance: 'moderate',
          investmentHorizon: 'medium',
          experience: 'intermediate',
          capitalRange: 'medium',
          goals: [],
        };
  });
  const [showInvestorProfile, setShowInvestorProfile] = useState(false);

  // AI Chat
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');
  const [showModelPicker, setShowModelPicker] = useState(false);
  const modelPickerRef = useRef(null);

  // Health monitoring
  const [healthStatus, setHealthStatus] = useState('HEALTHY');
  const [pollingInterval, setPollingInterval] = useState(POLLING_INTERVALS.HEALTHY);
  const [lastFetchTime, setLastFetchTime] = useState(null);
  const [demoMode, setDemoMode] = useState(true); // assume demo until health check says otherwise

  // User GROQ API key (stored in localStorage, sent with AI requests)
  const [groqApiKey, setGroqApiKey] = useState(() => localStorage.getItem('groqApiKey') || '');
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);

  // Toast notifications
  const [toasts, setToasts] = useState([]);
  const openTradesRef = useRef({});

  // Refs
  const intervalRef = useRef(null);
  const searchInputRef = useRef(null);

  // Close model picker on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (modelPickerRef.current && !modelPickerRef.current.contains(e.target)) {
        setShowModelPicker(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // WebSocket real-time price updates
  useEffect(() => {
    const stream = getPriceStream();
    stream.connect();
    const cleanup = stream.onQuote((data) => {
      if (data.symbol === selectedSymbol) {
        setQuote((prev) =>
          prev
            ? {
                ...prev,
                price: data.price,
                change: data.change,
                changePercent: data.changePercent,
                volume: data.volume,
                dataQuality: data.dataQuality,
              }
            : prev
        );
      }
    });
    const allSymbols = [...new Set([selectedSymbol, ...watchlist])];
    stream.subscribe(allSymbols);
    return () => {
      cleanup();
    };
  }, [selectedSymbol, watchlist]);

  const currentMarket = useMemo(
    () => MARKETS.find((m) => m.id === selectedMarket) || MARKETS[0],
    [selectedMarket]
  );

  // Hydrate investorProfile from DB on login, then decide onboarding
  useEffect(() => {
    if (!isLoggedIn) return;

    getProfile()
      .then((dbProfile) => {
        const existing = JSON.parse(localStorage.getItem('investorProfile') || '{}');

        let parsedGoals = existing.goals || [];
        try {
          if (dbProfile.goals) parsedGoals = JSON.parse(dbProfile.goals);
        } catch {
          /* keep existing */
        }

        const merged = {
          ...existing,
          name: dbProfile.full_name || existing.name || '',
          tradingStyle: dbProfile.trader_style || existing.tradingStyle || 'swing',
          riskTolerance: dbProfile.risk_tolerance || existing.riskTolerance || 'moderate',
          investmentHorizon: dbProfile.investment_horizon || existing.investmentHorizon || 'medium',
          experience: dbProfile.experience_level || existing.experience || 'intermediate',
          capitalRange: dbProfile.capital_range || existing.capitalRange || 'medium',
          goals: parsedGoals,
        };

        localStorage.setItem('investorProfile', JSON.stringify(merged));
        setInvestorProfile(merged);

        // Skip onboarding if the DB already has non-default profile data
        const hasSetUpProfile =
          merged.investmentHorizon !== 'medium' ||
          merged.experience !== 'intermediate' ||
          merged.goals.length > 0 ||
          merged.riskTolerance !== 'moderate';

        if (!localStorage.getItem('onboardingComplete') && !hasSetUpProfile) {
          setShowOnboarding(true);
        }
      })
      .catch(() => {
        // DB fetch failed — fall back to local-only check
        if (!localStorage.getItem('onboardingComplete')) {
          setShowOnboarding(true);
        }
      });
  }, [isLoggedIn]);

  // Stable helper to add a toast that auto-dismisses after 5 s
  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  // Poll open paper trades every 60 s; notify when one auto-closes (SL/TP hit)
  useEffect(() => {
    if (!isLoggedIn) return;
    const checkTrades = async () => {
      try {
        const res = await authFetch(`${API_BASE}/api/paper-trade?status=open`);
        if (!res.ok) return;
        const data = await res.json();
        const currentIds = new Set((data.trades || []).map((t) => t.id));
        const currentMap = Object.fromEntries(
          (data.trades || []).map((t) => [t.id, { symbol: t.symbol, side: t.side }])
        );
        Object.entries(openTradesRef.current).forEach(([id, info]) => {
          if (!currentIds.has(Number(id))) {
            addToast(
              `${info.symbol} ${info.side.toUpperCase()} trade auto-closed (SL/TP hit)`,
              'warning'
            );
          }
        });
        openTradesRef.current = currentMap;
      } catch {
        /* silent */
      }
    };
    checkTrades();
    const interval = setInterval(checkTrades, 60_000);
    return () => clearInterval(interval);
  }, [isLoggedIn, addToast]);

  // Must be declared before keyboard shortcut effect (used in its dep array)
  const refreshWatchlistFromApi = useCallback(async () => {
    try {
      const data = await getUserWatchlist();
      if (data.watchlist && data.watchlist.length > 0) {
        setWatchlist(data.watchlist.map((item) => item.symbol));
      }
    } catch {
      // Silently fall back to local state
    }
  }, []);

  // Must be declared before addToPortfolio (used in its dep array)
  const refreshPortfolioFromApi = useCallback(async () => {
    try {
      const data = await getUserPortfolio();
      if (data.holdings) {
        setPortfolio(
          data.holdings.map((item) => ({
            id: item.id,
            symbol: item.symbol,
            shares: item.shares,
            avgPrice: item.avg_price,
            currency: item.currency,
            market: item.market,
          }))
        );
      }
    } catch {
      // Silently fall back to local state
    }
  }, []);

  // Must be declared before addAlert/removeAlert/handleWatchlistAddAlert (used in their dep arrays)
  const refreshAlertsFromApi = useCallback(async () => {
    try {
      const data = await getUserAlerts();
      if (data.alerts) {
        setAlerts(
          data.alerts.map((item) => ({
            id: item.id,
            symbol: item.symbol,
            condition: item.condition,
            price: item.target_value,
            is_triggered: item.is_triggered,
            is_active: item.is_active,
          }))
        );
      }
    } catch {
      // Silently fall back to local state
    }
  }, []);

  // ============================================================
  // KEYBOARD SHORTCUTS
  // ============================================================
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') e.target.blur();
        return;
      }
      const anyModalOpen =
        showScreener ||
        showPortfolio ||
        showAddToPortfolio ||
        showAlerts ||
        showUserGuide ||
        showWhatsNext ||
        showWatchlistEdit ||
        showKeyboardHelp ||
        showStrategyIntelligence;
      switch (e.key) {
        case '/':
          e.preventDefault();
          searchInputRef.current?.focus();
          break;
        case '1':
          e.preventDefault();
          setChartInterval('1m');
          break;
        case '2':
          e.preventDefault();
          setChartInterval('5m');
          break;
        case '3':
          e.preventDefault();
          setChartInterval('15m');
          break;
        case '4':
          e.preventDefault();
          setChartInterval('1h');
          break;
        case '5':
          e.preventDefault();
          setChartInterval('1d');
          break;
        case '6':
          e.preventDefault();
          setChartInterval('1wk');
          break;
        case 'w':
        case 'W':
          e.preventDefault();
          if (!watchlist.includes(selectedSymbol)) {
            setWatchlist((prev) => [...prev, selectedSymbol]);
            if (isLoggedIn) {
              apiAddToWatchlist(selectedSymbol, selectedMarket)
                .then(() => refreshWatchlistFromApi())
                .catch(() => {});
            }
          } else {
            setWatchlist((prev) => prev.filter((s) => s !== selectedSymbol));
            if (isLoggedIn) {
              apiRemoveFromWatchlist(selectedSymbol)
                .then(() => refreshWatchlistFromApi())
                .catch(() => {});
            }
          }
          break;
        case 'p':
        case 'P':
          e.preventDefault();
          if (!anyModalOpen) setShowPortfolio(true);
          break;
        case 's':
        case 'S':
          e.preventDefault();
          if (!anyModalOpen) {
            setShowScreener(true);
            fetchScreenerData();
          }
          break;
        case 'a':
        case 'A':
          e.preventDefault();
          if (!anyModalOpen) setShowAlerts(true);
          break;
        case '?':
          e.preventDefault();
          if (!anyModalOpen) setShowKeyboardHelp(true);
          break;
        case 'Escape':
          setShowScreener(false);
          setShowPortfolio(false);
          setShowAddToPortfolio(false);
          setShowAlerts(false);
          setShowUserGuide(false);
          setShowWhatsNext(false);
          setShowWatchlistEdit(false);
          setShowKeyboardHelp(false);
          setShowDebug(false);
          setShowStrategyIntelligence(false);
          break;
        default:
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    selectedSymbol,
    watchlist,
    showScreener,
    showPortfolio,
    showAlerts,
    showUserGuide,
    showWhatsNext,
    showWatchlistEdit,
    showAddToPortfolio,
    showKeyboardHelp,
    isLoggedIn,
    selectedMarket,
    refreshWatchlistFromApi,
  ]);

  // ============================================================
  // SYMBOL & MARKET HANDLERS
  // ============================================================
  const handleSymbolSelect = useCallback((symbol) => {
    const upperSymbol = symbol.toUpperCase();
    setSelectedSymbol(upperSymbol);
    setSearchQuery('');
    setShowSearchDrop(false);
    setAiMessages([]);
    if (upperSymbol.endsWith('.NS') || upperSymbol.endsWith('.BO')) setSelectedMarket('India');
    else if (upperSymbol.endsWith('.L')) setSelectedMarket('UK');
    else if (upperSymbol.endsWith('.DE')) setSelectedMarket('Germany');
    else if (upperSymbol.endsWith('.T')) setSelectedMarket('Japan');
    else if (upperSymbol.endsWith('.AX')) setSelectedMarket('Australia');
    else if (upperSymbol.includes('-USD') || upperSymbol === 'BTC' || upperSymbol === 'ETH')
      setSelectedMarket('Crypto');
    else if (upperSymbol.includes('=X')) setSelectedMarket('Forex');
    else if (upperSymbol.includes('=F')) setSelectedMarket('Commodities');
    else if (['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'GLD'].includes(upperSymbol))
      setSelectedMarket('ETF');
  }, []);

  const handleMarketChange = useCallback(async (marketId) => {
    const fallbackMovers = generateDemoMovers(marketId);
    setMovers(fallbackMovers);
    setSelectedMarket(marketId);
    const market = MARKETS.find((m) => m.id === marketId);
    if (market) {
      setSelectedSymbol(market.defaultSymbol);
      setAiMessages([]);
      try {
        const freshMovers = await fetchTopMovers(marketId);
        if (freshMovers && freshMovers.length > 0) setMovers(freshMovers);
      } catch (err) {
        /* fallback already set */
      }
    }
  }, []);

  // ============================================================
  // DATA FETCHING
  // ============================================================
  const fetchAllData = useCallback(
    async (signal = null) => {
      if (!selectedSymbol) return;
      setLoading(true);
      setFinancialsLoading(true);
      try {
        const [quoteRes, historyRes, signalsRes, newsRes, sentimentRes, financialsRes, healthRes] =
          await Promise.allSettled([
            fetch(`${API_BASE}/api/v4/quote/${selectedSymbol}`, { signal }),
            fetch(`${API_BASE}/api/v4/history/${selectedSymbol}?interval=${chartInterval}`, {
              signal,
            }),
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
          const chartData =
            historyData.candles ||
            historyData.history ||
            historyData.data ||
            historyData.prices ||
            [];
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
                symbol: data.symbol,
                name: data.name,
                currency: data.currency,
                sector: f.sector || 'Technology',
                industry: f.industry || 'Software',
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
          } catch {
            setFinancials(null);
          }
        } else {
          setFinancials(null);
        }
        setFinancialsLoading(false);

        if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
          const healthData = await healthRes.value.json();
          setHealthStatus(healthData.status?.toUpperCase() || 'HEALTHY');
          if (healthData.polling_recommendation)
            setPollingInterval(healthData.polling_recommendation * 1000);
          if (healthData.demo_mode !== undefined) setDemoMode(healthData.demo_mode);
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
    },
    [selectedSymbol, chartInterval, selectedMarket]
  );

  // ============================================================
  // SCREENER
  // ============================================================
  const fetchScreenerData = useCallback(async () => {
    setScreenerLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/screener/universe`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const metaKeys = [
        'timestamp',
        'categories',
        'total_stocks',
        'source',
        'category_counts',
        'signal_counts',
        'all',
        'total_count',
        'demoMode',
        'refresh_interval',
        'message',
      ];
      const categoryKeys = Object.keys(data).filter((k) => !metaKeys.includes(k));
      if (categoryKeys.length > 0) setScreenerCategories(categoryKeys);
      const processed = {};
      categoryKeys.forEach((category) => {
        const stocks = data[category];
        if (Array.isArray(stocks) && stocks.length > 0) {
          processed[category] = stocks.map((s) => ({
            symbol: s.symbol,
            name: s.name || s.symbol.split('.')[0],
            price: s.price,
            changePct: s.change_percent || s.changePct || 0,
            rsi: s.rsi,
            signal: s.signal,
            currency: s.currency || '$',
            flag: getFlagForSymbol(s.symbol),
            dataQuality: s.dataQuality || 'DEMO',
          }));
        }
      });
      if (Object.keys(processed).length === 0) {
        Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
          processed[category] = stocks.map((s) => ({
            ...s,
            rsi: Math.random() * 100,
            signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
            price: 100 + Math.random() * 500,
            changePct: (Math.random() * 10 - 5).toFixed(2),
            flag: s.flag || getFlagForSymbol(s.symbol),
            dataQuality: 'DEMO',
          }));
        });
        setScreenerCategories(Object.keys(STATIC_UNIVERSE));
      }
      setScreenerData(processed);
    } catch {
      const demo = {};
      Object.entries(STATIC_UNIVERSE).forEach(([category, stocks]) => {
        demo[category] = stocks.map((s) => ({
          ...s,
          rsi: Math.random() * 100,
          signal: Math.random() > 0.5 ? 'BUY' : 'HOLD',
          price: 100 + Math.random() * 500,
          changePct: (Math.random() * 10 - 5).toFixed(2),
          flag: s.flag || getFlagForSymbol(s.symbol),
          dataQuality: 'DEMO',
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
    setAiMessages((prev) => [...prev, { role: 'user', content: prompt }]);
    setAiInput('');
    setAiLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/genai/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: prompt,
          symbol: selectedSymbol,
          price: quote?.price,
          currency: currentMarket.currency,
          market: currentMarket.name,
          trader_style: traderStyle.toLowerCase(),
          risk_tolerance: investorProfile.riskTolerance,
          experience_level: investorProfile.experience,
          investment_horizon: investorProfile.investmentHorizon,
          rsi: getSignalValue(signals?.rsi),
          signal: signals?.signal || signals?.overall_signal,
          model: selectedModel,
          groq_api_key: groqApiKey || undefined,
        }),
      });
      const data = await response.json();
      const modelLabel = AI_MODEL_OPTIONS.find((m) => m.id === data.model)?.label;
      setAiMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer || data.response || 'Unable to generate response',
          source: data.model ? `${modelLabel || data.model}` : data.source || 'rule-based',
        },
      ]);
    } catch (err) {
      setAiMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `AI service temporarily unavailable. Error: ${err.message}`,
          source: 'error',
        },
      ]);
    } finally {
      setAiLoading(false);
    }
  };

  // ============================================================
  // WATCHLIST / PORTFOLIO / ALERT HANDLERS
  // ============================================================
  const addToWatchlist = useCallback(async () => {
    if (selectedSymbol && !watchlist.includes(selectedSymbol)) {
      setWatchlist((prev) => [...prev, selectedSymbol]);
      if (isLoggedIn) {
        try {
          await apiAddToWatchlist(selectedSymbol, selectedMarket);
          await refreshWatchlistFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    }
  }, [selectedSymbol, watchlist, isLoggedIn, selectedMarket, refreshWatchlistFromApi]);

  const isInWatchlist = useMemo(
    () => watchlist.includes(selectedSymbol),
    [watchlist, selectedSymbol]
  );
  const isInPortfolio = useMemo(
    () => portfolio.some((p) => p.symbol === selectedSymbol),
    [portfolio, selectedSymbol]
  );

  const addToPortfolio = useCallback(async () => {
    const shares = parseFloat(portfolioShares);
    const avgPrice = parseFloat(portfolioAvgPrice);
    if (isNaN(shares) || shares <= 0 || isNaN(avgPrice) || avgPrice <= 0) return;
    setPortfolio((prev) => {
      const existing = prev.find((p) => p.symbol === selectedSymbol);
      if (existing) {
        const totalShares = existing.shares + shares;
        const newAvgPrice = (existing.shares * existing.avgPrice + shares * avgPrice) / totalShares;
        return prev.map((p) =>
          p.symbol === selectedSymbol ? { ...p, shares: totalShares, avgPrice: newAvgPrice } : p
        );
      }
      return [...prev, { symbol: selectedSymbol, shares, avgPrice }];
    });
    setPortfolioShares('');
    setPortfolioAvgPrice('');
    setShowAddToPortfolio(false);
    if (isLoggedIn) {
      try {
        await apiAddToPortfolio({
          symbol: selectedSymbol,
          shares,
          avgPrice,
          market: selectedMarket,
        });
        await refreshPortfolioFromApi();
      } catch {
        // Local state already updated as fallback
      }
    }
  }, [
    selectedSymbol,
    portfolioShares,
    portfolioAvgPrice,
    isLoggedIn,
    selectedMarket,
    refreshPortfolioFromApi,
  ]);

  const removeFromPortfolio = useCallback(
    async (symbolOrId) => {
      if (isLoggedIn) {
        // Find the portfolio item to get its DB id
        const item = portfolio.find((p) => p.symbol === symbolOrId || p.id === symbolOrId);
        setPortfolio((prev) => prev.filter((p) => p.symbol !== symbolOrId && p.id !== symbolOrId));
        if (item?.id) {
          try {
            await apiRemoveFromPortfolio(item.id);
            await refreshPortfolioFromApi();
          } catch {
            // Local state already updated as fallback
          }
        }
      } else {
        setPortfolio((prev) => prev.filter((p) => p.symbol !== symbolOrId));
      }
    },
    [isLoggedIn, portfolio, refreshPortfolioFromApi]
  );

  const addAlert = useCallback(async () => {
    const price = parseFloat(newAlertPrice);
    if (isNaN(price) || price <= 0) return;
    const newAlert = { symbol: selectedSymbol, condition: newAlertCondition, price };
    if (
      !alerts.some(
        (a) =>
          a.symbol === newAlert.symbol &&
          a.condition === newAlert.condition &&
          a.price === newAlert.price
      )
    ) {
      setAlerts((prev) => [...prev, newAlert]);
      setNewAlertPrice('');
      if (isLoggedIn) {
        try {
          await apiCreateAlert({
            symbol: selectedSymbol,
            condition: newAlertCondition,
            targetValue: price,
          });
          await refreshAlertsFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    }
  }, [selectedSymbol, newAlertCondition, newAlertPrice, alerts, isLoggedIn, refreshAlertsFromApi]);

  const removeAlert = useCallback(
    async (index) => {
      const alertToRemove = alerts[index];
      setAlerts((prev) => prev.filter((_, i) => i !== index));
      if (isLoggedIn && alertToRemove?.id) {
        try {
          await apiDeleteAlert(alertToRemove.id);
          await refreshAlertsFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    },
    [alerts, isLoggedIn, refreshAlertsFromApi]
  );

  // Watchlist handlers for WatchlistEditModal (API-aware)
  const handleWatchlistAdd = useCallback(
    async (symbol) => {
      if (!symbol || watchlist.includes(symbol)) return;
      setWatchlist((prev) => [...prev, symbol]);
      if (isLoggedIn) {
        try {
          await apiAddToWatchlist(symbol, selectedMarket);
          await refreshWatchlistFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    },
    [watchlist, isLoggedIn, selectedMarket, refreshWatchlistFromApi]
  );

  const handleWatchlistRemove = useCallback(
    async (symbol) => {
      setWatchlist((prev) => prev.filter((s) => s !== symbol));
      if (isLoggedIn) {
        try {
          await apiRemoveFromWatchlist(symbol);
          await refreshWatchlistFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    },
    [isLoggedIn, refreshWatchlistFromApi]
  );

  const handleWatchlistClear = useCallback(async () => {
    const oldWatchlist = [...watchlist];
    setWatchlist([]);
    if (isLoggedIn) {
      try {
        await Promise.all(oldWatchlist.map((symbol) => apiRemoveFromWatchlist(symbol)));
        await refreshWatchlistFromApi();
      } catch {
        // Local state already cleared as fallback
      }
    }
  }, [watchlist, isLoggedIn, refreshWatchlistFromApi]);

  const handleWatchlistReorder = useCallback((newWatchlist) => {
    setWatchlist(newWatchlist);
  }, []);

  const handleWatchlistAddAlert = useCallback(
    async (symbol) => {
      const newAlert = { symbol, condition: 'above', price: 0 };
      setAlerts((prev) => [...prev, newAlert]);
      if (isLoggedIn) {
        try {
          await apiCreateAlert({ symbol, condition: 'above', targetValue: 0 });
          await refreshAlertsFromApi();
        } catch {
          // Local state already updated as fallback
        }
      }
    },
    [isLoggedIn, refreshAlertsFromApi]
  );

  // ============================================================
  // EFFECTS
  // ============================================================
  useEffect(() => {
    const loadMovers = async () => {
      try {
        const freshMovers = await fetchTopMovers(selectedMarket);
        if (freshMovers && freshMovers.length > 0) setMovers(freshMovers);
        else setMovers(generateDemoMovers(selectedMarket));
      } catch {
        setMovers(generateDemoMovers(selectedMarket));
      }
    };
    loadMovers();
  }, [selectedMarket]);

  useEffect(() => {
    const controller = new AbortController();
    fetchAllData(controller.signal);
    intervalRef.current = setInterval(() => fetchAllData(null), pollingInterval);
    return () => {
      controller.abort();
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAllData, pollingInterval]);

  useEffect(() => {
    setHistory([]);
    setLoading(true);
  }, [chartInterval]);

  // ============================================================
  // SYNC USER DATA FROM BACKEND ON LOGIN
  // ============================================================

  useEffect(() => {
    if (isLoggedIn) {
      refreshWatchlistFromApi();
      refreshPortfolioFromApi();
      refreshAlertsFromApi();
    }
  }, [isLoggedIn, refreshWatchlistFromApi, refreshPortfolioFromApi, refreshAlertsFromApi]);

  // Filtered screener data
  const filteredScreenerData = useMemo(() => {
    let data = { ...screenerData };
    if (screenerCategory !== 'all')
      data = { [screenerCategory]: screenerData[screenerCategory] || [] };
    if (screenerFilter !== 'all') {
      const filtered = {};
      Object.entries(data).forEach(([cat, stocks]) => {
        if (!Array.isArray(stocks)) return;
        const filteredStocks = stocks.filter((stock) => {
          const rsi = stock.rsi || 50;
          if (screenerFilter === 'oversold') return rsi < 30;
          if (screenerFilter === 'overbought') return rsi > 70;
          if (screenerFilter === 'buy') {
            const sig = (stock.signal || '').toUpperCase();
            return sig === 'BUY' || sig === 'STRONG BUY' || sig === 'STRONG_BUY';
          }
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
          {' • Polling: '}
          {pollingInterval / 1000}s{' • Press ? for shortcuts'}
        </span>
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-400 hover:underline"
        >
          API Docs
        </a>
      </div>

      {/* Header */}
      <header className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            {/* Mobile sidebar toggle */}
            <button
              className="md:hidden p-1.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
              onClick={() => setShowMobileSidebar((v) => !v)}
              aria-label="Toggle watchlist"
            >
              ☰
            </button>
            <h1 className="text-xl font-bold text-cyan-400">TraderAI Pro</h1>
            <span className="text-xs text-gray-500">v{APP_VERSION}</span>
            <div className="relative">
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  const q = e.target.value;
                  setSearchQuery(q);
                  const results = searchSymbols(q, 8);
                  setSearchResults(results);
                  setShowSearchDrop(results.length > 0);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    const top = searchResults[0];
                    handleSymbolSelect(top ? top.symbol : searchQuery.trim().toUpperCase());
                    setShowSearchDrop(false);
                    setSearchQuery('');
                  }
                  if (e.key === 'Escape') {
                    e.target.blur();
                    setSearchQuery('');
                    setShowSearchDrop(false);
                  }
                }}
                onBlur={() => setTimeout(() => setShowSearchDrop(false), 150)}
                placeholder="Search stocks... (press /)"
                className="bg-gray-700 px-4 py-2 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              {showSearchDrop && (
                <div className="absolute left-0 top-full mt-1 w-80 bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-50 overflow-hidden">
                  {searchResults.map((item) => (
                    <button
                      key={item.symbol}
                      onMouseDown={() => {
                        handleSymbolSelect(item.symbol);
                        setShowSearchDrop(false);
                        setSearchQuery('');
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-700 text-left text-sm transition-colors"
                    >
                      <div>
                        <span className="font-mono font-semibold text-cyan-400 text-xs">
                          {item.symbol.replace('.NS', '').replace('.L', '').replace('.DE', '')}
                        </span>
                        <span className="ml-2 text-gray-300 text-xs">{item.name}</span>
                      </div>
                      <span className="text-[10px] text-gray-500 shrink-0 ml-2">
                        {item.market} · {item.sector}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto flex-nowrap pb-0.5 sm:flex-wrap sm:overflow-visible">
            <button
              onClick={() => setShowStrategyIntelligence(true)}
              className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 rounded-lg text-sm font-bold shadow-lg shadow-cyan-500/30 border border-cyan-400/30 animate-pulse hover:animate-none flex items-center gap-1.5"
            >
              <span className="text-base">&#x1F9E0;</span> Strategy AI
            </button>
            <button
              onClick={() => {
                setShowScreener(true);
                fetchScreenerData();
              }}
              className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm font-medium"
            >
              Screener
            </button>
            <button
              onClick={() => setShowPortfolio(true)}
              className="px-3 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm font-medium"
            >
              💰 Portfolio
            </button>
            {isLoggedIn && (
              <>
                <button
                  onClick={() => setShowPaperTrades(true)}
                  className="px-3 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium"
                >
                  📋 Paper Trades
                </button>
                <button
                  onClick={() => setShowJournal(true)}
                  className="px-3 py-2 bg-indigo-700 hover:bg-indigo-600 rounded-lg text-sm font-medium"
                >
                  📊 Journal
                </button>
              </>
            )}
            <button
              onClick={() => setShowAlerts(true)}
              className="px-3 py-2 bg-orange-600 hover:bg-orange-500 rounded-lg text-sm font-medium relative"
            >
              🔔 Alerts
              {alerts.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {alerts.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setShowWhatsNext(true)}
              className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium"
            >
              🚀 What&apos;s Next
            </button>
            <button
              onClick={() => setShowUserGuide(true)}
              className="px-3 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium"
            >
              📖 Guide
            </button>
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg text-sm font-medium"
            >
              🔧
            </button>
            {/* DEMO_MODE indicator */}
            {demoMode && (
              <span
                title="Simulated prices. On Render dashboard: set TWELVE_DATA_API_KEY (twelvedata.com, free) + DEMO_MODE=false, then redeploy."
                className="px-2 py-1 bg-orange-500/20 text-orange-400 border border-orange-500/30 rounded text-xs font-medium cursor-help"
              >
                📦 Demo prices — not live
              </span>
            )}
            {/* User GROQ API key */}
            <div className="relative">
              <button
                onClick={() => setShowApiKeyInput((v) => !v)}
                title={
                  groqApiKey
                    ? 'GROQ API key set — AI responses powered by your key'
                    : 'Add your GROQ API key for real AI responses (free at console.groq.com)'
                }
                className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${groqApiKey ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-gray-700 text-gray-400 border-gray-600 hover:border-gray-500'}`}
              >
                🔑 {groqApiKey ? 'AI Key ✓' : 'AI Key'}
              </button>
              {showApiKeyInput && (
                <div className="absolute right-0 top-9 z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 w-80 shadow-xl">
                  <p className="text-xs font-semibold text-white mb-1">Enable Real AI Responses</p>
                  <p className="text-xs text-gray-400 mb-2">
                    Get a <strong>free</strong> API key from your AI provider, paste it below.
                  </p>
                  <div className="flex flex-col gap-1 mb-2 p-2 bg-gray-700/50 rounded text-xs">
                    <a
                      href="https://console.groq.com/keys"
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-400 hover:underline flex items-center gap-1"
                    >
                      🔗 Groq — fastest, free tier available
                    </a>
                    <span className="text-gray-500 text-[10px] pl-4">
                      console.groq.com → API Keys → Create Key → starts with gsk_
                    </span>
                  </div>
                  <input
                    type="password"
                    value={groqApiKey}
                    onChange={(e) => setGroqApiKey(e.target.value)}
                    placeholder="Paste Groq key here (gsk_...)"
                    className="w-full bg-gray-700 px-2 py-1.5 rounded text-xs text-white focus:outline-none focus:ring-1 focus:ring-cyan-500 mb-2"
                  />
                  <div className="flex gap-1.5">
                    <button
                      onClick={async () => {
                        if (!groqApiKey.trim()) return;
                        addToast('Testing key…', 'warning');
                        try {
                          const res = await fetch(`${API_BASE}/api/genai/test-key`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ groq_api_key: groqApiKey.trim() }),
                          });
                          const data = await res.json();
                          if (data.ok) {
                            localStorage.setItem('groqApiKey', groqApiKey.trim());
                            setShowApiKeyInput(false);
                            addToast('Key verified ✓ AI chat now uses real Groq LLM', 'success');
                          } else {
                            addToast(`Key rejected: ${data.error}`, 'error');
                          }
                        } catch {
                          addToast('Could not reach server to test key', 'error');
                        }
                      }}
                      className="flex-1 py-1 bg-cyan-700 hover:bg-cyan-600 text-white rounded text-xs"
                    >
                      Test &amp; Save
                    </button>
                    <button
                      onClick={() => {
                        localStorage.setItem('groqApiKey', groqApiKey);
                        setShowApiKeyInput(false);
                        addToast(groqApiKey ? 'Key saved (not tested)' : 'Key cleared', 'warning');
                      }}
                      className="px-2 py-1 bg-gray-600 hover:bg-gray-500 text-gray-300 rounded text-xs"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setGroqApiKey('');
                        localStorage.removeItem('groqApiKey');
                        setShowApiKeyInput(false);
                      }}
                      className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-400 rounded text-xs"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              )}
            </div>
            <ConnectionStatus />
            {isLoggedIn ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-cyan-400">{user?.username}</span>
                <button
                  onClick={logout}
                  className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
                >
                  Logout
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="px-3 py-2 bg-cyan-700 hover:bg-cyan-600 rounded-lg text-sm font-medium"
              >
                Login
              </button>
            )}
          </div>
        </div>

        {/* Market Selector */}
        <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-2">
          {MARKETS.map((market) => (
            <button
              key={market.id}
              onClick={() => handleMarketChange(market.id)}
              className={`px-3 py-1 rounded text-sm whitespace-nowrap transition-colors ${
                selectedMarket === market.id
                  ? 'bg-cyan-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
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
        {/* Mobile overlay backdrop */}
        {showMobileSidebar && (
          <div
            className="fixed inset-0 bg-black/60 z-30 md:hidden"
            onClick={() => setShowMobileSidebar(false)}
          />
        )}
        <aside
          className={`${showMobileSidebar ? 'fixed inset-y-0 left-0 z-40 translate-x-0' : 'hidden md:block'} w-56 bg-gray-800 border-r border-gray-700 p-4 space-y-6 overflow-y-auto transition-transform`}
        >
          {/* Trading Style */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Trading Style</h3>
            <select
              value={traderStyle}
              onChange={(e) => setTraderStyle(e.target.value)}
              className="w-full bg-gray-700 text-white px-3 py-2 rounded text-sm"
            >
              {Object.keys(TRADING_STYLES).map((style) => (
                <option key={style} value={style}>
                  {style}
                </option>
              ))}
            </select>
          </div>

          {/* Investor Profile - Collapsible */}
          <div className="bg-gray-700/50 rounded-lg border border-gray-600/50 overflow-hidden">
            <button
              onClick={() => setShowInvestorProfile(!showInvestorProfile)}
              className="w-full p-3 flex items-center justify-between hover:bg-gray-700/30 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span>👤</span>
                <span className="font-medium text-sm">Investor Profile</span>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded border ${
                    investorProfile.riskTolerance === 'conservative'
                      ? 'bg-green-500/20 text-green-400 border-green-500/30'
                      : investorProfile.riskTolerance === 'aggressive'
                        ? 'bg-red-500/20 text-red-400 border-red-500/30'
                        : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                  }`}
                >
                  {investorProfile.riskTolerance?.toUpperCase() || 'MODERATE'}
                </span>
                <span
                  className={`transform transition-transform text-xs ${showInvestorProfile ? 'rotate-180' : ''}`}
                >
                  ▼
                </span>
              </div>
            </button>
            {showInvestorProfile && (
              <div className="p-3 border-t border-gray-600/50 space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Display Name</label>
                  <input
                    type="text"
                    value={investorProfile.name}
                    onChange={(e) =>
                      setInvestorProfile((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="Your name"
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Risk Tolerance</label>
                  <div className="grid grid-cols-3 gap-1">
                    {['conservative', 'moderate', 'aggressive'].map((level) => (
                      <button
                        key={level}
                        onClick={() =>
                          setInvestorProfile((prev) => ({ ...prev, riskTolerance: level }))
                        }
                        className={`py-1.5 px-1 rounded text-xs font-medium transition-all border ${
                          investorProfile.riskTolerance === level
                            ? level === 'conservative'
                              ? 'bg-green-500/20 text-green-400 border-green-500/30'
                              : level === 'aggressive'
                                ? 'bg-red-500/20 text-red-400 border-red-500/30'
                                : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
                            : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                        }`}
                      >
                        {level === 'conservative' ? '🛡️' : level === 'aggressive' ? '🔥' : '⚖️'}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Horizon</label>
                  <select
                    value={investorProfile.investmentHorizon}
                    onChange={(e) =>
                      setInvestorProfile((prev) => ({ ...prev, investmentHorizon: e.target.value }))
                    }
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="short">Short (&lt;1 year)</option>
                    <option value="medium">Medium (1-5 years)</option>
                    <option value="long">Long (5+ years)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Experience</label>
                  <select
                    value={investorProfile.experience}
                    onChange={(e) =>
                      setInvestorProfile((prev) => ({ ...prev, experience: e.target.value }))
                    }
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="beginner">🌱 Beginner</option>
                    <option value="intermediate">📈 Intermediate</option>
                    <option value="advanced">🎯 Advanced</option>
                    <option value="expert">🏆 Expert</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Capital Range</label>
                  <select
                    value={investorProfile.capitalRange}
                    onChange={(e) =>
                      setInvestorProfile((prev) => ({ ...prev, capitalRange: e.target.value }))
                    }
                    className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="small">$1K - $10K</option>
                    <option value="medium">$10K - $100K</option>
                    <option value="large">$100K - $1M</option>
                    <option value="institutional">$1M+</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Goals</label>
                  <div className="flex flex-wrap gap-1">
                    {['income', 'growth', 'preservation', 'speculation'].map((goal) => (
                      <button
                        key={goal}
                        onClick={() => {
                          const goals = investorProfile.goals || [];
                          const newGoals = goals.includes(goal)
                            ? goals.filter((g) => g !== goal)
                            : [...goals, goal];
                          setInvestorProfile((prev) => ({ ...prev, goals: newGoals }));
                        }}
                        className={`py-1 px-2 rounded text-xs transition-all border ${
                          (investorProfile.goals || []).includes(goal)
                            ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                            : 'bg-gray-700/30 text-gray-400 border-gray-600 hover:bg-gray-700/50'
                        }`}
                      >
                        {goal === 'income'
                          ? '💰'
                          : goal === 'growth'
                            ? '📈'
                            : goal === 'preservation'
                              ? '🛡️'
                              : '🎲'}
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  onClick={async () => {
                    localStorage.setItem('investorProfile', JSON.stringify(investorProfile));
                    if (isLoggedIn) {
                      try {
                        await authFetch(`${API_BASE}/api/auth/me`, {
                          method: 'PUT',
                          body: JSON.stringify({
                            trader_style:
                              investorProfile.tradingStyle || investorProfile.experience,
                            risk_tolerance: investorProfile.riskTolerance,
                            investment_horizon: investorProfile.investmentHorizon,
                            experience_level: investorProfile.experience,
                            capital_range: investorProfile.capitalRange,
                            goals: JSON.stringify(investorProfile.goals || []),
                          }),
                        });
                      } catch {
                        // Profile saved locally; DB sync will retry on next login
                      }
                    }
                    setShowInvestorProfile(false);
                  }}
                  className="w-full py-2 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium rounded hover:opacity-90 transition-opacity"
                >
                  Save Profile
                </button>
                {investorProfile.name && (
                  <div className="p-2 bg-gray-700/30 rounded text-xs text-gray-400">
                    <span className="text-white font-medium">{investorProfile.name}</span> •{' '}
                    {investorProfile.experience} • {investorProfile.riskTolerance} risk
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Top Movers */}
          <div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wide mb-2">Top Movers</h3>
            <div className="space-y-1">
              {movers.slice(0, 4).map((mover) => (
                <button
                  key={mover.symbol}
                  onClick={() => handleSymbolSelect(mover.fullSymbol || mover.symbol)}
                  className="w-full flex items-center justify-between p-2 rounded text-sm hover:bg-gray-700 transition-colors"
                >
                  <span className="text-cyan-400">{mover.symbol}</span>
                  <span
                    className={`text-sm ${parseFloat(mover.change) >= 0 ? 'text-green-400' : 'text-red-400'}`}
                  >
                    {parseFloat(mover.change) >= 0 ? '+' : ''}
                    {mover.change}%
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Watchlist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs text-gray-400 uppercase tracking-wide">Watchlist</h3>
              <button
                onClick={() => setShowWatchlistEdit(true)}
                className="text-xs text-cyan-400 hover:underline"
              >
                Edit
              </button>
            </div>
            <div className="space-y-1">
              {watchlist.slice(0, 5).map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => handleSymbolSelect(symbol)}
                  className={`w-full text-left p-2 rounded text-sm transition-colors ${selectedSymbol === symbol ? 'bg-cyan-600/30 text-cyan-400' : 'hover:bg-gray-700'}`}
                >
                  {symbol}
                </button>
              ))}
              {watchlist.length > 5 && (
                <button
                  onClick={() => setShowWatchlistEdit(true)}
                  className="w-full text-center text-xs text-gray-500 hover:text-cyan-400 py-1"
                >
                  +{watchlist.length - 5} more
                </button>
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
                {(() => {
                  const dq = quote?.dataQuality || (demoMode ? 'DEMO' : 'LIVE');
                  const isLive = dq === 'LIVE' || dq === 'REALTIME';
                  const isDelayed = dq === 'DELAYED' || dq === '15min';
                  return (
                    <span
                      title={
                        isLive
                          ? 'Real-time price data'
                          : isDelayed
                            ? '15-minute delayed data'
                            : 'Simulated/demo data — not real market prices'
                      }
                      className={`px-2 py-0.5 text-xs rounded cursor-help ${isLive ? 'bg-green-600/30 text-green-400' : isDelayed ? 'bg-yellow-600/30 text-yellow-400' : 'bg-orange-600/30 text-orange-400'}`}
                    >
                      {isLive ? '⚡ Live' : isDelayed ? '⏱ Delayed' : '📦 Demo data'}
                    </span>
                  );
                })()}
                {selectedMarket === 'India' &&
                  (() => {
                    const now = new Date();
                    const ist = new Date(
                      now.toLocaleString('en-US', { timeZone: NSE_HOURS.timezone })
                    );
                    const day = ist.getDay(); // 0=Sun,6=Sat
                    const hhmm = ist.getHours() * 100 + ist.getMinutes();
                    const isWeekday = day >= 1 && day <= 5;
                    const isOpen = isWeekday && hhmm >= 915 && hhmm < 1530;
                    const isPreOpen = isWeekday && hhmm >= 900 && hhmm < 915;
                    return (
                      <span
                        title={
                          isOpen
                            ? 'NSE regular session (9:15–15:30 IST)'
                            : isPreOpen
                              ? 'NSE pre-open (9:00–9:15 IST)'
                              : 'NSE market closed'
                        }
                        className={`px-2 py-0.5 text-xs rounded cursor-help ${isOpen ? 'bg-green-700/30 text-green-300' : isPreOpen ? 'bg-yellow-700/30 text-yellow-300' : 'bg-gray-700/40 text-gray-400'}`}
                      >
                        {isOpen ? '🟢 NSE Open' : isPreOpen ? '🟡 Pre-open' : '🔴 NSE Closed'}
                      </span>
                    );
                  })()}
                <span className="text-2xl font-bold">
                  {currentMarket.currency}
                  {quote?.price?.toFixed(2) || '-'}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span>
                  {currentMarket.flag} {currentMarket.name}
                </span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-400">{currentMarket.currencyName}</span>
                {quote?.changePercent !== undefined && (
                  <span className={quote.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {quote.changePercent >= 0 ? '+' : ''}
                    {quote.changePercent.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={addToWatchlist}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${isInWatchlist ? 'bg-yellow-600/30 text-yellow-400 border border-yellow-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                {isInWatchlist ? '★ Watching' : '+ Watchlist'}
              </button>
              <button
                onClick={() => {
                  if (isInPortfolio) {
                    removeFromPortfolio(selectedSymbol);
                  } else {
                    setPortfolioShares('');
                    setPortfolioAvgPrice(quote?.price?.toFixed(2) || '');
                    setShowAddToPortfolio(true);
                  }
                }}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${isInPortfolio ? 'bg-green-600/30 text-green-400 border border-green-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                {isInPortfolio ? '💰 In Portfolio' : '+ Portfolio'}
              </button>
              <button
                onClick={() => setShowAlerts(true)}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm font-medium"
              >
                Set Alert
              </button>
            </div>
          </div>

          {/* Time Interval Buttons */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {['1m', '5m', '15m', '1h', '1d', '1wk'].map((interval, idx) => (
              <button
                key={interval}
                onClick={() => setChartInterval(interval)}
                className={`px-3 py-1 rounded text-sm ${chartInterval === interval ? 'bg-cyan-600 text-white' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                {interval.toUpperCase()}
                <span className="ml-1 text-xs text-gray-500">({idx + 1})</span>
              </button>
            ))}
            <span className="ml-auto text-sm text-gray-400">
              Last: {lastFetchTime?.toLocaleTimeString() || '-'} • Poll: {pollingInterval / 1000}s
            </span>
          </div>

          {/* Chart */}
          <div
            key={`chart-${selectedSymbol}-${chartInterval}`}
            className="bg-gray-800 rounded-lg p-4 mb-4"
          >
            <ChartPanel
              history={history}
              selectedSymbol={selectedSymbol}
              chartInterval={chartInterval}
              currency={currentMarket.currency}
            />
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
            {['technicals', 'backtest', 'sentiment', 'fundamentals', 'news', 'AI scanner'].map(
              (tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 rounded text-sm font-medium capitalize whitespace-nowrap ${activeTab === tab ? 'bg-cyan-600 text-white' : 'bg-gray-700 hover:bg-gray-600'}`}
                >
                  {tab === 'AI scanner' && selectedMarket === 'India' ? 'Nifty 50' : tab}
                </button>
              )
            )}
          </div>

          {/* Tab Content */}
          <div className="bg-gray-800 rounded-lg p-4">
            {activeTab === 'technicals' && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Relative Strength Index: measures how fast the price has moved. Below 30 = possibly oversold (bounce candidate). Above 70 = possibly overbought (pullback risk)."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    RSI <span className="text-gray-600 text-xs">(momentum 0–100)</span>
                  </h4>
                  <div
                    className={`text-2xl font-bold ${getRsiColor(getSignalValue(signals?.rsi))}`}
                  >
                    {getSignalValue(signals?.rsi)?.toFixed(1) || '-'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {getSignalValue(signals?.rsi) < 30
                      ? 'Oversold — possible bounce'
                      : getSignalValue(signals?.rsi) > 70
                        ? 'Overbought — pullback risk'
                        : 'Neutral zone'}
                  </p>
                </div>
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Combined signal from multiple technical indicators. BUY = conditions favour going long. SELL = consider exiting or shorting. HOLD = no clear edge right now."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    Signal <span className="text-gray-600 text-xs">(overall bias)</span>
                  </h4>
                  <div
                    className={`text-2xl font-bold ${getSignalColor(signals?.signal || signals?.overall_signal)}`}
                  >
                    {signals?.signal || signals?.overall_signal || '-'}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Combined indicator verdict</p>
                </div>
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Simple Moving Average of the last 20 closing prices. Price above SMA20 = short-term uptrend. Price below = downtrend."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    SMA 20 <span className="text-gray-600 text-xs">(20-day avg price)</span>
                  </h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(
                      getSignalValue(signals?.sma_20 || signals?.sma20),
                      currentMarket.currency
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {quote?.price && getSignalValue(signals?.sma_20 || signals?.sma20)
                      ? quote.price > getSignalValue(signals?.sma_20 || signals?.sma20)
                        ? 'Price above — bullish bias'
                        : 'Price below — bearish bias'
                      : 'Trend reference level'}
                  </p>
                </div>
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Exponential Moving Average: like a moving average but gives more weight to recent prices. Reacts faster to price changes than SMA."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    EMA 12 <span className="text-gray-600 text-xs">(fast-reacting avg)</span>
                  </h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(
                      getSignalValue(signals?.ema_12 || signals?.ema12),
                      currentMarket.currency
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Reacts faster than SMA</p>
                </div>
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Volume-Weighted Average Price: the average price weighted by trading volume. Institutions use this as a benchmark — price above VWAP is bullish intraday."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    VWAP <span className="text-gray-600 text-xs">(volume avg price)</span>
                  </h4>
                  <div className="text-2xl font-bold text-cyan-400">
                    {formatPrice(getSignalValue(signals?.vwap), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {quote?.price && getSignalValue(signals?.vwap)
                      ? quote.price > getSignalValue(signals?.vwap)
                        ? 'Above VWAP — institutions buying'
                        : 'Below VWAP — selling pressure'
                      : 'Intraday fair-value benchmark'}
                  </p>
                </div>
                <div
                  className="p-3 bg-gray-700/50 rounded-lg"
                  title="Average True Range: measures how much the price typically moves per day. High ATR = volatile stock. Use it to size your stop-loss — e.g. stop = 1.5× ATR below entry."
                >
                  <h4 className="text-sm text-gray-400 mb-1">
                    ATR <span className="text-gray-600 text-xs">(daily move range)</span>
                  </h4>
                  <div className="text-2xl font-bold text-orange-400">
                    {formatPrice(getSignalValue(signals?.atr), currentMarket.currency)}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Typical daily price swing</p>
                </div>
              </div>
            )}

            {activeTab === 'sentiment' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <h4 className="text-sm text-gray-400 mb-2">Reddit Sentiment</h4>
                    <div className="flex items-center gap-4">
                      <div className="text-3xl font-bold">
                        {sentiment?.sentiment?.bullish || sentiment?.bullish_percent || 50}%
                      </div>
                      <div className="flex-1">
                        <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-green-500"
                            style={{
                              width: `${sentiment?.sentiment?.bullish || sentiment?.bullish_percent || 50}%`,
                            }}
                          />
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Bearish</span>
                          <span>Bullish</span>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm text-gray-400 mt-2">
                      {sentiment?.mentions || 0} mentions • {sentiment?.sentiment?.label || 'N/A'}
                    </p>
                  </div>
                  <div className="p-4 bg-gray-700/50 rounded-lg">
                    <h4 className="text-sm text-gray-400 mb-2">Overall Sentiment</h4>
                    <div className="text-xl font-bold text-cyan-400">
                      {(sentiment?.sentiment?.bullish || 50) > 60
                        ? '🚀 Bullish'
                        : (sentiment?.sentiment?.bullish || 50) < 40
                          ? '🐻 Bearish'
                          : '😐 Neutral'}
                    </div>
                    <p className="text-sm text-gray-400 mt-2">
                      Bullish: {sentiment?.sentiment?.bullish || 50}% • Bearish:{' '}
                      {sentiment?.sentiment?.bearish || 30}%
                    </p>
                  </div>
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
                  <div className="text-center py-8 text-gray-400">
                    <p>Financial data not available for {selectedSymbol}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="bg-gray-700/50 rounded-lg p-4">
                      <h4 className="text-sm font-semibold text-cyan-400 mb-3">Company Overview</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-400">Sector</p>
                          <p className="text-sm text-white">{financials.sector || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-400">Industry</p>
                          <p className="text-sm text-white">{financials.industry || 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        ['Market Cap', financials.marketCap],
                        ['P/E Ratio', financials.peRatio],
                        ['Revenue', financials.revenue],
                        ['EPS', financials.eps],
                        ['Div Yield', financials.dividendYield],
                        [
                          '52W High',
                          financials.fiftyTwoWeekHigh
                            ? `${currentMarket.currency}${financials.fiftyTwoWeekHigh}`
                            : 'N/A',
                        ],
                        [
                          '52W Low',
                          financials.fiftyTwoWeekLow
                            ? `${currentMarket.currency}${financials.fiftyTwoWeekLow}`
                            : 'N/A',
                        ],
                        ['Beta', financials.beta],
                      ].map(([label, value]) => (
                        <div key={label} className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-xs text-gray-400 mb-1">{label}</p>
                          <p className="text-lg font-semibold text-white">{value || 'N/A'}</p>
                        </div>
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 text-center">
                      Data Quality:{' '}
                      <span
                        className={`px-2 py-0.5 rounded ${financials.dataQuality === 'LIVE' ? 'bg-green-600' : financials.dataQuality === 'CACHED' ? 'bg-blue-600' : 'bg-orange-600'} text-white`}
                      >
                        {financials.dataQuality || 'DEMO'}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'news' && (
              <div className="space-y-3">
                {news.length === 0 ? (
                  <p className="text-gray-400 text-center py-4">No recent news available</p>
                ) : (
                  news.slice(0, 5).map((item, i) => (
                    <div key={i} className="p-3 bg-gray-700/50 rounded-lg">
                      <h4 className="font-medium text-sm mb-1">{item.title || item.headline}</h4>
                      <p className="text-xs text-gray-400">
                        {item.source} • {item.time_ago || item.time || item.date || 'Recent'}
                        {item.sentiment && (
                          <span
                            className={`ml-2 ${item.sentiment === 'positive' ? 'text-green-400' : item.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'}`}
                          >
                            • {item.sentiment}
                          </span>
                        )}
                      </p>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'backtest' && (
              <BacktestPanel
                symbol={selectedSymbol}
                traderStyle={traderStyle?.toLowerCase()}
                currency={currentMarket.currency}
              />
            )}
            {activeTab === 'sentiment' && <SentimentDashboard symbol={selectedSymbol} />}
            {activeTab === 'AI scanner' &&
              (selectedMarket === 'India' ? (
                <Nifty50Scanner
                  traderStyle={traderStyle || 'Day'}
                  onSymbolSelect={handleSymbolSelect}
                />
              ) : (
                <AIScanner
                  traderStyle={traderStyle?.toLowerCase()}
                  onSymbolSelect={handleSymbolSelect}
                />
              ))}
          </div>
        </main>

        {/* Floating AI chat button — mobile only */}
        <button
          className="fixed bottom-4 right-4 z-30 md:hidden bg-cyan-600 hover:bg-cyan-500 rounded-full w-12 h-12 flex items-center justify-center text-xl shadow-lg shadow-cyan-500/30"
          onClick={() => setShowMobileAI((v) => !v)}
          aria-label="Toggle AI chat"
        >
          🤖
        </button>

        {/* Right Sidebar - AI Chat */}
        <aside
          className={`${showMobileAI ? 'fixed inset-y-0 right-0 z-40 w-full sm:w-80' : 'hidden md:flex'} md:flex md:w-80 bg-gray-800 border-l border-gray-700 flex-col`}
        >
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-cyan-400">AI Assistant</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-green-400">● Active</span>
                <button
                  className="md:hidden text-gray-400 hover:text-white text-lg leading-none"
                  onClick={() => setShowMobileAI(false)}
                  aria-label="Close AI panel"
                >
                  &times;
                </button>
              </div>
            </div>
            <div className="mt-2 relative" ref={modelPickerRef}>
              <button
                onClick={() => setShowModelPicker(!showModelPicker)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors w-full"
              >
                <span>🧠</span>
                <span className="flex-1 text-left">
                  {AI_MODEL_OPTIONS.find((m) => m.id === selectedModel)?.label || 'Select Model'}
                </span>
                <span className="text-gray-500 text-[10px]">▼</span>
              </button>
              {showModelPicker && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded-lg p-1 z-50 shadow-xl">
                  {AI_MODEL_OPTIONS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setSelectedModel(m.id);
                        setShowModelPicker(false);
                      }}
                      className={`flex items-center justify-between w-full px-3 py-2 rounded text-xs transition-colors ${
                        selectedModel === m.id
                          ? 'bg-cyan-600/20 text-cyan-400'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      <span>
                        {selectedModel === m.id ? '✓ ' : ''}
                        {m.label}
                      </span>
                      {m.tag && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            m.tag === 'Best'
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-yellow-500/20 text-yellow-400'
                          }`}
                        >
                          {m.tag}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {aiMessages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-3">🤖</div>
                <p className="text-sm mb-2">Ask me about {selectedSymbol}</p>
                <p className="text-xs text-gray-600 mb-4">
                  Style: {traderStyle} ({TRADING_STYLES[traderStyle]?.focus})
                </p>
                <div className="space-y-2">
                  {AI_PROMPTS.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleAiSubmit(prompt)}
                      className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-xs text-left transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              aiMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg text-sm ${msg.role === 'user' ? 'bg-cyan-600/30 ml-8' : 'bg-gray-700/50 mr-8'}`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.source && msg.role === 'assistant' && (
                    <p
                      className={`text-xs mt-1 ${msg.source.startsWith('rule-based') && groqApiKey ? 'text-orange-400' : 'text-gray-500'}`}
                    >
                      {msg.source.startsWith('rule-based') && groqApiKey
                        ? `⚠ ${msg.source}`
                        : `via ${msg.source}`}
                    </p>
                  )}
                </div>
              ))
            )}
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
              <input
                type="text"
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAiSubmit()}
                placeholder="Ask about this stock..."
                className="flex-1 bg-gray-700 px-3 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <button
                onClick={() => handleAiSubmit()}
                disabled={aiLoading || !aiInput.trim()}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium"
              >
                Send
              </button>
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
        <span>
          Data: DEMO • Watchlist: {watchlist.length} • Alerts: {alerts.length}
        </span>
      </footer>

      {/* Lazy-loaded Modals */}
      <Suspense fallback={null}>
        {showUserGuide && <UserGuideModal onClose={() => setShowUserGuide(false)} />}
        {showWhatsNext && (
          <WhatsNextModal isLoggedIn={isLoggedIn} onClose={() => setShowWhatsNext(false)} />
        )}
        {showKeyboardHelp && <KeyboardShortcutsModal onClose={() => setShowKeyboardHelp(false)} />}
        {showWatchlistEdit && (
          <WatchlistEditModal
            onClose={() => setShowWatchlistEdit(false)}
            watchlist={watchlist}
            onAdd={handleWatchlistAdd}
            onRemove={handleWatchlistRemove}
            onClear={handleWatchlistClear}
            onReorder={handleWatchlistReorder}
            onSelectSymbol={handleSymbolSelect}
            onAddAlert={handleWatchlistAddAlert}
            currentSymbol={selectedSymbol}
          />
        )}
        {showScreener && (
          <ScreenerModal
            onClose={() => setShowScreener(false)}
            screenerCategory={screenerCategory}
            setScreenerCategory={setScreenerCategory}
            screenerCategories={screenerCategories}
            screenerFilter={screenerFilter}
            setScreenerFilter={setScreenerFilter}
            screenerLoading={screenerLoading}
            filteredScreenerData={filteredScreenerData}
            onSymbolSelect={handleSymbolSelect}
          />
        )}
        {showPortfolio && (
          <PortfolioModal
            onClose={() => setShowPortfolio(false)}
            portfolio={portfolio}
            quote={quote}
            onSymbolSelect={handleSymbolSelect}
            onRemove={removeFromPortfolio}
          />
        )}
        {showPaperTrades && <PaperTradesModal onClose={() => setShowPaperTrades(false)} />}
        {showJournal && <TradeJournalModal onClose={() => setShowJournal(false)} />}
        {showAlerts && (
          <AlertsModal
            onClose={() => setShowAlerts(false)}
            alerts={alerts}
            newAlertPrice={newAlertPrice}
            setNewAlertPrice={setNewAlertPrice}
            newAlertCondition={newAlertCondition}
            setNewAlertCondition={setNewAlertCondition}
            onAddAlert={addAlert}
            onRemoveAlert={removeAlert}
          />
        )}
        {showAddToPortfolio && (
          <AddToPortfolioModal
            onClose={() => setShowAddToPortfolio(false)}
            selectedSymbol={selectedSymbol}
            quote={quote}
            portfolioShares={portfolioShares}
            setPortfolioShares={setPortfolioShares}
            portfolioAvgPrice={portfolioAvgPrice}
            setPortfolioAvgPrice={setPortfolioAvgPrice}
            onAdd={addToPortfolio}
            isInPortfolio={isInPortfolio}
          />
        )}
        {showStrategyIntelligence && (
          <StrategyIntelligence
            symbol={selectedSymbol}
            onClose={() => setShowStrategyIntelligence(false)}
          />
        )}
      </Suspense>

      {/* Debug Panel */}
      {showDebug && (
        <div className="fixed bottom-0 right-0 w-96 max-h-64 bg-gray-900 border border-gray-700 rounded-tl-lg overflow-auto text-xs font-mono p-2 z-50">
          <div className="flex justify-between items-center mb-2">
            <span className="text-cyan-400">Debug Info</span>
            <button onClick={() => setShowDebug(false)} className="text-gray-400">
              ×
            </button>
          </div>
          <pre className="text-gray-300 whitespace-pre-wrap">
            {JSON.stringify(
              {
                version: APP_VERSION,
                market: selectedMarket,
                symbol: selectedSymbol,
                chartInterval,
                healthStatus,
                pollingInterval,
                historyLength: history?.length || 0,
                screenerCategories: screenerCategories.length,
                watchlistCount: watchlist.length,
                alertsCount: alerts.length,
                financials: financials
                  ? {
                      marketCap: financials.marketCap,
                      peRatio: financials.peRatio,
                      dataQuality: financials.dataQuality,
                    }
                  : null,
                signals: signals
                  ? {
                      rsi: getSignalValue(signals.rsi),
                      signal: signals.signal || signals.overall_signal,
                    }
                  : null,
              },
              null,
              2
            )}
          </pre>
        </div>
      )}

      {/* Onboarding wizard — shown once after first login */}
      {showOnboarding && (
        <Suspense fallback={null}>
          <OnboardingModal
            onComplete={(profile) => {
              setInvestorProfile((prev) => ({ ...prev, ...profile }));
              setShowOnboarding(false);
            }}
          />
        </Suspense>
      )}

      {/* Persistent risk disclaimer banner */}
      <RiskDisclaimer />

      {/* Toast notifications (auto-closing trades, etc.) */}
      <ToastNotification
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />
    </div>
  );
}
