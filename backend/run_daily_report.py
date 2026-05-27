#!/usr/bin/env python3
"""
Daily data-quality report for AITraderIQ.

Boots the FastAPI app in-process (same as the test suite — no network needed
in DEMO_MODE) and hits every key endpoint, capturing the ACTUAL numbers so a
human reviewer can verify correctness at a glance.

Usage
-----
    # From backend/ directory:
    python run_daily_report.py

    # With live Render backend (skip in-process boot):
    BASE_URL=https://aitraderiq.onrender.com python run_daily_report.py

Output
------
    reports/YYYY-MM-DD.json   — machine-readable raw numbers
    reports/YYYY-MM-DD.html   — human-readable table report
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# ── Environment bootstrap (mirrors conftest.py) ──────────────────────────────
BASE_URL = os.getenv("BASE_URL", "")  # empty → in-process app
DEMO_MODE = not BASE_URL  # in-process always uses DEMO_MODE

if DEMO_MODE:
    os.environ.setdefault("DEMO_MODE", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "report-secret-key-not-for-production")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./report_temp.db")
    os.environ.setdefault("GROQ_API_KEY", "")


# ── HTTP client setup ─────────────────────────────────────────────────────────

async def _make_client():
    """Return an AsyncClient — either ASGI-backed or real HTTP."""
    from httpx import AsyncClient

    if BASE_URL:
        return AsyncClient(base_url=BASE_URL, timeout=30)

    # In-process: boot app + create tables
    from httpx import ASGITransport
    from main import app
    from database.engine import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Capture helpers ───────────────────────────────────────────────────────────

def _ok(r) -> bool:
    return r.status_code == 200


def _flag(val, condition: bool) -> str:
    """Return 'OK' or 'WARN' string for report."""
    return "OK" if condition else "WARN"


# ── Individual probe functions ────────────────────────────────────────────────

async def probe_quote(client, symbol: str) -> dict:
    r = await client.get(f"/api/v4/quote/{symbol}")
    if not _ok(r):
        return {"symbol": symbol, "status": r.status_code, "error": r.text[:120]}
    d = r.json()
    return {
        "symbol": symbol,
        "price": d.get("price"),
        "currency": d.get("currency"),
        "market": d.get("market"),
        "change_pct": d.get("change_pct"),
        "volume": d.get("volume"),
        "currency_ok": _flag(d, d.get("currency") == "₹"),
    }


async def probe_history(client, symbol: str) -> dict:
    r = await client.get(f"/api/v4/history/{symbol}?interval=1d&period=1mo")
    if not _ok(r):
        return {"symbol": symbol, "status": r.status_code, "candle_count": 0}
    d = r.json()
    candles = d if isinstance(d, list) else d.get("candles", d.get("data", []))
    first = candles[0] if candles else {}
    return {
        "symbol": symbol,
        "candle_count": len(candles),
        "first_open": first.get("open"),
        "first_close": first.get("close"),
        "has_ohlcv": _flag(first, all(k in first for k in ("open", "high", "low", "close"))),
    }


async def probe_signals(client, symbol: str) -> dict:
    r = await client.get(f"/api/v4/signals/{symbol}")
    if not _ok(r):
        return {"symbol": symbol, "status": r.status_code}
    d = r.json()
    rsi = d.get("rsi") or (d.get("signals", {}) or {}).get("rsi")
    signal = d.get("signal") or d.get("overall_signal")
    return {
        "symbol": symbol,
        "rsi": rsi,
        "signal": signal,
        "rsi_ok": _flag(rsi, rsi is None or 0 <= float(rsi) <= 100),
    }


async def probe_top_movers(client, market: str) -> dict:
    r = await client.get(f"/api/v4/top-movers/{market}?limit=5")
    if not _ok(r):
        return {"market": market, "status": r.status_code, "count": 0}
    d = r.json()
    gainers = d.get("gainers", [])
    losers = d.get("losers", [])
    movers = d.get("movers", [])
    all_syms = [m.get("ticker", m.get("symbol", "")) for m in gainers + losers + movers]
    return {
        "market": market,
        "gainers": len(gainers),
        "losers": len(losers),
        "movers": len(movers),
        "sample_symbols": all_syms[:5],
    }


async def probe_screener(client) -> dict:
    r = await client.get("/api/screener/universe")
    if not _ok(r):
        return {"status": r.status_code, "total": 0}
    d = r.json()
    all_stocks = d.get("all", [])
    categories = d.get("categories", [])
    india = [s for s in all_stocks if s.get("category") == "India"]
    bse = [s for s in all_stocks if s.get("category") == "India_BSE"]
    rsi_stocks = [s for s in all_stocks if s.get("rsi") is not None]

    # Sample RSI values from India category
    sample_rsi = [
        {"symbol": s["symbol"], "rsi": s["rsi"], "price": s.get("price")}
        for s in india[:5]
        if s.get("rsi") is not None
    ]

    return {
        "total_stocks": len(all_stocks),
        "categories": categories,
        "india_nse_count": len(india),
        "india_bse_count": len(bse),
        "rsi_covered": len(rsi_stocks),
        "india_nse_ok": _flag(india, len(india) >= 50),
        "india_bse_ok": _flag(bse, len(bse) >= 30),
        "sample_nse_rsi": sample_rsi,
        "sample_bse_symbols": [s["symbol"] for s in bse[:5]],
    }


async def probe_scanner(client, market: str, top_n: int = 5) -> dict:
    r = await client.get(f"/api/scanner/nifty50?top_n={top_n}&market={market}")
    if not _ok(r):
        return {"market": market, "status": r.status_code, "picks": []}
    d = r.json()
    picks = d.get("top_picks", [])
    return {
        "market": market,
        "success": d.get("success"),
        "market_bias": d.get("market_bias"),
        "session": d.get("session"),
        "pick_count": len(picks),
        "market_label": d.get("market", ""),
        "picks": [
            {
                "rank": p.get("rank"),
                "symbol": p.get("symbol"),
                "ai_score": p.get("ai_score"),
                "signal": p.get("signal"),
                "rsi": p.get("rsi"),
            }
            for p in picks
        ],
        "scores_ok": _flag(picks, all(0 <= (p.get("ai_score") or 0) <= 100 for p in picks)),
    }


async def probe_paper_trade(client) -> dict:
    """Register a fresh user, place NSE + BSE trades, close, get journal."""
    # Register
    reg = await client.post("/api/auth/register", json={
        "email": "report_probe@test.com",
        "username": "report_probe",
        "password": "ReportPass123!",
        "trader_style": "day",
    })
    if reg.status_code != 201:
        return {"error": f"register failed: {reg.status_code}", "trades": []}

    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    results = {"trades": [], "journal": {}}

    # Place trades
    for sym in ["RELIANCE.NS", "TCS.BO", "HDFCBANK.NS"]:
        r = await client.post(
            "/api/paper-trade",
            json={"symbol": sym, "side": "buy", "quantity": 1},
            headers=headers,
        )
        if r.status_code == 201:
            d = r.json()
            results["trades"].append({
                "symbol": sym,
                "entry_price": d.get("entry_price"),
                "currency": d.get("currency"),
                "market": d.get("market"),
                "trade_id": d.get("id"),
                "currency_ok": _flag(d, d.get("currency") == "₹"),
                "price_ok": _flag(d, (d.get("entry_price") or 0) > 100),
            })

    # Close all and get journal
    for t in results["trades"]:
        await client.post(f"/api/paper-trade/{t['trade_id']}/close", headers=headers)

    j = await client.get("/api/paper-trade/journal", headers=headers)
    if j.status_code == 200:
        jd = j.json()
        metrics = jd.get("metrics", {})
        jtrades = jd.get("trades", [])
        results["journal"] = {
            "total_closed": metrics.get("total_closed", len(jtrades)),
            "total_pnl": metrics.get("total_pnl") if metrics.get("total_pnl") is not None else metrics.get("total_realized_pnl"),
            "win_rate": metrics.get("win_rate"),
            "sample_trade_currencies": [t.get("currency") for t in jtrades[:3]],
        }

    return results


async def probe_auth(client) -> dict:
    """Basic auth flow: register, login, wrong password."""
    results = {}

    # Register
    reg = await client.post("/api/auth/register", json={
        "email": "auth_probe@test.com",
        "username": "auth_probe",
        "password": "AuthProbe123!",
        "trader_style": "swing",
    })
    results["register_status"] = reg.status_code
    results["register_has_token"] = "access_token" in (reg.json() if reg.status_code == 201 else {})

    # Login
    login = await client.post("/api/auth/login", data={
        "username": "auth_probe",
        "password": "AuthProbe123!",
    })
    results["login_status"] = login.status_code
    results["login_has_token"] = "access_token" in (login.json() if login.status_code == 200 else {})

    # Wrong password
    bad = await client.post("/api/auth/login", data={
        "username": "auth_probe",
        "password": "WrongPass999!",
    })
    results["wrong_pw_status"] = bad.status_code
    results["wrong_pw_rejected"] = _flag(bad, bad.status_code in (400, 401))

    # Profile (no auth)
    me = await client.get("/api/auth/me")
    results["profile_unauth_status"] = me.status_code
    results["profile_requires_auth"] = _flag(me, me.status_code in (401, 403))

    return results


# ── Main orchestrator ─────────────────────────────────────────────────────────

async def run_report() -> dict:
    client = await _make_client()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "date": str(date.today()),
        "mode": "DEMO" if DEMO_MODE else "LIVE",
        "base_url": BASE_URL or "in-process",
    }

    print("▶ Probing NSE quotes…")
    nse_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS"]
    report["nse_quotes"] = [await probe_quote(client, s) for s in nse_symbols]

    print("▶ Probing BSE quotes…")
    bse_symbols = ["RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "INFY.BO", "SBIN.BO"]
    report["bse_quotes"] = [await probe_quote(client, s) for s in bse_symbols]

    print("▶ Probing price history…")
    report["history"] = [
        await probe_history(client, "RELIANCE.NS"),
        await probe_history(client, "TCS.BO"),
    ]

    print("▶ Probing signals/RSI…")
    report["signals"] = [
        await probe_signals(client, "RELIANCE.NS"),
        await probe_signals(client, "TCS.NS"),
        await probe_signals(client, "HDFCBANK.BO"),
    ]

    print("▶ Probing top-movers…")
    report["top_movers"] = [
        await probe_top_movers(client, "INDIA"),
        await probe_top_movers(client, "INDIA_BSE"),
    ]

    print("▶ Probing screener universe…")
    report["screener"] = await probe_screener(client)

    print("▶ Probing NSE scanner…")
    report["nse_scanner"] = await probe_scanner(client, "NSE", top_n=10)

    print("▶ Probing BSE scanner…")
    report["bse_scanner"] = await probe_scanner(client, "BSE", top_n=10)

    print("▶ Probing paper trade flow…")
    report["paper_trade"] = await probe_paper_trade(client)

    print("▶ Probing auth flow…")
    report["auth"] = await probe_auth(client)

    await client.aclose()

    # Teardown temp DB
    if DEMO_MODE:
        try:
            from database.engine import engine
            async with engine.begin() as conn:
                from database.engine import Base
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
        db_path = Path("report_temp.db")
        if db_path.exists():
            db_path.unlink()

    return report


# ── Report writers ────────────────────────────────────────────────────────────

def _warn_class(val: str) -> str:
    return 'class="warn"' if val == "WARN" else ""


def write_html(report: dict, path: Path):
    today = report["date"]
    mode = report["mode"]
    ts = report["generated_at"]

    sections = []

    # NSE quotes table
    rows = ""
    for q in report.get("nse_quotes", []):
        err = q.get("error", "")
        price_cls = ""
        if q.get("price") and q["price"] < 100:
            price_cls = 'class="warn"'
        rows += (
            f"<tr><td>{q['symbol']}</td>"
            f'<td {price_cls}>{q.get("price", "—")}</td>'
            f"<td>{q.get('currency', '—')}</td>"
            f"<td>{q.get('market', '—')}</td>"
            f"<td>{q.get('change_pct', '—')}</td>"
            f'<td {_warn_class(q.get("currency_ok",""))}>{q.get("currency_ok","—")}</td>'
            f"<td>{err}</td></tr>\n"
        )
    sections.append(f"""
