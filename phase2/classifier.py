"""
Phase 2 — LLM Call 2: Review Classifier (Groq, batched).

Takes each review and the discovered ThemeList, assigns every review
to exactly one theme_id. Processed in batches to stay within rate limits.

IN:  list of review dicts + ThemeList
OUT: list[ClassifiedReview]
"""

from groq import Groq

from llm_client.groq_client import chat, parse_json_response
from phase2.config import (
    GROQ_MODEL,
    MAX_TOKENS,
    CLASSIFIER_BATCH_SIZE,
    REVIEW_TEXT_TRUNCATE,
)
from phase2.models import ThemeList, ClassifiedReview
from phase2.review_filter import filter_reviews

_PROMPT_TEMPLATE = """\
You are classifying app reviews into predefined themes.

Available themes:
{themes_text}

Classify each of the following reviews into exactly one theme.
Use the theme_id number only. If a review could fit multiple themes, pick the best one.

Reviews:
{reviews_text}

Respond with ONLY valid JSON:
{{
  "classifications": [
    {{"id": "<review_id>", "theme_id": <integer>}}
  ]
}}

- Every review must appear exactly once in the output
- theme_id must be one of: {valid_ids}
- Do not include any text outside the JSON\
"""


def _build_themes_text(theme_list: ThemeList) -> str:
    return "\n".join(
        f"  {t.theme_id}. {t.label} — {t.description}"
        for t in theme_list.themes
    )


def _build_reviews_text(batch: list[dict]) -> str:
    return "\n".join(
        f"  id={r['id']} [{r['rating']}★] {r['clean_text'][:REVIEW_TEXT_TRUNCATE]}"
        for r in batch
    )


def _classify_batch(
    batch: list[dict],
    theme_list: ThemeList,
    client: Groq,
) -> list[ClassifiedReview]:
    """Classify one batch of reviews. Returns ClassifiedReview list."""
    valid_ids = ", ".join(str(i) for i in theme_list.ids())
    prompt = _PROMPT_TEMPLATE.format(
        themes_text=_build_themes_text(theme_list),
        reviews_text=_build_reviews_text(batch),
        valid_ids=valid_ids,
    )

    raw = chat(client, prompt, model=GROQ_MODEL, max_tokens=MAX_TOKENS)
    data = parse_json_response(raw)

    results = []
    valid_id_set = set(theme_list.ids())
    for item in data.get("classifications", []):
        theme_id = int(item["theme_id"])
        if theme_id not in valid_id_set:
            # Fall back to first theme rather than crashing the whole batch
            theme_id = theme_list.themes[0].theme_id
        results.append(ClassifiedReview(
            review_id=str(item["id"]),
            theme_id=theme_id,
        ))
    return results


def classify_reviews(
    reviews: list[dict],
    theme_list: ThemeList,
    client: Groq,
) -> list[ClassifiedReview]:
    """
    Classify all reviews into themes using Groq (batched).

    Args:
        reviews:    list of review dicts from review_store.load_reviews()
        theme_list: ThemeList from theme_discovery.discover_themes()
        client:     Groq client instance

    Raises:
        ValueError: if reviews or themes are empty
    """
    if not reviews:
        raise ValueError("reviews list is empty — nothing to classify")
    if not theme_list.themes:
        raise ValueError("theme_list is empty — cannot classify without themes")

    reviews, _ = filter_reviews(reviews)

    classified: list[ClassifiedReview] = []
    for i in range(0, len(reviews), CLASSIFIER_BATCH_SIZE):
        batch = reviews[i: i + CLASSIFIER_BATCH_SIZE]
        classified.extend(_classify_batch(batch, theme_list, client))

    return classified
