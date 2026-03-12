"""
Tests for phase1.pii_scrubber — scrub() and scrub_reviews().
"""

import pytest
from phase1.pii_scrubber import scrub, scrub_reviews
from phase1.models import Review

REDACTED = "[REDACTED]"


# ---------------------------------------------------------------------------
# scrub() — individual pattern tests
# ---------------------------------------------------------------------------

class TestScrubEmail:
    def test_simple_email(self):
        assert REDACTED in scrub("Contact me at user@example.com please")

    def test_email_at_start(self):
        assert REDACTED in scrub("user@example.com is my mail")

    def test_email_at_end(self):
        assert REDACTED in scrub("my email is someone@gmail.com")

    def test_multiple_emails(self):
        result = scrub("a@b.com and c@d.org both removed")
        assert result.count(REDACTED) >= 2

    def test_no_false_positive_on_normal_text(self):
        text = "This app crashes when I open it"
        assert scrub(text) == text


class TestScrubPhone:
    def test_indian_10_digit(self):
        assert REDACTED in scrub("Call me at 9876543210 for help")

    def test_indian_with_plus91(self):
        assert REDACTED in scrub("My number is +919876543210")

    def test_indian_with_plus91_space(self):
        assert REDACTED in scrub("reach me at +91 9876543210")

    def test_does_not_redact_short_numbers(self):
        # 4-digit numbers (ratings, years) should not be redacted
        result = scrub("rated 4 stars in 2024")
        assert REDACTED not in result


class TestScrubURL:
    def test_http_url(self):
        assert REDACTED in scrub("see http://example.com for details")

    def test_https_url(self):
        assert REDACTED in scrub("visit https://indmoney.com/refer")

    def test_www_url(self):
        assert REDACTED in scrub("go to www.example.com")


class TestScrubUPI:
    def test_upi_id(self):
        assert REDACTED in scrub("send to 9876543210@ybl please")

    def test_upi_paytm(self):
        assert REDACTED in scrub("my upi is name@paytm")


class TestScrubGeneral:
    def test_text_without_pii_unchanged(self):
        text = "The app is great but login is slow."
        assert scrub(text) == text

    def test_empty_string(self):
        assert scrub("") == ""

    def test_only_pii(self):
        result = scrub("user@gmail.com")
        assert result == REDACTED

    def test_mixed_pii_and_text(self):
        result = scrub("Email user@x.com or call 9876543210 for support")
        assert "user@x.com" not in result
        assert "9876543210" not in result
        assert "for support" in result


# ---------------------------------------------------------------------------
# scrub_reviews() — list-level function
# ---------------------------------------------------------------------------

class TestScrubReviews:
    def _make_review(self, text: str, rating: int = 4, title: str = "") -> Review:
        return Review(rating=rating, text=text, date="2025-01-15", title=title)

    def test_returns_new_list(self):
        originals = [self._make_review("Clean text")]
        scrubbed = scrub_reviews(originals)
        assert scrubbed is not originals

    def test_original_reviews_not_mutated(self):
        text = "Email me at spy@evil.com"
        original = self._make_review(text)
        scrub_reviews([original])
        assert original.text == text  # unchanged

    def test_pii_removed_from_returned_reviews(self):
        reviews = [self._make_review("Contact spy@evil.com")]
        result = scrub_reviews(reviews)
        assert "spy@evil.com" not in result[0].text
        assert REDACTED in result[0].text

    def test_clean_review_passes_through_unchanged(self):
        reviews = [self._make_review("Great app, very fast!")]
        result = scrub_reviews(reviews)
        assert result[0].text == "Great app, very fast!"

    def test_rating_and_date_preserved(self):
        reviews = [self._make_review("spy@evil.com", rating=2)]
        result = scrub_reviews(reviews)
        assert result[0].rating == 2
        assert result[0].date == "2025-01-15"

    def test_empty_list(self):
        assert scrub_reviews([]) == []

    def test_multiple_reviews_all_scrubbed(self):
        reviews = [
            self._make_review("email me at a@b.com"),
            self._make_review("call 9876543210"),
            self._make_review("perfectly clean text"),
        ]
        result = scrub_reviews(reviews)
        assert "a@b.com" not in result[0].text
        assert "9876543210" not in result[1].text
        assert result[2].text == "perfectly clean text"

    def test_title_also_scrubbed(self):
        reviews = [self._make_review("some text", title="Contact spy@evil.com")]
        result = scrub_reviews(reviews)
        assert "spy@evil.com" not in result[0].title
        assert REDACTED in result[0].title

    def test_empty_title_stays_empty(self):
        reviews = [self._make_review("text", title="")]
        result = scrub_reviews(reviews)
        assert result[0].title == ""
