"""
Tests for phase4.sender — no real IMAP connections.
All network calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from email.message import EmailMessage

from phase4.sender import create_draft, _get_credentials
from phase4.config import GMAIL_IMAP_HOST, GMAIL_IMAP_PORT, GMAIL_DRAFTS_FOLDER

PATCH_IMAP = "phase4.sender.imaplib.IMAP4_SSL"
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
# create_draft — IMAP interactions
# ---------------------------------------------------------------------------

class TestCreateDraft:
    def test_connects_to_gmail_imap(self):
        mock_imap = MagicMock()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(_make_msg())
        # IMAP4_SSL called with correct host and port
        from phase4.sender import imaplib
        with patch(PATCH_IMAP) as MockIMAP, _mock_env():
            MockIMAP.return_value = mock_imap
            create_draft(_make_msg())
        MockIMAP.assert_called_once_with(GMAIL_IMAP_HOST, GMAIL_IMAP_PORT)

    def test_logs_in_with_credentials(self):
        mock_imap = MagicMock()
        with patch(PATCH_IMAP, return_value=mock_imap), \
             _mock_env("me@gmail.com", "myapppass"):
            create_draft(_make_msg())
        mock_imap.login.assert_called_once_with("me@gmail.com", "myapppass")

    def test_appends_to_drafts_folder(self):
        mock_imap = MagicMock()
        msg = _make_msg()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(msg)
        append_call = mock_imap.append.call_args
        assert append_call[0][0] == GMAIL_DRAFTS_FOLDER

    def test_appends_with_draft_flag(self):
        mock_imap = MagicMock()
        msg = _make_msg()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(msg)
        append_call = mock_imap.append.call_args
        assert "\\Draft" in append_call[0][1]

    def test_appends_message_bytes(self):
        mock_imap = MagicMock()
        msg = _make_msg()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(msg)
        append_call = mock_imap.append.call_args
        assert append_call[0][3] == msg.as_bytes()

    def test_logout_called_after_append(self):
        mock_imap = MagicMock()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(_make_msg())
        mock_imap.logout.assert_called_once()

    def test_logout_called_even_if_append_fails(self):
        mock_imap = MagicMock()
        mock_imap.append.side_effect = Exception("IMAP append failed")
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            with pytest.raises(Exception, match="IMAP append failed"):
                create_draft(_make_msg())
        mock_imap.logout.assert_called_once()

    def test_missing_credentials_raises_before_imap(self):
        with patch(PATCH_IMAP) as MockIMAP, _mock_env(address="", password=""):
            with pytest.raises(ValueError):
                create_draft(_make_msg())
        MockIMAP.assert_not_called()


# ---------------------------------------------------------------------------
# create_draft — message content preserved
# ---------------------------------------------------------------------------

class TestCreateDraftMessageContent:
    def test_subject_preserved_in_bytes(self):
        mock_imap = MagicMock()
        msg = _make_msg()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(msg)
        appended_bytes = mock_imap.append.call_args[0][3]
        assert b"INDMoney App Review Pulse" in appended_bytes

    def test_recipient_preserved_in_bytes(self):
        mock_imap = MagicMock()
        msg = _make_msg()
        with patch(PATCH_IMAP, return_value=mock_imap), _mock_env():
            create_draft(msg)
        appended_bytes = mock_imap.append.call_args[0][3]
        assert b"product@indmoney.com" in appended_bytes
