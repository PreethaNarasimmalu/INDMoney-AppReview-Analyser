"""
Tests for phase3.models — ThemeSummary, PulseNote.
"""

import pytest
from phase3.models import ThemeSummary, PulseNote


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(theme_id: int = 1, label: str = "Login Issues") -> ThemeSummary:
    return ThemeSummary(
        theme_id=theme_id,
        label=label,
        summary="Users frequently report problems logging in to the app.",
        representative_quote="I can't login since the last update.",
        quote_rating=2,
        quote_platform="Google Play",
    )


def _make_note() -> PulseNote:
    return PulseNote(
        week_label="Week of 2026-03-09",
        theme_summaries=[_make_summary(1), _make_summary(2, "App Speed"), _make_summary(3, "KYC")],
        action_ideas=["Action 1: Fix login", "Action 2: Speed up app", "Action 3: Improve KYC"],
        whats_working=["Working 1: Portfolio UI", "Working 2: US stocks", "Working 3: Fund picks"],
    )


# ---------------------------------------------------------------------------
# ThemeSummary
# ---------------------------------------------------------------------------

class TestThemeSummary:
    def test_valid_construction(self):
        ts = _make_summary()
        assert ts.theme_id == 1
        assert ts.label == "Login Issues"
        assert ts.quote_rating == 2
        assert ts.quote_platform == "Google Play"

    def test_empty_label_raises(self):
        with pytest.raises(ValueError, match="label"):
            ThemeSummary(
                theme_id=1, label="", summary="s", representative_quote="q",
                quote_rating=3, quote_platform="Google Play",
            )

    def test_blank_label_raises(self):
        with pytest.raises(ValueError, match="label"):
            ThemeSummary(
                theme_id=1, label="   ", summary="s", representative_quote="q",
                quote_rating=3, quote_platform="Google Play",
            )

    def test_empty_summary_raises(self):
        with pytest.raises(ValueError, match="summary"):
            ThemeSummary(
                theme_id=1, label="L", summary="", representative_quote="q",
                quote_rating=3, quote_platform="Google Play",
            )

    def test_empty_quote_raises(self):
        with pytest.raises(ValueError, match="representative_quote"):
            ThemeSummary(
                theme_id=1, label="L", summary="s", representative_quote="",
                quote_rating=3, quote_platform="Google Play",
            )

    def test_rating_zero_raises(self):
        with pytest.raises(ValueError, match="quote_rating"):
            ThemeSummary(
                theme_id=1, label="L", summary="s", representative_quote="q",
                quote_rating=0, quote_platform="Google Play",
            )

    def test_rating_six_raises(self):
        with pytest.raises(ValueError, match="quote_rating"):
            ThemeSummary(
                theme_id=1, label="L", summary="s", representative_quote="q",
                quote_rating=6, quote_platform="Google Play",
            )

    def test_rating_1_ok(self):
        ts = ThemeSummary(
            theme_id=1, label="L", summary="s", representative_quote="q",
            quote_rating=1, quote_platform="Google Play",
        )
        assert ts.quote_rating == 1

    def test_rating_5_ok(self):
        ts = ThemeSummary(
            theme_id=1, label="L", summary="s", representative_quote="q",
            quote_rating=5, quote_platform="Google Play",
        )
        assert ts.quote_rating == 5

    def test_to_dict_keys(self):
        ts = _make_summary()
        d = ts.to_dict()
        assert set(d.keys()) == {
            "theme_id", "label", "summary", "representative_quote",
            "quote_rating", "quote_platform",
        }

    def test_to_dict_values(self):
        ts = _make_summary()
        d = ts.to_dict()
        assert d["theme_id"] == 1
        assert d["label"] == "Login Issues"
        assert d["quote_rating"] == 2


# ---------------------------------------------------------------------------
# PulseNote
# ---------------------------------------------------------------------------

class TestPulseNote:
    def test_valid_construction(self):
        note = _make_note()
        assert note.week_label == "Week of 2026-03-09"
        assert len(note.theme_summaries) == 3
        assert len(note.action_ideas) == 3
        assert len(note.whats_working) == 3

    def test_empty_week_label_raises(self):
        with pytest.raises(ValueError, match="week_label"):
            PulseNote(week_label="")

    def test_blank_week_label_raises(self):
        with pytest.raises(ValueError, match="week_label"):
            PulseNote(week_label="   ")

    def test_empty_summaries_allowed(self):
        note = PulseNote(week_label="Week of 2026-03-09")
        assert note.theme_summaries == []
        assert note.action_ideas == []
        assert note.whats_working == []

    def test_to_dict_keys(self):
        note = _make_note()
        d = note.to_dict()
        assert set(d.keys()) == {"week_label", "theme_summaries", "action_ideas", "whats_working"}

    def test_to_dict_theme_summaries_serialised(self):
        note = _make_note()
        d = note.to_dict()
        assert isinstance(d["theme_summaries"], list)
        assert d["theme_summaries"][0]["theme_id"] == 1

    def test_to_dict_action_ideas_serialised(self):
        note = _make_note()
        d = note.to_dict()
        assert d["action_ideas"][0] == "Action 1: Fix login"

    def test_to_dict_whats_working_serialised(self):
        note = _make_note()
        d = note.to_dict()
        assert d["whats_working"][0] == "Working 1: Portfolio UI"
