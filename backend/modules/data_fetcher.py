import yfinance as yf
import requests
import praw
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


class DataFetcher:
    def __init__(self):
        self.newsapi_key = os.getenv("NEWSAPI_KEY", "")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_KEY", "")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "DayTradingBot/1.0")

        self.reddit = None
        if self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent,
                )
            except Exception as e:
                print(f"Reddit API initialization failed: {e}")

    def get_ticker_data(
        self, symbol: str, period: str = "1d", interval: str = "1m"
    ) -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            if data.empty:
                return None
            return data
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def get_ticker_info(self, symbol: str) -> Dict:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info
        except Exception as e:
            print(f"Error fetching info for {symbol}: {e}")
            return {}

    def get_live_quote(self, symbol: str) -> Dict:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "change": info.get("regularMarketChange", 0),
                "change_percent": info.get("regularMarketChangePercent", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
                "market_cap": info.get("marketCap", 0),
                "day_high": info.get("dayHigh", 0),
                "day_low": info.get("dayLow", 0),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
            }
        except Exception as e:
            print(f"Error fetching live quote for {symbol}: {e}")
            return {
                "symbol": symbol,
                "price": 0,
                "change": 0,
                "change_percent": 0,
            }

    def get_top_gainers_losers(self, symbols: List[str]) -> Dict[str, List[Dict]]:
        quotes = []
        for symbol in symbols:
            quote = self.get_live_quote(symbol)
            if quote["price"] > 0:
                quotes.append(quote)

        sorted_quotes = sorted(quotes, key=lambda x: x["change_percent"], reverse=True)

        return {
            "gainers": sorted_quotes[:10],
            "losers": sorted_quotes[-10:][::-1],
        }

    def get_news(self, query: str = "stock market", days: int = 1) -> List[Dict]:
        if not self.newsapi_key or self.newsapi_key == "your_newsapi_key_here":
            return []

        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={query}&from={from_date}&sortBy=publishedAt"
                f"&language=en&apiKey={self.newsapi_key}"
            )

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                return [
                    {
                        "title": article["title"],
                        "description": article.get("description", ""),
                        "source": article["source"]["name"],
                        "url": article["url"],
                        "published_at": article["publishedAt"],
                    }
                    for article in articles[:20]
                ]
            else:
                print(f"NewsAPI error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def get_reddit_posts(self, subreddit: str = "wallstreetbets", limit: int = 50) -> List[Dict]:
        if not self.reddit:
            return []

        try:
            sub = self.reddit.subreddit(subreddit)
            posts = []

            for post in sub.hot(limit=limit):
                posts.append(
                    {
                        "title": post.title,
                        "selftext": post.selftext,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc,
                        "url": post.url,
                        "subreddit": subreddit,
                    }
                )

            return posts
        except Exception as e:
            print(f"Error fetching Reddit posts: {e}")
            return []

    def get_earnings_calendar(self, symbol: str) -> List[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            if calendar is not None and not calendar.empty:
                return calendar.to_dict()
            return {}
        except Exception as e:
            print(f"Error fetching earnings calendar for {symbol}: {e}")
            return {}

    def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            recommendations = ticker.recommendations
            if recommendations is not None and not recommendations.empty:
                return recommendations.tail(10)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching analyst recommendations for {symbol}: {e}")
            return pd.DataFrame()

    def get_institutional_holders(self, symbol: str) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            holders = ticker.institutional_holders
            if holders is not None and not holders.empty:
                return holders
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching institutional holders for {symbol}: {e}")
            return pd.DataFrame()

    def get_sp500_symbols(self) -> List[str]:
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_table = tables[0]
            symbols = sp500_table["Symbol"].tolist()
            return [s.replace(".", "-") for s in symbols[:100]]
        except Exception as e:
            print(f"Error fetching S&P 500 symbols: {e}")
            return [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "NVDA",
                "META",
                "TSLA",
                "BRK-B",
                "UNH",
                "JNJ",
                "XOM",
                "V",
                "WMT",
                "JPM",
                "LLY",
                "PG",
                "MA",
                "HD",
                "CVX",
                "MRK",
                "ABBV",
                "AVGO",
                "KO",
                "PEP",
                "COST",
                "ADBE",
                "MCD",
            ]

    def get_market_breadth(self, symbols: List[str]) -> Dict:
        advancing = 0
        declining = 0
        unchanged = 0

        for symbol in symbols:
            quote = self.get_live_quote(symbol)
            change = quote.get("change_percent", 0)

            if change > 0.1:
                advancing += 1
            elif change < -0.1:
                declining += 1
            else:
                unchanged += 1

        total = advancing + declining + unchanged

        return {
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "advance_decline_ratio": advancing / declining if declining > 0 else 0,
            "breadth_score": (advancing - declining) / total if total > 0 else 0,
        }

    def detect_unusual_volume(self, symbols: List[str]) -> List[Dict]:
        unusual = []

        for symbol in symbols:
            quote = self.get_live_quote(symbol)
            volume = quote.get("volume", 0)
            avg_volume = quote.get("avg_volume", 0)

            if avg_volume > 0 and volume > 0:
                volume_ratio = volume / avg_volume
                if volume_ratio > 2.0:
                    unusual.append(
                        {
                            "symbol": symbol,
                            "volume": volume,
                            "avg_volume": avg_volume,
                            "volume_ratio": volume_ratio,
                            "price": quote.get("price", 0),
                            "change_percent": quote.get("change_percent", 0),
                        }
                    )

        return sorted(unusual, key=lambda x: x["volume_ratio"], reverse=True)[:10]

    def detect_52_week_extremes(self, symbols: List[str]) -> Dict[str, List[Dict]]:
        highs = []
        lows = []

        for symbol in symbols:
            quote = self.get_live_quote(symbol)
            price = quote.get("price", 0)
            high_52w = quote.get("fifty_two_week_high", 0)
            low_52w = quote.get("fifty_two_week_low", 0)

            if price > 0 and high_52w > 0:
                pct_from_high = ((price - high_52w) / high_52w) * 100
                if pct_from_high > -1.0:
                    highs.append(
                        {
                            "symbol": symbol,
                            "price": price,
                            "fifty_two_week_high": high_52w,
                            "pct_from_high": pct_from_high,
                        }
                    )

            if price > 0 and low_52w > 0:
                pct_from_low = ((price - low_52w) / low_52w) * 100
                if pct_from_low < 1.0:
                    lows.append(
                        {
                            "symbol": symbol,
                            "price": price,
                            "fifty_two_week_low": low_52w,
                            "pct_from_low": pct_from_low,
                        }
                    )

        return {
            "highs": sorted(highs, key=lambda x: x["pct_from_high"], reverse=True)[:10],
            "lows": sorted(lows, key=lambda x: x["pct_from_low"])[:10],
        }