<h2>NSE Quotes</h2>
<table>
<tr><th>Symbol</th><th>Price (₹)</th><th>Currency</th><th>Market</th><th>Chg%</th><th>₹ OK?</th><th>Error</th></tr>
{rows}
</table>""")

    # BSE quotes table
    rows = ""
    for q in report.get("bse_quotes", []):
        err = q.get("error", "")
        price_cls = ""
        if q.get("price") and q["price"] < 100:
            price_cls = 'class="warn"'
        rows += (
            f"<tr><td>{q['symbol']}</td>"
            f'<td {price_cls}>{q.get("price", "—")}</td>'
            f"<td>{q.get('currency', '—')}</td>"
            f"<td>{q.get('market', '—')}</td>"
            f"<td>{q.get('change_pct', '—')}</td>"
            f'<td {_warn_class(q.get("currency_ok",""))}>{q.get("currency_ok","—")}</td>'
            f"<td>{err}</td></tr>\n"
        )
    sections.append(f"""
<h2>BSE Quotes</h2>
<table>
<tr><th>Symbol</th><th>Price (₹)</th><th>Currency</th><th>Market</th><th>Chg%</th><th>₹ OK?</th><th>Error</th></tr>
{rows}
</table>""")

    # Signals/RSI
    rows = ""
    for s in report.get("signals", []):
        rows += (
            f"<tr><td>{s['symbol']}</td>"
            f"<td>{s.get('rsi', '—')}</td>"
            f"<td>{s.get('signal', '—')}</td>"
            f'<td {_warn_class(s.get("rsi_ok",""))}>{s.get("rsi_ok","—")}</td></tr>\n'
        )
    sections.append(f"""
