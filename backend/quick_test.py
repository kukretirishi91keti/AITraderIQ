#!/usr/bin/env python3
"""
Quick Backend Verification Script
==================================
Run this BEFORE the full test suite to verify the backend is working.

Usage:
    python quick_test.py
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_endpoint(name, url):
    """Test a single endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"\nResponse preview:")
            print(json.dumps(data, indent=2)[:500] + "...")
            return True
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ FAILED - Cannot connect to backend")
        print(f"   Make sure backend is running: python app_complete.py")
        return False
    except Exception as e:
        print(f"❌ FAILED - {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("🚀 Quick Backend Verification")
    print("="*60)
    print(f"Testing backend at: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Health Check", f"{API_BASE}/api/health"),
        ("Quote - AAPL", f"{API_BASE}/api/v4/quote/AAPL"),
        ("Top Movers - US", f"{API_BASE}/api/v4/top-movers/US?limit=3"),
        ("Sentiment - AAPL", f"{API_BASE}/api/v4/sentiment/AAPL"),
    ]
    
    results = []
    for name, url in tests:
        results.append(test_endpoint(name, url))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(tests):
        status = "✅" if results[i] else "❌"
        print(f"{status} {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All quick tests passed!")
        print("You can now run the full test suite:")
        print("   python test_backend_endpoints.py")
    else:
        print("\n⚠️  Some tests failed.")
        print("Make sure:")
        print("   1. Backend is running (python app_complete.py)")
        print("   2. Using the updated app_complete.py (v5.7.3)")
        print("   3. No errors in backend console")

if __name__ == "__main__":
    main()
