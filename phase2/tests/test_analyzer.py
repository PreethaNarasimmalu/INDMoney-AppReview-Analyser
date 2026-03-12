"""
Tests for phase2.analyzer.analyze.

All tests mock anthropic.Anthropic so no real API calls are made.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from phase1.models import Review, FetchResult
from phase2.analyzer import analyze, _strip_code_fence
from phase2.models import AnalysisResult
from phase2.config import CLAUDE_MODEL, MAX_TOKENS, MAX_REVIEWS_IN_PROMPT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_review(rating: int = 4, text: str = "Good app", date: str = "2026-01-01") -> Review:
    return Review(rating=rating, text=text, date=date, thumbs_up=0)


def _make_fetch_result(n: int = 5) -> FetchResult:
    reviews = [_make_review(rating=(i % 5) + 1, text=f"Review {i}") for i in range(n)]
    return FetchResult(app_id="in.indwealth", weeks=4, max_count=100, reviews=reviews)


_VALID_CLAUDE_JSON = {
    "sentiment": {"positive": 60, "neutral": 20, "negative": 20},
    "themes": [
        {"theme": "Performance", "count": 20, "sentiment": "negative", "examples": ["slow"]},
        {"theme": "UI", "count": 15, "sentiment": "positive", "examples": ["clean"]},
    ],
    "summary": "Users mostly happy but flag performance.",
    "action_items": ["Improve load times", "Fix KYC flow"],
}


def _mock_client(response_text: str) -> MagicMock:
    """Build a mock anthropic.Anthropic client returning response_text."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


# ---------------------------------------------------------------------------
# _strip_code_fence
# ---------------------------------------------------------------------------

class TestStripCodeFence:
    def test_no_fence_unchanged(self):
        assert _strip_code_fence('{"a": 1}') == '{"a": 1}'

    def test_strips_json_fence(self):
        fenced = "```json\n{\"a\": 1}\n```"
        assert _strip_code_fence(fenced) == '{"a": 1}'

    def test_strips_plain_fence(self):
        fenced = "```\n{\"a\": 1}\n```"
        assert _strip_code_fence(fenced) == '{"a": 1}'

    def test_handles_leading_trailing_whitespace(self):
        fenced = "  ```json\n{\"a\": 1}\n```  "
        assert _strip_code_fence(fenced) == '{"a": 1}'


# ---------------------------------------------------------------------------
# analyze — input validation
# ---------------------------------------------------------------------------

class TestAnalyzeValidation:
    def test_empty_fetch_result_raises(self):
        empty = FetchResult(app_id="in.indwealth", weeks=4, max_count=100, reviews=[])
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        with pytest.raises(ValueError, match="no reviews"):
            analyze(empty, client)

    def test_no_api_call_on_empty_input(self):
        empty = FetchResult(app_id="in.indwealth", weeks=4, max_count=100, reviews=[])
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        with pytest.raises(ValueError):
            analyze(empty, client)
        client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# analyze — happy path
# ---------------------------------------------------------------------------

class TestAnalyzeHappyPath:
    def test_returns_analysis_result(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(10), client)
        assert isinstance(result, AnalysisResult)

    def test_review_count_matches_fetch_result(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(7), client)
        assert result.review_count == 7

    def test_sentiment_parsed(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(5), client)
        assert result.sentiment.positive == 60
        assert result.sentiment.neutral == 20
        assert result.sentiment.negative == 20

    def test_themes_parsed(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(5), client)
        assert len(result.themes) == 2
        assert result.themes[0].theme == "Performance"

    def test_summary_parsed(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(5), client)
        assert result.summary == "Users mostly happy but flag performance."

    def test_action_items_parsed(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(_make_fetch_result(5), client)
        assert "Improve load times" in result.action_items

    def test_handles_code_fence_in_response(self):
        fenced = "```json\n" + json.dumps(_VALID_CLAUDE_JSON) + "\n```"
        client = _mock_client(fenced)
        result = analyze(_make_fetch_result(5), client)
        assert isinstance(result, AnalysisResult)


# ---------------------------------------------------------------------------
# analyze — Claude API call params
# ---------------------------------------------------------------------------

class TestAnalyzeApiCall:
    def test_calls_messages_create_once(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        analyze(_make_fetch_result(5), client)
        assert client.messages.create.call_count == 1

    def test_uses_correct_model(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        analyze(_make_fetch_result(5), client)
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == CLAUDE_MODEL

    def test_uses_correct_max_tokens(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        analyze(_make_fetch_result(5), client)
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == MAX_TOKENS

    def test_prompt_contains_review_text(self):
        fr = _make_fetch_result(3)
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        analyze(fr, client)
        messages = client.messages.create.call_args.kwargs["messages"]
        prompt_text = messages[0]["content"]
        assert "Review 0" in prompt_text

    def test_prompt_role_is_user(self):
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        analyze(_make_fetch_result(3), client)
        messages = client.messages.create.call_args.kwargs["messages"]
        assert messages[0]["role"] == "user"


# ---------------------------------------------------------------------------
# analyze — review cap
# ---------------------------------------------------------------------------

class TestAnalyzeReviewCap:
    def test_caps_reviews_in_prompt_at_max(self):
        """Even if fetch_result has more than MAX_REVIEWS_IN_PROMPT reviews,
        all of them contribute to review_count but only MAX_REVIEWS_IN_PROMPT
        appear in the prompt text."""
        n = MAX_REVIEWS_IN_PROMPT + 10
        fr = _make_fetch_result(n)
        client = _mock_client(json.dumps(_VALID_CLAUDE_JSON))
        result = analyze(fr, client)
        # review_count reflects actual total
        assert result.review_count == n
        # prompt should mention the cap
        messages = client.messages.create.call_args.kwargs["messages"]
        prompt_text = messages[0]["content"]
        assert str(MAX_REVIEWS_IN_PROMPT) in prompt_text


# ---------------------------------------------------------------------------
# analyze — error handling
# ---------------------------------------------------------------------------

class TestAnalyzeErrorHandling:
    def test_invalid_json_raises(self):
        client = _mock_client("this is not json")
        with pytest.raises(json.JSONDecodeError):
            analyze(_make_fetch_result(5), client)

    def test_invalid_sentiment_sum_raises(self):
        bad = {**_VALID_CLAUDE_JSON, "sentiment": {"positive": 50, "neutral": 50, "negative": 50}}
        client = _mock_client(json.dumps(bad))
        with pytest.raises(ValueError, match="sum to 100"):
            analyze(_make_fetch_result(5), client)

    def test_api_exception_propagates(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            analyze(_make_fetch_result(5), client)
