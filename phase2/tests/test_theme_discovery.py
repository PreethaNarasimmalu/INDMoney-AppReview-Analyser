"""
Tests for phase2.theme_discovery.discover_themes.

All tests mock the Groq client — no real API calls.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from phase2.theme_discovery import discover_themes
from phase2.models import ThemeList
from phase2.config import MIN_THEMES, MAX_THEMES, MAX_REVIEWS_FOR_DISCOVERY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_reviews(n: int) -> list[dict]:
    return [
        {"id": f"id{i}", "date": "2026-01-01", "rating": 4, "clean_text": f"Review text {i}"}
        for i in range(n)
    ]


def _valid_groq_json(count: int = 3) -> dict:
    return {
        "themes": [
            {"theme_id": i + 1, "label": f"Theme {i + 1}", "description": f"Desc {i + 1}"}
            for i in range(count)
        ]
    }


def _mock_client(response: dict) -> MagicMock:
    """Mock Groq client whose chat() path returns JSON."""
    client = MagicMock()
    # patch groq_client.chat used inside theme_discovery
    return client


PATCH_CHAT = "phase2.theme_discovery.chat"
PATCH_PARSE = "phase2.theme_discovery.parse_json_response"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestDiscoverThemesValidation:
    def test_empty_reviews_raises(self):
        client = MagicMock()
        with pytest.raises(ValueError, match="empty"):
            discover_themes([], client)

    def test_no_api_call_on_empty_input(self):
        client = MagicMock()
        with patch(PATCH_CHAT) as mock_chat:
            with pytest.raises(ValueError):
                discover_themes([], client)
            mock_chat.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestDiscoverThemesHappyPath:
    def test_returns_theme_list(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            result = discover_themes(_make_reviews(10), MagicMock())
        assert isinstance(result, ThemeList)

    def test_correct_theme_count_3(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            result = discover_themes(_make_reviews(10), MagicMock())
        assert result.count == 3

    def test_correct_theme_count_5(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(5)):
            result = discover_themes(_make_reviews(10), MagicMock())
        assert result.count == 5

    def test_theme_labels_parsed(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            result = discover_themes(_make_reviews(5), MagicMock())
        assert result.themes[0].label == "Theme 1"

    def test_theme_ids_start_at_1(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            result = discover_themes(_make_reviews(5), MagicMock())
        assert result.ids() == [1, 2, 3]


# ---------------------------------------------------------------------------
# Theme count validation
# ---------------------------------------------------------------------------

class TestDiscoverThemesCountValidation:
    def test_too_few_themes_raises(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(MIN_THEMES - 1)):
            with pytest.raises(ValueError, match="themes"):
                discover_themes(_make_reviews(10), MagicMock())

    def test_too_many_themes_raises(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(MAX_THEMES + 1)):
            with pytest.raises(ValueError, match="themes"):
                discover_themes(_make_reviews(10), MagicMock())

    def test_exactly_min_themes_ok(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(MIN_THEMES)):
            result = discover_themes(_make_reviews(10), MagicMock())
        assert result.count == MIN_THEMES

    def test_exactly_max_themes_ok(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_groq_json(MAX_THEMES)):
            result = discover_themes(_make_reviews(10), MagicMock())
        assert result.count == MAX_THEMES


# ---------------------------------------------------------------------------
# Review capping
# ---------------------------------------------------------------------------

class TestDiscoverThemesReviewCap:
    def test_caps_reviews_sent_to_llm(self):
        reviews = _make_reviews(MAX_REVIEWS_FOR_DISCOVERY + 50)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            discover_themes(reviews, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]  # second positional arg = prompt
        # The prompt should mention MAX_REVIEWS_FOR_DISCOVERY as max_shown
        assert str(MAX_REVIEWS_FOR_DISCOVERY) in prompt_arg

    def test_all_reviews_below_cap_sent(self):
        reviews = _make_reviews(5)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_groq_json(3)):
            discover_themes(reviews, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]
        assert "Review text 0" in prompt_arg


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

class TestDiscoverThemesErrors:
    def test_invalid_json_raises(self):
        with patch(PATCH_CHAT, return_value="not json"):
            with pytest.raises(Exception):
                discover_themes(_make_reviews(5), MagicMock())

    def test_api_error_propagates(self):
        with patch(PATCH_CHAT, side_effect=RuntimeError("Groq down")):
            with pytest.raises(RuntimeError, match="Groq down"):
                discover_themes(_make_reviews(5), MagicMock())
