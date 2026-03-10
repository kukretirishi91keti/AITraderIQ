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
    if not jwt_secret or jwt_secret == "change-this-in-production":
        warnings.append("JWT_SECRET_KEY is not set or is using the default value. Set a strong secret for production.")

    demo_mode = os.getenv("DEMO_MODE", "true").lower()
    if demo_mode == "true":
        warnings.append("DEMO_MODE=true - using simulated data. Set DEMO_MODE=false for live market data.")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        warnings.append("GROQ_API_KEY not set - AI commentary will use rule-based fallback.")

    cors = os.getenv("CORS_ORIGINS", "")
    if "*" in cors:
        warnings.append("CORS_ORIGINS contains '*' - restrict origins in production.")

    for w in warnings:
        print(f"[ENV WARNING] {w}", file=sys.stderr)
    for e in errors:
        print(f"[ENV ERROR] {e}", file=sys.stderr)

    if errors:
        print("[ENV] Fatal configuration errors found. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"[ENV] Validation passed ({len(warnings)} warnings)")
