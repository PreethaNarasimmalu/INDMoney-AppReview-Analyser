"""
Scheduler entry point — runs the full pipeline and sends the weekly pulse email.

Invoked by GitHub Actions every Monday at 09:00 UTC, or manually:
    python -m scheduler.run

Required environment variables (set as GitHub secrets or in .env):
    GROQ_API_KEY
    GEMINI_API_KEY
    GMAIL_ADDRESS
    GMAIL_APP_PASSWORD
    SCHEDULER_RECIPIENT_EMAIL

Optional environment variables:
    SCHEDULER_WEEKS           (default: 3)
    SCHEDULER_MAX_REVIEWS     (default: 200)
    SCHEDULER_RECIPIENT_NAME  (default: "")
"""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from scheduler.config import (
    SCHEDULER_WEEKS,
    SCHEDULER_MAX_REVIEWS,
    SCHEDULER_RECIPIENT_EMAIL,
    SCHEDULER_RECIPIENT_NAME,
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


def main() -> None:
    if not SCHEDULER_RECIPIENT_EMAIL:
        log.error("SCHEDULER_RECIPIENT_EMAIL is not set — cannot send email")
        sys.exit(1)

    log.info("Starting scheduled pipeline run")
    log.info("  weeks=%d  max_reviews=%d", SCHEDULER_WEEKS, SCHEDULER_MAX_REVIEWS)
    log.info("  recipient=%s", SCHEDULER_RECIPIENT_EMAIL)

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
    msg = compose(
        markdown=result.pulse_markdown,
        week_label=result.week_label,
        recipient_name=SCHEDULER_RECIPIENT_NAME,
        recipient_email=SCHEDULER_RECIPIENT_EMAIL,
        sender_address=sender_address,
    )

    send_email(msg)
    log.info("Email sent to %s", SCHEDULER_RECIPIENT_EMAIL)


if __name__ == "__main__":
    main()