<h2>Signals / RSI</h2>
<table>
<tr><th>Symbol</th><th>RSI</th><th>Signal</th><th>RSI Valid?</th></tr>
{rows}
</table>""")

    # Price History
    rows = ""
    for h in report.get("history", []):
        rows += (
            f"<tr><td>{h['symbol']}</td>"
            f"<td>{h.get('candle_count', 0)}</td>"
            f"<td>{h.get('first_open', '—')}</td>"
            f"<td>{h.get('first_close', '—')}</td>"
            f'<td {_warn_class(h.get("has_ohlcv",""))}>{h.get("has_ohlcv","—")}</td></tr>\n'
        )
    sections.append(f"""
<h2>Price History (1-month daily)</h2>
<table>
<tr><th>Symbol</th><th>Candles</th><th>First Open</th><th>First Close</th><th>OHLCV OK?</th></tr>
{rows}
</table>""")

    # Screener
    sc = report.get("screener", {})
    rsi_rows = "".join(
        f"<tr><td>{s['symbol']}</td><td>{s['rsi']}</td><td>{s.get('price','—')}</td></tr>\n"
        for s in sc.get("sample_nse_rsi", [])
    )
    sections.append(f"""
<h2>Screener Universe</h2>
<table>
<tr><th>Metric</th><th>Value</th><th>Status</th></tr>
<tr><td>Total stocks</td><td>{sc.get('total_stocks','—')}</td><td>—</td></tr>
<tr><td>India (NSE) count</td><td>{sc.get('india_nse_count','—')}</td>
    <td {_warn_class(sc.get('india_nse_ok',''))}>{sc.get('india_nse_ok','—')}</td></tr>
