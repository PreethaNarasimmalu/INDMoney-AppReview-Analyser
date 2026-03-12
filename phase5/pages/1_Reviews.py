"""
Phase 5 — Reviews Page.

Shows a filterable table of all stored reviews (PII already scrubbed).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from phase1.review_store import get_connection, create_table, load_reviews
from phase2.store import migrate, load_themes

load_dotenv()

st.set_page_config(
    page_title="Reviews — INDMoney Pulse",
    page_icon="https://www.indmoney.com/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_IND_FAVICON = (
    "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmci"
    "IHZpZXdCb3g9IjAgMCA2NCA2NCI+CiAgPGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMzEiIGZp"
    "bGw9IiMxQTFBMUEiLz4KICA8dGV4dCB4PSIzMiIgeT0iNDAiIGZvbnQtZmFtaWx5PSJBcmlhbCxI"
    "ZWx2ZXRpY2Esc2Fucy1zZXJpZiIgZm9udC13ZWlnaHQ9IjkwMCIKICAgICAgICBmb250LXNpemU9"
    "IjIyIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgbGV0dGVyLXNwYWNpbmc9IjEi"
    "PklORDwvdGV4dD4KPC9zdmc+"
)
st.markdown(
    f'<link rel="shortcut icon" href="{_IND_FAVICON}">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
  [data-testid="collapsedControl"] { display: none !important; }
  section[data-testid="stSidebar"] { display: none !important; }
  .stApp { background: #F7F8FA; }
  .main .block-container { max-width: 1080px; padding: 2rem 2rem 4rem; }
  .ind-topbar {
    display: flex; align-items: center; gap: 14px;
    padding-bottom: 18px; border-bottom: 2px solid #E4E7EC; margin-bottom: 28px;
  }
  .ind-logo-circle {
    width: 42px; height: 42px; background: #1A1A1A; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 800; font-size: 12px; letter-spacing: -0.5px; flex-shrink: 0;
  }
  .ind-app-name { font-size: 22px; font-weight: 700; color: #1A1A1A; margin: 0; }
  .ind-app-sub { font-size: 13px; color: #8A94A6; margin: 0; }
  .filter-panel {
    background: white; border: 1px solid #E4E7EC; border-radius: 14px;
    padding: 20px 28px; margin-bottom: 24px;
  }
  .filter-label {
    font-size: 12px; font-weight: 600; color: #8A94A6;
    text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 14px;
  }
  .review-count {
    font-size: 13px; color: #8A94A6; margin-bottom: 12px;
  }
  .review-count strong { color: #1A1A1A; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ind-topbar">
  <div class="ind-logo-circle">IND</div>
  <div>
    <div class="ind-app-name">Reviews</div>
    <div class="ind-app-sub">All reviews are PII-scrubbed at ingestion · No personal data stored</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
conn = get_connection()
create_table(conn)
migrate(conn)

# ---------------------------------------------------------------------------
# Filters (inline, not sidebar)
# ---------------------------------------------------------------------------
st.markdown('<div class="filter-panel"><div class="filter-label">Filters</div>', unsafe_allow_html=True)
fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])

with fc1:
    weeks_options = {4: "Last 4 weeks", 8: "Last 8 weeks", 12: "Last 12 weeks"}
    selected_weeks = st.selectbox("Date window", options=list(weeks_options.keys()), format_func=lambda x: weeks_options[x], index=1)

all_reviews = load_reviews(conn, weeks=selected_weeks)

if not all_reviews:
    st.markdown("</div>", unsafe_allow_html=True)
    st.info("No reviews found. Run the pipeline from the Dashboard first.")
    st.stop()

df = pd.DataFrame(all_reviews)

with fc2:
    rating_filter = st.multiselect("Rating", options=[1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])

with fc3:
    themes = load_themes(conn)
    theme_options = {t["id"]: t["label"] for t in themes}
    theme_labels = ["All"] + list(theme_options.values())
    selected_theme = st.selectbox("Theme", theme_labels)

with fc4:
    search = st.text_input("Search text", placeholder="keyword…")

st.markdown("</div>", unsafe_allow_html=True)

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
st.markdown(
    f'<div class="review-count"><strong>{len(filtered)}</strong> reviews shown (of {len(df)} total)</div>',
    unsafe_allow_html=True,
)

display_cols = ["date", "rating", "clean_text", "week_label"]
if "theme_id" in filtered.columns:
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
