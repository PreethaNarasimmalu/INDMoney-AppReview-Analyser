"""
Phase 4 — Email Sender.

Sends the weekly pulse email via Gmail SMTP (TLS on port 587).

Credentials loaded from .env:
  GMAIL_ADDRESS       — your Gmail address
  GMAIL_APP_PASSWORD  — 16-char Google App Password (not your login password)

IN:  EmailMessage from composer.compose()
OUT: Email sent to recipient
"""

import os
import re
import smtplib
from email.message import EmailMessage

from phase4.config import GMAIL_SMTP_HOST, GMAIL_SMTP_PORT


def _get_credentials() -> tuple[str, str, str]:
    """
    Load Gmail credentials from environment. Raises if missing.

    GMAIL_ADDRESS can be either:
      - plain email:        preethanarasimmalu19@gmail.com
      - with display name:  Preetha <preethanarasimmalu19@gmail.com>

    Returns (from_header, login_email, password).
    """
    raw = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if not raw:
        raise ValueError("GMAIL_ADDRESS environment variable is not set")
    if not password:
        raise ValueError("GMAIL_APP_PASSWORD environment variable is not set")

    # Extract bare email for SMTP login
    m = re.search(r"<(.+?)>", raw)
    login_email = m.group(1).strip() if m else raw

    return raw, login_email, password


def send_email(msg: EmailMessage) -> None:
    """
    Send an EmailMessage via Gmail SMTP.

    Args:
        msg: composed EmailMessage from composer.compose()

    Raises:
        ValueError: if Gmail credentials are missing from .env
        smtplib.SMTPException: if login or send fails
    """
    from_header, login_email, password = _get_credentials()

    if not msg["From"]:
        msg["From"] = from_header

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(login_email, password)
        smtp.send_message(msg)
