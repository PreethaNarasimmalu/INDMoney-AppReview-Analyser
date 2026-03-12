"""
Phase 5 — Themes Page.

Shows theme cards with review counts, ratings, and expandable review lists.
"""

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from phase1.review_store import get_connection, create_table
from phase2.store import migrate, load_themes, load_classified_reviews

load_dotenv()

st.set_page_config(page_title="Themes — INDMoney Pulse", layout="wide")
st.title("🏷 Themes")
st.caption("Themes are discovered fresh each pipeline run from the current review window.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
conn = get_connection()
create_table(conn)
migrate(conn)

themes = load_themes(conn)
reviews = load_classified_reviews(conn)

if not themes:
    st.info("No themes found. Run the pipeline from the Dashboard first.")
    st.stop()

# Build review lookup: theme_id → list of review dicts
reviews_by_theme: dict[int, list[dict]] = {}
for r in reviews:
    tid = r.get("theme_id")
    if tid is not None:
        reviews_by_theme.setdefault(tid, []).append(r)

# ---------------------------------------------------------------------------
# Theme cards
# ---------------------------------------------------------------------------
for theme in themes:
    tid = theme["id"]
    theme_reviews = reviews_by_theme.get(tid, [])
    avg_rating = (
        sum(r["rating"] for r in theme_reviews) / len(theme_reviews)
        if theme_reviews else 0.0
    )
    stars = "★" * round(avg_rating) + "☆" * (5 - round(avg_rating))

    with st.container(border=True):
        col1, col2, col3 = st.columns([4, 1, 1])
        col1.markdown(f"**{theme['label']}**")
        col2.markdown(f"**{theme['review_count']}** reviews")
        col3.markdown(f"{stars} {avg_rating:.1f}")

        if theme.get("description"):
            st.caption(theme["description"])

        if theme_reviews:
            with st.expander(f"Show {len(theme_reviews)} reviews"):
                df = pd.DataFrame(theme_reviews)[["date", "rating", "clean_text"]]
                st.dataframe(
                    df.rename(columns={"date": "Date", "rating": "Rating", "clean_text": "Review"}),
                    use_container_width=True,
                    hide_index=True,
                )
