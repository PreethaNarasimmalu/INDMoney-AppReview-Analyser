"""
Tests for phase1.review_store — SQLite persistence layer.

All tests use an in-memory SQLite DB so no files are written to disk.
"""

import sqlite3
import pytest
from datetime import datetime, timedelta, timezone

from phase1.models import Review
from phase1.review_store import (
    create_table,
    upsert_reviews,
    load_reviews,
    count_reviews,
    _week_label,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """In-memory SQLite connection with the reviews table ready."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_table(c)
    yield c
    c.close()


def _review(
    text: str = "Great app",
    rating: int = 4,
    days_ago: int = 1,
    title: str = "",
) -> Review:
    date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return Review(rating=rating, text=text, date=date, title=title)


# ---------------------------------------------------------------------------
# _week_label helper
# ---------------------------------------------------------------------------

class TestWeekLabel:
    def test_format(self):
        label = _week_label("2025-01-06")  # Monday of week 2
        assert label.startswith("2025-W")
        assert len(label) == 8  # e.g. 2025-W02 (4+1+1+2)

    def test_week_number_padded(self):
        label = _week_label("2025-01-06")
        # week number should be zero-padded to 2 digits
        week_part = label.split("-W")[1]
        assert len(week_part) == 2


# ---------------------------------------------------------------------------
# create_table
# ---------------------------------------------------------------------------

class TestCreateTable:
    def test_table_exists_after_create(self):
        c = sqlite3.connect(":memory:")
        create_table(c)
        row = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'"
        ).fetchone()
        assert row is not None
        c.close()

    def test_idempotent(self):
        """Calling create_table twice should not raise."""
        c = sqlite3.connect(":memory:")
        create_table(c)
        create_table(c)  # should not raise
        c.close()


# ---------------------------------------------------------------------------
# upsert_reviews
# ---------------------------------------------------------------------------

class TestUpsertReviews:
    def test_inserts_new_reviews(self, conn):
        reviews = [_review("text A"), _review("text B", days_ago=2)]
        inserted = upsert_reviews(reviews, conn)
        assert inserted == 2

    def test_returns_count_of_new_rows(self, conn):
        reviews = [_review("unique text xyz")]
        assert upsert_reviews(reviews, conn) == 1

    def test_duplicate_skipped(self, conn):
        r = _review("same text")
        upsert_reviews([r], conn)
        inserted_again = upsert_reviews([r], conn)
        assert inserted_again == 0

    def test_total_count_correct_after_dedup(self, conn):
        r = _review("repeated")
        upsert_reviews([r], conn)
        upsert_reviews([r], conn)
        assert count_reviews(conn) == 1

    def test_stores_all_columns(self, conn):
        r = Review(rating=5, text="Excellent!", date="2025-03-01", title="Love it")
        upsert_reviews([r], conn)
        row = conn.execute("SELECT * FROM reviews").fetchone()
        assert row["rating"] == 5
        assert row["clean_text"] == "Excellent!"
        assert row["date"] == "2025-03-01"
        assert row["title"] == "Love it"
        assert row["platform"] == "google_play"

    def test_week_label_stored(self, conn):
        r = Review(rating=4, text="ok", date="2025-01-06")
        upsert_reviews([r], conn)
        row = conn.execute("SELECT week_label FROM reviews").fetchone()
        assert row["week_label"].startswith("2025-W")

    def test_custom_platform(self, conn):
        r = _review("some text")
        upsert_reviews([r], conn, platform="app_store")
        row = conn.execute("SELECT platform FROM reviews").fetchone()
        assert row["platform"] == "app_store"

    def test_empty_list_no_error(self, conn):
        inserted = upsert_reviews([], conn)
        assert inserted == 0


# ---------------------------------------------------------------------------
# load_reviews
# ---------------------------------------------------------------------------

class TestLoadReviews:
    def test_returns_reviews_within_window(self, conn):
        upsert_reviews([_review("recent", days_ago=3)], conn)
        rows = load_reviews(conn, weeks=8)
        assert len(rows) == 1

    def test_excludes_old_reviews(self, conn):
        upsert_reviews([_review("old", days_ago=70)], conn)  # > 8 weeks
        rows = load_reviews(conn, weeks=8)
        assert len(rows) == 0

    def test_returns_dicts(self, conn):
        upsert_reviews([_review("text")], conn)
        rows = load_reviews(conn, weeks=8)
        assert isinstance(rows[0], dict)

    def test_all_expected_keys_present(self, conn):
        upsert_reviews([_review("text")], conn)
        row = load_reviews(conn, weeks=8)[0]
        for key in ("id", "platform", "rating", "title", "clean_text", "date", "week_label"):
            assert key in row

    def test_platform_filter(self, conn):
        upsert_reviews([_review("gplay text")], conn, platform="google_play")
        upsert_reviews([_review("appstore text")], conn, platform="app_store")
        gplay = load_reviews(conn, weeks=8, platform="google_play")
        assert all(r["platform"] == "google_play" for r in gplay)

    def test_ordered_newest_first(self, conn):
        upsert_reviews([
            _review("older", days_ago=5),
            _review("newer", days_ago=1),
        ], conn)
        rows = load_reviews(conn, weeks=8)
        assert rows[0]["date"] >= rows[-1]["date"]

    def test_empty_store_returns_empty_list(self, conn):
        assert load_reviews(conn, weeks=8) == []


# ---------------------------------------------------------------------------
# count_reviews
# ---------------------------------------------------------------------------

class TestCountReviews:
    def test_zero_on_empty(self, conn):
        assert count_reviews(conn) == 0

    def test_counts_all_rows(self, conn):
        upsert_reviews([_review("a"), _review("b"), _review("c")], conn)
        assert count_reviews(conn) == 3