<tr><td>India_BSE count</td><td>{sc.get('india_bse_count','—')}</td>
    <td {_warn_class(sc.get('india_bse_ok',''))}>{sc.get('india_bse_ok','—')}</td></tr>
<tr><td>Stocks with RSI</td><td>{sc.get('rsi_covered','—')}</td><td>—</td></tr>
<tr><td>Categories</td><td colspan="2">{', '.join(sc.get('categories',[]))}</td></tr>
<tr><td>Sample BSE symbols</td><td colspan="2">{', '.join(sc.get('sample_bse_symbols',[]))}</td></tr>
</table>
<h3>Sample NSE RSI values (manual sanity check)</h3>
<table>
<tr><th>Symbol</th><th>RSI</th><th>Price (₹)</th></tr>
{rsi_rows}
</table>""")

    # Scanner NSE
    nsc = report.get("nse_scanner", {})
    pick_rows = "".join(
        f"<tr><td>{p['rank']}</td><td>{p['symbol']}</td>"
        f"<td>{p.get('ai_score','—')}</td><td>{p.get('signal','—')}</td>"
        f"<td>{p.get('rsi','—')}</td></tr>\n"
        for p in nsc.get("picks", [])
    )
    bsc = report.get("bse_scanner", {})
    bpick_rows = "".join(
        f"<tr><td>{p['rank']}</td><td>{p['symbol']}</td>"
        f"<td>{p.get('ai_score','—')}</td><td>{p.get('signal','—')}</td>"
        f"<td>{p.get('rsi','—')}</td></tr>\n"
        for p in bsc.get("picks", [])
    )
    sections.append(f"""
