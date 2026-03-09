#!/usr/bin/env python3
"""
Backend Endpoint Verification Script
=====================================
Tests all critical endpoints to diagnose issues with chart, fundamentals, and screener.

Usage:
    python verify_backend.py
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"
SYMBOLS_TO_TEST = ["AAPL", "RELIANCE.NS", "BTC-USD"]

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_endpoint(name, url, expected_keys=None):
    """Test a single endpoint."""
    print(f"\n🔍 Testing: {name}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for expected keys
            if expected_keys:
                missing = [k for k in expected_keys if k not in data]
                if missing:
                    print(f"   ⚠️  Missing keys: {missing}")
                else:
                    print(f"   ✅ All expected keys present")
            
            # Show data structure
            if isinstance(data, dict):
                print(f"   Keys: {list(data.keys())[:10]}...")
            elif isinstance(data, list):
                print(f"   Array length: {len(data)}")
                if len(data) > 0:
                    print(f"   First item keys: {list(data[0].keys())}")
            
            return True, data
        else:
            print(f"   ❌ Failed: {response.text[:200]}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Backend not running on {API_BASE}")
        return False, None
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False, None

def main():
    """Run all tests."""
    print_header("TraderAI Pro Backend Verification")
    print(f"Testing backend at: {API_BASE}")
    print(f"Time: {datetime.now()}")
    
    results = {}
    
    # Test 1: Health Check
    print_header("1. HEALTH CHECK")
    success, data = test_endpoint(
        "Health",
        f"{API_BASE}/api/health",
        ["status"]
    )
    results['health'] = success
    
    # Test 2: History/Chart Endpoint
    print_header("2. CHART DATA (CRITICAL for fixing charts)")
    for symbol in SYMBOLS_TO_TEST:
        success, data = test_endpoint(
            f"History - {symbol}",
            f"{API_BASE}/api/v4/history/{symbol}?interval=1d",
            ["candles", "history", "data"]  # At least one of these should exist
        )
        
        if success and data:
            # Check data structure
            candles = data.get('candles') or data.get('history') or data.get('data')
            if candles:
                print(f"   📊 {len(candles)} candles found")
                if len(candles) > 0:
                    sample = candles[0]
                    print(f"   Sample candle keys: {list(sample.keys())}")
                    has_ohlc = all(k in sample for k in ['open', 'high', 'low', 'close'])
                    print(f"   Has OHLC data: {'✅' if has_ohlc else '❌'}")
            else:
                print(f"   ⚠️  No candles/history/data found in response!")
        
        results[f'history_{symbol}'] = success
        print()
    
    # Test 3: Financials Endpoint
    print_header("3. FUNDAMENTALS DATA")
    for symbol in SYMBOLS_TO_TEST:
        success, data = test_endpoint(
            f"Financials - {symbol}",
            f"{API_BASE}/api/v4/financials/{symbol}",
            ["symbol"]
        )
        
        if success and data:
            # Check for key financial metrics
            metrics = ['marketCap', 'peRatio', 'eps', 'revenue', 'sector']
            present = [m for m in metrics if m in data and data[m] not in [None, 'N/A']]
            print(f"   Metrics with data: {present}")
            
            if len(present) < 3:
                print(f"   ⚠️  Very few metrics have data - check backend implementation")
        
        results[f'financials_{symbol}'] = success
        print()
    
    # Test 4: Screener Endpoint
    print_header("4. SCREENER DATA")
    success, data = test_endpoint(
        "Screener Universe",
        f"{API_BASE}/api/screener/universe"
    )
    
    if success and data:
        # Count categories
        categories = [k for k in data.keys() if k not in ['timestamp', 'categories', 'total_stocks', 'source']]
        print(f"   Categories found: {len(categories)}")
        print(f"   Category names: {categories}")
        
        # Check sample stocks
        for cat in categories[:2]:
            stocks = data.get(cat, [])
            if stocks and len(stocks) > 0:
                sample = stocks[0]
                print(f"\n   {cat} - Sample stock:")
                print(f"      Keys: {list(sample.keys())}")
                has_required = all(k in sample for k in ['symbol', 'price', 'rsi', 'signal'])
                print(f"      Has required fields: {'✅' if has_required else '❌'}")
    
    results['screener'] = success
    
    # Summary
    print_header("SUMMARY")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    if not results.get('health'):
        print("\n⚠️  CRITICAL: Backend is not running!")
        print("   → Start your backend server on port 8000")
        print("   → Command: python main.py (or uvicorn main:app)")
    
    history_tests = [k for k in results.keys() if k.startswith('history_')]
    history_passed = sum(1 for k in history_tests if results[k])
    if history_passed < len(history_tests):
        print("\n⚠️  Chart endpoint issues detected")
        print("   → Charts will show 'Loading...' or 'No data'")
        print("   → Check backend /api/v4/history endpoint implementation")
    
    financials_tests = [k for k in results.keys() if k.startswith('financials_')]
    financials_passed = sum(1 for k in financials_tests if results[k])
    if financials_passed < len(financials_tests):
        print("\n⚠️  Fundamentals endpoint issues detected")
        print("   → Fundamentals tab will show N/A values")
        print("   → Check backend /api/v4/financials endpoint")
    
    if not results.get('screener'):
        print("\n⚠️  Screener endpoint issues detected")
        print("   → Screener will be empty or show demo data")
        print("   → Check backend /api/screener/universe endpoint")
    
    print("\n" + "=" * 70)
    print()

if __name__ == "__main__":
    main()
