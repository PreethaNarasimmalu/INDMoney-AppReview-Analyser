"""
Phase 1: PII Scrubber.

Hard gate — every review text MUST pass through scrub() before storage
or any LLM call. Detected PII is replaced with [REDACTED].

Patterns covered (regex only; spaCy NER not required):
  - Email addresses
  - Indian & international phone numbers
  - URLs (http / https / bare www.)
  - UPI IDs  (handle@upi)
  - Device / account IDs  (long hex / alphanumeric tokens)
"""

import re
from phase1.models import Review

# ---------------------------------------------------------------------------
# Compiled patterns — ordered most-specific → least-specific
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Email addresses
    ("email", re.compile(
        r"\b[\w.%+-]+@(?!REDACTED\b)[\w.-]+\.[a-zA-Z]{2,}\b",
        re.IGNORECASE,
    )),
    # UPI IDs  e.g. user@okaxis, 9876543210@ybl
    ("upi", re.compile(
        r"\b[\w.\-]+@(?:okaxis|okhdfcbank|okicici|oksbi|ybl|axl|ibl|upi|paytm|apl)\b",
        re.IGNORECASE,
    )),
    # Indian mobile numbers — 10 digits starting 6-9, optional +91 / 0 prefix
    ("phone_in", re.compile(
        r"(?<!\d)(?:\+91[\s\-]?|0)?[6-9]\d{9}(?!\d)"
    )),
    # International phone — +<country> then 6-14 digits
    ("phone_intl", re.compile(
        r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{2,5}[\s\-]?\d{2,6}"
    )),
    # URLs
    ("url", re.compile(
        r"https?://\S+|www\.\S+",
        re.IGNORECASE,
    )),
    # Hex/alphanumeric tokens ≥ 16 chars (device IDs, order IDs, tokens)
    ("token", re.compile(
        r"\b[A-Za-z0-9_\-]{16,}\b"
    )),
]

_REDACTED = "[REDACTED]"


def scrub(text: str) -> str:
    """
    Return a copy of *text* with all detected PII replaced by [REDACTED].

    This is a pure function — it never modifies input in place.
    """
    for _label, pattern in _PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


def scrub_reviews(reviews: list[Review]) -> list[Review]:
    """
    Return new Review objects with PII scrubbed from the text field.

    The original list is not modified. Every review passes through
    scrub() — this is the hard gate before storage.
    """
    result = []
    for r in reviews:
        result.append(Review(
            rating=r.rating,
            text=scrub(r.text),
            date=r.date,
            thumbs_up=r.thumbs_up,
            title=scrub(r.title) if r.title else r.title,
        ))
    return result