<h2>Nifty 50 Scanner (NSE)</h2>
<p>Bias: <strong>{nsc.get('market_bias','—')}</strong> &nbsp;|&nbsp;
   Session: <strong>{nsc.get('session','—')}</strong> &nbsp;|&nbsp;
   Scores valid: <span {_warn_class(nsc.get('scores_ok',''))}>{nsc.get('scores_ok','—')}</span></p>
<table>
<tr><th>Rank</th><th>Symbol</th><th>AI Score</th><th>Signal</th><th>RSI</th></tr>
{pick_rows}
</table>
<h2>Sensex 30 Scanner (BSE)</h2>
<p>Bias: <strong>{bsc.get('market_bias','—')}</strong> &nbsp;|&nbsp;
   Session: <strong>{bsc.get('session','—')}</strong> &nbsp;|&nbsp;
   Scores valid: <span {_warn_class(bsc.get('scores_ok',''))}>{bsc.get('scores_ok','—')}</span></p>
<table>
<tr><th>Rank</th><th>Symbol</th><th>AI Score</th><th>Signal</th><th>RSI</th></tr>
{bpick_rows}
</table>""")

    # Paper Trade
    pt = report.get("paper_trade", {})
    trade_row_parts = []
    for t in pt.get("trades", []):
        price_cls = "" if (t.get("entry_price") or 0) > 100 else 'class="warn"'
        trade_row_parts.append(
            f"<tr><td>{t['symbol']}</td>"
            f"<td {price_cls}>{t.get('entry_price', '—')}</td>"
            f"<td>{t.get('currency', '—')}</td>"
            f"<td>{t.get('market', '—')}</td>"
            f"<td {_warn_class(t.get('currency_ok', ''))}>{t.get('currency_ok', '—')}</td>"
            f"<td {_warn_class(t.get('price_ok', ''))}>{t.get('price_ok', '—')}</td></tr>\n"
        )
    trade_rows = "".join(trade_row_parts)
    jnl = pt.get("journal", {})
    sections.append(f"""
