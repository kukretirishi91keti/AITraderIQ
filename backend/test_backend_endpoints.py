#!/usr/bin/env python3
"""
Backend Endpoint Tester for TraderAI Pro v5.7.0
================================================

Tests all critical endpoints to verify backend is working correctly.
Run this BEFORE implementing frontend fixes.

Usage:
    python test_backend_endpoints.py
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List

# Configuration
API_BASE = "http://localhost:8000"
TIMEOUT = 10  # seconds

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"{status} {name}")
    if details:
        print(f"     {Colors.YELLOW}{details}{Colors.RESET}")

def test_endpoint(name: str, url: str, expected_keys: List[str] = None) -> Dict[str, Any]:
    """Generic endpoint tester"""
    full_url = f"{API_BASE}{url}"
    
    try:
        print(f"\n{Colors.BLUE}Testing: {Colors.RESET}{name}")
        print(f"  URL: {full_url}")
        
        response = requests.get(full_url, timeout=TIMEOUT)
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            print_test(name, False, f"HTTP {response.status_code}")
            return {"passed": False, "error": f"HTTP {response.status_code}"}
        
        data = response.json()
        
        # Check expected keys
        if expected_keys:
            missing_keys = [k for k in expected_keys if k not in data]
            if missing_keys:
                print_test(name, False, f"Missing keys: {missing_keys}")
                return {"passed": False, "error": f"Missing keys: {missing_keys}", "data": data}
        
        print_test(name, True, f"Response keys: {list(data.keys())[:5]}...")
        return {"passed": True, "data": data}
        
    except requests.exceptions.ConnectionError:
        print_test(name, False, "Backend not running! Start with: python app_complete.py")
        return {"passed": False, "error": "Connection refused"}
    except requests.exceptions.Timeout:
        print_test(name, False, f"Timeout after {TIMEOUT}s")
        return {"passed": False, "error": "Timeout"}
    except json.JSONDecodeError:
        print_test(name, False, "Invalid JSON response")
        return {"passed": False, "error": "Invalid JSON"}
    except Exception as e:
        print_test(name, False, str(e))
        return {"passed": False, "error": str(e)}

def test_health():
    """Test health endpoint"""
    print_header("1. HEALTH CHECK")
    result = test_endpoint(
        "Health Endpoint",
        "/api/health",
        ["status", "timestamp"]
    )
    
    if result["passed"]:
        data = result["data"]
        print(f"\n  System Status: {Colors.GREEN if data.get('status') == 'healthy' else Colors.RED}{data.get('status', 'unknown')}{Colors.RESET}")
        print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
    
    return result["passed"]

def test_top_movers():
    """Test top movers endpoints"""
    print_header("2. TOP MOVERS ENDPOINTS")
    
    markets = ["US", "India", "UK", "Germany", "Crypto", "ETF"]
    results = []
    
    for market in markets:
        result = test_endpoint(
            f"Top Movers - {market}",
            f"/api/v4/top-movers/{market}?limit=5",
            ["success", "market", "gainers", "losers"]
        )
        
        if result["passed"]:
            data = result["data"]
            gainers_count = len(data.get("gainers", []))
            losers_count = len(data.get("losers", []))
            print(f"     Gainers: {gainers_count}, Losers: {losers_count}")
            
            # Show sample
            if gainers_count > 0:
                sample = data["gainers"][0]
                print(f"     Sample: {sample.get('ticker', 'N/A')} {sample.get('changePercent', 0):+.2f}%")
        
        results.append(result["passed"])
    
    return all(results)

def test_screener():
    """Test screener endpoint"""
    print_header("3. SCREENER ENDPOINT")
    
    result = test_endpoint(
        "Screener Universe",
        "/api/screener/universe",
        ["timestamp"]
    )
    
    if result["passed"]:
        data = result["data"]
        
        # Check for categories
        categories = [k for k in data.keys() if k not in ["timestamp", "categories", "total_stocks", "source"]]
        print(f"\n  Categories found: {len(categories)}")
        print(f"  Categories: {', '.join(categories)}")
        
        # Check sample data
        for cat in categories[:2]:  # Check first 2 categories
            stocks = data.get(cat, [])
            if stocks and len(stocks) > 0:
                sample = stocks[0]
                print(f"\n  {cat} Sample:")
                print(f"    Symbol: {sample.get('symbol', 'N/A')}")
                print(f"    Price: {sample.get('price', 'N/A')}")
                print(f"    RSI: {sample.get('rsi', 'N/A')}")
                print(f"    Signal: {sample.get('signal', 'N/A')}")
    
    return result["passed"]

def test_financials():
    """Test financials endpoint"""
    print_header("4. FINANCIALS ENDPOINT")
    
    symbols = ["AAPL", "MSFT", "RELIANCE.NS"]
    results = []
    
    for symbol in symbols:
        result = test_endpoint(
            f"Financials - {symbol}",
            f"/api/v4/financials/{symbol}",
            ["symbol"]
        )
        
        if result["passed"]:
            data = result["data"]
            print(f"\n  {symbol}:")
            print(f"    Market Cap: {data.get('marketCap', 'N/A')}")
            print(f"    P/E Ratio: {data.get('peRatio', 'N/A')}")
            print(f"    Sector: {data.get('sector', 'N/A')}")
            
            # Check for AI summary
            if data.get('aiSummary'):
                print(f"    AI Summary: ✅ Present ({len(data['aiSummary'])} chars)")
            else:
                print(f"    AI Summary: ❌ Missing")
            
            # Check for recommendation
            if data.get('recommendation'):
                print(f"    Recommendation: {data['recommendation']}")
        
        results.append(result["passed"])
    
    return all(results)

def test_quote():
    """Test quote endpoint"""
    print_header("5. QUOTE ENDPOINT")
    
    result = test_endpoint(
        "Quote - AAPL",
        "/api/v4/quote/AAPL",
        ["symbol", "price"]
    )
    
    if result["passed"]:
        data = result["data"]
        print(f"\n  Symbol: {data.get('symbol', 'N/A')}")
        print(f"  Price: {data.get('price', 'N/A')}")
        print(f"  Change: {data.get('changePercent', 0):+.2f}%")
        print(f"  Data Quality: {data.get('dataQuality', 'N/A')}")
    
    return result["passed"]

def test_signals():
    """Test signals endpoint"""
    print_header("6. SIGNALS ENDPOINT")
    
    result = test_endpoint(
        "Signals - AAPL",
        "/api/v4/signals/AAPL",
        ["symbol"]
    )
    
    if result["passed"]:
        data = result["data"]
        print(f"\n  Symbol: {data.get('symbol', 'N/A')}")
        print(f"  RSI: {data.get('rsi', 'N/A')}")
        print(f"  MACD: {data.get('macd', 'N/A')}")
        print(f"  Recommendation: {data.get('recommendation', 'N/A')}")
    
    return result["passed"]

def test_history():
    """Test history endpoint"""
    print_header("7. HISTORY ENDPOINT")
    
    result = test_endpoint(
        "History - AAPL (1d)",
        "/api/v4/history/AAPL?interval=1d",
        ["symbol", "candles"]
    )
    
    if result["passed"]:
        data = result["data"]
        candles = data.get("candles", [])
        print(f"\n  Symbol: {data.get('symbol', 'N/A')}")
        print(f"  Candles: {len(candles)}")
        
        if candles and len(candles) > 0:
            sample = candles[-1]  # Latest candle
            print(f"  Latest:")
            print(f"    Date: {sample.get('date', 'N/A')}")
            print(f"    Close: {sample.get('close', 'N/A')}")
    
    return result["passed"]

def test_sentiment():
    """Test sentiment endpoint"""
    print_header("8. SENTIMENT ENDPOINT")
    
    result = test_endpoint(
        "Sentiment - AAPL",
        "/api/v4/sentiment/AAPL"
    )
    
    if result["passed"]:
        data = result["data"]
        overall = data.get("overall", {})
        print(f"\n  Overall Sentiment: {overall.get('sentiment', 'N/A')}")
        print(f"  Score: {overall.get('score', 'N/A')}")
        print(f"  Confidence: {overall.get('confidence', 'N/A')}")
        
        # Explain neutral
        score = overall.get('score', 0.5)
        if 0.4 <= score <= 0.6:
            print(f"  {Colors.YELLOW}ℹ️  This is NEUTRAL (score between 0.4-0.6){Colors.RESET}")
    
    return result["passed"]

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}TraderAI Pro Backend Endpoint Tester{Colors.RESET}")
    print(f"{Colors.CYAN}Testing backend at: {API_BASE}{Colors.RESET}")
    print(f"{Colors.CYAN}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    
    # Run all tests
    results = {
        "Health Check": test_health(),
        "Top Movers": test_top_movers(),
        "Screener": test_screener(),
        "Financials": test_financials(),
        "Quote": test_quote(),
        "Signals": test_signals(),
        "History": test_history(),
        "Sentiment": test_sentiment(),
    }
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✅{Colors.RESET}" if result else f"{Colors.RED}❌{Colors.RESET}"
        print(f"{status} {test_name}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.RESET}")
        print(f"{Colors.GREEN}Backend is ready. You can now apply frontend fixes.{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.RESET}")
        print(f"{Colors.RED}Fix backend issues before applying frontend fixes.{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit(main())
