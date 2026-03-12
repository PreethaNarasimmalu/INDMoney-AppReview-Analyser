"""
Tests for phase2.store — DB operations for themes and classifications.

All tests use in-memory SQLite. No files written to disk.
"""

import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

from phase2.models import Theme, ThemeList, ClassifiedReview
from phase2.store import (
    migrate,
    save_themes,
    save_classifications,
    load_themes,
    load_classified_reviews,
)
from phase1.review_store import create_table, upsert_reviews
from phase1.models import Review


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """In-memory SQLite with both phase1 reviews table and phase2 tables."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_table(c)   # phase1 schema
    migrate(c)        # phase2 adds themes table + theme_id column
    yield c
    c.close()


def _make_theme(theme_id: int, review_count: int = 5) -> Theme:
    return Theme(
        theme_id=theme_id,
        label=f"Theme {theme_id}",
        description=f"Description {theme_id}",
        review_count=review_count,
    )


def _make_theme_list(*ids) -> ThemeList:
    return ThemeList(themes=[_make_theme(i) for i in ids])


def _store_review(conn, review_id: str, days_ago: int = 1) -> str:
    from datetime import datetime, timedelta, timezone
    date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    r = Review(rating=4, text="some text", date=date)
    # Override hash by directly inserting
    from phase1.review_store import _week_label
    conn.execute(
        "INSERT OR IGNORE INTO reviews (id, platform, rating, title, clean_text, date, week_label)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (review_id, "google_play", 4, "", "some text", date, _week_label(date)),
    )
    conn.commit()
    return review_id


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------

class TestMigrate:
    def test_themes_table_created(self):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        create_table(c)
        migrate(c)
        row = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='themes'"
        ).fetchone()
        assert row is not None
        c.close()

    def test_theme_id_column_added_to_reviews(self, conn):
        cols = [row[1] for row in conn.execute("PRAGMA table_info(reviews)").fetchall()]
        assert "theme_id" in cols

    def test_idempotent(self, conn):
        migrate(conn)  # second call should not raise
        migrate(conn)


# ---------------------------------------------------------------------------
# save_themes
# ---------------------------------------------------------------------------

class TestSaveThemes:
    def test_saves_all_themes(self, conn, tmp_path):
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", tmp_path / "themes.json"):
            save_themes(_make_theme_list(1, 2, 3), conn)
        rows = load_themes(conn)
        assert len(rows) == 3

    def test_replaces_previous_themes(self, conn, tmp_path):
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", tmp_path / "themes.json"):
            save_themes(_make_theme_list(1, 2, 3), conn)
            save_themes(_make_theme_list(4, 5), conn)
        rows = load_themes(conn)
        assert len(rows) == 2

    def test_writes_themes_json(self, conn, tmp_path):
        json_path = tmp_path / "themes.json"
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", json_path):
            save_themes(_make_theme_list(1, 2, 3), conn)
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert len(data) == 3

    def test_theme_fields_stored(self, conn, tmp_path):
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", tmp_path / "themes.json"):
            save_themes(ThemeList(themes=[_make_theme(1, review_count=42)]), conn)
        row = load_themes(conn)[0]
        assert row["id"] == 1
        assert row["label"] == "Theme 1"
        assert row["review_count"] == 42


# ---------------------------------------------------------------------------
# save_classifications
# ---------------------------------------------------------------------------

class TestSaveClassifications:
    def test_writes_theme_id_to_review(self, conn):
        rev_id = _store_review(conn, "rev1")
        classified = [ClassifiedReview(review_id=rev_id, theme_id=2)]
        save_classifications(classified, conn)
        row = conn.execute("SELECT theme_id FROM reviews WHERE id = ?", (rev_id,)).fetchone()
        assert row["theme_id"] == 2

    def test_multiple_reviews_classified(self, conn):
        ids = [_store_review(conn, f"rev{i}") for i in range(3)]
        classified = [ClassifiedReview(review_id=rid, theme_id=i + 1) for i, rid in enumerate(ids)]
        save_classifications(classified, conn)
        for i, rid in enumerate(ids):
            row = conn.execute("SELECT theme_id FROM reviews WHERE id = ?", (rid,)).fetchone()
            assert row["theme_id"] == i + 1

    def test_empty_classified_no_error(self, conn):
        save_classifications([], conn)  # should not raise


# ---------------------------------------------------------------------------
# load_themes
# ---------------------------------------------------------------------------

class TestLoadThemes:
    def test_empty_store(self, conn):
        assert load_themes(conn) == []

    def test_ordered_by_review_count_desc(self, conn, tmp_path):
        tl = ThemeList(themes=[
            _make_theme(1, review_count=5),
            _make_theme(2, review_count=20),
            _make_theme(3, review_count=10),
        ])
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", tmp_path / "themes.json"):
            save_themes(tl, conn)
        rows = load_themes(conn)
        counts = [r["review_count"] for r in rows]
        assert counts == sorted(counts, reverse=True)

    def test_returns_dicts(self, conn, tmp_path):
        with patch("phase2.store.OUTPUT_DIR", tmp_path), \
             patch("phase2.store.THEMES_JSON_PATH", tmp_path / "themes.json"):
            save_themes(_make_theme_list(1), conn)
        rows = load_themes(conn)
        assert isinstance(rows[0], dict)


# ---------------------------------------------------------------------------
# load_classified_reviews
# ---------------------------------------------------------------------------

class TestLoadClassifiedReviews:
    def test_returns_only_classified(self, conn):
        _store_review(conn, "classified_rev", days_ago=1)
        _store_review(conn, "unclassified_rev", days_ago=2)
        save_classifications([ClassifiedReview("classified_rev", theme_id=1)], conn)

        rows = load_classified_reviews(conn, weeks=8)
        ids = {r["id"] for r in rows}
        assert "classified_rev" in ids
        assert "unclassified_rev" not in ids

    def test_empty_when_nothing_classified(self, conn):
        _store_review(conn, "rev1")
        assert load_classified_reviews(conn, weeks=8) == []
