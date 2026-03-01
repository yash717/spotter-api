"""
Brevo API email backend for Render.com compatibility.

Render blocks outbound SMTP (ports 25, 465, 587) on free tier.
Brevo's REST API uses HTTPS (port 443) and works on Render.
"""
import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoAPIEmailBackend(BaseEmailBackend):
    """
    Send email via Brevo's REST API instead of SMTP.
    Use when SMTP is blocked (e.g. Render free tier).
    """

    def __init__(self, api_key=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, "BREVO_API_KEY", None)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY is required for BrevoAPIEmailBackend")
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._send_one(message)
                sent += 1
            except Exception as e:
                logger.exception("Failed to send email via Brevo API: %s", e)
                if not self.fail_silently:
                    raise
        return sent

    def _send_one(self, message):
        from_addr = message.from_email
        from_name, from_email = parseaddr(from_addr)
        if not from_name and from_email:
            from_name = from_email.split("@")[0]

        html_content = None
        for alt in getattr(message, "alternatives", []) or []:
            if alt[1] == "text/html":
                html_content = alt[0]
                break

        payload = {
            "sender": {"name": from_name or "Spotter AI", "email": from_email},
            "to": [{"email": addr} for addr in message.to],
            "subject": message.subject,
            "textContent": message.body or "",
        }
        if html_content:
            payload["htmlContent"] = html_content

        resp = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={"api-key": self.api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
