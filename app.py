import os
import streamlit as st
import pandas as pd
import plotly.express as px
import anthropic
from dotenv import load_dotenv
from scraper import fetch_reviews
from analyzer import analyze_reviews

load_dotenv()

st.set_page_config(
    page_title="App Review Pulse",
    page_icon="📱",
    layout="wide"
)

st.title("📱 App Review Pulse")
st.caption("Analyse Google Play reviews for any app using Claude AI")

# --- Sidebar inputs ---
with st.sidebar:
    st.header("Settings")
    app_id = st.text_input(
        "Google Play App ID",
        value="com.indmoney",
        help="e.g. com.indmoney or com.phonepe.app"
    )
    weeks = st.selectbox(
        "Date window",
        options=[4, 6, 8, 10, 12, 16],
        index=2,  # default: 8 weeks
        format_func=lambda w: f"Last {w} weeks"
    )
    max_reviews = st.number_input(
        "Max reviews to fetch",
        min_value=50,
        max_value=5000,
        value=1000,
        step=50,
        help="Leave at 1000 to fetch all reviews in the date window up to this cap"
    )
    api_key = st.text_input(
        "Anthropic API Key",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Get yours at console.anthropic.com"
    )
    run = st.button("▶ Run Analysis", type="primary", use_container_width=True)

# --- Main area ---
if not run:
    st.info("Configure settings in the sidebar and click **Run Analysis** to start.")
    st.stop()

if not api_key:
    st.error("Please enter your Anthropic API key in the sidebar.")
    st.stop()

# Step 1: Fetch reviews
with st.status(f"Fetching reviews for `{app_id}`…", expanded=True) as status:
    try:
        fetched = fetch_reviews(app_id, max_count=max_reviews, weeks=weeks)
        status.update(
            label=f"Fetched **{len(fetched):,}** reviews from the last {weeks} weeks",
            state="complete"
        )
    except Exception as e:
        status.update(label=f"Failed to fetch reviews: {e}", state="error")
        st.stop()

if not fetched:
    st.warning("No reviews found in the selected date window. Try a wider window or different app ID.")
    st.stop()

# Step 2: Analyse with Claude
with st.status("Analysing reviews with Claude…", expanded=False) as status:
    try:
        client = anthropic.Anthropic(api_key=api_key)
        analysis = analyze_reviews(fetched, client)
        status.update(label="Analysis complete", state="complete")
    except Exception as e:
        status.update(label=f"Analysis failed: {e}", state="error")
        st.stop()

# --- Results ---
st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Reviews Analysed", f"{len(fetched):,}")
col2.metric("Date Window", f"Last {weeks} weeks")
avg_rating = sum(r['rating'] for r in fetched) / len(fetched)
col3.metric("Avg Rating", f"{avg_rating:.1f} ★")

st.divider()

# Sentiment donut
sentiment = analysis.get("sentiment", {})
if sentiment:
    col_sent, col_themes = st.columns([1, 2])
    with col_sent:
        st.subheader("Sentiment")
        fig = px.pie(
            values=[sentiment.get("positive", 0), sentiment.get("neutral", 0), sentiment.get("negative", 0)],
            names=["Positive", "Neutral", "Negative"],
            color_discrete_sequence=["#22c55e", "#f59e0b", "#ef4444"],
            hole=0.5
        )
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
        st.plotly_chart(fig, use_container_width=True)

    with col_themes:
        st.subheader("Top Themes")
        themes = analysis.get("themes", [])
        if themes:
            df = pd.DataFrame(themes)
            color_map = {"positive": "#22c55e", "neutral": "#f59e0b", "negative": "#ef4444"}
            for _, row in df.iterrows():
                color = color_map.get(row.get("sentiment", "neutral"), "#f59e0b")
                with st.expander(f"**{row['theme']}** — ~{row.get('count', '?')} reviews"):
                    for ex in row.get("examples", []):
                        st.markdown(f"> {ex}")

st.divider()
st.subheader("Summary")
st.info(analysis.get("summary", "No summary available."))

action_items = analysis.get("action_items", [])
if action_items:
    st.subheader("Action Items")
    for item in action_items:
        st.markdown(f"- {item}")

# Raw data toggle
with st.expander("View raw reviews"):
    df_raw = pd.DataFrame(fetched)
    st.dataframe(df_raw, use_container_width=True)
