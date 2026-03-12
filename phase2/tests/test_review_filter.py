"""
Tests for phase2.review_filter.filter_reviews.
"""

import pytest
from phase2.review_filter import (
    filter_reviews,
    _is_too_short,
    _is_low_signal,
    _is_all_caps_spam,
    _normalise,
)
from phase2.config import MIN_WORD_COUNT, MIN_ALPHA_RATIO, MAX_UPPERCASE_RATIO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _r(text: str, id: str = "r1") -> dict:
    return {"id": id, "clean_text": text, "rating": 3, "date": "2026-01-01"}


def _reviews(*texts) -> list[dict]:
    return [_r(t, f"r{i}") for i, t in enumerate(texts)]


# ---------------------------------------------------------------------------
# _is_too_short
# ---------------------------------------------------------------------------

class TestIsTooShort:
    def test_empty_string(self):
        assert _is_too_short("") is True

    def test_one_word(self):
        assert _is_too_short("Good") is True

    def test_four_words(self):
        assert _is_too_short("Good app I like") is True

    def test_exactly_min_words(self):
        words = " ".join(["word"] * MIN_WORD_COUNT)
        assert _is_too_short(words) is False

    def test_above_min_words(self):
        assert _is_too_short("This app is really great to use") is False

    def test_whitespace_only(self):
        assert _is_too_short("     ") is True


# ---------------------------------------------------------------------------
# _is_low_signal
# ---------------------------------------------------------------------------

class TestIsLowSignal:
    def test_emoji_only(self):
        assert _is_low_signal("👍👍👍👍👍") is True

    def test_numbers_only(self):
        assert _is_low_signal("12345 99999") is True

    def test_normal_text(self):
        assert _is_low_signal("This app crashes every time I open it") is False

    def test_empty_string(self):
        assert _is_low_signal("") is True

    def test_mixed_high_alpha(self):
        assert _is_low_signal("Great app! Love it 100%") is False

    def test_border_low(self):
        # exactly at MIN_ALPHA_RATIO — should NOT be filtered (ratio == threshold)
        # 4 alpha chars out of 10 total = 0.4 = MIN_ALPHA_RATIO (not strictly less)
        text = "abcd 23456"  # 4 alpha, 10 chars total → ratio = 0.4
        assert _is_low_signal(text) is False


# ---------------------------------------------------------------------------
# _is_all_caps_spam
# ---------------------------------------------------------------------------

class TestIsAllCapsSpam:
    def test_all_caps(self):
        assert _is_all_caps_spam("THIS APP IS TERRIBLE AND CRASHES ALL THE TIME") is True

    def test_normal_case(self):
        assert _is_all_caps_spam("This app is really good but needs improvement") is False

    def test_mixed_mostly_upper(self):
        assert _is_all_caps_spam("AAAAAAA b") is True

    def test_no_letters(self):
        # no letters → ratio 0.0 → not spam
        assert _is_all_caps_spam("12345 !!!") is False

    def test_single_uppercase_word(self):
        # one short all-caps word in a normal sentence
        assert _is_all_caps_spam("I love the UPI feature of this app it is great") is False

    def test_border_upper(self):
        # exactly at MAX_UPPERCASE_RATIO — should NOT be filtered (not strictly greater)
        # 8 upper out of 10 letters = 0.8 = MAX_UPPERCASE_RATIO (not greater than)
        assert _is_all_caps_spam("ABCDEFGH ij") is False


