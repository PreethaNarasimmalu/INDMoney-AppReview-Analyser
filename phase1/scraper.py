"""
Phase 1: Google Play review scraper.

Fetches up to `max_count` reviews for `app_id` published within the last
`weeks` weeks, paging newest-first and stopping as soon as a review falls
outside the date window or the count cap is hit.
"""

from datetime import datetime, timedelta, timezone
from google_play_scraper import reviews as gp_reviews, Sort

from phase1.config import (
    DEFAULT_APP_ID,
    DEFAULT_MAX_REVIEWS,
    DEFAULT_WEEKS,
    DEFAULT_LANG,
    DEFAULT_COUNTRY,
    BATCH_SIZE,
)
from phase1.models import Review, FetchResult


def _cutoff(weeks: int) -> datetime:
    """Return timezone-aware UTC datetime `weeks` weeks ago."""
    return datetime.now(timezone.utc) - timedelta(weeks=weeks)


def fetch_reviews(
    app_id: str = DEFAULT_APP_ID,
    max_count: int = DEFAULT_MAX_REVIEWS,
    weeks: int = DEFAULT_WEEKS,
    lang: str = DEFAULT_LANG,
    country: str = DEFAULT_COUNTRY,
) -> FetchResult:
    """
    Fetch reviews from Google Play.

    Stops when:
    - `max_count` reviews have been collected, OR
    - a review is older than `weeks` weeks, OR
    - there are no more pages.

    Returns a FetchResult containing the collected Review objects.

    Raises:
        ValueError: if app_id is empty or max_count / weeks are non-positive.
        Exception: propagates network/scraper errors for the caller to handle.
    """
    if not app_id or not app_id.strip():
        raise ValueError("app_id must be a non-empty string")
    if max_count <= 0:
        raise ValueError(f"max_count must be > 0, got {max_count}")
    if weeks <= 0:
        raise ValueError(f"weeks must be > 0, got {weeks}")

    cutoff_dt = _cutoff(weeks)
    collected: list[Review] = []
    continuation_token = None
    done = False

    while not done and len(collected) < max_count:
        batch_size = min(BATCH_SIZE, max_count - len(collected))

        raw_batch, continuation_token = gp_reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token,
        )

        if not raw_batch:
            break

        for raw in raw_batch:
            at = raw.get("at")
            if at is None:
                continue  # skip reviews without a timestamp
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at < cutoff_dt:
                done = True  # all subsequent reviews are older
                break
            collected.append(Review.from_raw(raw))
            if len(collected) >= max_count:
                done = True
                break

        if not continuation_token:
            break

    return FetchResult(
        app_id=app_id,
        weeks=weeks,
        max_count=max_count,
        reviews=collected,
    )
