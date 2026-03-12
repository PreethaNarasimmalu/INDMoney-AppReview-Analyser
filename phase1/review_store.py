"""
Phase 1: Review Store.

Persists PII-scrubbed reviews to SQLite (data/reviews.db).
Schema: id, platform, rating, title, clean_text, date, week_label

Deduplication is handled by the PRIMARY KEY on `id` (review_hash).
Re-running the pipeline for the same date window is safe — existing
rows are silently skipped via INSERT OR IGNORE.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase1.models import Review

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reviews.db"
PLATFORM_GOOGLE_PLAY = "google_play"


def _week_label(date_str: str) -> str:
    """Return an ISO week label like '2025-W03' for a YYYY-MM-DD date string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


# ---------------------------------------------------------------------------
# Core store helpers
# ---------------------------------------------------------------------------

def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open (and return) a SQLite connection, creating the DB file if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def create_table(conn: sqlite3.Connection) -> None:
    """Create the reviews table if it does not already exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          TEXT PRIMARY KEY,
            platform    TEXT NOT NULL,
            rating      INTEGER NOT NULL,
            title       TEXT NOT NULL DEFAULT '',
            clean_text  TEXT NOT NULL,
            date        TEXT NOT NULL,
            week_label  TEXT NOT NULL
        )
    """)
    conn.commit()


def upsert_reviews(
    reviews: list[Review],
    conn: sqlite3.Connection,
    platform: str = PLATFORM_GOOGLE_PLAY,
) -> int:
    """
    Insert reviews that don't already exist (INSERT OR IGNORE on PK).

    Returns the number of *new* rows actually inserted.
    """
    before = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    conn.executemany(
        """
        INSERT OR IGNORE INTO reviews
            (id, platform, rating, title, clean_text, date, week_label)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.review_hash,
                platform,
                r.rating,
                r.title,
                r.text,
                r.date,
                _week_label(r.date),
            )
            for r in reviews
        ],
    )
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    return after - before


def load_reviews(
    conn: sqlite3.Connection,
    weeks: int = 8,
    platform: str | None = None,
) -> list[dict]:
    """
    Load reviews within the last *weeks* weeks.

    Returns a list of dicts (sqlite3.Row converted) with all columns.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).strftime("%Y-%m-%d")

    if platform:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE date >= ? AND platform = ? ORDER BY date DESC",
            (cutoff, platform),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE date >= ? ORDER BY date DESC",
            (cutoff,),
        ).fetchall()

    return [dict(row) for row in rows]


def count_reviews(conn: sqlite3.Connection) -> int:
    """Total number of stored reviews."""
    return conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]


def purge_old_reviews(
    conn: sqlite3.Connection,
    retention_weeks: int,
) -> int:
    """
    Delete reviews older than *retention_weeks* weeks.

    Called once per run after upsert to keep the DB from growing unboundedly.
    Returns the number of rows deleted.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=retention_weeks)).strftime("%Y-%m-%d")
    cursor = conn.execute("DELETE FROM reviews WHERE date < ?", (cutoff,))
    conn.commit()
    return cursor.rowcount
