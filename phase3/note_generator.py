"""
Phase 3 — LLM Calls 3 & 4: Note Generation (Gemini).

Call 3 (generate_summaries):
  IN:  top-3 themes + their classified reviews
  OUT: ThemeSummary × 3  (2-3 sentence summary + representative quote each)

Call 4 (generate_action_ideas):
  IN:  3 ThemeSummary objects
  OUT: list of 3 action idea strings
"""

import sqlite3

from llm_client.gemini_client import chat, parse_json_response
from phase3.config import GEMINI_MODEL, MAX_TOKENS, TOP_N_THEMES, REVIEW_TEXT_TRUNCATE
from phase3.models import ThemeSummary, PulseNote
from phase2.store import load_themes, load_classified_reviews


# ---------------------------------------------------------------------------
# LLM Call 3 — Theme Summariser + Quote Picker
# ---------------------------------------------------------------------------

_SUMMARY_PROMPT_TEMPLATE = """\
You are a product analyst for INDMoney, a fintech app used in India.

Below are the top {n} user feedback themes from this week's app reviews, \
each followed by the actual user reviews assigned to that theme.

{themes_block}

For each theme provide:
1. A 2-3 sentence summary of what users are saying about this theme.
2. The single most representative verbatim quote from the reviews listed for that theme.
   Pick a quote that best captures the core sentiment. Use the exact text as written.

Respond with ONLY valid JSON in this exact structure:
{{
  "themes": [
    {{
      "theme_id": <int>,
      "summary": "<2-3 sentence summary>",
      "representative_quote": "<exact verbatim quote from the review list>",
      "quote_rating": <star rating 1-5 of that review>,
      "quote_platform": "<platform of that review, e.g. Google Play>"
    }}
  ]
}}

Rules:
- One entry per theme, in the same order as above
- Do not invent quotes — use only text from the reviews provided
- Do not include any text outside the JSON\
"""


def _build_themes_block(
    top_themes: list[dict],
    reviews_by_theme: dict[int, list[dict]],
) -> str:
    """Format themes + their reviews into a readable block for the LLM prompt."""
    blocks = []
    for i, theme in enumerate(top_themes, 1):
        tid = theme["id"]
        theme_reviews = reviews_by_theme.get(tid, [])
        reviews_text = "\n".join(
            f"  [{r['rating']}★ | {r.get('platform', 'Google Play')}] "
            f"{r['clean_text'][:REVIEW_TEXT_TRUNCATE]}"
            for r in theme_reviews
        ) or "  (no reviews)"

        blocks.append(
            f"THEME {i}: {theme['label']} — {theme['description']}\n"
            f"Reviews:\n{reviews_text}"
        )
    return "\n\n".join(blocks)


def generate_summaries(
    top_themes: list[dict],
    reviews_by_theme: dict[int, list[dict]],
    genai,
) -> list[ThemeSummary]:
    """
    LLM Call 3: ask Gemini to summarise each theme and pick a representative quote.

    Args:
        top_themes:       list of theme dicts (id, label, description, review_count),
                          already sorted by review_count desc, max TOP_N_THEMES entries
        reviews_by_theme: dict mapping theme_id -> list of classified review dicts
        genai:            configured Gemini genai module from get_gemini_client()

    Returns:
        list of ThemeSummary, one per theme, in the same order as top_themes
    """
    if not top_themes:
        raise ValueError("top_themes is empty — nothing to summarise")

    themes_block = _build_themes_block(top_themes, reviews_by_theme)
    prompt = _SUMMARY_PROMPT_TEMPLATE.format(
        n=len(top_themes),
        themes_block=themes_block,
    )

    raw = chat(genai, prompt, model=GEMINI_MODEL, max_tokens=MAX_TOKENS)
    data = parse_json_response(raw)

    raw_themes = data.get("themes", [])
    if len(raw_themes) != len(top_themes):
        raise ValueError(
            f"Expected {len(top_themes)} theme summaries from Gemini, got {len(raw_themes)}"
        )

    summaries = []
    for i, t in enumerate(raw_themes):
        # Use positional match first (Gemini preserves input order),
        # fall back to id-based lookup if counts differ
        if i < len(top_themes):
            source_theme = top_themes[i]
        else:
            source_theme = next(
                (th for th in top_themes if th["id"] == int(t.get("theme_id", 0))),
                top_themes[0],
            )
        rating = int(t.get("quote_rating", 5))
        rating = max(1, min(5, rating))  # clamp to 1-5

        summaries.append(ThemeSummary(
            theme_id=source_theme["id"],
            label=source_theme["label"],
            summary=str(t["summary"]).strip(),
            representative_quote=str(t["representative_quote"]).strip(),
            quote_rating=rating,
            quote_platform=str(t.get("quote_platform", "Google Play")).strip(),
        ))
    return summaries


