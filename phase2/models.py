"""
Phase 2 data models — themes and classifications.
"""

from dataclasses import dataclass, field


@dataclass
class Theme:
    theme_id: int
    label: str
    description: str
    review_count: int = 0

    def __post_init__(self):
        if not self.label or not self.label.strip():
            raise ValueError("Theme.label must be a non-empty string")
        if not self.description or not self.description.strip():
            raise ValueError("Theme.description must be a non-empty string")
        if self.theme_id < 1:
            raise ValueError(f"Theme.theme_id must be >= 1, got {self.theme_id}")
        if self.review_count < 0:
            raise ValueError(f"Theme.review_count must be >= 0, got {self.review_count}")

    def to_dict(self) -> dict:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "description": self.description,
            "review_count": self.review_count,
        }


@dataclass
class ThemeList:
    themes: list[Theme] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.themes)

    def by_id(self, theme_id: int) -> Theme | None:
        for t in self.themes:
            if t.theme_id == theme_id:
                return t
        return None

    def ids(self) -> list[int]:
        return [t.theme_id for t in self.themes]

    def to_list(self) -> list[dict]:
        return [t.to_dict() for t in self.themes]

    @classmethod
    def from_groq_json(cls, data: dict) -> "ThemeList":
        """
        Parse the JSON returned by the theme discovery LLM call.

        Expected shape:
          { "themes": [{ "theme_id": 1, "label": "...", "description": "..." }, ...] }
        """
        raw_themes = data.get("themes", [])
        themes = [
            Theme(
                theme_id=int(t["theme_id"]),
                label=str(t["label"]).strip(),
                description=str(t.get("description", "")).strip(),
            )
            for t in raw_themes
        ]
        return cls(themes=themes)


@dataclass
class ClassifiedReview:
    review_id: str   # review_hash from phase1
    theme_id: int

    def to_dict(self) -> dict:
        return {"review_id": self.review_id, "theme_id": self.theme_id}
