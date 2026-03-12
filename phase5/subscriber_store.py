"""
Subscriber store — manages the weekly pulse email subscriber list.

Stored in the same SQLite DB as reviews (data/reviews.db).
Exposes: ensure_table, add_subscriber, list_subscribers, remove_subscriber.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "reviews.db"


@dataclass
class Subscriber:
    email: str
    name: str
    subscribed_at: str  # ISO datetime string


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            email         TEXT PRIMARY KEY,
            name          TEXT NOT NULL DEFAULT '',
            subscribed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def add_subscriber(conn: sqlite3.Connection, email: str, name: str = "") -> bool:
    """Add a subscriber. Returns True if added, False if already exists."""
    ensure_table(conn)
    cur = conn.execute(
        "INSERT OR IGNORE INTO subscribers (email, name) VALUES (?, ?)",
        (email.strip().lower(), name.strip()),
    )
    conn.commit()
    return cur.rowcount > 0


def list_subscribers(conn: sqlite3.Connection) -> list[Subscriber]:
    """Return all subscribers ordered by sign-up date."""
    ensure_table(conn)
    rows = conn.execute(
        "SELECT email, name, subscribed_at FROM subscribers ORDER BY subscribed_at"
    ).fetchall()
    return [
        Subscriber(email=r["email"], name=r["name"], subscribed_at=r["subscribed_at"])
        for r in rows
    ]


def remove_subscriber(conn: sqlite3.Connection, email: str) -> bool:
    """Remove a subscriber. Returns True if removed, False if not found."""
    ensure_table(conn)
    cur = conn.execute(
        "DELETE FROM subscribers WHERE email = ?",
        (email.strip().lower(),),
    )
    conn.commit()
    return cur.rowcount > 0