<h2>Paper Trade Flow</h2>
<table>
<tr><th>Symbol</th><th>Entry Price (₹)</th><th>Currency</th><th>Market</th><th>₹ OK?</th><th>Price &gt;100?</th></tr>
{trade_rows}
</table>
<h3>Journal After Closing All Trades</h3>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total closed</td><td>{jnl.get('total_closed','—')}</td></tr>
<tr><td>Total P&amp;L</td><td>{jnl.get('total_pnl','—')}</td></tr>
<tr><td>Win rate</td><td>{jnl.get('win_rate','—')}</td></tr>
<tr><td>Trade currencies</td><td>{', '.join(str(c) for c in jnl.get('sample_trade_currencies',[]))}</td></tr>
</table>""")

    # Auth
    auth = report.get("auth", {})
    sections.append(f"""
<h2>Auth Flow</h2>
<table>
<tr><th>Check</th><th>Value</th><th>Status</th></tr>
<tr><td>Register status</td><td>{auth.get('register_status','—')}</td>
    <td {'class="warn"' if auth.get('register_status') != 201 else ''}>{
        'OK' if auth.get('register_status') == 201 else 'WARN'}</td></tr>
<tr><td>Register has token</td><td>{auth.get('register_has_token','—')}</td>
    <td {'class="warn"' if not auth.get('register_has_token') else ''}>{
        'OK' if auth.get('register_has_token') else 'WARN'}</td></tr>
<tr><td>Login status</td><td>{auth.get('login_status','—')}</td>
    <td {'class="warn"' if auth.get('login_status') != 200 else ''}>{
        'OK' if auth.get('login_status') == 200 else 'WARN'}</td></tr>
<tr><td>Wrong password status</td><td>{auth.get('wrong_pw_status','—')}</td>
    <td {_warn_class(auth.get('wrong_pw_rejected',''))}>{auth.get('wrong_pw_rejected','—')}</td></tr>
<tr><td>Unauth profile status</td><td>{auth.get('profile_unauth_status','—')}</td>
    <td {_warn_class(auth.get('profile_requires_auth',''))}>{auth.get('profile_requires_auth','—')}</td></tr>
</table>""")

    # Top movers
    rows = ""
    for tm in report.get("top_movers", []):
        rows += (
            f"<tr><td>{tm['market']}</td>"
            f"<td>{tm.get('gainers',0)}</td><td>{tm.get('losers',0)}</td><td>{tm.get('movers',0)}</td>"
            f"<td>{', '.join(tm.get('sample_symbols',[]))}</td></tr>\n"
        )
    sections.append(f"""
<h2>Top Movers</h2>
<table>
<tr><th>Market</th><th>Gainers</th><th>Losers</th><th>Movers</th><th>Sample Symbols</th></tr>
{rows}
</table>""")

    body = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AITraderIQ Daily Report — {today}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 1100px; margin: 20px auto; color: #1a1a1a; }}
  h1 {{ background: #1e3a5f; color: #fff; padding: 16px 24px; border-radius: 8px; }}
  h2 {{ color: #1e3a5f; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; margin-top: 36px; }}
  h3 {{ color: #2c5282; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; font-size: 0.9em; }}
  th {{ background: #1e3a5f; color: #fff; padding: 8px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #e8e8e8; }}
  tr:hover td {{ background: #f5f8ff; }}
  .warn {{ background: #fff3cd; color: #856404; font-weight: bold; }}
  p {{ color: #444; }}
  .meta {{ background: #f0f4fa; border-radius: 6px; padding: 10px 16px; margin-bottom: 24px; font-size: 0.9em; color: #555; }}
</style>
</head>
<body>
<h1>AITraderIQ Daily Data Quality Report</h1>
<div class="meta">
  <strong>Date:</strong> {today} &nbsp;|&nbsp;
  <strong>Generated:</strong> {ts} &nbsp;|&nbsp;
  <strong>Mode:</strong> {mode} &nbsp;|&nbsp;
  <strong>Source:</strong> {report['base_url']}
</div>
<p><em>Yellow cells = values that may need manual review. All prices should be in ₹ (Indian Rupees). RSI should be 0–100. AI scores should be 0–100.</em></p>
{body}
</body>
</html>"""

    path.write_text(html, encoding="utf-8")


