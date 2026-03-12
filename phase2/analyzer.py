"""
Phase 2: Analyse reviews with Claude.

Takes a FetchResult from Phase 1 and returns a structured AnalysisResult.
"""

import json
import anthropic

from phase1.models import FetchResult
from phase2.config import (
    CLAUDE_MODEL,
    MAX_TOKENS,
    MAX_REVIEWS_IN_PROMPT,
    REVIEW_TEXT_TRUNCATE,
    TOP_THEMES,
)
from phase2.models import AnalysisResult


_PROMPT_TEMPLATE = """\
You are a product analyst reviewing user feedback for a fintech app (INDMoney / INDWealth).

Here are {count} app reviews (showing up to {max_shown}):

{review_text}

Analyze these reviews and respond with ONLY valid JSON in this exact structure:
{{
  "sentiment": {{
    "positive": <integer 0-100>,
    "neutral": <integer 0-100>,
    "negative": <integer 0-100>
  }},
  "themes": [
    {{
      "theme": "<theme name>",
      "count": <approximate number of reviews mentioning this>,
      "sentiment": "positive|neutral|negative",
      "examples": ["<short quote 1>", "<short quote 2>"]
    }}
  ],
  "summary": "<2-3 sentence summary for the product team>",
  "action_items": [
    "<specific actionable recommendation>"
  ]
}}

Return top {top_themes} themes. Sentiment percentages must add up to 100.\
"""


def _strip_code_fence(text: str) -> str:
    """Remove markdown ```json ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # drop opening fence line and closing fence line
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def analyze(fetch_result: FetchResult, client: anthropic.Anthropic) -> AnalysisResult:
    """
    Send reviews to Claude and return a structured AnalysisResult.

    Raises:
        ValueError: if fetch_result contains no reviews.
        json.JSONDecodeError: if Claude returns unparseable JSON.
        Exception: propagates Claude API errors.
    """
    if fetch_result.count == 0:
        raise ValueError("fetch_result contains no reviews to analyze")

    reviews = fetch_result.to_dicts()
    capped = reviews[:MAX_REVIEWS_IN_PROMPT]

    review_text = "\n".join(
        f"[{r['date']} | {r['rating']}★] {r['text'][:REVIEW_TEXT_TRUNCATE]}"
        for r in capped
    )

    prompt = _PROMPT_TEMPLATE.format(
        count=len(reviews),
        max_shown=MAX_REVIEWS_IN_PROMPT,
        review_text=review_text,
        top_themes=TOP_THEMES,
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    raw = _strip_code_fence(raw)
    data = json.loads(raw)
    return AnalysisResult.from_claude_json(data, review_count=len(reviews))
