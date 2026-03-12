"""
Tests for phase2.validator.validate_and_merge — pure logic, no mocks needed.
"""

import pytest
from phase2.models import Theme, ThemeList, ClassifiedReview
from phase2.validator import validate_and_merge, _count_per_theme
from phase2.config import MIN_THEMES, MIN_REVIEWS_PER_THEME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _theme(theme_id: int, label: str = None) -> Theme:
    return Theme(
        theme_id=theme_id,
        label=label or f"Theme {theme_id}",
        description=f"Desc {theme_id}",
    )


def _classified(review_id: str, theme_id: int) -> ClassifiedReview:
    return ClassifiedReview(review_id=review_id, theme_id=theme_id)


def _make_theme_list(*ids: int) -> ThemeList:
    return ThemeList(themes=[_theme(i) for i in ids])


# ---------------------------------------------------------------------------
# _count_per_theme helper
# ---------------------------------------------------------------------------

class TestCountPerTheme:
    def test_basic_count(self):
        tl = _make_theme_list(1, 2, 3)
        classified = [
            _classified("r1", 1), _classified("r2", 1),
            _classified("r3", 2),
        ]
        counts = _count_per_theme(tl, classified)
        assert counts[1] == 2
        assert counts[2] == 1
        assert counts[3] == 0

    def test_empty_classified(self):
        tl = _make_theme_list(1, 2)
        counts = _count_per_theme(tl, [])
        assert counts == {1: 0, 2: 0}


# ---------------------------------------------------------------------------
# validate_and_merge — input validation
# ---------------------------------------------------------------------------

class TestValidateAndMergeInputs:
    def test_empty_theme_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_and_merge(ThemeList(), [_classified("r1", 1)])

    def test_empty_classified_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_and_merge(_make_theme_list(1, 2, 3), [])


# ---------------------------------------------------------------------------
# validate_and_merge — happy path (all themes well-populated)
# ---------------------------------------------------------------------------

class TestValidateAndMergeHappyPath:
    def _make_classified(self, mapping: dict[int, int]) -> list[ClassifiedReview]:
        """mapping: theme_id → number of reviews for that theme"""
        classified = []
        rev_id = 0
        for theme_id, count in mapping.items():
            for _ in range(count):
                classified.append(_classified(f"r{rev_id}", theme_id))
                rev_id += 1
        return classified

    def test_returns_tuple(self):
        tl = _make_theme_list(1, 2, 3)
        classified = self._make_classified({1: 5, 2: 5, 3: 5})
        result = validate_and_merge(tl, classified)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_all_themes_kept_when_all_populated(self):
        tl = _make_theme_list(1, 2, 3)
        classified = self._make_classified({1: 5, 2: 4, 3: 3})
        final_tl, _ = validate_and_merge(tl, classified)
        assert final_tl.count == 3

    def test_review_counts_set_on_themes(self):
        tl = _make_theme_list(1, 2, 3)
        classified = self._make_classified({1: 10, 2: 5, 3: 3})
        final_tl, _ = validate_and_merge(tl, classified)
        counts = {t.theme_id: t.review_count for t in final_tl.themes}
        assert counts[1] == 10
        assert counts[2] == 5
        assert counts[3] == 3

    def test_themes_sorted_by_review_count_desc(self):
        tl = _make_theme_list(1, 2, 3)
        classified = self._make_classified({1: 3, 2: 10, 3: 6})
        final_tl, _ = validate_and_merge(tl, classified)
        counts = [t.review_count for t in final_tl.themes]
        assert counts == sorted(counts, reverse=True)

    def test_all_reviews_preserved(self):
        tl = _make_theme_list(1, 2, 3)
        classified = self._make_classified({1: 5, 2: 5, 3: 5})
        _, final_classified = validate_and_merge(tl, classified)
        assert len(final_classified) == 15


# ---------------------------------------------------------------------------
# validate_and_merge — merging under-populated themes
# ---------------------------------------------------------------------------

class TestValidateAndMergeMerging:
    def test_small_theme_gets_merged(self):
        """A theme with 1 review (< MIN_REVIEWS_PER_THEME=2) should be merged."""
        tl = _make_theme_list(1, 2, 3, 4)
        classified = [
            _classified("r1", 1), _classified("r2", 1), _classified("r3", 1),  # theme 1: 3
            _classified("r4", 2), _classified("r5", 2), _classified("r6", 2),  # theme 2: 3
            _classified("r7", 3), _classified("r8", 3), _classified("r9", 3),  # theme 3: 3
            _classified("r10", 4),                                              # theme 4: 1 — small
        ]
        final_tl, final_classified = validate_and_merge(tl, classified)
        assert final_tl.count == 3  # theme 4 merged away
        assert 4 not in final_tl.ids()

    def test_merged_reviews_reassigned(self):
        """Reviews from merged theme should be assigned to merge target."""
        tl = _make_theme_list(1, 2, 3, 4)
        classified = [
            _classified("r1", 1), _classified("r2", 1), _classified("r3", 1),
            _classified("r4", 2), _classified("r5", 2), _classified("r6", 2),
            _classified("r7", 3), _classified("r8", 3), _classified("r9", 3),
            _classified("r10", 4),  # single review — will be merged
        ]
        _, final_classified = validate_and_merge(tl, classified)
        # r10 must now point to a valid remaining theme
        r10 = next(c for c in final_classified if c.review_id == "r10")
        assert r10.theme_id != 4

    def test_stops_at_min_themes(self):
        """Never merges below MIN_THEMES even if some themes are under-populated."""
        # Exactly MIN_THEMES themes, all with 1 review — should NOT merge further
        mapping = {i + 1: 1 for i in range(MIN_THEMES)}
        tl = ThemeList(themes=[_theme(i + 1) for i in range(MIN_THEMES)])
        classified = [_classified(f"r{i}", i + 1) for i in range(MIN_THEMES)]
        final_tl, _ = validate_and_merge(tl, classified)
        assert final_tl.count == MIN_THEMES

    def test_total_review_count_unchanged_after_merge(self):
        tl = _make_theme_list(1, 2, 3, 4)
        classified = [
            _classified("r1", 1), _classified("r2", 1), _classified("r3", 1),
            _classified("r4", 2), _classified("r5", 2), _classified("r6", 2),
            _classified("r7", 3), _classified("r8", 3), _classified("r9", 3),
            _classified("r10", 4),
        ]
        _, final_classified = validate_and_merge(tl, classified)
        assert len(final_classified) == 10
