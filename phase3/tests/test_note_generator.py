"""
Tests for phase3.note_generator — generate_summaries, generate_action_ideas.

All tests mock the Gemini client — no real API calls.
"""

import pytest
from unittest.mock import MagicMock, patch

from phase3.note_generator import generate_summaries, generate_action_ideas
from phase3.models import ThemeSummary
from phase3.config import TOP_N_THEMES

PATCH_CHAT = "phase3.note_generator.chat"
PATCH_PARSE = "phase3.note_generator.parse_json_response"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_top_themes(n: int = 3) -> list[dict]:
    return [
        {
            "id": i + 1,
            "label": f"Theme {i + 1}",
            "description": f"Description {i + 1}",
            "review_count": 10 - i,
        }
        for i in range(n)
    ]


def _make_reviews_by_theme(top_themes: list[dict]) -> dict[int, list[dict]]:
    return {
        t["id"]: [
            {
                "id": f"rev{t['id']}_{j}",
                "clean_text": f"Review text for theme {t['id']}, review {j}",
                "rating": 3,
                "platform": "Google Play",
            }
            for j in range(3)
        ]
        for t in top_themes
    }


def _valid_summary_json(n: int = 3) -> dict:
    return {
        "themes": [
            {
                "theme_id": i + 1,
                "summary": f"Summary for theme {i + 1}.",
                "representative_quote": f"Quote for theme {i + 1}.",
                "quote_rating": 3,
                "quote_platform": "Google Play",
            }
            for i in range(n)
        ]
    }


def _valid_action_json() -> dict:
    return {
        "action_ideas": [
            "Action 1: Fix the login flow",
            "Action 2: Improve app speed",
            "Action 3: Streamline KYC",
        ]
    }


# ---------------------------------------------------------------------------
# generate_summaries — input validation
# ---------------------------------------------------------------------------

class TestGenerateSummariesValidation:
    def test_empty_themes_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_summaries([], {}, MagicMock())

    def test_no_api_call_on_empty_themes(self):
        with patch(PATCH_CHAT) as mock_chat:
            with pytest.raises(ValueError):
                generate_summaries([], {}, MagicMock())
            mock_chat.assert_not_called()


# ---------------------------------------------------------------------------
# generate_summaries — happy path
# ---------------------------------------------------------------------------

