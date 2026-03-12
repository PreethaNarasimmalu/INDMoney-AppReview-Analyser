"""
Tests for phase3.assembler.assemble — pure formatting, no LLM.
"""

import pytest
from pathlib import Path
from phase3.assembler import assemble
from phase3.models import PulseNote, ThemeSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(theme_id: int, label: str, quote: str = "App needs work.", rating: int = 2) -> ThemeSummary:
    return ThemeSummary(
        theme_id=theme_id,
        label=label,
        summary=f"Users report issues with {label.lower()}.",
        representative_quote=quote,
        quote_rating=rating,
        quote_platform="Google Play",
    )


def _make_note() -> PulseNote:
    return PulseNote(
        week_label="Week of 2026-03-09",
        theme_summaries=[
            _make_summary(1, "Login Issues", "Can't log in since update.", rating=1),
            _make_summary(2, "App Speed", "Very slow on Android.", rating=2),
            _make_summary(3, "KYC Delays", "KYC stuck for 2 weeks.", rating=2),
        ],
        action_ideas=[
            "Action 1: Fix the login flow",
            "Action 2: Optimise app startup time",
            "Action 3: Streamline KYC verification",
        ],
    )


# ---------------------------------------------------------------------------
# Output content
# ---------------------------------------------------------------------------

class TestAssembleContent:
    def test_returns_string(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert isinstance(result, str)

    def test_contains_week_label(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Week of 2026-03-09" in result

    def test_contains_theme_labels(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Login Issues" in result
        assert "App Speed" in result
        assert "KYC Delays" in result

    def test_contains_summaries(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Users report issues with login issues" in result

    def test_contains_quotes(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Can't log in since update." in result
        assert "Very slow on Android." in result

    def test_contains_star_ratings(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "1★" in result
        assert "2★" in result

    def test_contains_platform(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Google Play" in result

    def test_contains_action_ideas(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Action 1: Fix the login flow" in result
        assert "Action 2: Optimise app startup time" in result
        assert "Action 3: Streamline KYC verification" in result

    def test_section_headers_present(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "TOP THEMES" in result
        assert "USER VOICES" in result
        assert "ACTION IDEAS" in result

    def test_themes_numbered(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "  1." in result
        assert "  2." in result
        assert "  3." in result

    def test_title_contains_week_label(self, tmp_path):
        result = assemble(_make_note(), output_path=tmp_path / "pulse.md")
        assert "Weekly App Review Pulse — Week of 2026-03-09" in result


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

class TestAssembleFileOutput:
    def test_file_created(self, tmp_path):
        out = tmp_path / "weekly_pulse.md"
        assemble(_make_note(), output_path=out)
        assert out.exists()

    def test_file_content_matches_return_value(self, tmp_path):
        out = tmp_path / "weekly_pulse.md"
        result = assemble(_make_note(), output_path=out)
        assert out.read_text(encoding="utf-8") == result

    def test_creates_parent_dir_if_missing(self, tmp_path):
        out = tmp_path / "nested" / "dir" / "pulse.md"
        assemble(_make_note(), output_path=out)
        assert out.exists()

    def test_overwrites_existing_file(self, tmp_path):
        out = tmp_path / "pulse.md"
        out.write_text("old content", encoding="utf-8")
        assemble(_make_note(), output_path=out)
        assert "old content" not in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAssembleEdgeCases:
    def test_empty_summaries_renders(self, tmp_path):
        note = PulseNote(week_label="Week of 2026-03-09")
        result = assemble(note, output_path=tmp_path / "pulse.md")
        assert "TOP THEMES" in result
        assert "USER VOICES" in result
        assert "ACTION IDEAS" in result

    def test_single_theme_renders(self, tmp_path):
        note = PulseNote(
            week_label="Week of 2026-03-09",
            theme_summaries=[_make_summary(1, "Login Issues")],
            action_ideas=["Action 1: Fix it"],
        )
        result = assemble(note, output_path=tmp_path / "pulse.md")
        assert "Login Issues" in result
        assert "Action 1: Fix it" in result

    def test_unicode_content_handled(self, tmp_path):
        note = PulseNote(
            week_label="Week of 2026-03-09",
            theme_summaries=[
                ThemeSummary(
                    theme_id=1, label="Hindi Reviews",
                    summary="कुछ उपयोगकर्ताओं ने समस्याएं रिपोर्ट कीं।",
                    representative_quote="ऐप बहुत धीमी है।",
                    quote_rating=2, quote_platform="Google Play",
                )
            ],
            action_ideas=["Action 1: Support regional languages"],
        )
        result = assemble(note, output_path=tmp_path / "pulse.md")
        assert "Hindi Reviews" in result
        assert "ऐप बहुत धीमी है।" in result
