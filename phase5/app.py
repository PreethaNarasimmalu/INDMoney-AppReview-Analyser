"""
Phase 5 — Streamlit Dashboard (main page).

Run with:
    streamlit run phase5/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="INDMoney App Review Pulse",
    page_icon="https://www.indmoney.com/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject INDMoney logo as favicon (overrides Streamlit default)
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

  /* Cards — override Streamlit's bordered container */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white !important;
    border: 1px solid #E4E7EC !important;
    border-radius: 14px !important;
    padding: 8px 14px !important;
    margin-bottom: 16px !important;
  }

  /* Pure-HTML cards (Status) */
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

# Map progress % → which badges should be green
_STAGE_THRESHOLDS = {
    "Reviews":    20,
    "Themes":     50,
    "Grouped":    60,
    "Report":     90,
    "Draft email": 100,
}


def _badge(label: str, active: bool) -> str:
    cls = "badge badge-on" if active else "badge"
    return f'<span class="{cls}">{label}</span>'


def _status_html(stages_done: set[str], week_label: str = "") -> str:
    date_html = f'<span class="badge-date">Report date: {week_label}</span>' if week_label else ""
    badges = " ".join(_badge(s, s in stages_done) for s in _STAGE_THRESHOLDS)
    return f"""
<div class="card">
  <div class="card-title">Status</div>
  <div class="badge-row">{badges}{date_html}</div>
</div>"""


# ---------------------------------------------------------------------------
# 1. Status card  (st.empty so pipeline can update badges live)
# ---------------------------------------------------------------------------
status_placeholder = st.empty()

_initial_stages = set(_STAGE_THRESHOLDS.keys()) if has_result else set()
status_placeholder.markdown(
    _status_html(_initial_stages, result.week_label if has_result else ""),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. Run pipeline card
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown('<p class="card-title">Run pipeline</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="card-desc">Scrape reviews → discover themes → classify → generate report'
        ' → create draft email. This may take several minutes.</p>',
        unsafe_allow_html=True,
    )
    weeks = st.selectbox(
        "Weeks of reviews",
        options=[None] + list(range(1, 17)),
        index=0,
        format_func=lambda x: "Select number of weeks..." if x is None else str(x),
    )
    max_reviews = st.text_input(
        "Max reviews to fetch",
        placeholder="e.g. 500",
    )
    run_clicked = st.button("Run full pipeline", type="primary")

if run_clicked:
    _weeks_val = weeks
    _max_val = max_reviews.strip() if max_reviews else ""
    if _weeks_val is None:
        st.error("Please select the number of weeks.")
    elif not _max_val or not _max_val.isdigit() or not (100 <= int(_max_val) <= 5000):
        st.error("Max reviews must be a number between 100 and 5000.")
    else:
        from phase5.pipeline_runner import run_pipeline

        progress_bar = st.progress(0)
        msg_slot     = st.empty()

        def _on_progress(msg: str, pct: int) -> None:
            progress_bar.progress(pct)
            msg_slot.markdown(
                f'<div class="progress-step">● {msg}</div>',
                unsafe_allow_html=True,
            )
            done = {s for s, threshold in _STAGE_THRESHOLDS.items() if pct >= threshold}
            status_placeholder.markdown(_status_html(done), unsafe_allow_html=True)

        try:
            result = run_pipeline(weeks=_weeks_val, max_reviews=int(_max_val), on_progress=_on_progress)
            st.session_state["last_result"] = result
            st.session_state.pop("report_expanded", None)
            progress_bar.progress(100)
            msg_slot.success("Pipeline complete!")
            st.rerun()
        except Exception as exc:
            progress_bar.empty()
            msg_slot.empty()
            st.error(f"Pipeline failed: {exc}")

# ---------------------------------------------------------------------------
# 3–5  Only shown once a result exists
# ---------------------------------------------------------------------------
if has_result:

    # 3. View report card
    with st.container(border=True):
        st.markdown('<p class="card-title">View report</p>', unsafe_allow_html=True)
        if st.button("Load latest report", type="secondary"):
            st.session_state["report_expanded"] = not st.session_state.get("report_expanded", False)
        if st.session_state.get("report_expanded"):
            st.code(result.pulse_markdown, language=None)

    # 4. Download card
    with st.container(border=True):
        st.markdown('<p class="card-title">Download report</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="card-desc" style="margin-bottom:14px">Save the weekly pulse as a Markdown file.</p>',
            unsafe_allow_html=True,
        )
        st.download_button(
            label="Download .md",
            data=result.pulse_markdown,
            file_name=f"weekly_pulse_{result.week_label.replace(' ', '_')}.md",
            mime="text/plain",
        )

    # 5. Send email card
    with st.container(border=True):
        st.markdown('<p class="card-title">Send email</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="card-desc">Send the latest report to an email address. '
            'Optional name adds "Hi name," at the start.</p>',
            unsafe_allow_html=True,
        )
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

# ---------------------------------------------------------------------------
# 6. Subscribe card (always visible)
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown('<p class="card-title">Subscribe to weekly pulse</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="card-desc">Subscribers receive the automated weekly pulse every Monday at 9 AM IST.</p>',
        unsafe_allow_html=True,
    )

    with st.form("subscribe_form"):
        sub_email = st.text_input("Email address", placeholder="e.g. you@indmoney.com")
        sub_name  = st.text_input("Name (optional)", placeholder="e.g. Priya")
        subscribe_clicked = st.form_submit_button("Subscribe", type="primary")

    if subscribe_clicked:
        if not sub_email.strip():
            st.error("Email address is required.")
        else:
            try:
                from phase5.subscriber_store import get_connection as _sub_conn, add_subscriber
                _conn = _sub_conn()
                added, sync_err = add_subscriber(_conn, sub_email.strip(), sub_name.strip())
                _conn.close()
                if added:
                    st.session_state["sub_msg"] = ("success", f"**{sub_email.strip()}** subscribed to the weekly pulse!", time.time())
                    if sync_err:
                        st.session_state["sub_sync_err"] = sync_err
                else:
                    st.session_state["sub_msg"] = ("warning", f"**{sub_email.strip()}** is already subscribed.", time.time())
            except Exception as exc:
                st.session_state["sub_msg"] = ("error", f"Failed to subscribe: {exc}", time.time())

    # GitHub sync error — shown persistently so user can debug
    if "sub_sync_err" in st.session_state:
        st.warning(
            f"Subscribed locally, but GitHub sync failed: `{st.session_state['sub_sync_err']}`\n\n"
            "Check that **GITHUB_TOKEN** and **GITHUB_REPO** are set correctly in Streamlit secrets.",
            icon="⚠️",
        )

    # Auto-dismissing feedback message (disappears after 4 seconds)
    if "sub_msg" in st.session_state:
        msg_type, msg_text, msg_time = st.session_state["sub_msg"]
        elapsed = time.time() - msg_time
        if elapsed < 4:
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "warning":
                st.warning(msg_text)
            else:
                st.error(msg_text)
            time.sleep(0.5)
            st.rerun()
        else:
            del st.session_state["sub_msg"]

