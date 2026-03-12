"""
Phase 4 — Email Sender.

Creates a draft in the Gmail Drafts folder via IMAP APPEND.
Never auto-sends — the draft sits in Drafts for human review.

Credentials loaded from .env:
  GMAIL_ADDRESS       — your Gmail address
  GMAIL_APP_PASSWORD  — 16-char Google App Password (not your login password)

IN:  EmailMessage from composer.compose()
OUT: Draft in Gmail Drafts folder
"""

import imaplib
import os
import time
from email.message import EmailMessage

from phase4.config import GMAIL_IMAP_HOST, GMAIL_IMAP_PORT, GMAIL_DRAFTS_FOLDER


def _get_credentials() -> tuple[str, str]:
    """Load Gmail credentials from environment. Raises if missing."""
    address = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if not address:
        raise ValueError("GMAIL_ADDRESS environment variable is not set")
    if not password:
        raise ValueError("GMAIL_APP_PASSWORD environment variable is not set")
    return address, password


def create_draft(msg: EmailMessage) -> None:
    """
    Append an EmailMessage to the Gmail Drafts folder via IMAP.

    Args:
        msg: composed EmailMessage from composer.compose()

    Raises:
        ValueError: if Gmail credentials are missing from .env
        imaplib.IMAP4.error: if IMAP login or append fails
    """
    address, password = _get_credentials()

    imap = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)
    try:
        imap.login(address, password)
        imap.append(
            GMAIL_DRAFTS_FOLDER,
            "\\Draft",
            imaplib.Time2Internaldate(time.time()),
            msg.as_bytes(),
        )
    finally:
        try:
            imap.logout()
        except Exception:
            pass
