"""
Startup environment validation.
Imported by main.py to check critical config on boot.
"""

import os
import sys


def validate_environment():
    warnings = []
    errors = []

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if not jwt_secret or jwt_secret in ("change-this-in-production", "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32"):
        warnings.append(
            "JWT_SECRET_KEY is not set or is using the default value. "
            "Generate one with: openssl rand -hex 32"
        )

    demo_mode = os.getenv("DEMO_MODE", "true").lower()
    if demo_mode == "true":
        warnings.append("DEMO_MODE=true - using simulated data. Set DEMO_MODE=false for live market data.")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        warnings.append("GROQ_API_KEY not set - AI assistant will use rule-based fallback (still functional).")

    cors = os.getenv("CORS_ORIGINS", "")
    if "*" in cors:
        warnings.append("CORS_ORIGINS contains '*' - restrict to specific origins in production.")

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
