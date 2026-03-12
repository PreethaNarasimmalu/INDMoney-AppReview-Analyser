"""
Scheduler entry point — runs the full pipeline and sends the weekly pulse email.

Invoked by GitHub Actions every Monday at 09:00 IST (03:30 UTC), or manually:
    python -m scheduler.run

Recipients are resolved in priority order:
  1. Subscribers in data/reviews.db (when running locally with the Streamlit UI)
  2. SCHEDULER_RECIPIENTS env var — comma-separated "email" or "Name:email" entries
  3. Legacy SCHEDULER_RECIPIENT_EMAIL / SCHEDULER_RECIPIENT_NAME (single recipient)

Required environment variables (set as GitHub secrets or in .env):
    GROQ_API_KEY
    GEMINI_API_KEY
    GMAIL_ADDRESS
    GMAIL_APP_PASSWORD

At least one recipient source must be configured (exits with code 1 if none found).
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from scheduler.config import (
    SCHEDULER_WEEKS,
    SCHEDULER_MAX_REVIEWS,
    SCHEDULER_RECIPIENT_EMAIL,
    SCHEDULER_RECIPIENT_NAME,
    SCHEDULER_RECIPIENTS,
)
from phase5.pipeline_runner import run_pipeline
from phase4.composer import compose
from phase4.sender import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _load_recipients() -> list[tuple[str, str]]:
    """
    Return a list of (email, name) tuples from all available sources.

    Priority:
      1. subscribers.json (committed to repo — works in both local and GitHub Actions)
      2. DB subscribers (local runs, when DB exists)
      3. SCHEDULER_RECIPIENTS env var (manual override)
      4. Legacy SCHEDULER_RECIPIENT_EMAIL (backwards compat)
    """
    recipients: list[tuple[str, str]] = []

    # 1. subscribers.json — primary source, available in GitHub Actions checkout
    try:
        from phase5.subscriber_store import load_from_json
        subs = load_from_json()
        if subs:
            recipients = [(s.email, s.name) for s in subs]
            log.info("Loaded %d subscriber(s) from subscribers.json", len(recipients))
    except Exception as exc:
        log.warning("Could not load subscribers.json: %s", exc)

    # 2. DB subscribers (local fallback if JSON is empty/missing)
    if not recipients:
        try:
            db_path = Path(__file__).resolve().parent.parent / "data" / "reviews.db"
            if db_path.exists():
                from phase5.subscriber_store import get_connection, list_subscribers, ensure_table
                conn = get_connection(db_path)
                ensure_table(conn)
                subs = list_subscribers(conn)
                conn.close()
                if subs:
                    recipients = [(s.email, s.name) for s in subs]
                    log.info("Loaded %d subscriber(s) from DB", len(recipients))
        except Exception as exc:
            log.warning("Could not load DB subscribers: %s", exc)

    # 3. SCHEDULER_RECIPIENTS env var — "email" or "Name:email", comma-separated
    if not recipients and SCHEDULER_RECIPIENTS:
        for entry in SCHEDULER_RECIPIENTS.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                name, email = entry.split(":", 1)
                recipients.append((email.strip(), name.strip()))
            else:
                recipients.append((entry, ""))
        if recipients:
            log.info("Loaded %d recipient(s) from SCHEDULER_RECIPIENTS env var", len(recipients))

    # 4. Legacy single-recipient fallback
    if not recipients and SCHEDULER_RECIPIENT_EMAIL:
        recipients = [(SCHEDULER_RECIPIENT_EMAIL, SCHEDULER_RECIPIENT_NAME)]
        log.info("Using legacy SCHEDULER_RECIPIENT_EMAIL: %s", SCHEDULER_RECIPIENT_EMAIL)

    return recipients


def main() -> None:
    recipients = _load_recipients()

    if not recipients:
        log.error(
            "No recipients configured — set SCHEDULER_RECIPIENTS, SCHEDULER_RECIPIENT_EMAIL, "
            "or add subscribers via the Streamlit UI"
        )
        sys.exit(1)

    log.info("Starting scheduled pipeline run")
    log.info("  weeks=%d  max_reviews=%d", SCHEDULER_WEEKS, SCHEDULER_MAX_REVIEWS)
    log.info("  recipients=%d", len(recipients))

    def _on_progress(msg: str, pct: int) -> None:
        log.info("  [%3d%%] %s", pct, msg)

    result = run_pipeline(
        weeks=SCHEDULER_WEEKS,
        max_reviews=SCHEDULER_MAX_REVIEWS,
        on_progress=_on_progress,
    )

    log.info(
        "Pipeline complete — %d reviews, %d themes, week=%s",
        result.review_count,
        result.theme_count,
        result.week_label,
    )

    sender_address = os.getenv("GMAIL_ADDRESS", "")
    sent, failed = 0, 0

    for email, name in recipients:
        try:
            msg = compose(
                markdown=result.pulse_markdown,
                week_label=result.week_label,
                recipient_name=name,
                recipient_email=email,
                sender_address=sender_address,
            )
            send_email(msg)
            log.info("Email sent to %s", email)
            sent += 1
        except Exception as exc:
            log.error("Failed to send email to %s: %s", email, exc)
            failed += 1

    log.info("Done — %d sent, %d failed", sent, failed)
    if failed and sent == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