class TestGenerateSummariesHappyPath:
    def test_returns_list_of_theme_summaries(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert isinstance(result, list)
        assert all(isinstance(ts, ThemeSummary) for ts in result)

    def test_returns_correct_count(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert len(result) == 3

    def test_theme_ids_correct(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert [ts.theme_id for ts in result] == [1, 2, 3]

    def test_summary_text_parsed(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert result[0].summary == "Summary for theme 1."

    def test_quote_parsed(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert result[0].representative_quote == "Quote for theme 1."

    def test_label_resolved_from_themes(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            result = generate_summaries(themes, reviews, MagicMock())
        assert result[0].label == "Theme 1"

    def test_quote_rating_clamped_above_5(self):
        themes = _make_top_themes(1)
        reviews = _make_reviews_by_theme(themes)
        data = {"themes": [{
            "theme_id": 1,
            "summary": "s",
            "representative_quote": "q",
            "quote_rating": 99,
            "quote_platform": "Google Play",
        }]}
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=data):
            result = generate_summaries(themes, reviews, MagicMock())
        assert result[0].quote_rating == 5

    def test_quote_rating_clamped_below_1(self):
        themes = _make_top_themes(1)
        reviews = _make_reviews_by_theme(themes)
        data = {"themes": [{
            "theme_id": 1,
            "summary": "s",
            "representative_quote": "q",
            "quote_rating": -3,
            "quote_platform": "Google Play",
        }]}
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=data):
            result = generate_summaries(themes, reviews, MagicMock())
        assert result[0].quote_rating == 1


# ---------------------------------------------------------------------------
# generate_summaries — count mismatch
# ---------------------------------------------------------------------------

class TestGenerateSummariesCountMismatch:
    def test_wrong_theme_count_raises(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_summary_json(2)):
            with pytest.raises(ValueError, match="3"):
                generate_summaries(themes, reviews, MagicMock())


# ---------------------------------------------------------------------------
# generate_summaries — error propagation
# ---------------------------------------------------------------------------

class TestGenerateSummariesErrors:
    def test_api_error_propagates(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, side_effect=RuntimeError("Gemini down")):
            with pytest.raises(RuntimeError, match="Gemini down"):
                generate_summaries(themes, reviews, MagicMock())

    def test_invalid_json_raises(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="not json"):
            with pytest.raises(Exception):
                generate_summaries(themes, reviews, MagicMock())


# ---------------------------------------------------------------------------
# generate_summaries — prompt content
# ---------------------------------------------------------------------------

class TestGenerateSummariesPrompt:
    def test_prompt_contains_theme_labels(self):
        themes = _make_top_themes(3)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_summary_json(3)):
            generate_summaries(themes, reviews, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]
        assert "Theme 1" in prompt_arg
        assert "Theme 2" in prompt_arg

    def test_prompt_contains_review_text(self):
        themes = _make_top_themes(1)
        reviews = _make_reviews_by_theme(themes)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_summary_json(1)):
            generate_summaries(themes, reviews, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]
        assert "Review text for theme 1" in prompt_arg

    def test_prompt_handles_empty_reviews_for_theme(self):
        themes = _make_top_themes(1)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_summary_json(1)):
            generate_summaries(themes, {}, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]
        assert "no reviews" in prompt_arg


# ---------------------------------------------------------------------------
# generate_action_ideas — input validation
# ---------------------------------------------------------------------------

class TestGenerateActionIdeasValidation:
    def test_empty_summaries_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_action_ideas([], MagicMock())

    def test_no_api_call_on_empty(self):
        with patch(PATCH_CHAT) as mock_chat:
            with pytest.raises(ValueError):
                generate_action_ideas([], MagicMock())
            mock_chat.assert_not_called()


# ---------------------------------------------------------------------------
# generate_action_ideas — happy path
# ---------------------------------------------------------------------------

def _make_summaries(n: int = 3) -> list[ThemeSummary]:
    return [
        ThemeSummary(
            theme_id=i + 1,
            label=f"Theme {i + 1}",
            summary=f"Summary {i + 1}",
            representative_quote=f"Quote {i + 1}",
            quote_rating=3,
            quote_platform="Google Play",
        )
        for i in range(n)
    ]


class TestGenerateActionIdeasHappyPath:
    def test_returns_list_of_strings(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_action_json()):
            result = generate_action_ideas(_make_summaries(3), MagicMock())
        assert isinstance(result, list)
        assert all(isinstance(a, str) for a in result)

    def test_returns_exactly_3(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_action_json()):
            result = generate_action_ideas(_make_summaries(3), MagicMock())
        assert len(result) == 3

    def test_action_text_parsed(self):
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=_valid_action_json()):
            result = generate_action_ideas(_make_summaries(3), MagicMock())
        assert result[0] == "Action 1: Fix the login flow"

    def test_wrong_count_raises(self):
        bad_json = {"action_ideas": ["Only one action"]}
        with patch(PATCH_CHAT, return_value="{}"), \
             patch(PATCH_PARSE, return_value=bad_json):
            with pytest.raises(ValueError, match="3"):
                generate_action_ideas(_make_summaries(3), MagicMock())


# ---------------------------------------------------------------------------
# generate_action_ideas — prompt content
# ---------------------------------------------------------------------------

class TestGenerateActionIdeasPrompt:
    def test_prompt_contains_summaries(self):
        summaries = _make_summaries(3)
        with patch(PATCH_CHAT, return_value="{}") as mock_chat, \
             patch(PATCH_PARSE, return_value=_valid_action_json()):
            generate_action_ideas(summaries, MagicMock())
        prompt_arg = mock_chat.call_args[0][1]
        assert "Summary 1" in prompt_arg
        assert "Theme 1" in prompt_arg

    def test_api_error_propagates(self):
        with patch(PATCH_CHAT, side_effect=RuntimeError("Gemini offline")):
            with pytest.raises(RuntimeError, match="Gemini offline"):
                generate_action_ideas(_make_summaries(3), MagicMock())
