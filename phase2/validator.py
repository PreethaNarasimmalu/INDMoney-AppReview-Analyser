"""
Phase 2 — Theme Validator.

Sanity-checks classification results:
  - Counts reviews per theme
  - Merges themes with < MIN_REVIEWS_PER_THEME into the theme with the most reviews
  - Ensures final theme count stays within MIN_THEMES–MAX_THEMES

No LLM call — pure logic.

IN:  ThemeList + list[ClassifiedReview]
OUT: (validated ThemeList, updated list[ClassifiedReview])
"""

from collections import Counter

from phase2.config import MIN_REVIEWS_PER_THEME, MIN_THEMES, MAX_THEMES
from phase2.models import Theme, ThemeList, ClassifiedReview


def _count_per_theme(
    theme_list: ThemeList,
    classified: list[ClassifiedReview],
) -> dict[int, int]:
    """Return a mapping of theme_id → review count."""
    counts: Counter = Counter(c.theme_id for c in classified)
    return {t.theme_id: counts.get(t.theme_id, 0) for t in theme_list.themes}


def _find_merge_target(counts: dict[int, int], exclude_id: int) -> int:
    """Return the theme_id with the highest count, excluding exclude_id."""
    return max(
        (tid for tid in counts if tid != exclude_id),
        key=lambda tid: counts[tid],
    )


def validate_and_merge(
    theme_list: ThemeList,
    classified: list[ClassifiedReview],
) -> tuple[ThemeList, list[ClassifiedReview]]:
    """
    Merge under-populated themes and update review assignments accordingly.

    Returns updated (ThemeList, list[ClassifiedReview]) with review_count
    set on each Theme.

    Raises:
        ValueError: if theme_list is empty or classified is empty.
    """
    if not theme_list.themes:
        raise ValueError("theme_list is empty")
    if not classified:
        raise ValueError("classified list is empty")

    # Work with mutable copies
    themes = list(theme_list.themes)
    classified = list(classified)

    # Iteratively merge until no theme is below the minimum
    while True:
        counts = _count_per_theme(ThemeList(themes=themes), classified)

        # Find themes with too few reviews (skip if only MIN_THEMES remain)
        small = [
            tid for tid, cnt in counts.items()
            if cnt < MIN_REVIEWS_PER_THEME
        ]

        if not small or len(themes) <= MIN_THEMES:
            break

        # Merge the first under-populated theme into the largest one
        merge_from = small[0]
        merge_into = _find_merge_target(counts, exclude_id=merge_from)

        # Reassign reviews
        classified = [
            ClassifiedReview(
                review_id=c.review_id,
                theme_id=merge_into if c.theme_id == merge_from else c.theme_id,
            )
            for c in classified
        ]

        # Remove merged theme
        themes = [t for t in themes if t.theme_id != merge_from]

    # Set final review_count on each theme
    final_counts = _count_per_theme(ThemeList(themes=themes), classified)
    final_themes = [
        Theme(
            theme_id=t.theme_id,
            label=t.label,
            description=t.description,
            review_count=final_counts.get(t.theme_id, 0),
        )
        for t in themes
    ]
    final_themes.sort(key=lambda t: t.review_count, reverse=True)

    return ThemeList(themes=final_themes), classified
