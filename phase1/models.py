"""
Phase 1 data models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Review:
    rating: int          # 1-5
    text: str
    date: str            # ISO date string: YYYY-MM-DD
    thumbs_up: int = 0

    def to_dict(self) -> dict:
        return {
            "rating": self.rating,
            "text": self.text,
            "date": self.date,
            "thumbs_up": self.thumbs_up,
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
