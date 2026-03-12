"""
Phase 5 — Pipeline Runner.

Orchestrates Phases 1–4 in sequence. Called by the Streamlit UI
and the headless CLI runner.

Progress is reported via an optional callback:
    on_progress(message: str, percent: int)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from phase1.scraper import fetch_reviews
from phase1.pii_scrubber import scrub_reviews
from phase1.review_store import (
    get_connection,
    create_table,
    upsert_reviews,
    purge_old_reviews,
    load_reviews,
)
from phase1.config import DEFAULT_APP_ID, RETENTION_WEEKS

from phase2.store import migrate, save_themes, save_classifications, load_themes
from phase2.theme_discovery import discover_themes
from phase2.classifier import classify_reviews
from phase2.validator import validate_and_merge

from phase3.note_generator import generate_pulse
from phase3.assembler import assemble

from llm_client.groq_client import get_groq_client
from llm_client.gemini_client import get_gemini_client


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    week_label: str
    review_count: int        # reviews in the analysis window
    new_reviews: int         # newly scraped this run
    purged_reviews: int      # old reviews deleted this run
    theme_count: int
    pulse_markdown: str
    themes: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_pipeline(
    weeks: int = 8,
    max_reviews: int = 1000,
    db_path: Path | None = None,
    on_progress: Callable[[str, int], None] | None = None,
) -> PipelineResult:
    """
    Run the full INDMoney App Review Pulse pipeline.

    Args:
        weeks:        number of weeks to analyse (default 8)
        max_reviews:  max reviews to scrape (default 1000)
        db_path:      override SQLite DB path (used in tests)
        on_progress:  optional callback(message, percent) for UI progress

    Returns:
        PipelineResult with pulse markdown, metrics, and theme list.

    Raises:
        ValueError: if no reviews found in the date window after scraping
    """
    def _progress(msg: str, pct: int) -> None:
        if on_progress:
            on_progress(msg, pct)

    # ------------------------------------------------------------------ #
    # Phase 1 — Ingestion                                                 #
    # ------------------------------------------------------------------ #
    _progress("Phase 1: Fetching reviews from Google Play…", 5)
    fetch_result = fetch_reviews(app_id=DEFAULT_APP_ID, max_count=max_reviews, weeks=weeks)
    scrubbed = scrub_reviews(fetch_result.reviews)

    _progress("Phase 1: Storing reviews in DB…", 15)
    conn = get_connection(db_path)
    create_table(conn)
    migrate(conn)
    new_count = upsert_reviews(scrubbed, conn)
    purged_count = purge_old_reviews(conn, RETENTION_WEEKS)

    reviews = load_reviews(conn, weeks=weeks)
    if not reviews:
        raise ValueError(
            f"No reviews found in the last {weeks} weeks. "
            "Try increasing the review window or max reviews."
        )

    _progress(f"Phase 1 complete — {len(reviews)} reviews loaded, {new_count} new", 20)

    # ------------------------------------------------------------------ #
    # Phase 2 — Theme Grouping                                            #
    # ------------------------------------------------------------------ #
    _progress("Phase 2: Discovering themes with Groq…", 30)
    groq = get_groq_client()
    theme_list = discover_themes(reviews, groq)

    _progress("Phase 2: Classifying reviews…", 50)
    classified = classify_reviews(reviews, theme_list, groq)
    theme_list, classified = validate_and_merge(theme_list, classified)

    save_themes(theme_list, conn)
    save_classifications(classified, conn)
    _progress(f"Phase 2 complete — {len(theme_list.themes)} themes found", 60)

    # ------------------------------------------------------------------ #
    # Phase 3 — Note Generation                                           #
    # ------------------------------------------------------------------ #
    _progress("Phase 3: Generating weekly pulse with Gemini…", 70)
    gemini = get_gemini_client()
    pulse_note = generate_pulse(conn, gemini, weeks=weeks)
    pulse_markdown = assemble(pulse_note)
    _progress("Phase 3 complete — pulse note assembled", 90)

    themes = load_themes(conn)

    _progress("Pipeline complete.", 100)
    return PipelineResult(
        week_label=pulse_note.week_label,
        review_count=len(reviews),
        new_reviews=new_count,
        purged_reviews=purged_count,
        theme_count=len(themes),
        pulse_markdown=pulse_markdown,
        themes=themes,
    )
