"""
Startup environment validation.
Imported by main.py to check critical config on boot.
"""

import os
import sys


def validate_environment():
    warnings = []
    errors = []

    # ── P0: Hard-fail on default JWT secret in production ──
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    demo_mode = os.getenv("DEMO_MODE", "true").lower()
    _jwt_defaults = {
        "",
        "change-this-in-production",
        "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32",
    }
    if jwt_secret in _jwt_defaults:
        if demo_mode != "true":
            errors.append(
                "CRITICAL: JWT_SECRET_KEY is not set or uses the insecure default. "
                "This is REQUIRED in production. Generate one with: openssl rand -hex 32"
            )
        else:
            warnings.append(
                "JWT_SECRET_KEY is not set or is using the default value. "
                "Generate one with: openssl rand -hex 32"
            )
    elif len(jwt_secret) < 32:
        warnings.append(
            "JWT_SECRET_KEY is shorter than 32 characters. "
            "Use a longer key for production: openssl rand -hex 32"
        )

    if demo_mode == "true":
        warnings.append("DEMO_MODE=true - using simulated data. Set DEMO_MODE=false for live market data.")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        warnings.append("GROQ_API_KEY not set - AI assistant will use rule-based fallback (still functional).")

    cors = os.getenv("CORS_ORIGINS", "")
    if "*" in cors:
        warnings.append("CORS_ORIGINS contains '*' - restrict to specific origins in production.")

    # ── Database check (warning only — SQLite is fine for small deployments) ──
    db_url = os.getenv("DATABASE_URL", "")
    if "sqlite" in db_url or not db_url:
        warnings.append(
            "Using SQLite database. For 100+ concurrent users, switch to PostgreSQL: "
            "DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/traderai"
        )

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        warnings.append("STRIPE_SECRET_KEY not set - payment features will run in demo mode.")

    for w in warnings:
        print(f"[ENV WARNING] {w}", file=sys.stderr)
    for e in errors:
        print(f"[ENV ERROR] {e}", file=sys.stderr)

    if errors:
        print("[ENV] Fatal configuration errors found. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"[ENV] Validation passed ({len(warnings)} warnings)")

    # ── Print API key status clearly so Render logs show it on every deploy ──
    td_key  = os.getenv("TWELVE_DATA_API_KEY", "")
    fh_key  = os.getenv("FINNHUB_API_KEY", "")
    sg_key  = os.getenv("SENDGRID_API_KEY", "")

    def _mask(k):
        if not k:
            return "NOT SET ❌"
        if len(k) <= 8:
            return "SET (short) ✓"
        return f"{k[:4]}...{k[-4:]} ✓"

    print("[API KEYS]")
    print(f"  TWELVE_DATA_API_KEY : {_mask(td_key)}")
    print(f"  FINNHUB_API_KEY     : {_mask(fh_key)}")
    print(f"  GROQ_API_KEY        : {'SET ✓' if groq_key else 'NOT SET ❌'}")
    print(f"  SENDGRID_API_KEY    : {'SET ✓' if sg_key else 'NOT SET (email alerts disabled)'}")
    print(f"  DATABASE_URL        : {'SET ✓' if db_url else 'NOT SET ❌ (using SQLite)'}")