# ---------------------------------------------------------------------------
# _normalise
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_lowercases(self):
        assert _normalise("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert _normalise("  hello  ") == "hello"

    def test_collapses_spaces(self):
        assert _normalise("hello   world") == "hello world"

    def test_empty(self):
        assert _normalise("") == ""


# ---------------------------------------------------------------------------
# filter_reviews — happy path
# ---------------------------------------------------------------------------

class TestFilterReviewsHappyPath:
    def test_clean_reviews_all_kept(self):
        reviews = _reviews(
            "This app crashes every time I open it",
            "Really good investment guidance and cashback offers",
            "The KYC process is stuck and nobody is helping me",
        )
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 3
        assert stats["kept"] == 3
        assert stats["total"] == 3

    def test_returns_tuple(self):
        kept, stats = filter_reviews(_reviews("This is a good app overall"))
        assert isinstance(kept, list)
        assert isinstance(stats, dict)

    def test_empty_input(self):
        kept, stats = filter_reviews([])
        assert kept == []
        assert stats["total"] == 0
        assert stats["kept"] == 0


# ---------------------------------------------------------------------------
# filter_reviews — too short
# ---------------------------------------------------------------------------

class TestFilterReviewsTooShort:
    def test_short_review_removed(self):
        reviews = _reviews("Bad app", "This app is really great and useful for investing")
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_short"] == 1

    def test_all_short_removed(self):
        reviews = _reviews("Good", "Bad app", "Nice")
        kept, stats = filter_reviews(reviews)
        assert kept == []
        assert stats["removed_short"] == 3

    def test_exactly_min_words_kept(self):
        text = " ".join(["word"] * MIN_WORD_COUNT)
        kept, stats = filter_reviews([_r(text)])
        assert len(kept) == 1
        assert stats["removed_short"] == 0


# ---------------------------------------------------------------------------
# filter_reviews — low signal
# ---------------------------------------------------------------------------

class TestFilterReviewsLowSignal:
    def test_emoji_only_removed(self):
        # Use space-separated emojis so it passes word-count check but fails alpha ratio
        reviews = [
            _r("👍 👍 👍 👍 👍 👍", "r1"),
            _r("This app is very useful for tracking my investments", "r2"),
        ]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_low_signal"] == 1

    def test_numbers_only_removed(self):
        reviews = [_r("111 222 333 444 555", "r1")]
        kept, stats = filter_reviews(reviews)
        assert kept == []
        assert stats["removed_low_signal"] == 1


# ---------------------------------------------------------------------------
# filter_reviews — all caps spam
# ---------------------------------------------------------------------------

class TestFilterReviewsSpam:
    def test_all_caps_removed(self):
        reviews = [
            _r("THIS APP IS TERRIBLE CRASHES EVERY SINGLE TIME", "r1"),
            _r("This app is very useful for managing my portfolio", "r2"),
        ]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_spam"] == 1

    def test_normal_caps_kept(self):
        reviews = [_r("I use this App daily for SIP investments it is great", "r1")]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_spam"] == 0


# ---------------------------------------------------------------------------
# filter_reviews — duplicates
# ---------------------------------------------------------------------------

class TestFilterReviewsDuplicates:
    def test_exact_duplicate_removed(self):
        text = "This app is very useful for tracking my investments daily"
        reviews = [_r(text, "r1"), _r(text, "r2")]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_duplicate"] == 1

    def test_case_insensitive_duplicate_removed(self):
        reviews = [
            _r("This app is very useful for tracking my investments daily", "r1"),
            _r("this app is very useful for tracking my investments daily", "r2"),
        ]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_duplicate"] == 1

    def test_whitespace_normalised_duplicate_removed(self):
        reviews = [
            _r("This app is  very  useful for tracking investments", "r1"),
            _r("This app is very useful for tracking investments", "r2"),
        ]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 1
        assert stats["removed_duplicate"] == 1

    def test_similar_but_different_both_kept(self):
        reviews = [
            _r("This app is very useful for tracking my investments daily", "r1"),
            _r("This app is very useful for tracking my portfolio daily", "r2"),
        ]
        kept, stats = filter_reviews(reviews)
        assert len(kept) == 2
        assert stats["removed_duplicate"] == 0

    def test_first_occurrence_kept(self):
        text = "This app is very useful for all my investment tracking needs"
        reviews = [_r(text, "r1"), _r(text, "r2"), _r(text, "r3")]
        kept, stats = filter_reviews(reviews)
        assert kept[0]["id"] == "r1"
        assert stats["removed_duplicate"] == 2


# ---------------------------------------------------------------------------
# filter_reviews — stats completeness
# ---------------------------------------------------------------------------

class TestFilterReviewsStats:
    def test_stats_keys_present(self):
        _, stats = filter_reviews([])
        assert "total" in stats
        assert "kept" in stats
        assert "removed_short" in stats
        assert "removed_low_signal" in stats
        assert "removed_spam" in stats
        assert "removed_duplicate" in stats

    def test_kept_plus_removed_equals_total(self):
        reviews = [
            _r("bad", "r1"),                                           # too short
            _r("👍👍👍👍👍👍👍", "r2"),                               # low signal
            _r("THIS APP IS TOTALLY BROKEN AND CRASHES EVERY TIME", "r3"),  # spam
            _r("This app is great for all my investment needs daily", "r4"),
            _r("This app is great for all my investment needs daily", "r5"),  # dup
        ]
        kept, stats = filter_reviews(reviews)
        total_removed = (
            stats["removed_short"]
            + stats["removed_low_signal"]
            + stats["removed_spam"]
            + stats["removed_duplicate"]
        )
        assert stats["kept"] + total_removed == stats["total"]

    def test_review_fields_preserved(self):
        reviews = [_r("This app is very useful for tracking my investments", "r99")]
        kept, _ = filter_reviews(reviews)
        assert kept[0]["id"] == "r99"
        assert kept[0]["rating"] == 3
