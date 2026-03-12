"""
Phase 5 — Themes Page.

Shows theme cards with review counts, ratings, and expandable review lists.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from phase1.review_store import get_connection, create_table
from phase2.store import migrate, load_themes, load_classified_reviews

load_dotenv()

st.set_page_config(
    page_title="Themes — INDMoney Pulse",
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
  .theme-card {
    background: white; border: 1px solid #E4E7EC; border-radius: 14px;
    padding: 20px 24px; margin-bottom: 14px;
  }
  .theme-name { font-size: 15px; font-weight: 700; color: #1A1A1A; margin-bottom: 4px; }
  .theme-desc { font-size: 13px; color: #8A94A6; margin-bottom: 10px; }
  .theme-meta { display: flex; gap: 20px; align-items: center; margin-top: 6px; }
  .theme-badge {
    font-size: 12px; font-weight: 600; background: #F0FBF3;
    color: #2DB34A; border-radius: 20px; padding: 3px 10px;
  }
  .theme-rating { font-size: 13px; color: #8A94A6; }
  .stars-filled { color: #2DB34A; }
  .stars-empty { color: #D1D5DB; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="ind-topbar">
  <div class="ind-logo-circle">IND</div>
  <div>
    <div class="ind-app-name">Themes</div>
    <div class="ind-app-sub">Discovered fresh each pipeline run from the current review window</div>
  </div>
</div>
""", unsafe_allow_html=True)

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
    filled = round(avg_rating)
    stars_html = (
        f'<span class="stars-filled">{"★" * filled}</span>'
        f'<span class="stars-empty">{"★" * (5 - filled)}</span>'
    )

    st.markdown(f"""
    <div class="theme-card">
      <div class="theme-name">{theme['label']}</div>
      {"<div class='theme-desc'>" + theme['description'] + "</div>" if theme.get('description') else ""}
      <div class="theme-meta">
        <span class="theme-badge">{theme['review_count']} reviews</span>
        <span class="theme-rating">{stars_html} {avg_rating:.1f}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if theme_reviews:
        with st.expander(f"Show {len(theme_reviews)} reviews for "{theme['label']}""):
            df = pd.DataFrame(theme_reviews)[["date", "rating", "clean_text"]]
            st.dataframe(
                df.rename(columns={"date": "Date", "rating": "Rating", "clean_text": "Review"}),
                use_container_width=True,
                hide_index=True,
            )
