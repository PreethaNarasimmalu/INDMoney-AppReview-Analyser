"""
Tests for phase2.models — Theme, ThemeList, ClassifiedReview.
"""

import pytest
from phase2.models import Theme, ThemeList, ClassifiedReview


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

class TestTheme:
    def test_valid_construction(self):
        t = Theme(theme_id=1, label="Login Issues", description="Problems signing in")
        assert t.theme_id == 1
        assert t.label == "Login Issues"
        assert t.description == "Problems signing in"
        assert t.review_count == 0

    def test_review_count_set(self):
        t = Theme(theme_id=2, label="Speed", description="App performance", review_count=42)
        assert t.review_count == 42

    def test_empty_label_raises(self):
        with pytest.raises(ValueError, match="label"):
            Theme(theme_id=1, label="", description="desc")

    def test_blank_label_raises(self):
        with pytest.raises(ValueError, match="label"):
            Theme(theme_id=1, label="   ", description="desc")

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            Theme(theme_id=1, label="Label", description="")

    def test_zero_theme_id_raises(self):
        with pytest.raises(ValueError, match="theme_id"):
            Theme(theme_id=0, label="L", description="D")

    def test_negative_theme_id_raises(self):
        with pytest.raises(ValueError, match="theme_id"):
            Theme(theme_id=-1, label="L", description="D")

    def test_negative_review_count_raises(self):
        with pytest.raises(ValueError, match="review_count"):
            Theme(theme_id=1, label="L", description="D", review_count=-1)

    def test_to_dict(self):
        t = Theme(theme_id=3, label="KYC Delays", description="KYC issues", review_count=10)
        assert t.to_dict() == {
            "theme_id": 3,
            "label": "KYC Delays",
            "description": "KYC issues",
            "review_count": 10,
        }


# ---------------------------------------------------------------------------
# ThemeList
# ---------------------------------------------------------------------------

def _make_theme(theme_id: int, label: str = None) -> Theme:
    return Theme(
        theme_id=theme_id,
        label=label or f"Theme {theme_id}",
        description=f"Description {theme_id}",
    )


class TestThemeList:
    def test_empty_by_default(self):
        tl = ThemeList()
        assert tl.count == 0

    def test_count(self):
        tl = ThemeList(themes=[_make_theme(1), _make_theme(2)])
        assert tl.count == 2

    def test_by_id_found(self):
        tl = ThemeList(themes=[_make_theme(1), _make_theme(2)])
        assert tl.by_id(2).theme_id == 2

    def test_by_id_not_found(self):
        tl = ThemeList(themes=[_make_theme(1)])
        assert tl.by_id(99) is None

    def test_ids(self):
        tl = ThemeList(themes=[_make_theme(1), _make_theme(3)])
        assert tl.ids() == [1, 3]

    def test_to_list(self):
        tl = ThemeList(themes=[_make_theme(1)])
        result = tl.to_list()
        assert isinstance(result, list)
        assert result[0]["theme_id"] == 1

    def test_from_groq_json_basic(self):
        data = {
            "themes": [
                {"theme_id": 1, "label": "Login Issues", "description": "Sign-in problems"},
                {"theme_id": 2, "label": "App Speed", "description": "Performance issues"},
                {"theme_id": 3, "label": "KYC Delays", "description": "Verification issues"},
            ]
        }
        tl = ThemeList.from_groq_json(data)
        assert tl.count == 3
        assert tl.themes[0].label == "Login Issues"

    def test_from_groq_json_strips_whitespace(self):
        data = {"themes": [{"theme_id": 1, "label": "  Speed  ", "description": "  Fast  "}]}
        tl = ThemeList.from_groq_json(data)
        assert tl.themes[0].label == "Speed"
        assert tl.themes[0].description == "Fast"

    def test_from_groq_json_empty_themes(self):
        tl = ThemeList.from_groq_json({"themes": []})
        assert tl.count == 0

    def test_from_groq_json_missing_themes_key(self):
        tl = ThemeList.from_groq_json({})
        assert tl.count == 0


# ---------------------------------------------------------------------------
# ClassifiedReview
# ---------------------------------------------------------------------------

class TestClassifiedReview:
    def test_construction(self):
        cr = ClassifiedReview(review_id="abc123", theme_id=2)
        assert cr.review_id == "abc123"
        assert cr.theme_id == 2

    def test_to_dict(self):
        cr = ClassifiedReview(review_id="xyz", theme_id=1)
        assert cr.to_dict() == {"review_id": "xyz", "theme_id": 1}
