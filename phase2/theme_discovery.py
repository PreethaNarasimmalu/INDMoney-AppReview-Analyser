"""
Phase 2 — LLM Call 1: Theme Discovery (Groq).

Reads all clean review texts and asks Groq to return 3-5 distinct
theme labels with short descriptions.

IN:  list of review dicts (from review_store.load_reviews)
OUT: ThemeList
"""

from groq import Groq

from llm_client.groq_client import chat, parse_json_response
from phase2.config import (
    GROQ_MODEL,
    MAX_TOKENS,
    MIN_THEMES,
    MAX_THEMES,
    REVIEW_TEXT_TRUNCATE,
    MAX_REVIEWS_FOR_DISCOVERY,
)
from phase2.models import ThemeList

_PROMPT_TEMPLATE = """\
You are a product analyst for INDMoney, a fintech app used in India.

Here are {count} user reviews (showing up to {max_shown}):

{review_text}

Identify exactly {min_themes}–{max_themes} distinct themes from these reviews.
Each theme should represent a recurring topic, pain point, or praise area.

Respond with ONLY valid JSON in this exact structure:
{{
  "themes": [
    {{
      "theme_id": 1,
      "label": "<short theme name, 2-4 words>",
      "description": "<one sentence describing what this theme covers>"
    }}
  ]
}}

Rules:
- Exactly {min_themes}–{max_themes} themes, numbered 1 to N
- Labels must be distinct and specific (not generic like "Other")
- Do not include any text outside the JSON\
"""


def discover_themes(reviews: list[dict], client: Groq) -> ThemeList:
    """
    Send reviews to Groq and return a ThemeList of 3–5 discovered themes.

    Args:
        reviews: list of review dicts from review_store.load_reviews()
        client:  Groq client instance

    Raises:
        ValueError: if reviews list is empty or response has wrong theme count
        json.JSONDecodeError: if Groq returns unparseable JSON
    """
    if not reviews:
        raise ValueError("reviews list is empty — nothing to discover themes from")

    capped = reviews[:MAX_REVIEWS_FOR_DISCOVERY]
    review_text = "\n".join(
        f"[{r['date']} | {r['rating']}★] {r['clean_text'][:REVIEW_TEXT_TRUNCATE]}"
        for r in capped
    )

    prompt = _PROMPT_TEMPLATE.format(
        count=len(reviews),
        max_shown=len(capped),
        review_text=review_text,
        min_themes=MIN_THEMES,
        max_themes=MAX_THEMES,
    )

    raw = chat(client, prompt, model=GROQ_MODEL, max_tokens=MAX_TOKENS)
    data = parse_json_response(raw)
    theme_list = ThemeList.from_groq_json(data)

    if not (MIN_THEMES <= theme_list.count <= MAX_THEMES):
        raise ValueError(
            f"Expected {MIN_THEMES}–{MAX_THEMES} themes from Groq, got {theme_list.count}"
        )

    return theme_list
