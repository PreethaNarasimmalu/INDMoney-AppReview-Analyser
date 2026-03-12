"""
Phase 1 data models.
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Review:
    rating: int          # 1-5
    text: str
    date: str            # ISO date string: YYYY-MM-DD
    thumbs_up: int = 0
    title: str = ""      # review title (may be empty)

    @property
    def review_hash(self) -> str:
        """Stable unique ID derived from content — used for deduplication."""
        raw = f"{self.date}|{self.rating}|{self.text[:200]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def to_dict(self) -> dict:
        return {
            "rating": self.rating,
            "text": self.text,
            "date": self.date,
            "thumbs_up": self.thumbs_up,
            "title": self.title,
        }

    @classmethod
    def from_raw(cls, raw: dict) -> "Review":
        """Build a Review from a raw google-play-scraper result dict."""
        at: datetime = raw.get("at")
        if at is None:
            raise ValueError("Review has no timestamp")
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return cls(
            rating=int(raw.get("score", 0)),
            text=raw.get("content", ""),
            date=at.strftime("%Y-%m-%d"),
            thumbs_up=int(raw.get("thumbsUpCount", 0)),
            title=raw.get("title") or "",
        )


@dataclass
class FetchResult:
    app_id: str
    weeks: int
    max_count: int
    reviews: list[Review] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.reviews)

    @property
    def avg_rating(self) -> float:
        if not self.reviews:
            return 0.0
        return sum(r.rating for r in self.reviews) / len(self.reviews)

    def to_dicts(self) -> list[dict]:
        return [r.to_dict() for r in self.reviews]