# ---------------------------------------------------------------------------
# LLM Call 4 — Action Idea Generator
# ---------------------------------------------------------------------------

_ACTION_PROMPT_TEMPLATE = """\
You are a product analyst for INDMoney, a fintech app used in India.

Based on this week's top user feedback themes:

{summaries_block}

1. Propose exactly 3 concrete, actionable product or support recommendations \
that address these user pain points. Each action should be specific and \
implementable.

2. Also identify exactly 3 things users are genuinely praising — features or \
experiences that are working well and should be preserved or amplified.

Respond with ONLY valid JSON in this exact structure:
{{
  "action_ideas": [
    "Action 1: <specific recommendation>",
    "Action 2: <specific recommendation>",
    "Action 3: <specific recommendation>"
  ],
  "whats_working": [
    "<Short Title>: <one sentence describing what users love>",
    "<Short Title>: <one sentence describing what users love>",
    "<Short Title>: <one sentence describing what users love>"
  ]
}}

Rules:
- Exactly 3 action ideas and exactly 3 whats_working items
- Each action must start with "Action N: "
- Each whats_working item must be in the format "Short Title: description" where Short Title is 2-4 words
- Do not include any text outside the JSON\
"""


def generate_action_ideas(
    summaries: list[ThemeSummary], genai
) -> tuple[list[str], list[str]]:
    """
    LLM Call 4: ask Gemini for 3 actionable recommendations and 3 "what's working"
    highlights based on theme summaries.

    Args:
        summaries: list of ThemeSummary objects (typically 3)
        genai:     configured Gemini genai module

    Returns:
        (action_ideas, whats_working) — each a list of 3 strings
    """
    if not summaries:
        raise ValueError("summaries is empty — nothing to generate action ideas from")

    summaries_block = "\n".join(
        f"{i}. {s.label}: {s.summary}"
        for i, s in enumerate(summaries, 1)
    )
    prompt = _ACTION_PROMPT_TEMPLATE.format(summaries_block=summaries_block)

    raw = chat(genai, prompt, model=GEMINI_MODEL, max_tokens=MAX_TOKENS)
    data = parse_json_response(raw)

    ideas = data.get("action_ideas", [])
    if len(ideas) != 3:
        raise ValueError(f"Expected 3 action ideas from Gemini, got {len(ideas)}")

    working = data.get("whats_working", [])
    if len(working) != 3:
        raise ValueError(f"Expected 3 whats_working items from Gemini, got {len(working)}")

    return (
        [str(idea).strip() for idea in ideas],
        [str(item).strip() for item in working],
    )


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def generate_pulse(conn: sqlite3.Connection, genai, weeks: int = 8) -> PulseNote:
    """
    Orchestrate LLM Calls 3 & 4 to produce a PulseNote.

    Loads top themes + classified reviews from the DB, calls Gemini twice,
    and returns a fully populated PulseNote ready for the assembler.
    """
    from datetime import datetime, timezone

    # Load themes sorted by review_count desc
    all_themes = load_themes(conn)
    if not all_themes:
        raise ValueError("No themes found in DB — run Phase 2 first")

    top_themes = all_themes[:TOP_N_THEMES]
    top_ids = {t["id"] for t in top_themes}

    # Load classified reviews and group by theme_id
    all_reviews = load_classified_reviews(conn, weeks=weeks)
    reviews_by_theme: dict[int, list[dict]] = {t["id"]: [] for t in top_themes}
    for r in all_reviews:
        if r.get("theme_id") in top_ids:
            reviews_by_theme[r["theme_id"]].append(r)

    # LLM Call 3
    summaries = generate_summaries(top_themes, reviews_by_theme, genai)

    # LLM Call 4
    action_ideas, whats_working = generate_action_ideas(summaries, genai)

    # Week label: Monday of the current week
    today = datetime.now(timezone.utc).date()
    week_start = today - __import__("datetime").timedelta(days=today.weekday())
    week_label = f"Week of {week_start.isoformat()}"

    return PulseNote(
        week_label=week_label,
        theme_summaries=summaries,
        action_ideas=action_ideas,
        whats_working=whats_working,
    )
