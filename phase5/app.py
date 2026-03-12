"""
Phase 5 — Streamlit Dashboard (main page).

Run with:
    streamlit run phase5/app.py
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="INDMoney App Review Pulse",
    page_icon="📱",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    weeks = st.slider(
        "Review window (weeks)",
        min_value=1, max_value=16, value=8,
        help="How many weeks of reviews to analyse",
    )
    max_reviews = st.number_input(
        "Max reviews to scrape",
        min_value=100, max_value=2000, value=1000, step=100,
    )
    st.divider()
    st.caption("Credentials loaded from `.env`")
    st.caption("DB retains last 12 weeks of reviews.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📱 INDMoney App Review Pulse")
st.caption("Weekly intelligence from Google Play reviews — powered by Groq + Gemini")
st.divider()

# ---------------------------------------------------------------------------
# Run Now button
# ---------------------------------------------------------------------------
run_clicked = st.button("▶ Run Now", type="primary")

if run_clicked:
    from phase5.pipeline_runner import run_pipeline

    progress_bar = st.progress(0)
    status_text = st.empty()

    def _on_progress(msg: str, pct: int) -> None:
        progress_bar.progress(pct)
        status_text.info(msg)

    try:
        result = run_pipeline(weeks=weeks, max_reviews=max_reviews, on_progress=_on_progress)
        st.session_state["last_result"] = result
        progress_bar.progress(100)
        status_text.success("Pipeline complete!")
    except Exception as exc:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Pipeline failed: {exc}")

# ---------------------------------------------------------------------------
# Last run results
# ---------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reviews Analysed", result.review_count)
    c2.metric("New This Run", result.new_reviews)
    c3.metric("Themes Found", result.theme_count)
    c4.metric("Old Reviews Purged", result.purged_reviews)

    st.divider()

    # Pulse note
    st.subheader(f"Weekly Pulse — {result.week_label}")
    st.code(result.pulse_markdown, language=None)

    # Download
    st.download_button(
        label="⬇ Download Report (.md)",
        data=result.pulse_markdown,
        file_name=f"weekly_pulse_{result.week_label.replace(' ', '_')}.md",
        mime="text/plain",
    )

    st.divider()

    # Send Email form
    st.subheader("📧 Send Email")
    with st.form("email_form"):
        recipient_name = st.text_input("Recipient Name", placeholder="Product Team")
        recipient_email = st.text_input("Recipient Email", placeholder="team@indmoney.com")
        send_clicked = st.form_submit_button("Confirm & Send")

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
else:
    st.info("Click **▶ Run Now** to generate the weekly pulse report.")
