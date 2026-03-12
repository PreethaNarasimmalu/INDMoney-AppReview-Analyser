"""
Phase 5 — Reviews Page.

Shows a filterable table of all stored reviews (PII already scrubbed).
"""

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from phase1.review_store import get_connection, create_table, load_reviews
from phase2.store import migrate, load_themes

load_dotenv()

st.set_page_config(page_title="Reviews — INDMoney Pulse", layout="wide")
st.title("🗂 Reviews")
st.caption("All reviews are PII-scrubbed at ingestion. No personal data is stored.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
conn = get_connection()
create_table(conn)
migrate(conn)

weeks_options = {4: "Last 4 weeks", 8: "Last 8 weeks", 12: "Last 12 weeks"}
selected_weeks = st.sidebar.selectbox("Date window", options=list(weeks_options.keys()), format_func=lambda x: weeks_options[x], index=1)

all_reviews = load_reviews(conn, weeks=selected_weeks)

if not all_reviews:
    st.info("No reviews found. Run the pipeline from the Dashboard first.")
    st.stop()

df = pd.DataFrame(all_reviews)

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")

    rating_filter = st.multiselect(
        "Rating", options=[1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5]
    )

    themes = load_themes(conn)
    theme_options = {t["id"]: t["label"] for t in themes}
    theme_labels = ["All"] + list(theme_options.values())
    selected_theme = st.selectbox("Theme", theme_labels)

    search = st.text_input("Search text", placeholder="keyword…")

# Apply filters
filtered = df[df["rating"].isin(rating_filter)]

if selected_theme != "All":
    theme_id = next((k for k, v in theme_options.items() if v == selected_theme), None)
    if theme_id is not None and "theme_id" in filtered.columns:
        filtered = filtered[filtered["theme_id"] == theme_id]

if search.strip():
    filtered = filtered[filtered["clean_text"].str.contains(search.strip(), case=False, na=False)]

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
st.markdown(f"**{len(filtered)}** reviews shown (of {len(df)} total)")

display_cols = ["date", "rating", "clean_text", "week_label"]
if "theme_id" in filtered.columns:
    # Map theme_id → label
    filtered = filtered.copy()
    filtered["theme"] = filtered["theme_id"].map(theme_options).fillna("—")
    display_cols = ["date", "rating", "theme", "clean_text"]

st.dataframe(
    filtered[display_cols].rename(columns={
        "date": "Date",
        "rating": "Rating",
        "clean_text": "Review",
        "week_label": "Week",
        "theme": "Theme",
    }),
    use_container_width=True,
    hide_index=True,
)
