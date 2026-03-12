"""
Tests for phase4.sender — no real SMTP connections.
All network calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch
from email.message import EmailMessage

from phase4.sender import send_email, _get_credentials
from phase4.config import GMAIL_SMTP_HOST, GMAIL_SMTP_PORT

PATCH_SMTP = "phase4.sender.smtplib.SMTP"
PATCH_ENV = "phase4.sender.os.getenv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg() -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "INDMoney App Review Pulse — Week of 2026-03-09"
    msg["From"] = "sender@gmail.com"
    msg["To"] = "product@indmoney.com"
    msg.set_content("Weekly pulse plain text content here for testing purposes.")
    return msg


def _mock_env(address: str = "me@gmail.com", password: str = "app-pass-word-1234"):
    """Patch os.getenv to return test credentials."""
    def _getenv(key, default=""):
        return {"GMAIL_ADDRESS": address, "GMAIL_APP_PASSWORD": password}.get(key, default)
    return patch(PATCH_ENV, side_effect=_getenv)


def _make_smtp_mock():
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    return mock_smtp


# ---------------------------------------------------------------------------
# _get_credentials
# ---------------------------------------------------------------------------

class TestGetCredentials:
    def test_returns_address_and_password(self):
        with _mock_env("me@gmail.com", "secret1234"):
            addr, pwd = _get_credentials()
        assert addr == "me@gmail.com"
        assert pwd == "secret1234"

    def test_missing_address_raises(self):
        with _mock_env(address="", password="secret"):
            with pytest.raises(ValueError, match="GMAIL_ADDRESS"):
                _get_credentials()

    def test_missing_password_raises(self):
        with _mock_env(address="me@gmail.com", password=""):
            with pytest.raises(ValueError, match="GMAIL_APP_PASSWORD"):
                _get_credentials()

    def test_strips_whitespace(self):
        with _mock_env(address="  me@gmail.com  ", password="  secret  "):
            addr, pwd = _get_credentials()
        assert addr == "me@gmail.com"
        assert pwd == "secret"


# ---------------------------------------------------------------------------
# send_email — SMTP interactions
# ---------------------------------------------------------------------------

class TestSendEmail:
    def test_connects_to_gmail_smtp(self):
        mock_smtp = _make_smtp_mock()
        with patch(PATCH_SMTP, return_value=mock_smtp) as MockSMTP, _mock_env():
            send_email(_make_msg())
        MockSMTP.assert_called_once_with(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT)

    def test_starts_tls(self):
        mock_smtp = _make_smtp_mock()
        with patch(PATCH_SMTP, return_value=mock_smtp), _mock_env():
            send_email(_make_msg())
        mock_smtp.starttls.assert_called_once()

    def test_logs_in_with_credentials(self):
        mock_smtp = _make_smtp_mock()
        with patch(PATCH_SMTP, return_value=mock_smtp), \
             _mock_env("me@gmail.com", "myapppass"):
            send_email(_make_msg())
        mock_smtp.login.assert_called_once_with("me@gmail.com", "myapppass")

    def test_sends_message(self):
        mock_smtp = _make_smtp_mock()
        msg = _make_msg()
        with patch(PATCH_SMTP, return_value=mock_smtp), _mock_env():
            send_email(msg)
        mock_smtp.send_message.assert_called_once_with(msg)

    def test_missing_credentials_raises_before_smtp(self):
        with patch(PATCH_SMTP) as MockSMTP, _mock_env(address="", password=""):
            with pytest.raises(ValueError):
                send_email(_make_msg())
        MockSMTP.assert_not_called()

    def test_ehlo_called(self):
        mock_smtp = _make_smtp_mock()
        with patch(PATCH_SMTP, return_value=mock_smtp), _mock_env():
            send_email(_make_msg())
        assert mock_smtp.ehlo.call_count >= 1


# ---------------------------------------------------------------------------
# send_email — message content preserved
# ---------------------------------------------------------------------------

class TestSendEmailMessageContent:
    def test_subject_preserved(self):
        mock_smtp = _make_smtp_mock()
        msg = _make_msg()
        with patch(PATCH_SMTP, return_value=mock_smtp), _mock_env():
            send_email(msg)
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert "INDMoney App Review Pulse" in sent_msg["Subject"]

    def test_recipient_preserved(self):
        mock_smtp = _make_smtp_mock()
        msg = _make_msg()
        with patch(PATCH_SMTP, return_value=mock_smtp), _mock_env():
            send_email(msg)
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert "product@indmoney.com" in sent_msg["To"]
