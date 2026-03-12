"""
Tests for phase4.composer.compose.
"""

import pytest
from email.message import EmailMessage

from phase4.composer import compose, _escape_html
from phase4.config import EMAIL_SUBJECT_PREFIX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = """\
Weekly App Review Pulse — Week of 2026-03-09
─────────────────────────────────────────

TOP THEMES
  1. Login Issues — Users report frequent login failures after the recent update.
  2. App Speed — Startup time has increased significantly on older devices.
  3. KYC Delays — Verification is stuck for many users for over a week.

USER VOICES
  "I cannot login since the last update."  — Google Play, 1★
  "App takes 30 seconds to load now."  — Google Play, 2★
  "KYC stuck for 10 days with no response."  — Google Play, 2★

ACTION IDEAS
  1. Action 1: Fix the login regression introduced in the last release.
  2. Action 2: Profile and optimise app startup on Android devices.
  3. Action 3: Add automated KYC status notifications to reduce support load.
"""

def _compose(**kwargs) -> EmailMessage:
    defaults = dict(
        markdown=SAMPLE_MARKDOWN,
        week_label="Week of 2026-03-09",
        recipient_name="Product Team",
        recipient_email="product@indmoney.com",
        sender_address="sender@gmail.com",
    )
    defaults.update(kwargs)
    return compose(**defaults)


# ---------------------------------------------------------------------------
# Subject line
# ---------------------------------------------------------------------------

class TestComposeSubject:
    def test_subject_contains_prefix(self):
        msg = _compose()
        assert EMAIL_SUBJECT_PREFIX in msg["Subject"]

    def test_subject_contains_week_label(self):
        msg = _compose(week_label="Week of 2026-03-09")
        assert "Week of 2026-03-09" in msg["Subject"]

    def test_subject_format(self):
        msg = _compose(week_label="Week of 2026-03-09")
        assert msg["Subject"] == "INDMoney App Review Pulse — Week of 2026-03-09"


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------

class TestComposeHeaders:
    def test_from_header(self):
        msg = _compose(sender_address="me@gmail.com")
        assert "me@gmail.com" in msg["From"]

    def test_to_header_with_name(self):
        msg = _compose(recipient_name="Product Team", recipient_email="product@indmoney.com")
        assert "product@indmoney.com" in msg["To"]
        assert "Product Team" in msg["To"]

    def test_to_header_without_name(self):
        msg = _compose(recipient_name="", recipient_email="product@indmoney.com")
        assert msg["To"] == "product@indmoney.com"

    def test_to_header_name_whitespace_only(self):
        msg = _compose(recipient_name="   ", recipient_email="product@indmoney.com")
        assert msg["To"] == "product@indmoney.com"


# ---------------------------------------------------------------------------
# Body parts
# ---------------------------------------------------------------------------

class TestComposeBodyParts:
    def test_returns_email_message(self):
        msg = _compose()
        assert isinstance(msg, EmailMessage)

    def test_has_plain_text_part(self):
        msg = _compose()
        plain = msg.get_body(preferencelist=("plain",))
        assert plain is not None

    def test_has_html_part(self):
        msg = _compose()
        html = msg.get_body(preferencelist=("html",))
        assert html is not None

    def test_plain_text_contains_markdown(self):
        msg = _compose()
        plain = msg.get_body(preferencelist=("plain",))
        assert "TOP THEMES" in plain.get_content()

    def test_plain_text_contains_action_ideas(self):
        msg = _compose()
        plain = msg.get_body(preferencelist=("plain",))
        assert "ACTION IDEAS" in plain.get_content()

    def test_html_contains_markdown_content(self):
        msg = _compose()
        html = msg.get_body(preferencelist=("html",))
        assert "Login Issues" in html.get_content()

    def test_html_contains_section_titles(self):
        msg = _compose()
        html = msg.get_body(preferencelist=("html",))
        content = html.get_content()
        assert "Top Themes" in content
        assert "User Voices" in content
        assert "Action Ideas" in content

    def test_html_is_valid_html(self):
        msg = _compose()
        html = msg.get_body(preferencelist=("html",))
        content = html.get_content()
        assert "<html>" in content
        assert "</html>" in content


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestComposeValidation:
    def test_empty_markdown_raises(self):
        with pytest.raises(ValueError, match="markdown"):
            compose(
                markdown="",
                week_label="Week of 2026-03-09",
                recipient_name="Team",
                recipient_email="team@example.com",
                sender_address="me@gmail.com",
            )

    def test_whitespace_markdown_raises(self):
        with pytest.raises(ValueError, match="markdown"):
            compose(
                markdown="   ",
                week_label="Week of 2026-03-09",
                recipient_name="Team",
                recipient_email="team@example.com",
                sender_address="me@gmail.com",
            )

    def test_empty_recipient_email_raises(self):
        with pytest.raises(ValueError, match="recipient_email"):
            compose(
                markdown=SAMPLE_MARKDOWN,
                week_label="Week of 2026-03-09",
                recipient_name="Team",
                recipient_email="",
                sender_address="me@gmail.com",
            )

    def test_empty_sender_raises(self):
        with pytest.raises(ValueError, match="sender_address"):
            compose(
                markdown=SAMPLE_MARKDOWN,
                week_label="Week of 2026-03-09",
                recipient_name="Team",
                recipient_email="team@example.com",
                sender_address="",
            )


# ---------------------------------------------------------------------------
# HTML escaping
# ---------------------------------------------------------------------------

class TestEscapeHtml:
    def test_escapes_ampersand(self):
        assert _escape_html("a & b") == "a &amp; b"

    def test_escapes_less_than(self):
        assert _escape_html("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        assert _escape_html("a > b") == "a &gt; b"

    def test_no_special_chars_unchanged(self):
        assert _escape_html("hello world") == "hello world"

    def test_empty_string(self):
        assert _escape_html("") == ""

    def test_html_in_markdown_escaped(self):
        msg = compose(
            markdown="TOP THEMES\n  1. XSS Theme — Review with <script>alert('xss')</script> content here",
            week_label="Week of 2026-03-09",
            recipient_name="Team",
            recipient_email="team@example.com",
            sender_address="me@gmail.com",
        )
        html = msg.get_body(preferencelist=("html",))
        assert "<script>" not in html.get_content()
        assert "&lt;script&gt;" in html.get_content()


# ---------------------------------------------------------------------------
# Week label variations
# ---------------------------------------------------------------------------

class TestComposeWeekLabel:
    def test_different_week_labels(self):
        msg = _compose(week_label="Week of 2025-01-06")
        assert "Week of 2025-01-06" in msg["Subject"]

    def test_week_label_in_subject_only_once(self):
        msg = _compose(week_label="Week of 2026-03-09")
        assert msg["Subject"].count("Week of 2026-03-09") == 1
