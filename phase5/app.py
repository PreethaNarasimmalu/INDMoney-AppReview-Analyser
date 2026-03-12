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
# CSS — INDMoney brand, section-card structure
# ---------------------------------------------------------------------------
st.markdown("""
<style>
  [data-testid="collapsedControl"] { display: none !important; }
  section[data-testid="stSidebar"]  { display: none !important; }

  .stApp { background: #F7F8FA; }
  .main .block-container {
    max-width: 760px;
    padding: 3.5rem 2rem 5rem;
  }

  /* Page header */
  .page-title {
    font-size: 34px; font-weight: 800; color: #1A1A1A;
    margin: 0 0 8px; line-height: 1.15;
  }
  .page-sub {
    font-size: 15px; color: #8A94A6; margin: 0 0 36px;
  }

  /* Cards */
  .card {
    background: white;
    border: 1px solid #E4E7EC;
    border-radius: 14px;
    padding: 26px 30px 22px;
    margin-bottom: 16px;
  }
  .card-title {
    font-size: 18px; font-weight: 700; color: #1A1A1A;
    margin: 0 0 10px;
  }
  .card-desc {
    font-size: 14px; color: #6B7280; line-height: 1.6;
    margin: 0 0 20px;
  }

  /* Status badges */
  .badge-row {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    margin-top: 4px;
  }
  .badge {
    font-size: 13px; font-weight: 600;
    padding: 5px 14px; border-radius: 6px;
    border: 1.5px solid #D1D5DB;
    color: #9CA3AF; background: #F9FAFB;
  }
  .badge-on {
    background: #F0FBF3; color: #2DB34A; border-color: #2DB34A;
  }
  .badge-date {
    font-size: 13px; color: #8A94A6; margin-left: 6px;
  }

  /* Primary green button */
  div[data-testid="stButton"] > button[kind="primary"] {
    background: #2DB34A !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 9px 26px !important;
  }
  div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #249C3F !important;
  }

  /* Outline / secondary button */
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: white !important;
    color: #2DB34A !important;
    border: 1.5px solid #2DB34A !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
  }

  /* Download button */
  div[data-testid="stDownloadButton"] > button {
    background: white !important;
    color: #2DB34A !important;
    border: 1.5px solid #2DB34A !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
  }

  /* Form submit button */
  div[data-testid="stFormSubmitButton"] > button {
    background: #2DB34A !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 9px 26px !important;
  }

  /* Input labels */
  label[data-testid="stWidgetLabel"] p {
    font-size: 13px !important;
    color: #4B5563 !important;
    font-weight: 500 !important;
  }

  /* Progress step */
  .progress-step {
    font-size: 13px; color: #2DB34A; font-weight: 500; padding: 3px 0;
  }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="page-title">INDMoney App Review Pulse</div>
<div class="page-sub">Generate the one-page weekly pulse from Play Store reviews and send it by email.</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
result = st.session_state.get("last_result")
has_result = result is not None


def _badge(label: str, active: bool) -> str:
    cls = "badge badge-on" if active else "badge"
    return f'<span class="{cls}">{label}</span>'


# ---------------------------------------------------------------------------
# 1. Status card
# ---------------------------------------------------------------------------
date_html = (
    f'<span class="badge-date">Report date: {result.week_label}</span>'
    if has_result else ""
)
st.markdown(f"""
<div class="card">
  <div class="card-title">Status</div>
  <div class="badge-row">
    {_badge("Reviews",     has_result)}
    {_badge("Themes",      has_result)}
    {_badge("Grouped",     has_result)}
    {_badge("Report",      has_result)}
    {_badge("Draft email", has_result)}
    {date_html}
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. Run pipeline card
# ---------------------------------------------------------------------------
st.markdown("""
<div class="card">
  <div class="card-title">Run pipeline</div>
  <div class="card-desc">
    Scrape reviews &rarr; discover themes &rarr; classify &rarr; generate report
    &rarr; create draft email. This may take several minutes.
  </div>
""", unsafe_allow_html=True)

weeks = st.selectbox(
    "Weeks of reviews",
    options=list(range(1, 17)),
    index=7,
    format_func=lambda x: str(x),
)
max_reviews = st.number_input(
    "Max reviews to fetch",
    min_value=100, max_value=5000, value=1000, step=100,
)
run_clicked = st.button("Run full pipeline", type="primary")

st.markdown("</div>", unsafe_allow_html=True)

if run_clicked:
    from phase5.pipeline_runner import run_pipeline

    progress_bar = st.progress(0)
    status_slot  = st.empty()

    def _on_progress(msg: str, pct: int) -> None:
        progress_bar.progress(pct)
        status_slot.markdown(
            f'<div class="progress-step">● {msg}</div>',
            unsafe_allow_html=True,
        )

    try:
        result = run_pipeline(weeks=weeks, max_reviews=int(max_reviews), on_progress=_on_progress)
        st.session_state["last_result"] = result
        st.session_state.pop("report_expanded", None)
        progress_bar.progress(100)
        status_slot.success("Pipeline complete!")
        st.rerun()
    except Exception as exc:
        progress_bar.empty()
        status_slot.empty()
        st.error(f"Pipeline failed: {exc}")

# ---------------------------------------------------------------------------
# 3–5  Only shown once a result exists
# ---------------------------------------------------------------------------
if has_result:

    # 3. View report card
    st.markdown("""
    <div class="card">
      <div class="card-title">View report</div>
    """, unsafe_allow_html=True)

    if st.button("Load latest report", type="secondary"):
        st.session_state["report_expanded"] = not st.session_state.get("report_expanded", False)

    if st.session_state.get("report_expanded"):
        st.code(result.pulse_markdown, language=None)

    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Download card
    st.markdown("""
    <div class="card">
      <div class="card-title">Download report</div>
      <div class="card-desc" style="margin-bottom:14px">
        Save the weekly pulse as a Markdown file.
      </div>
    """, unsafe_allow_html=True)

    st.download_button(
        label="Download .md",
        data=result.pulse_markdown,
        file_name=f"weekly_pulse_{result.week_label.replace(' ', '_')}.md",
        mime="text/plain",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # 5. Send email card
    st.markdown("""
    <div class="card">
      <div class="card-title">Send email</div>
      <div class="card-desc">
        Send the latest report to an email address.
        Optional name adds &ldquo;Hi name,&rdquo; at the start.
      </div>
    """, unsafe_allow_html=True)

    with st.form("email_form"):
        recipient_email = st.text_input("Recipient email", placeholder="e.g. you@indmoney.com")
        recipient_name  = st.text_input("Recipient name (optional)", placeholder="e.g. Priya")
        send_clicked = st.form_submit_button("Send email")

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
