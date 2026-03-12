"""
Tests for phase2.models — Sentiment, Theme, AnalysisResult.
"""

import pytest
from phase2.models import Sentiment, Theme, AnalysisResult


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------

class TestSentiment:
    def test_valid_construction(self):
        s = Sentiment(positive=60, neutral=20, negative=20)
        assert s.positive == 60
        assert s.neutral == 20
        assert s.negative == 20

    def test_sums_to_100_exact(self):
        # should not raise
        Sentiment(positive=33, neutral=33, negative=34)

    def test_raises_if_sum_not_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            Sentiment(positive=50, neutral=30, negative=10)

    def test_raises_if_value_exceeds_100(self):
        with pytest.raises(ValueError, match="0-100"):
            Sentiment(positive=101, neutral=0, negative=0)

    def test_raises_if_value_negative(self):
        with pytest.raises(ValueError, match="0-100"):
            Sentiment(positive=-1, neutral=51, negative=50)

    def test_to_dict(self):
        s = Sentiment(positive=70, neutral=20, negative=10)
        assert s.to_dict() == {"positive": 70, "neutral": 20, "negative": 10}


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

class TestTheme:
    def test_valid_construction(self):
        t = Theme(theme="UX Issues", count=42, sentiment="negative", examples=["slow app"])
        assert t.theme == "UX Issues"
        assert t.count == 42
        assert t.sentiment == "negative"
        assert t.examples == ["slow app"]

    def test_empty_theme_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            Theme(theme="", count=1, sentiment="positive")

    def test_blank_theme_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            Theme(theme="   ", count=1, sentiment="positive")

    def test_negative_count_raises(self):
        with pytest.raises(ValueError, match="count"):
            Theme(theme="Bug", count=-1, sentiment="negative")

    def test_invalid_sentiment_raises(self):
        with pytest.raises(ValueError, match="sentiment"):
            Theme(theme="Bug", count=5, sentiment="mixed")

    def test_examples_default_empty(self):
        t = Theme(theme="Support", count=10, sentiment="neutral")
        assert t.examples == []

    def test_to_dict(self):
        t = Theme(theme="KYC", count=15, sentiment="negative", examples=["KYC fails"])
        d = t.to_dict()
        assert d == {
            "theme": "KYC",
            "count": 15,
            "sentiment": "negative",
            "examples": ["KYC fails"],
        }


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------

def _make_result(**overrides) -> AnalysisResult:
    defaults = dict(
        sentiment=Sentiment(positive=60, neutral=20, negative=20),
        themes=[Theme(theme="Speed", count=50, sentiment="negative")],
        summary="App has speed issues.",
        action_items=["Fix login lag"],
        review_count=100,
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


class TestAnalysisResult:
    def test_to_dict_structure(self):
        result = _make_result()
        d = result.to_dict()
        assert "sentiment" in d
        assert "themes" in d
        assert "summary" in d
        assert "action_items" in d
        assert "review_count" in d

    def test_to_dict_values(self):
        result = _make_result()
        d = result.to_dict()
        assert d["review_count"] == 100
        assert d["summary"] == "App has speed issues."
        assert d["action_items"] == ["Fix login lag"]

    def test_from_claude_json_basic(self):
        data = {
            "sentiment": {"positive": 60, "neutral": 20, "negative": 20},
            "themes": [
                {"theme": "UX", "count": 30, "sentiment": "negative", "examples": ["slow"]}
            ],
            "summary": "UX needs work.",
            "action_items": ["Improve UX"],
        }
        result = AnalysisResult.from_claude_json(data, review_count=80)
        assert result.review_count == 80
        assert result.sentiment.positive == 60
        assert len(result.themes) == 1
        assert result.themes[0].theme == "UX"
        assert result.summary == "UX needs work."
        assert result.action_items == ["Improve UX"]

    def test_from_claude_json_multiple_themes(self):
        data = {
            "sentiment": {"positive": 50, "neutral": 30, "negative": 20},
            "themes": [
                {"theme": "Speed", "count": 10, "sentiment": "negative", "examples": []},
                {"theme": "Support", "count": 5, "sentiment": "positive", "examples": ["great help"]},
            ],
            "summary": "Mixed reviews.",
            "action_items": [],
        }
        result = AnalysisResult.from_claude_json(data, review_count=50)
        assert len(result.themes) == 2

    def test_from_claude_json_missing_optional_fields(self):
        """Should handle missing action_items / themes gracefully."""
        data = {
            "sentiment": {"positive": 100, "neutral": 0, "negative": 0},
            "summary": "All good.",
        }
        result = AnalysisResult.from_claude_json(data, review_count=5)
        assert result.themes == []
        assert result.action_items == []

    def test_from_claude_json_invalid_sentiment_raises(self):
        """Propagates Sentiment validation error."""
        data = {
            "sentiment": {"positive": 50, "neutral": 50, "negative": 50},
            "themes": [],
            "summary": "x",
            "action_items": [],
        }
        with pytest.raises(ValueError, match="sum to 100"):
            AnalysisResult.from_claude_json(data, review_count=10)
