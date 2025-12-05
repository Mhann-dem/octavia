"""Email sending utilities for Octavia.

This module uses the `EMAIL_PROVIDER` and `EMAIL_API_KEY` environment variables.
If `EMAIL_PROVIDER` is `sendgrid` and `EMAIL_API_KEY` is set, it will POST to SendGrid.
Otherwise it prints the verification URL to stdout for dev.
"""
import os
import requests
from typing import Optional

SENDGRID_SEND_URL = "https://api.sendgrid.com/v3/mail/send"

EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "sendgrid")
EMAIL_API_KEY = os.environ.get("EMAIL_API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "octavia@example.com")


def send_verification_email(to_email: str, verify_url: str, subject: Optional[str] = None) -> bool:
    """Send a verification email. Returns True if sent (or printed), False on failure."""
    if not EMAIL_API_KEY or EMAIL_PROVIDER.lower() != "sendgrid":
        # Dev fallback: print link so developer can click it locally
        print(f"[DEV] Verification link for {to_email}: {verify_url}")
        return True

    payload = {
        "personalizations": [
            {"to": [{"email": to_email}], "subject": subject or "Verify your Octavia account"}
        ],
        "from": {"email": EMAIL_FROM},
        "content": [
            {"type": "text/plain", "value": f"Click to verify your account: {verify_url}"},
            {
                "type": "text/html",
                "value": f"<p>Click to verify your account:</p><p><a href=\"{verify_url}\">Verify account</a></p>",
            },
        ],
    }

    headers = {"Authorization": f"Bearer {EMAIL_API_KEY}", "Content-Type": "application/json"}

    try:
        r = requests.post(SENDGRID_SEND_URL, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 202):
            return True
        else:
            print(f"[EMAIL ERROR] SendGrid returned {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"[EMAIL ERROR] Exception sending email: {e}")
        return False