def write_json(report: dict, path: Path):
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def print_summary(report: dict):
    print("\n" + "=" * 60)
    print(f"  AITraderIQ Daily Report — {report['date']}  ({report['mode']})")
    print("=" * 60)

    # NSE price spot-check
    print("\nNSE Quote Spot-Check:")
    for q in report.get("nse_quotes", []):
        price = q.get("price", "ERR")
        curr = q.get("currency", "?")
        warn = " ⚠ WARN" if q.get("currency_ok") == "WARN" else ""
        print(f"  {q['symbol']:20s} ₹{price:<10}  {curr}{warn}")

    print("\nBSE Quote Spot-Check:")
    for q in report.get("bse_quotes", []):
        price = q.get("price", "ERR")
        curr = q.get("currency", "?")
        warn = " ⚠ WARN" if q.get("currency_ok") == "WARN" else ""
        print(f"  {q['symbol']:20s} ₹{price:<10}  {curr}{warn}")

    sc = report.get("screener", {})
    print(f"\nScreener: {sc.get('india_nse_count',0)} NSE stocks, "
          f"{sc.get('india_bse_count',0)} BSE stocks, "
          f"{sc.get('rsi_covered',0)} with RSI")

    nsc = report.get("nse_scanner", {})
    print(f"\nNifty 50 Scanner: {nsc.get('pick_count',0)} picks, "
          f"bias={nsc.get('market_bias','?')}, session={nsc.get('session','?')}")
    for p in nsc.get("picks", [])[:5]:
        print(f"  #{p['rank']} {p['symbol']:15s} score={p.get('ai_score','?'):>5}  "
              f"signal={p.get('signal','?')}")

    bsc = report.get("bse_scanner", {})
    print(f"\nSensex 30 Scanner: {bsc.get('pick_count',0)} picks, "
          f"bias={bsc.get('market_bias','?')}, session={bsc.get('session','?')}")
    for p in bsc.get("picks", [])[:5]:
        print(f"  #{p['rank']} {p['symbol']:15s} score={p.get('ai_score','?'):>5}  "
              f"signal={p.get('signal','?')}")

    pt = report.get("paper_trade", {})
    print(f"\nPaper Trades placed and closed:")
    for t in pt.get("trades", []):
        warn = " ⚠" if t.get("currency_ok") == "WARN" or t.get("price_ok") == "WARN" else ""
        print(f"  {t['symbol']:15s} entry=₹{t.get('entry_price','?')}  "
              f"currency={t.get('currency','?')}{warn}")
    jnl = pt.get("journal", {})
    print(f"  Journal: {jnl.get('total_closed','?')} closed, "
          f"P&L={jnl.get('total_pnl','?')}, win_rate={jnl.get('win_rate','?')}")

    auth = report.get("auth", {})
    print(f"\nAuth: register={auth.get('register_status','?')}, "
          f"login={auth.get('login_status','?')}, "
          f"bad_pw={auth.get('wrong_pw_status','?')}, "
          f"unauth_profile={auth.get('profile_unauth_status','?')}")

    print("\n" + "=" * 60)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    today = str(date.today())
    json_path = reports_dir / f"{today}.json"
    html_path = reports_dir / f"{today}.html"

    report = await run_report()

    write_json(report, json_path)
    write_html(report, html_path)
    print_summary(report)

    print(f"\nReport saved:")
    print(f"  JSON → {json_path}")
    print(f"  HTML → {html_path}")


if __name__ == "__main__":
    # Add backend to sys.path when run directly
    sys.path.insert(0, str(Path(__file__).parent))
    asyncio.run(main())
