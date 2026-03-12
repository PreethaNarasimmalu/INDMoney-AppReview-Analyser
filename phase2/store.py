"""
Phase 2 DB operations.

Extends reviews.db with:
  - themes table  (id, label, description, review_count)
  - theme_id column on reviews table (written back after classification)

Also writes themes.json to output/.
"""

import json
import sqlite3
from pathlib import Path

from phase2.models import Theme, ThemeList, ClassifiedReview

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
THEMES_JSON_PATH = OUTPUT_DIR / "themes.json"


def migrate(conn: sqlite3.Connection) -> None:
    """
    Create the themes table and add theme_id column to reviews if missing.
    Safe to call on every run — idempotent.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS themes (
            id           INTEGER PRIMARY KEY,
            label        TEXT NOT NULL,
            description  TEXT NOT NULL,
            review_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    try:
        conn.execute("ALTER TABLE reviews ADD COLUMN theme_id INTEGER")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()


def save_themes(theme_list: ThemeList, conn: sqlite3.Connection) -> None:
    """
    Persist themes to the DB (replacing previous run's themes).
    Also writes output/themes.json.
    """
    conn.execute("DELETE FROM themes")
    conn.executemany(
        "INSERT INTO themes (id, label, description, review_count) VALUES (?, ?, ?, ?)",
        [
            (t.theme_id, t.label, t.description, t.review_count)
            for t in theme_list.themes
        ],
    )
    conn.commit()

    # Write themes.json
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    THEMES_JSON_PATH.write_text(
        json.dumps(theme_list.to_list(), indent=2, ensure_ascii=False)
    )


def save_classifications(
    classified: list[ClassifiedReview],
    conn: sqlite3.Connection,
) -> None:
    """Write theme_id back to each review row."""
    conn.executemany(
        "UPDATE reviews SET theme_id = ? WHERE id = ?",
        [(c.theme_id, c.review_id) for c in classified],
    )
    conn.commit()


def load_themes(conn: sqlite3.Connection) -> list[dict]:
    """Load all themes ordered by review_count descending."""
    rows = conn.execute(
        "SELECT * FROM themes ORDER BY review_count DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def load_classified_reviews(
    conn: sqlite3.Connection,
    weeks: int = 8,
) -> list[dict]:
    """Load reviews that have been assigned a theme, within the date window."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM reviews WHERE date >= ? AND theme_id IS NOT NULL ORDER BY date DESC",
        (cutoff,),
    ).fetchall()
    return [dict(row) for row in rows]
