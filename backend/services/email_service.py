"""
Email service — SendGrid REST API wrapper.
Falls back to a no-op log when SENDGRID_API_KEY is not configured so the app
works without email during development.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

_SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "")
_FROM_EMAIL   = os.getenv("ALERT_FROM_EMAIL", "alerts@aitraderiq.com")
_FROM_NAME    = "AITraderIQ Alerts"
_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


async def send_price_alert_email(
    to_email: str,
    symbol: str,
    condition: str,
    target_value: float,
    current_price: float,
) -> bool:
    """Send a price-alert triggered email. Returns True on success."""
    if not _SENDGRID_KEY:
        logger.info(
            "SENDGRID_API_KEY not set — skipping email for %s %s %.2f",
            symbol, condition, target_value,
        )
        return False

    direction = "above" if condition in ("above",) else "below"
    subject = f"AITraderIQ Alert: {symbol} is {direction} ₹{target_value:,.2f}"
    body = f"""
<html><body style="font-family:sans-serif;background:#111;color:#ddd;padding:24px">
<h2 style="color:#22d3ee">Price Alert Triggered</h2>
<p>Your alert for <strong>{symbol}</strong> has been triggered.</p>
<table style="border-collapse:collapse;margin:16px 0">
  <tr><td style="padding:6px 12px;color:#9ca3af">Symbol</td>
      <td style="padding:6px 12px;font-weight:bold">{symbol}</td></tr>
  <tr><td style="padding:6px 12px;color:#9ca3af">Condition</td>
      <td style="padding:6px 12px">{condition.replace("_", " ").title()}</td></tr>
  <tr><td style="padding:6px 12px;color:#9ca3af">Target</td>
      <td style="padding:6px 12px">₹{target_value:,.2f}</td></tr>
  <tr><td style="padding:6px 12px;color:#9ca3af">Current Price</td>
      <td style="padding:6px 12px;color:#4ade80;font-weight:bold">₹{current_price:,.2f}</td></tr>
</table>
<p style="color:#6b7280;font-size:12px">
  This is an automated alert from AITraderIQ. Not financial advice.
  Trading involves risk of loss.
</p>
</body></html>
"""

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": _FROM_EMAIL, "name": _FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": body}],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _SENDGRID_URL,
                json=payload,
                headers={"Authorization": f"Bearer {_SENDGRID_KEY}"},
            )
        if resp.status_code in (200, 202):
            logger.info("Alert email sent to %s for %s", to_email, symbol)
            return True
        logger.warning("SendGrid returned %d for %s: %s", resp.status_code, to_email, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("SendGrid send failed: %s", exc)
        return False
