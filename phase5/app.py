"""
Phase 5 — Streamlit Dashboard (main page).

Run with:
    streamlit run phase5/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="INDMoney App Review Pulse",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# INDMoney brand CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  /* Hide sidebar toggle */
  [data-testid="collapsedControl"] { display: none !important; }
  section[data-testid="stSidebar"] { display: none !important; }

  /* Page background */
  .stApp { background: #F7F8FA; }

  /* Main container */
  .main .block-container {
    max-width: 1080px;
    padding: 2rem 2rem 4rem;
  }

  /* Topbar */
  .ind-topbar {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 18px;
    border-bottom: 2px solid #E4E7EC;
    margin-bottom: 28px;
  }
  .ind-logo-circle {
    width: 42px; height: 42px;
    background: #1A1A1A;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 800; font-size: 12px; letter-spacing: -0.5px;
    flex-shrink: 0;
  }
  .ind-app-name {
    font-size: 22px; font-weight: 700; color: #1A1A1A; margin: 0;
  }
  .ind-app-sub {
    font-size: 13px; color: #8A94A6; margin: 0;
  }

  /* Config panel */
  .config-panel {
    background: white;
    border: 1px solid #E4E7EC;
    border-radius: 14px;
    padding: 24px 28px 20px;
    margin-bottom: 24px;
  }
  .config-label {
    font-size: 12px; font-weight: 600; color: #8A94A6;
    text-transform: uppercase; letter-spacing: 0.6px;
    margin-bottom: 18px;
  }

  /* Primary green button */
  div[data-testid="stButton"] > button[kind="primary"] {
    background: #2DB34A !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 32px !important;
    width: 100%;
    transition: background 0.2s;
  }
  div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #249C3F !important;
  }

  /* Secondary button (download) */
  div[data-testid="stDownloadButton"] > button {
    background: white !important;
    color: #2DB34A !important;
    border: 1.5px solid #2DB34A !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
  }

  /* Metric cards */
  div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E4E7EC;
    border-radius: 12px;
    padding: 16px 20px !important;
  }
  div[data-testid="stMetricValue"] {
    font-size: 30px !important;
    font-weight: 700 !important;
    color: #1A1A1A !important;
  }
  div[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    color: #8A94A6 !important;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  /* Section card */
  .section-card {
    background: white;
    border: 1px solid #E4E7EC;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 20px;
  }
  .section-title {
    font-size: 16px; font-weight: 700; color: #1A1A1A;
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }
  .green-dot {
    width: 8px; height: 8px;
    background: #2DB34A; border-radius: 50%;
    display: inline-block;
  }

  /* Phase progress step */
  .progress-step {
    font-size: 13px; color: #2DB34A; font-weight: 500;
    padding: 4px 0;
  }

  /* Empty state */
  .empty-state {
    text-align: center; padding: 60px 20px;
    color: #8A94A6;
  }
  .empty-state-icon { font-size: 48px; margin-bottom: 12px; }
  .empty-state-text { font-size: 15px; }

  /* Email section */
  .email-note {
    font-size: 12px; color: #8A94A6; margin-top: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Topbar
# ---------------------------------------------------------------------------
st.markdown("""
<div class="ind-topbar">
  <div class="ind-logo-circle">IND</div>
  <div>
    <div class="ind-app-name">App Review Pulse</div>
    <div class="ind-app-sub">Weekly intelligence from Google Play · Groq + Gemini</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Configuration panel (inline, not sidebar)
# ---------------------------------------------------------------------------
st.markdown('<div class="config-panel"><div class="config-label">Configuration</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([3, 3, 2])
with col1:
    weeks = st.slider("Review window (weeks)", min_value=1, max_value=16, value=8)
with col2:
    max_reviews = st.number_input("Max reviews to scrape", min_value=100, max_value=2000, value=1000, step=100)
with col3:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run_clicked = st.button("▶  Run Now", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------
if run_clicked:
    from phase5.pipeline_runner import run_pipeline

    progress_bar = st.progress(0)
    status_slot = st.empty()

    def _on_progress(msg: str, pct: int) -> None:
        progress_bar.progress(pct)
        status_slot.markdown(
            f'<div class="progress-step">● {msg}</div>',
            unsafe_allow_html=True,
        )

    try:
        result = run_pipeline(weeks=weeks, max_reviews=max_reviews, on_progress=_on_progress)
        st.session_state["last_result"] = result
        progress_bar.progress(100)
        status_slot.success("Pipeline complete!")
    except Exception as exc:
        progress_bar.empty()
        status_slot.empty()
        st.error(f"Pipeline failed: {exc}")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reviews Analysed", f"{result.review_count:,}")
    m2.metric("New This Run", f"{result.new_reviews:,}")
    m3.metric("Themes Found", result.theme_count)
    m4.metric("Old Reviews Purged", result.purged_reviews)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Pulse note card
    st.markdown(f"""
    <div class="section-card">
      <div class="section-title">
        <span class="green-dot"></span> Weekly Pulse — {result.week_label}
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.code(result.pulse_markdown, language=None)

    st.download_button(
        label="⬇  Download Report (.md)",
        data=result.pulse_markdown,
        file_name=f"weekly_pulse_{result.week_label.replace(' ', '_')}.md",
        mime="text/plain",
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Send email card
    st.markdown('<div class="section-card"><div class="section-title"><span class="green-dot"></span> Send Email</div>', unsafe_allow_html=True)
    with st.form("email_form"):
        ec1, ec2 = st.columns(2)
        recipient_name = ec1.text_input("Recipient Name", placeholder="Product Team")
        recipient_email = ec2.text_input("Recipient Email", placeholder="team@indmoney.com")
        st.markdown('<div class="email-note">Email is sent directly from your GMAIL_ADDRESS configured in .env</div>', unsafe_allow_html=True)
        send_clicked = st.form_submit_button("Send Email")

        if send_clicked:
            if not recipient_email.strip():
                st.error("Recipient email is required.")
            else:
                try:
                    from phase4.composer import compose
                    from phase4.sender import send_email, _get_credentials
                    from_header, _, _ = _get_credentials()
                    msg = compose(
                        markdown=result.pulse_markdown,
                        week_label=result.week_label,
                        recipient_name=recipient_name,
                        recipient_email=recipient_email,
                        sender_address=from_header,
                    )
                    send_email(msg)
                    st.success(f"Email sent to **{recipient_email}**!")
                except Exception as exc:
                    st.error(f"Failed to send email: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-state-icon">📊</div>
      <div class="empty-state-text">Configure the settings above and click <strong>Run Now</strong> to generate the weekly pulse.</div>
    </div>
    """, unsafe_allow_html=True)
