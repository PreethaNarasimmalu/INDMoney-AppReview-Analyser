"""
Phase 2 — Review Filter.

Removes low-signal reviews before any LLM call to reduce token usage
and improve theme quality. Applied before both theme discovery and
classification.

Filters applied (in order):
  1. Too short       — fewer than MIN_WORD_COUNT words
  2. Low signal      — < MIN_ALPHA_RATIO alphabetic chars (emoji-only, number spam)
  3. All-caps spam   — > MAX_UPPERCASE_RATIO uppercase letters
  4. Exact duplicate — same normalised text seen before (keep first occurrence)
"""

import re
from phase2.config import MIN_WORD_COUNT, MIN_ALPHA_RATIO, MAX_UPPERCASE_RATIO


def _word_count(text: str) -> int:
    return len(text.split())


def _alpha_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(c.isalpha() for c in text) / len(text)


def _uppercase_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(c.isupper() for c in letters) / len(letters)


def _normalise(text: str) -> str:
    """Lowercase + collapse whitespace — used for duplicate detection."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_too_short(text: str) -> bool:
    return _word_count(text) < MIN_WORD_COUNT


def _is_low_signal(text: str) -> bool:
    return _alpha_ratio(text) < MIN_ALPHA_RATIO


def _is_all_caps_spam(text: str) -> bool:
    return _uppercase_ratio(text) > MAX_UPPERCASE_RATIO


def filter_reviews(reviews: list[dict]) -> tuple[list[dict], dict]:
    """
    Filter low-signal reviews from a list of review dicts.

    Args:
        reviews: list of review dicts, each must have a 'clean_text' key

    Returns:
        (kept, stats) where:
          kept  — filtered list, safe to pass to LLM calls
          stats — dict with counts: total, kept, removed_short,
                  removed_low_signal, removed_spam, removed_duplicate
    """
    stats = {
        "total": len(reviews),
        "removed_short": 0,
        "removed_low_signal": 0,
        "removed_spam": 0,
        "removed_duplicate": 0,
        "kept": 0,
    }

    kept: list[dict] = []
    seen: set[str] = set()

    for review in reviews:
        text = review.get("clean_text", "") or ""

        if _is_too_short(text):
            stats["removed_short"] += 1
            continue

        if _is_low_signal(text):
            stats["removed_low_signal"] += 1
            continue

        if _is_all_caps_spam(text):
            stats["removed_spam"] += 1
            continue

        norm = _normalise(text)
        if norm in seen:
            stats["removed_duplicate"] += 1
            continue
        seen.add(norm)

        kept.append(review)

    stats["kept"] = len(kept)
    return kept, stats
