"""
Tests for phase2.classifier.classify_reviews.

All Groq API calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from phase2.classifier import classify_reviews, _classify_batch
from phase2.models import Theme, ThemeList, ClassifiedReview
from phase2.config import CLASSIFIER_BATCH_SIZE

PATCH_CHAT = "phase2.classifier.chat"
PATCH_PARSE = "phase2.classifier.parse_json_response"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_themes(n: int = 3) -> ThemeList:
    return ThemeList(themes=[
        Theme(theme_id=i + 1, label=f"Theme {i + 1}", description=f"Desc {i + 1}")
        for i in range(n)
    ])


def _make_reviews(n: int) -> list[dict]:
    return [
        {"id": f"rev{i}", "date": "2026-01-01", "rating": 4, "clean_text": f"Review {i}"}
        for i in range(n)
    ]


def _groq_classifications(reviews: list[dict], theme_id: int = 1) -> dict:
    return {
        "classifications": [
            {"id": r["id"], "theme_id": theme_id}
            for r in reviews
        ]
    }


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestClassifyReviewsValidation:
    def test_empty_reviews_raises(self):
        with pytest.raises(ValueError, match="empty"):
            classify_reviews([], _make_themes(), MagicMock())

    def test_empty_themes_raises(self):
        with pytest.raises(ValueError, match="empty"):
            classify_reviews(_make_reviews(5), ThemeList(), MagicMock())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestClassifyReviewsHappyPath:
    def test_returns_classified_reviews(self):
        reviews = _make_reviews(3)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews, theme_id=1)):
            result = classify_reviews(reviews, _make_themes(), MagicMock())
        assert isinstance(result, list)
        assert all(isinstance(r, ClassifiedReview) for r in result)

    def test_returns_one_result_per_review(self):
        reviews = _make_reviews(5)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews, theme_id=2)):
            result = classify_reviews(reviews, _make_themes(), MagicMock())
        assert len(result) == 5

    def test_review_ids_preserved(self):
        reviews = _make_reviews(3)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews, theme_id=1)):
            result = classify_reviews(reviews, _make_themes(), MagicMock())
        returned_ids = {r.review_id for r in result}
        expected_ids = {r["id"] for r in reviews}
        assert returned_ids == expected_ids

    def test_theme_ids_valid(self):
        reviews = _make_reviews(4)
        themes = _make_themes(3)
        valid_ids = set(themes.ids())
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews, theme_id=2)):
            result = classify_reviews(reviews, themes, MagicMock())
        assert all(r.theme_id in valid_ids for r in result)


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

class TestClassifyReviewsBatching:
    def test_single_batch_for_small_input(self):
        reviews = _make_reviews(CLASSIFIER_BATCH_SIZE - 1)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews)):
            classify_reviews(reviews, _make_themes(), MagicMock())
        assert mock_chat.call_count == 1

    def test_two_batches_for_large_input(self):
        reviews = _make_reviews(CLASSIFIER_BATCH_SIZE + 1)
        batch1 = reviews[:CLASSIFIER_BATCH_SIZE]
        batch2 = reviews[CLASSIFIER_BATCH_SIZE:]
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, side_effect=[
                 _groq_classifications(batch1),
                 _groq_classifications(batch2),
             ]):
            result = classify_reviews(reviews, _make_themes(), MagicMock())
        assert mock_chat.call_count == 2
        assert len(result) == CLASSIFIER_BATCH_SIZE + 1

    def test_exact_batch_size_single_call(self):
        reviews = _make_reviews(CLASSIFIER_BATCH_SIZE)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_groq_classifications(reviews)):
            classify_reviews(reviews, _make_themes(), MagicMock())
        assert mock_chat.call_count == 1


# ---------------------------------------------------------------------------
# Invalid theme_id fallback
# ---------------------------------------------------------------------------

class TestClassifyReviewsInvalidThemeId:
    def test_invalid_theme_id_falls_back_to_first(self):
        reviews = _make_reviews(2)
        themes = _make_themes(3)
        bad_response = {
            "classifications": [
                {"id": reviews[0]["id"], "theme_id": 99},  # invalid
                {"id": reviews[1]["id"], "theme_id": 1},   # valid
            ]
        }
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=bad_response):
            result = classify_reviews(reviews, themes, MagicMock())
        fallback_id = themes.themes[0].theme_id
        assert result[0].theme_id == fallback_id
        assert result[1].theme_id == 1


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

class TestClassifyReviewsErrors:
    def test_api_error_propagates(self):
        with patch(PATCH_CHAT, side_effect=RuntimeError("Groq down")):
            with pytest.raises(RuntimeError, match="Groq down"):
                classify_reviews(_make_reviews(3), _make_themes(), MagicMock())
