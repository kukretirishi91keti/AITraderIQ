"""
demo_data.py - Pre-cached Realistic Market Data
================================================
Provides bulletproof demo data when Yahoo Finance is rate-limited.
Data is based on realistic price ranges and technical indicators.

This ensures the demo NEVER fails due to external API issues.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import math

# ============================================================
# REALISTIC STOCK DATA - Updated December 2024
# ============================================================

DEMO_STOCKS = {
    # US Tech
    "AAPL": {
        "name": "Apple Inc.",
        "base_price": 248.50,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 32.5,
        "market_cap": "3.85T",
        "typical_volume": 45_000_000,
        "rsi_base": 55,
        "volatility": 0.018
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "base_price": 138.50,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 65.2,
        "market_cap": "3.41T",
        "typical_volume": 280_000_000,
        "rsi_base": 62,
        "volatility": 0.032
    },
    "TSLA": {
        "name": "Tesla, Inc.",
        "base_price": 436.00,
        "currency": "$",
        "market": "US",
        "sector": "Automotive",
        "pe_ratio": 112.5,
        "market_cap": "1.39T",
        "typical_volume": 85_000_000,
        "rsi_base": 58,
        "volatility": 0.035
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "base_price": 438.00,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 37.8,
        "market_cap": "3.26T",
        "typical_volume": 18_000_000,
        "rsi_base": 52,
        "volatility": 0.014
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "base_price": 192.50,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 26.4,
        "market_cap": "2.37T",
        "typical_volume": 22_000_000,
        "rsi_base": 54,
        "volatility": 0.016
    },
    "AMZN": {
        "name": "Amazon.com, Inc.",
        "base_price": 227.00,
        "currency": "$",
        "market": "US",
        "sector": "Consumer",
        "pe_ratio": 48.6,
        "market_cap": "2.38T",
        "typical_volume": 35_000_000,
        "rsi_base": 56,
        "volatility": 0.020
    },
    "META": {
        "name": "Meta Platforms, Inc.",
        "base_price": 612.00,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 29.8,
        "market_cap": "1.56T",
        "typical_volume": 12_000_000,
        "rsi_base": 60,
        "volatility": 0.022
    },
    "AMD": {
        "name": "Advanced Micro Devices",
        "base_price": 119.50,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 105.2,
        "market_cap": "193B",
        "typical_volume": 45_000_000,
        "rsi_base": 48,
        "volatility": 0.028
    },
    "ADBE": {
        "name": "Adobe Inc.",
        "base_price": 445.00,
        "currency": "$",
        "market": "US",
        "sector": "Technology",
        "pe_ratio": 42.1,
        "market_cap": "196B",
        "typical_volume": 3_500_000,
        "rsi_base": 45,
        "volatility": 0.022
    },
    
    # India
    "RELIANCE.NS": {
        "name": "Reliance Industries",
        "base_price": 1265.00,
        "currency": "₹",
        "market": "India",
        "sector": "Conglomerate",
        "pe_ratio": 25.8,
        "market_cap": "₹17.1T",
        "typical_volume": 15_000_000,
        "rsi_base": 52,
        "volatility": 0.016
    },
    "TCS.NS": {
        "name": "Tata Consultancy Services",
        "base_price": 4150.00,
        "currency": "₹",
        "market": "India",
        "sector": "Technology",
        "pe_ratio": 31.2,
        "market_cap": "₹15.0T",
        "typical_volume": 2_500_000,
        "rsi_base": 48,
        "volatility": 0.012
    },
    "INFY.NS": {
        "name": "Infosys Limited",
        "base_price": 1890.00,
        "currency": "₹",
        "market": "India",
        "sector": "Technology",
        "pe_ratio": 28.5,
        "market_cap": "₹7.8T",
        "typical_volume": 8_000_000,
        "rsi_base": 50,
        "volatility": 0.014
    },
    "HDFCBANK.NS": {
        "name": "HDFC Bank Limited",
        "base_price": 1785.00,
        "currency": "₹",
        "market": "India",
        "sector": "Banking",
        "pe_ratio": 19.2,
        "market_cap": "₹13.6T",
        "typical_volume": 12_000_000,
        "rsi_base": 55,
        "volatility": 0.013
    },
    "ICICIBANK.NS": {
        "name": "ICICI Bank Limited",
        "base_price": 1285.00,
        "currency": "₹",
        "market": "India",
        "sector": "Banking",
        "pe_ratio": 18.5,
        "market_cap": "₹9.0T",
        "typical_volume": 18_000_000,
        "rsi_base": 58,
        "volatility": 0.015
    },
    
    # Crypto
    "BTC-USD": {
        "name": "Bitcoin",
        "base_price": 106500.00,
        "currency": "$",
        "market": "Crypto",
        "sector": "Cryptocurrency",
        "pe_ratio": None,
        "market_cap": "$2.1T",
        "typical_volume": 35_000_000_000,
        "rsi_base": 65,
        "volatility": 0.035
    },
    "ETH-USD": {
        "name": "Ethereum",
        "base_price": 3950.00,
        "currency": "$",
        "market": "Crypto",
        "sector": "Cryptocurrency",
        "pe_ratio": None,
        "market_cap": "$475B",
        "typical_volume": 18_000_000_000,
        "rsi_base": 58,
        "volatility": 0.040
    },
    "BNB-USD": {
        "name": "Binance Coin",
        "base_price": 715.00,
        "currency": "$",
        "market": "Crypto",
        "sector": "Cryptocurrency",
        "pe_ratio": None,
        "market_cap": "$103B",
        "typical_volume": 1_500_000_000,
        "rsi_base": 52,
        "volatility": 0.038
    },
    "XRP-USD": {
        "name": "XRP",
        "base_price": 2.42,
        "currency": "$",
        "market": "Crypto",
        "sector": "Cryptocurrency",
        "pe_ratio": None,
        "market_cap": "$138B",
        "typical_volume": 8_000_000_000,
        "rsi_base": 68,
        "volatility": 0.055
    },
    "SOL-USD": {
        "name": "Solana",
        "base_price": 218.00,
        "currency": "$",
        "market": "Crypto",
        "sector": "Cryptocurrency",
        "pe_ratio": None,
        "market_cap": "$104B",
        "typical_volume": 4_500_000_000,
        "rsi_base": 62,
        "volatility": 0.050
    },
    
    # ETFs
    "SPY": {
        "name": "SPDR S&P 500 ETF",
        "base_price": 602.00,
        "currency": "$",
        "market": "ETF",
        "sector": "Index Fund",
        "pe_ratio": 24.5,
        "market_cap": "$585B",
        "typical_volume": 55_000_000,
        "rsi_base": 54,
        "volatility": 0.010
    },
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "base_price": 525.00,
        "currency": "$",
        "market": "ETF",
        "sector": "Tech Index",
        "pe_ratio": 32.8,
        "market_cap": "$298B",
        "typical_volume": 38_000_000,
        "rsi_base": 56,
        "volatility": 0.014
    },
    "DIA": {
        "name": "SPDR Dow Jones ETF",
        "base_price": 438.00,
        "currency": "$",
        "market": "ETF",
        "sector": "Index Fund",
        "pe_ratio": 21.2,
        "market_cap": "$35B",
        "typical_volume": 3_000_000,
        "rsi_base": 52,
        "volatility": 0.009
    },
    "IWM": {
        "name": "iShares Russell 2000",
        "base_price": 235.00,
        "currency": "$",
        "market": "ETF",
        "sector": "Small Cap",
        "pe_ratio": 18.5,
        "market_cap": "$72B",
        "typical_volume": 25_000_000,
        "rsi_base": 50,
        "volatility": 0.016
    },
    "VTI": {
        "name": "Vanguard Total Market",
        "base_price": 295.00,
        "currency": "$",
        "market": "ETF",
        "sector": "Total Market",
        "pe_ratio": 23.8,
        "market_cap": "$435B",
        "typical_volume": 4_000_000,
        "rsi_base": 53,
        "volatility": 0.011
    },
    
    # Europe
    "SAP.DE": {
        "name": "SAP SE",
        "base_price": 236.00,
        "currency": "€",
        "market": "Germany",
        "sector": "Technology",
        "pe_ratio": 38.5,
        "market_cap": "€275B",
        "typical_volume": 1_800_000,
        "rsi_base": 58,
        "volatility": 0.015
    },
    "ASML.AS": {
        "name": "ASML Holding",
        "base_price": 695.00,
        "currency": "€",
        "market": "Netherlands",
        "sector": "Technology",
        "pe_ratio": 42.1,
        "market_cap": "€273B",
        "typical_volume": 650_000,
        "rsi_base": 52,
        "volatility": 0.022
    },
    "OR.PA": {
        "name": "L'Oréal S.A.",
        "base_price": 338.00,
        "currency": "€",
        "market": "France",
        "sector": "Consumer",
        "pe_ratio": 32.8,
        "market_cap": "€179B",
        "typical_volume": 450_000,
        "rsi_base": 48,
        "volatility": 0.012
    },
    "SAN.MC": {
        "name": "Banco Santander",
        "base_price": 4.58,
        "currency": "€",
        "market": "Spain",
        "sector": "Banking",
        "pe_ratio": 7.2,
        "market_cap": "€72B",
        "typical_volume": 85_000_000,
        "rsi_base": 55,
        "volatility": 0.018
    },
    "HSBA.L": {
        "name": "HSBC Holdings",
        "base_price": 782.00,
        "currency": "£",
        "market": "UK",
        "sector": "Banking",
        "pe_ratio": 8.5,
        "market_cap": "£142B",
        "typical_volume": 22_000_000,
        "rsi_base": 54,
        "volatility": 0.014
    },
    
    # Commodities
    "GC=F": {
        "name": "Gold Futures",
        "base_price": 2655.00,
        "currency": "$",
        "market": "Commodities",
        "sector": "Precious Metals",
        "pe_ratio": None,
        "market_cap": None,
        "typical_volume": 180_000,
        "rsi_base": 58,
        "volatility": 0.012
    },
    "CL=F": {
        "name": "Crude Oil Futures",
        "base_price": 69.50,
        "currency": "$",
        "market": "Commodities",
        "sector": "Energy",
        "pe_ratio": None,
        "market_cap": None,
        "typical_volume": 450_000,
        "rsi_base": 45,
        "volatility": 0.025
    },
    "SI=F": {
        "name": "Silver Futures",
        "base_price": 30.25,
        "currency": "$",
        "market": "Commodities",
        "sector": "Precious Metals",
        "pe_ratio": None,
        "market_cap": None,
        "typical_volume": 85_000,
        "rsi_base": 52,
        "volatility": 0.020
    },
}

# ============================================================
# DEMO DATA GENERATOR
# ============================================================

class DemoDataEngine:
    """Generate realistic demo data based on time-seeded randomness."""
    
    def __init__(self):
        self.stocks = DEMO_STOCKS
    
    def _get_time_seed(self, symbol: str, interval: str = "1m") -> float:
        """Generate time-based seed for consistent data within time windows."""
        now = datetime.now()
        if interval == "1m":
            seed_time = now.replace(second=0, microsecond=0)
        elif interval == "5m":
            seed_time = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)
        elif interval == "1h":
            seed_time = now.replace(minute=0, second=0, microsecond=0)
        else:
            seed_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create deterministic seed from symbol + time
        seed_str = f"{symbol}:{seed_time.isoformat()}"
        return sum(ord(c) for c in seed_str) / 1000.0
    
    def _seeded_random(self, seed: float, index: int = 0) -> float:
        """Generate seeded random number between 0 and 1."""
        x = math.sin(seed * (index + 1) * 12.9898) * 43758.5453
        return x - math.floor(x)
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic quote data."""
        symbol = symbol.upper()
        stock = self.stocks.get(symbol)
        
        if not stock:
            # Generate generic data for unknown symbols
            stock = {
                "name": symbol,
                "base_price": 100.0,
                "currency": "$",
                "market": "US",
                "sector": "Unknown",
                "pe_ratio": 20.0,
                "market_cap": "10B",
                "typical_volume": 1_000_000,
                "rsi_base": 50,
                "volatility": 0.02
            }
        
        seed = self._get_time_seed(symbol, "1m")
        rand1 = self._seeded_random(seed, 1)
        rand2 = self._seeded_random(seed, 2)
        rand3 = self._seeded_random(seed, 3)
        
        # Calculate price with realistic movement
        volatility = stock["volatility"]
        change_pct = (rand1 - 0.5) * volatility * 100 * 2  # -vol% to +vol%
        
        base_price = stock["base_price"]
        price = base_price * (1 + change_pct / 100)
        change = price - base_price
        
        # OHLC
        day_range = base_price * volatility
        open_price = base_price * (1 + (rand2 - 0.5) * volatility)
        high_price = max(price, open_price) + day_range * rand3 * 0.5
        low_price = min(price, open_price) - day_range * (1 - rand3) * 0.5
        
        # Volume variation
        volume_mult = 0.7 + rand1 * 0.6  # 70% to 130% of typical
        volume = int(stock["typical_volume"] * volume_mult)
        
        return {
            "symbol": symbol,
            "name": stock["name"],
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "prev_close": round(base_price, 2),
            "volume": volume,
            "market": stock["market"],
            "currency": stock["currency"],
            "sector": stock.get("sector", "Unknown"),
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "DEMO",
            "source": "demo_data"
        }
    
    def get_signals(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic technical signals."""
        symbol = symbol.upper()
        stock = self.stocks.get(symbol, {"rsi_base": 50, "volatility": 0.02, "base_price": 100})
        
        seed = self._get_time_seed(symbol, "5m")
        rand1 = self._seeded_random(seed, 1)
        rand2 = self._seeded_random(seed, 2)
        rand3 = self._seeded_random(seed, 3)
        rand4 = self._seeded_random(seed, 4)
        
        # RSI with realistic distribution around base
        rsi_base = stock.get("rsi_base", 50)
        rsi = rsi_base + (rand1 - 0.5) * 30  # +/- 15 from base
        rsi = max(15, min(85, rsi))  # Clamp to realistic range
        
        # Determine signal from RSI
        if rsi < 30:
            signal = "BUY" if rand2 > 0.3 else "STRONG_BUY"
            confidence = 70 + rand3 * 20
        elif rsi > 70:
            signal = "SELL" if rand2 > 0.3 else "STRONG_SELL"
            confidence = 70 + rand3 * 20
        elif rsi < 45:
            signal = "BUY" if rand2 > 0.5 else "HOLD"
            confidence = 55 + rand3 * 20
        elif rsi > 55:
            signal = "SELL" if rand2 > 0.5 else "HOLD"
            confidence = 55 + rand3 * 20
        else:
            signal = "HOLD"
            confidence = 50 + rand3 * 15
        
        base_price = stock.get("base_price", 100)
        volatility = stock.get("volatility", 0.02)
        currency = stock.get("currency", "$")
        
        # VWAP (typically close to current price)
        vwap = base_price * (1 + (rand1 - 0.5) * 0.01)
        
        # MACD
        macd_value = (rand2 - 0.5) * 2 * volatility * base_price
        macd_signal = macd_value * (0.8 + rand3 * 0.4)
        macd_histogram = macd_value - macd_signal
        
        # Bollinger Bands
        bb_middle = vwap
        bb_width = base_price * volatility * 2
        bb_upper = bb_middle + bb_width
        bb_lower = bb_middle - bb_width
        
        # SMA
        sma20 = base_price * (1 + (rand4 - 0.5) * 0.02)
        sma50 = base_price * (1 + (rand3 - 0.5) * 0.03)
        
        # ATR
        atr = base_price * volatility * 1.5
        
        # Risk based on volatility and RSI
        if rsi < 25 or rsi > 75:
            risk = "HIGH"
        elif volatility > 0.03 or rsi < 35 or rsi > 65:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        
        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": round(confidence),
            "rsi": {
                "value": round(rsi, 1),
                "signal": "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
            },
            "vwap": {
                "value": round(vwap, 2),
                "signal": "Above" if base_price > vwap else "Below"
            },
            "macd": {
                "value": round(macd_value, 3),
                "signal": round(macd_signal, 3),
                "histogram": round(macd_histogram, 3)
            },
            "bollinger": {
                "upper": round(bb_upper, 2),
                "middle": round(bb_middle, 2),
                "lower": round(bb_lower, 2)
            },
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "atr": round(atr, 2),
            "risk": risk,
            "currency": currency,
            "timestamp": datetime.now().isoformat(),
            "dataQuality": "DEMO"
        }
    
    def get_history(self, symbol: str, interval: str = "1d", period: str = "1mo") -> Dict[str, Any]:
        """Generate realistic price history."""
        symbol = symbol.upper()
        stock = self.stocks.get(symbol, {"base_price": 100, "volatility": 0.02, "currency": "$"})
        
        base_price = stock.get("base_price", 100)
        volatility = stock.get("volatility", 0.02)
        currency = stock.get("currency", "$")
        
        # Determine number of candles based on period
        period_candles = {
            "1d": 78 if interval in ["1m", "5m"] else 24 if interval == "1h" else 1,
            "5d": 390 if interval == "1m" else 78 if interval == "5m" else 5,
            "1mo": 22,
            "3mo": 66,
            "6mo": 132,
            "1y": 252
        }
        num_candles = period_candles.get(period, 22)
        
        # Generate candles
        candles = []
        seed = self._get_time_seed(symbol, "1d")
        price = base_price
        
        for i in range(num_candles):
            rand1 = self._seeded_random(seed + i * 0.1, i)
            rand2 = self._seeded_random(seed + i * 0.1, i + 100)
            
            # Random walk with mean reversion
            drift = (rand1 - 0.5) * volatility * 2
            mean_reversion = (base_price - price) / base_price * 0.1
            change = drift + mean_reversion
            
            open_price = price
            close_price = price * (1 + change)
            high_price = max(open_price, close_price) * (1 + rand2 * volatility * 0.5)
            low_price = min(open_price, close_price) * (1 - (1 - rand2) * volatility * 0.5)
            
            # Volume
            volume = int(stock.get("typical_volume", 1000000) * (0.5 + rand1))
            
            # Timestamp
            if interval == "1d":
                timestamp = datetime.now() - timedelta(days=num_candles - i - 1)
            elif interval == "1h":
                timestamp = datetime.now() - timedelta(hours=num_candles - i - 1)
            else:
                timestamp = datetime.now() - timedelta(minutes=(num_candles - i - 1) * 5)
            
            candles.append({
                "timestamp": timestamp.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume
            })
            
            price = close_price
        
        return {
            "symbol": symbol,
            "interval": interval,
            "period": period,
            "candles": candles,
            "currency": currency,
            "dataQuality": "DEMO"
        }
    
    def get_screener_data(self) -> Dict[str, Any]:
        """Get full screener data for all demo stocks."""
        results = []
        
        categories = {
            "US Tech": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "AMD"],
            "India": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
            "Crypto": ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD"],
            "ETF": ["SPY", "QQQ", "DIA", "IWM", "VTI"],
            "Europe": ["SAP.DE", "ASML.AS", "OR.PA", "SAN.MC", "HSBA.L"]
        }
        
        for category, symbols in categories.items():
            for symbol in symbols:
                quote = self.get_quote(symbol)
                signals = self.get_signals(symbol)
                
                results.append({
                    "symbol": symbol,
                    "name": quote["name"],
                    "category": category,
                    "price": quote["price"],
                    "change_percent": quote["change_percent"],
                    "rsi": signals["rsi"]["value"],
                    "signal": signals["signal"],
                    "currency": quote["currency"],
                    "dataQuality": "DEMO"
                })
        
        # Categorize
        oversold = [r for r in results if r["rsi"] < 30]
        overbought = [r for r in results if r["rsi"] > 70]
        buy_signals = [r for r in results if r["signal"] in ["BUY", "STRONG_BUY"]]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "all": results,
            "oversold": oversold,
            "overbought": overbought,
            "buySignals": buy_signals,
            "systemStatus": "demo"
        }


# Singleton instance
demo_engine = DemoDataEngine()
