"""
Phase 3 data models — theme summaries and the assembled pulse note.
"""

from dataclasses import dataclass, field


@dataclass
class ThemeSummary:
    theme_id: int
    label: str
    summary: str                  # 2-3 sentence summary from Gemini
    representative_quote: str     # verbatim, PII-free user quote
    quote_rating: int             # star rating (1-5) of the quoted review
    quote_platform: str           # e.g. "Google Play"

    def __post_init__(self):
        if not self.label or not self.label.strip():
            raise ValueError("ThemeSummary.label must be non-empty")
        if not self.summary or not self.summary.strip():
            raise ValueError("ThemeSummary.summary must be non-empty")
        if not self.representative_quote or not self.representative_quote.strip():
            raise ValueError("ThemeSummary.representative_quote must be non-empty")
        if not (1 <= self.quote_rating <= 5):
            raise ValueError(f"ThemeSummary.quote_rating must be 1-5, got {self.quote_rating}")

    def to_dict(self) -> dict:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "summary": self.summary,
            "representative_quote": self.representative_quote,
            "quote_rating": self.quote_rating,
            "quote_platform": self.quote_platform,
        }


@dataclass
class PulseNote:
    week_label: str                          # e.g. "Week of 2026-03-09"
    theme_summaries: list[ThemeSummary] = field(default_factory=list)
    action_ideas: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.week_label or not self.week_label.strip():
            raise ValueError("PulseNote.week_label must be non-empty")

    def to_dict(self) -> dict:
        return {
            "week_label": self.week_label,
            "theme_summaries": [t.to_dict() for t in self.theme_summaries],
            "action_ideas": self.action_ideas,
        }
