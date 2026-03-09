# 📈 TraderAI Pro

## AI-Powered Trading Dashboard for Day Traders

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B?style=for-the-badge)](https://trader-ai-pro-demo.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)

---

## 🌐 Live Demo

### **[👉 Click Here to Try TraderAI Pro](https://trader-ai-pro-demo.streamlit.app)**

---

## 📋 Project Overview

**TraderAI Pro** is a comprehensive AI-powered trading dashboard developed as the final project for the **TalentSprint AIML Program (Stage 2)**.

| | |
|---|---|
| **Project** | Database and GenAI-Powered Visualization Tool for Day Traders |
| **Domain** | Financial Services |
| **Author** | Rishi |
| **Version** | 5.8.6 |
| **Program** | TalentSprint AIML - Stage 2 |

---

## ✨ Key Features

### 🌍 Multi-Market Support
- **22 Global Markets**: US, India, UK, Germany, Japan, France, China, Hong Kong, Australia, Canada, Brazil, Korea, Singapore, Switzerland, and more
- **Alternative Assets**: Crypto, ETF, Forex, Commodities
- **Multi-Currency**: $, ₹, £, €, ¥, and more

### 📊 Technical Analysis
- **Real-time Charts**: Interactive candlestick charts with zoom/pan
- **Indicators**: RSI, MACD, SMA (20/50), Bollinger Bands
- **Signals**: Automated Buy/Sell/Hold recommendations

### 🤖 AI-Powered Features
- **AI Trading Assistant**: Context-aware financial analysis
- **Sentiment Analysis**: Reddit & StockTwits integration
- **Smart Recommendations**: Entry points, stop-loss, targets

### 📈 Trading Tools
- **Stock Screener**: Filter by RSI, signals, market
- **Watchlist**: Track favorite stocks
- **Portfolio Management**: P&L tracking
- **Price Alerts**: Custom notifications

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, TailwindCSS |
| **Backend** | FastAPI, Python 3.11 |
| **Data Source** | Yahoo Finance (yfinance) |
| **AI/ML** | Groq API (LLaMA 3), Sentiment Analysis |
| **Visualization** | Plotly, Recharts |
| **Testing** | Cypress (180+ tests), Pytest |
| **Deployment** | Streamlit Cloud |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm 9+

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
# API runs at http://localhost:8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

### Streamlit Demo (Standalone)
```bash
pip install streamlit pandas numpy plotly
streamlit run streamlit_app.py
# Demo runs at http://localhost:8501
```

---

## 📁 Project Structure

```
TraderAI_Pro/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── v5_complete.py       # Consolidated backend
│   ├── market_data_service.py
│   ├── genai_services.py
│   ├── sentiment_service.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── cypress/             # 180+ E2E tests
│   └── backend/             # API tests
├── streamlit_app.py         # Standalone demo
├── README.md
└── docs/
    └── TraderAI_Pro_Project_Report.docx
```

---

## 🧪 Testing

### Test Coverage
| Category | Tests | Status |
|----------|-------|--------|
| Backend Endpoints | 8 | ✅ Pass |
| UI Components | 50+ | ✅ Pass |
| User Journeys | 20+ | ✅ Pass |
| Market Coverage | 22 | ✅ Pass |
| **Total** | **180+** | ✅ **All Pass** |

### Run Tests
```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npx cypress run
```

---

## 📊 Screenshots

### Dashboard Overview
![Dashboard](screenshots/dashboard.png)

### AI Analysis
![AI Chat](screenshots/ai-analysis.png)

### Stock Screener
![Screener](screenshots/screener.png)

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| **🚀 Live Demo** | [https://trader-ai-pro-demo.streamlit.app](https://trader-ai-pro-demo.streamlit.app) |
| **📂 GitHub Repo** | [https://github.com/kukretirishi91keti/Trader-AI-Pro](https://github.com/kukretirishi91keti/Trader-AI-Pro) |
| **🎥 Demo Video** | [Link to Video] |

---

## 📈 Data Sources

| Data Type | Source | Status |
|-----------|--------|--------|
| Stock Prices | Yahoo Finance (yfinance) | ✅ Live |
| Technical Indicators | Calculated locally | ✅ Live |
| News Headlines | News APIs | ✅ Live |
| Social Sentiment | Reddit, StockTwits | ✅ Live |
| AI Analysis | Groq LLM (LLaMA 3) | ✅ Live |

---

## ⚠️ Disclaimer

This is an **academic demonstration project** for the TalentSprint AIML Program.

- Data shown may be simulated in demo mode
- This is **NOT financial advice**
- Always consult a qualified financial advisor before making investment decisions
- Past performance does not guarantee future results

---

## 🙏 Acknowledgments

- **TalentSprint** - AIML Program
- **Yahoo Finance** - Market data
- **Groq** - AI inference
- **Streamlit** - Demo hosting
- Open source community

---

## 📝 License

Academic Project - TalentSprint AIML Program Stage 2

---

<div align="center">

**📈 TraderAI Pro v5.8.6**

*AI-Powered Trading Dashboard for Day Traders*

[Live Demo](https://trader-ai-pro-demo.streamlit.app) • [GitHub](https://github.com/kukretirishi91keti/Trader-AI-Pro)

**TalentSprint AIML Program - Stage 2 Final Project**

</div>
