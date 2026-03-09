from google_play_scraper import reviews, Sort
from datetime import datetime, timedelta, timezone

def fetch_reviews(app_id: str, max_count: int = 1000, weeks: int = 8) -> list[dict]:
    """
    Fetch up to max_count reviews from Google Play for app_id,
    filtered to the last `weeks` weeks. Returns list of review dicts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    all_reviews = []
    continuation_token = None

    while len(all_reviews) < max_count:
        batch_size = min(200, max_count - len(all_reviews))
        result, continuation_token = reviews(
            app_id,
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=continuation_token
        )
        if not result:
            break
        for r in result:
            at = r.get('at')
            if at is None:
                continue
            # make timezone-aware
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at < cutoff:
                return all_reviews  # reviews are newest-first, stop when past window
            all_reviews.append({
                'rating': r.get('score', 0),
                'text': r.get('content', ''),
                'date': at.strftime('%Y-%m-%d'),
                'thumbs_up': r.get('thumbsUpCount', 0),
            })
        if not continuation_token:
            break

    return all_reviews
