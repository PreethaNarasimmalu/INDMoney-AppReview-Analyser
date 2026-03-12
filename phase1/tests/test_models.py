"""
Tests for phase1.models — Review and FetchResult dataclasses.
"""

import pytest
from datetime import datetime, timezone
from phase1.models import Review, FetchResult


# ---------------------------------------------------------------------------
# Review.from_raw
# ---------------------------------------------------------------------------

def _raw(score=4, content="Great app", at=None, thumbs=2):
    if at is None:
        at = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    return {"score": score, "content": content, "at": at, "thumbsUpCount": thumbs}


class TestReviewFromRaw:
    def test_basic_fields(self):
        r = Review.from_raw(_raw(score=5, content="Love it", thumbs=10))
        assert r.rating == 5
        assert r.text == "Love it"
        assert r.thumbs_up == 10
        assert r.date == "2025-01-15"

    def test_naive_datetime_becomes_utc(self):
        naive_at = datetime(2025, 3, 1, 8, 30)
        r = Review.from_raw(_raw(at=naive_at))
        assert r.date == "2025-03-01"

    def test_aware_datetime_preserved(self):
        aware_at = datetime(2024, 12, 25, 0, 0, tzinfo=timezone.utc)
        r = Review.from_raw(_raw(at=aware_at))
        assert r.date == "2024-12-25"

    def test_missing_timestamp_raises(self):
        raw = _raw()
        raw["at"] = None
        with pytest.raises(ValueError, match="no timestamp"):
            Review.from_raw(raw)

    def test_zero_thumbs_default(self):
        raw = _raw()
        raw.pop("thumbsUpCount")
        r = Review.from_raw(raw)
        assert r.thumbs_up == 0

    def test_empty_content_default(self):
        raw = _raw()
        raw.pop("content")
        r = Review.from_raw(raw)
        assert r.text == ""

    def test_to_dict_round_trip(self):
        r = Review(rating=3, text="OK app", date="2025-02-10", thumbs_up=1)
        d = r.to_dict()
        assert d == {"rating": 3, "text": "OK app", "date": "2025-02-10", "thumbs_up": 1}


# ---------------------------------------------------------------------------
# FetchResult properties
# ---------------------------------------------------------------------------

class TestFetchResult:
    def _make_result(self, ratings: list[int]) -> FetchResult:
        reviews = [Review(rating=r, text="x", date="2025-01-01") for r in ratings]
        return FetchResult(app_id="com.test", weeks=8, max_count=1000, reviews=reviews)

    def test_count(self):
        fr = self._make_result([4, 5, 3])
        assert fr.count == 3

    def test_count_empty(self):
        fr = self._make_result([])
        assert fr.count == 0

    def test_avg_rating(self):
        fr = self._make_result([4, 5, 3])
        assert fr.avg_rating == pytest.approx(4.0)

    def test_avg_rating_empty(self):
        fr = self._make_result([])
        assert fr.avg_rating == 0.0

    def test_to_dicts(self):
        fr = self._make_result([5])
        dicts = fr.to_dicts()
        assert len(dicts) == 1
        assert dicts[0]["rating"] == 5
