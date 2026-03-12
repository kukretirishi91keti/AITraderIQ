"""
Startup environment validation.
Imported by main.py to check critical config on boot.
"""

import os
import sys


_INSECURE_JWT_VALUES = {
    "",
    "change-this-in-production",
    "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32",
}


def validate_environment():
    warnings = []
    errors = []

    is_demo = os.getenv("DEMO_MODE", "true").lower() == "true"

    # ---- Critical checks ----
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if jwt_secret in _INSECURE_JWT_VALUES:
        if is_demo:
            warnings.append("JWT_SECRET_KEY is not set — acceptable in DEMO_MODE only.")
        else:
            errors.append(
                "JWT_SECRET_KEY is not set or uses a default value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

    if jwt_secret and len(jwt_secret) < 32 and jwt_secret not in _INSECURE_JWT_VALUES:
        warnings.append("JWT_SECRET_KEY is shorter than 32 characters — consider a longer key.")

    # ---- Non-critical checks ----
    if is_demo:
        warnings.append("DEMO_MODE=true — using simulated data. Set DEMO_MODE=false for live market data.")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        warnings.append("GROQ_API_KEY not set — AI commentary will use rule-based fallback.")

    cors = os.getenv("CORS_ORIGINS", "")
    if "*" in cors:
        if is_demo:
            warnings.append("CORS_ORIGINS contains '*' — restrict origins in production.")
        else:
            errors.append("CORS_ORIGINS contains '*' — wildcard origins are not allowed in production.")

    # ---- Output ----
    for w in warnings:
        print(f"[ENV WARNING] {w}", file=sys.stderr)
    for e in errors:
        print(f"[ENV ERROR]   {e}", file=sys.stderr)

    if errors:
        print(f"[ENV] {len(errors)} fatal configuration error(s). Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"[ENV] Validation passed ({len(warnings)} warning(s))")
