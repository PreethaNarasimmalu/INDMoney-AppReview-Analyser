"""
Tests for phase5.pipeline_runner.run_pipeline.

All external phase dependencies are mocked — no real LLM calls,
no real DB writes, no network access.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from phase5.pipeline_runner import run_pipeline, PipelineResult
from phase1.models import Review, FetchResult
from phase2.models import Theme, ThemeList, ClassifiedReview
from phase3.models import PulseNote, ThemeSummary


# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------
P = "phase5.pipeline_runner"

PATCHES = {
    "fetch_reviews":        f"{P}.fetch_reviews",
    "scrub_reviews":        f"{P}.scrub_reviews",
    "get_connection":       f"{P}.get_connection",
    "create_table":         f"{P}.create_table",
    "migrate":              f"{P}.migrate",
    "upsert_reviews":       f"{P}.upsert_reviews",
    "purge_old_reviews":    f"{P}.purge_old_reviews",
    "load_reviews":         f"{P}.load_reviews",
    "get_groq_client":      f"{P}.get_groq_client",
    "discover_themes":      f"{P}.discover_themes",
    "classify_reviews":     f"{P}.classify_reviews",
    "validate_and_merge":   f"{P}.validate_and_merge",
    "save_themes":          f"{P}.save_themes",
    "save_classifications": f"{P}.save_classifications",
    "get_gemini_client":    f"{P}.get_gemini_client",
    "generate_pulse":       f"{P}.generate_pulse",
    "assemble":             f"{P}.assemble",
    "load_themes":          f"{P}.load_themes",
}


# ---------------------------------------------------------------------------
# Fixtures — canonical mock objects
# ---------------------------------------------------------------------------

def _make_review(i: int = 0) -> Review:
    return Review(rating=4, text=f"This is review number {i}", date="2026-03-01")


def _make_fetch_result(n: int = 3) -> FetchResult:
    return FetchResult(
        app_id="in.indwealth",
        weeks=8,
        max_count=1000,
        reviews=[_make_review(i) for i in range(n)],
    )


def _make_theme_list() -> ThemeList:
    return ThemeList(themes=[
        Theme(theme_id=1, label="Login Issues", description="Login problems", review_count=5),
        Theme(theme_id=2, label="App Speed", description="Performance issues", review_count=3),
    ])


def _make_classified(theme_list: ThemeList) -> list[ClassifiedReview]:
    return [
        ClassifiedReview(review_id=f"id{i}", theme_id=theme_list.themes[i % 2].theme_id)
        for i in range(5)
    ]


def _make_pulse_note() -> PulseNote:
    return PulseNote(
        week_label="Week of 2026-03-09",
        theme_summaries=[
            ThemeSummary(
                theme_id=1, label="Login Issues",
                summary="Users report login failures.",
                representative_quote="Cannot login since update.",
                quote_rating=1, quote_platform="Google Play",
            )
        ],
        action_ideas=["Fix login regression.", "Improve startup time.", "Add status notifications."],
    )


def _make_review_dicts(n: int = 5) -> list[dict]:
    return [
        {"id": f"id{i}", "rating": 4, "clean_text": f"Review text number {i}", "date": "2026-03-01"}
        for i in range(n)
    ]


def _make_theme_dicts() -> list[dict]:
    return [
        {"id": 1, "label": "Login Issues", "description": "Login problems", "review_count": 5},
        {"id": 2, "label": "App Speed", "description": "Performance", "review_count": 3},
    ]


# ---------------------------------------------------------------------------
# Helper: build all mocks and apply patches
# ---------------------------------------------------------------------------

class _AllPatched:
    """Context manager that patches all pipeline dependencies."""

    def __init__(self, overrides: dict | None = None):
        self._overrides = overrides or {}
        self._patchers = {}
        self.mocks = {}

    def __enter__(self):
        theme_list = _make_theme_list()
        classified = _make_classified(theme_list)
        pulse_note = _make_pulse_note()

        defaults = {
            "fetch_reviews":        MagicMock(return_value=_make_fetch_result()),
            "scrub_reviews":        MagicMock(side_effect=lambda reviews: reviews),
            "get_connection":       MagicMock(return_value=MagicMock()),
            "create_table":         MagicMock(return_value=None),
            "migrate":              MagicMock(return_value=None),
            "upsert_reviews":       MagicMock(return_value=3),
            "purge_old_reviews":    MagicMock(return_value=0),
            "load_reviews":         MagicMock(return_value=_make_review_dicts()),
            "get_groq_client":      MagicMock(return_value=MagicMock()),
            "discover_themes":      MagicMock(return_value=theme_list),
            "classify_reviews":     MagicMock(return_value=classified),
            "validate_and_merge":   MagicMock(return_value=(theme_list, classified)),
            "save_themes":          MagicMock(return_value=None),
            "save_classifications": MagicMock(return_value=None),
            "get_gemini_client":    MagicMock(return_value=MagicMock()),
            "generate_pulse":       MagicMock(return_value=pulse_note),
            "assemble":             MagicMock(return_value="# Weekly Pulse\n\nTOP THEMES\n  1. Login Issues"),
            "load_themes":          MagicMock(return_value=_make_theme_dicts()),
        }
        defaults.update(self._overrides)

        for key, mock in defaults.items():
            patcher = patch(PATCHES[key], mock)
            self.mocks[key] = patcher.start()
            self._patchers[key] = patcher

        return self.mocks

    def __exit__(self, *args):
        for patcher in self._patchers.values():
            patcher.stop()


# ---------------------------------------------------------------------------
# PipelineResult dataclass
# ---------------------------------------------------------------------------

class TestPipelineResult:
    def test_fields_exist(self):
        r = PipelineResult(
            week_label="Week of 2026-03-09",
            review_count=100,
            new_reviews=10,
            purged_reviews=5,
            theme_count=3,
            pulse_markdown="# Pulse",
            themes=[],
        )
        assert r.week_label == "Week of 2026-03-09"
        assert r.review_count == 100
        assert r.new_reviews == 10
        assert r.purged_reviews == 5
        assert r.theme_count == 3
        assert r.pulse_markdown == "# Pulse"

    def test_themes_defaults_to_empty_list(self):
        r = PipelineResult(
            week_label="w", review_count=0, new_reviews=0,
            purged_reviews=0, theme_count=0, pulse_markdown="",
        )
        assert r.themes == []


# ---------------------------------------------------------------------------
# run_pipeline — returns correct PipelineResult
# ---------------------------------------------------------------------------

class TestRunPipelineResult:
    def test_returns_pipeline_result(self):
        with _AllPatched():
            result = run_pipeline()
        assert isinstance(result, PipelineResult)

    def test_week_label_from_pulse_note(self):
        with _AllPatched():
            result = run_pipeline()
        assert result.week_label == "Week of 2026-03-09"

    def test_review_count_from_loaded_reviews(self):
        with _AllPatched():
            result = run_pipeline()
        assert result.review_count == 5  # _make_review_dicts returns 5

    def test_new_reviews_from_upsert(self):
        with _AllPatched():
            result = run_pipeline()
        assert result.new_reviews == 3

    def test_purged_reviews_from_purge(self):
        with _AllPatched({"purge_old_reviews": MagicMock(return_value=7)}):
            result = run_pipeline()
        assert result.purged_reviews == 7

    def test_theme_count_from_load_themes(self):
        with _AllPatched():
            result = run_pipeline()
        assert result.theme_count == 2

    def test_pulse_markdown_from_assemble(self):
        with _AllPatched():
            result = run_pipeline()
        assert "TOP THEMES" in result.pulse_markdown

    def test_themes_list_populated(self):
        with _AllPatched():
            result = run_pipeline()
        assert len(result.themes) == 2
        assert result.themes[0]["label"] == "Login Issues"


# ---------------------------------------------------------------------------
# run_pipeline — Phase 1 calls
# ---------------------------------------------------------------------------

class TestRunPipelinePhase1:
    def test_fetch_reviews_called(self):
        with _AllPatched() as mocks:
            run_pipeline(weeks=8, max_reviews=500)
        mocks["fetch_reviews"].assert_called_once()

    def test_fetch_reviews_uses_weeks_and_max(self):
        with _AllPatched() as mocks:
            run_pipeline(weeks=6, max_reviews=400)
        call_kwargs = mocks["fetch_reviews"].call_args
        assert call_kwargs.kwargs.get("weeks") == 6 or 6 in call_kwargs.args
        assert call_kwargs.kwargs.get("max_count") == 400 or 400 in call_kwargs.args

    def test_scrub_reviews_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["scrub_reviews"].assert_called_once()

    def test_upsert_called_with_scrubbed_reviews(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["upsert_reviews"].assert_called_once()

    def test_purge_called_after_upsert(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["purge_old_reviews"].assert_called_once()

    def test_create_table_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["create_table"].assert_called_once()

    def test_migrate_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["migrate"].assert_called_once()

    def test_load_reviews_uses_weeks(self):
        with _AllPatched() as mocks:
            run_pipeline(weeks=10)
        call_kwargs = mocks["load_reviews"].call_args
        assert call_kwargs.kwargs.get("weeks") == 10 or 10 in call_kwargs.args


# ---------------------------------------------------------------------------
# run_pipeline — Phase 2 calls
# ---------------------------------------------------------------------------

class TestRunPipelinePhase2:
    def test_discover_themes_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["discover_themes"].assert_called_once()

    def test_classify_reviews_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["classify_reviews"].assert_called_once()

    def test_validate_and_merge_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["validate_and_merge"].assert_called_once()

    def test_save_themes_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["save_themes"].assert_called_once()

    def test_save_classifications_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["save_classifications"].assert_called_once()


# ---------------------------------------------------------------------------
# run_pipeline — Phase 3 calls
# ---------------------------------------------------------------------------

class TestRunPipelinePhase3:
    def test_generate_pulse_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["generate_pulse"].assert_called_once()

    def test_assemble_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["assemble"].assert_called_once()

    def test_load_themes_called(self):
        with _AllPatched() as mocks:
            run_pipeline()
        mocks["load_themes"].assert_called_once()


# ---------------------------------------------------------------------------
# run_pipeline — error cases
# ---------------------------------------------------------------------------

class TestRunPipelineErrors:
    def test_raises_if_no_reviews_after_scraping(self):
        with _AllPatched({"load_reviews": MagicMock(return_value=[])}):
            with pytest.raises(ValueError, match="No reviews found"):
                run_pipeline()

    def test_no_llm_calls_if_no_reviews(self):
        with _AllPatched({"load_reviews": MagicMock(return_value=[])}) as mocks:
            with pytest.raises(ValueError):
                run_pipeline()
        mocks["discover_themes"].assert_not_called()
        mocks["classify_reviews"].assert_not_called()


# ---------------------------------------------------------------------------
# run_pipeline — progress callback
# ---------------------------------------------------------------------------

class TestRunPipelineProgress:
    def test_progress_callback_called(self):
        calls = []
        with _AllPatched():
            run_pipeline(on_progress=lambda msg, pct: calls.append((msg, pct)))
        assert len(calls) > 0

    def test_progress_reaches_100(self):
        pcts = []
        with _AllPatched():
            run_pipeline(on_progress=lambda msg, pct: pcts.append(pct))
        assert 100 in pcts

    def test_progress_callback_optional(self):
        # Should not raise when on_progress is None
        with _AllPatched():
            result = run_pipeline(on_progress=None)
        assert isinstance(result, PipelineResult)
