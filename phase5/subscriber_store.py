"""
Subscriber store — manages the weekly pulse email subscriber list.

Primary store: SQLite `subscribers` table in `data/reviews.db`.
Mirror store:  `subscribers.json` at the repo root — committed to git so
               GitHub Actions can read the list without DB access.

Every add/remove syncs both stores automatically.
"""

import base64
import json
import os
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT  = Path(__file__).resolve().parent.parent
DB_PATH     = _REPO_ROOT / "data" / "reviews.db"
JSON_PATH   = _REPO_ROOT / "subscribers.json"


@dataclass
class Subscriber:
    email: str
    name: str
    subscribed_at: str  # ISO datetime string


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

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
    if cur.rowcount > 0:
        _sync_json(conn)
        return True
    return False


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
    if cur.rowcount > 0:
        _sync_json(conn)
        return True
    return False


# ---------------------------------------------------------------------------
# JSON mirror — read by GitHub Actions scheduler
# ---------------------------------------------------------------------------

def _push_to_github(content: str) -> None:
    """
    Push subscribers.json to GitHub via API so GitHub Actions can read it.

    Requires env vars:
      GITHUB_TOKEN — Personal Access Token with contents:write scope
      GITHUB_REPO  — e.g. "PreethaNarasimmalu/INDMoney-AppReview-Analyser"
    """
    token = os.getenv("GITHUB_TOKEN", "")
    repo  = os.getenv("GITHUB_REPO", "")
    if not token or not repo:
        return

    api_url = f"https://api.github.com/repos/{repo}/contents/subscribers.json"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    # Fetch current SHA (required for update)
    sha = None
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            sha = json.loads(resp.read())["sha"]
    except Exception:
        pass

    encoded = base64.b64encode(content.encode()).decode()
    payload = {"message": "chore: sync subscribers.json", "content": encoded}
    if sha:
        payload["sha"] = sha

    put_req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode(),
        method="PUT",
        headers=headers,
    )
    with urllib.request.urlopen(put_req):
        pass


def _sync_json(conn: sqlite3.Connection, json_path: Path = JSON_PATH) -> None:
    """Write current subscribers to subscribers.json and push to GitHub if configured."""
    subs = list_subscribers(conn)
    data = [{"email": s.email, "name": s.name} for s in subs]
    content = json.dumps(data, indent=2)
    json_path.write_text(content, encoding="utf-8")
    try:
        _push_to_github(content)
    except Exception:
        pass  # Never block subscribe/unsubscribe if GitHub push fails


def load_from_json(json_path: Path = JSON_PATH) -> list[Subscriber]:
    """Read subscribers from the JSON file (used by scheduler in GitHub Actions)."""
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return [
            Subscriber(email=e["email"], name=e.get("name", ""), subscribed_at="")
            for e in data
            if e.get("email")
        ]
    except Exception:
        return []
