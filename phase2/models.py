"""
Phase 2 data models for analysis results.
"""
from dataclasses import dataclass, field


@dataclass
class Sentiment:
    positive: int   # 0-100
    neutral: int    # 0-100
    negative: int   # 0-100

    def __post_init__(self):
        for name, val in [("positive", self.positive), ("neutral", self.neutral), ("negative", self.negative)]:
            if not (0 <= val <= 100):
                raise ValueError(f"Sentiment.{name} must be 0-100, got {val}")
        total = self.positive + self.neutral + self.negative
        if total != 100:
            raise ValueError(f"Sentiment percentages must sum to 100, got {total}")

    def to_dict(self) -> dict:
        return {"positive": self.positive, "neutral": self.neutral, "negative": self.negative}


VALID_SENTIMENTS = {"positive", "neutral", "negative"}


@dataclass
class Theme:
    theme: str
    count: int
    sentiment: str              # "positive" | "neutral" | "negative"
    examples: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.theme or not self.theme.strip():
            raise ValueError("Theme.theme must be a non-empty string")
        if self.count < 0:
            raise ValueError(f"Theme.count must be >= 0, got {self.count}")
        if self.sentiment not in VALID_SENTIMENTS:
            raise ValueError(f"Theme.sentiment must be one of {VALID_SENTIMENTS}, got {self.sentiment!r}")

    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "count": self.count,
            "sentiment": self.sentiment,
            "examples": self.examples,
        }


@dataclass
class AnalysisResult:
    sentiment: Sentiment
    themes: list[Theme]
    summary: str
    action_items: list[str]
    review_count: int

    def to_dict(self) -> dict:
        return {
            "sentiment": self.sentiment.to_dict(),
            "themes": [t.to_dict() for t in self.themes],
            "summary": self.summary,
            "action_items": self.action_items,
            "review_count": self.review_count,
        }

    @classmethod
    def from_claude_json(cls, data: dict, review_count: int) -> "AnalysisResult":
        """Build an AnalysisResult from the parsed JSON returned by Claude."""
        raw_sent = data.get("sentiment", {})
        sentiment = Sentiment(
            positive=int(raw_sent.get("positive", 0)),
            neutral=int(raw_sent.get("neutral", 0)),
            negative=int(raw_sent.get("negative", 0)),
        )
        themes = [
            Theme(
                theme=t.get("theme", ""),
                count=int(t.get("count", 0)),
                sentiment=t.get("sentiment", "neutral"),
                examples=t.get("examples", []),
            )
            for t in data.get("themes", [])
        ]
        return cls(
            sentiment=sentiment,
            themes=themes,
            summary=data.get("summary", ""),
            action_items=data.get("action_items", []),
            review_count=review_count,
        )
