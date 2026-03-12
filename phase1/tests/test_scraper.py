"""
Tests for phase1.scraper.fetch_reviews.

All tests mock google_play_scraper.reviews so no network calls are made.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, call

from phase1.scraper import fetch_reviews, _cutoff
from phase1.config import DEFAULT_MAX_REVIEWS, DEFAULT_WEEKS, BATCH_SIZE
from phase1.models import FetchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _raw_review(days_ago: int, score: int = 4, content: str = "Test review", thumbs: int = 0) -> dict:
    """Create a fake raw review dict as google-play-scraper would return it."""
    return {
        "score": score,
        "content": content,
        "at": _now() - timedelta(days=days_ago),
        "thumbsUpCount": thumbs,
    }


# ---------------------------------------------------------------------------
# _cutoff helper
# ---------------------------------------------------------------------------

class TestCutoff:
    def test_returns_aware_datetime(self):
        dt = _cutoff(8)
        assert dt.tzinfo is not None

    def test_is_in_the_past(self):
        dt = _cutoff(8)
        assert dt < _now()

    def test_approximate_weeks(self):
        dt = _cutoff(8)
        expected = _now() - timedelta(weeks=8)
        diff = abs((dt - expected).total_seconds())
        assert diff < 5  # within 5 seconds


# ---------------------------------------------------------------------------
# fetch_reviews — input validation
# ---------------------------------------------------------------------------

class TestFetchReviewsValidation:
    def test_empty_app_id_raises(self):
        with pytest.raises(ValueError, match="app_id"):
            fetch_reviews(app_id="")

    def test_blank_app_id_raises(self):
        with pytest.raises(ValueError, match="app_id"):
            fetch_reviews(app_id="   ")

    def test_zero_max_count_raises(self):
        with pytest.raises(ValueError, match="max_count"):
            fetch_reviews(app_id="com.test", max_count=0)

    def test_negative_max_count_raises(self):
        with pytest.raises(ValueError, match="max_count"):
            fetch_reviews(app_id="com.test", max_count=-1)

    def test_zero_weeks_raises(self):
        with pytest.raises(ValueError, match="weeks"):
            fetch_reviews(app_id="com.test", weeks=0)

    def test_negative_weeks_raises(self):
        with pytest.raises(ValueError, match="weeks"):
            fetch_reviews(app_id="com.test", weeks=-3)


# ---------------------------------------------------------------------------
# fetch_reviews — normal operation
# ---------------------------------------------------------------------------

PATCH_TARGET = "phase1.scraper.gp_reviews"


class TestFetchReviewsNormal:
    def test_returns_fetch_result(self):
        batch = [_raw_review(1), _raw_review(2)]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=10, weeks=8)
        assert isinstance(result, FetchResult)

    def test_result_carries_metadata(self):
        with patch(PATCH_TARGET, return_value=([], None)):
            result = fetch_reviews("com.example", max_count=500, weeks=6)
        assert result.app_id == "com.example"
        assert result.max_count == 500
        assert result.weeks == 6

    def test_reviews_within_window_are_collected(self):
        batch = [_raw_review(1), _raw_review(3), _raw_review(7)]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 3

    def test_empty_batch_returns_empty_result(self):
        with patch(PATCH_TARGET, return_value=([], None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 0

    def test_review_fields_are_mapped_correctly(self):
        raw = _raw_review(1, score=5, content="Excellent!", thumbs=42)
        with patch(PATCH_TARGET, return_value=([raw], None)):
            result = fetch_reviews("com.test", max_count=10, weeks=8)
        r = result.reviews[0]
        assert r.rating == 5
        assert r.text == "Excellent!"
        assert r.thumbs_up == 42


# ---------------------------------------------------------------------------
# fetch_reviews — date-window filtering
# ---------------------------------------------------------------------------

class TestFetchReviewsDateFilter:
    def test_old_reviews_excluded(self):
        """A review older than the window should stop ingestion."""
        batch = [
            _raw_review(1),           # within 8-week window
            _raw_review(60),          # ~8.5 weeks ago — outside
            _raw_review(61),          # even older
        ]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 1

    def test_exactly_on_cutoff_is_excluded(self):
        """A review exactly at the cutoff boundary is outside the window."""
        at_cutoff = _now() - timedelta(weeks=8, seconds=1)
        batch = [{"score": 3, "content": "Old", "at": at_cutoff, "thumbsUpCount": 0}]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 0

    def test_reviews_without_timestamp_are_skipped(self):
        batch = [
            {"score": 4, "content": "No date", "at": None, "thumbsUpCount": 0},
            _raw_review(2),
        ]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 1

    def test_naive_datetime_treated_as_utc(self):
        naive_at = datetime.utcnow() - timedelta(days=1)  # naive, recent
        batch = [{"score": 4, "content": "Naive dt", "at": naive_at, "thumbsUpCount": 0}]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        assert result.count == 1


# ---------------------------------------------------------------------------
# fetch_reviews — max_count cap
# ---------------------------------------------------------------------------

class TestFetchReviewsMaxCount:
    def test_respects_max_count(self):
        batch = [_raw_review(i + 1) for i in range(10)]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=5, weeks=8)
        assert result.count == 5

    def test_max_count_of_one(self):
        batch = [_raw_review(1), _raw_review(2), _raw_review(3)]
        with patch(PATCH_TARGET, return_value=(batch, None)):
            result = fetch_reviews("com.test", max_count=1, weeks=8)
        assert result.count == 1

    def test_batch_size_capped_at_batch_size_constant(self):
        """Each scraper call should request at most BATCH_SIZE reviews."""
        with patch(PATCH_TARGET, return_value=([], None)) as mock_gp:
            fetch_reviews("com.test", max_count=BATCH_SIZE + 50, weeks=8)
        first_call_kwargs = mock_gp.call_args_list[0].kwargs
        assert first_call_kwargs["count"] == BATCH_SIZE


# ---------------------------------------------------------------------------
# fetch_reviews — pagination
# ---------------------------------------------------------------------------

class TestFetchReviewsPagination:
    def test_follows_continuation_token(self):
        page1 = [_raw_review(1), _raw_review(2)]
        page2 = [_raw_review(3), _raw_review(4)]
        token = "tok123"

        with patch(PATCH_TARGET, side_effect=[(page1, token), (page2, None)]) as mock_gp:
            result = fetch_reviews("com.test", max_count=100, weeks=8)

        assert result.count == 4
        assert mock_gp.call_count == 2
        # second call should pass the token
        second_kwargs = mock_gp.call_args_list[1].kwargs
        assert second_kwargs["continuation_token"] == token

    def test_stops_when_no_continuation_token(self):
        page1 = [_raw_review(1)]
        with patch(PATCH_TARGET, return_value=(page1, None)) as mock_gp:
            fetch_reviews("com.test", max_count=100, weeks=8)
        assert mock_gp.call_count == 1

    def test_stops_when_old_review_encountered_mid_batch(self):
        """If an old review appears mid-batch, stop and don't fetch next page."""
        batch = [_raw_review(1), _raw_review(60)]  # second one is old
        with patch(PATCH_TARGET, return_value=(batch, "more_token")) as mock_gp:
            result = fetch_reviews("com.test", max_count=100, weeks=8)
        # Should have stopped after the old review; only one scraper call
        assert mock_gp.call_count == 1
        assert result.count == 1

    def test_multiple_pages_accumulate_correctly(self):
        pages = [
            ([_raw_review(i + 1) for i in range(5)], f"tok{p}")
            for p in range(3)
        ]
        pages.append(([_raw_review(16), _raw_review(17)], None))

        with patch(PATCH_TARGET, side_effect=pages):
            result = fetch_reviews("com.test", max_count=1000, weeks=8)

        assert result.count == 17  # 3*5 + 2


# ---------------------------------------------------------------------------
# fetch_reviews — defaults
# ---------------------------------------------------------------------------

class TestFetchReviewsDefaults:
    def test_default_app_id(self):
        with patch(PATCH_TARGET, return_value=([], None)) as mock_gp:
            fetch_reviews()
        assert mock_gp.call_args.args[0] == "com.indmoney"

    def test_default_max_count_and_weeks(self):
        with patch(PATCH_TARGET, return_value=([], None)) as mock_gp:
            result = fetch_reviews()
        assert result.max_count == DEFAULT_MAX_REVIEWS
        assert result.weeks == DEFAULT_WEEKS

    def test_default_lang_and_country(self):
        with patch(PATCH_TARGET, return_value=([], None)) as mock_gp:
            fetch_reviews()
        kwargs = mock_gp.call_args.kwargs
        assert kwargs["lang"] == "en"
        assert kwargs["country"] == "in"
