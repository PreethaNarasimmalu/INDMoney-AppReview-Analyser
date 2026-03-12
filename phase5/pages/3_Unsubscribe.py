"""
Unsubscribe page — handles one-click unsubscribe from the weekly pulse email.

URL: /Unsubscribe?email=user@example.com
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Unsubscribe — INDMoney App Review Pulse",
    page_icon="https://www.indmoney.com/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="collapsedControl"] { display: none !important; }
  section[data-testid="stSidebar"]  { display: none !important; }

  .stApp { background: #F7F8FA; }
  .main .block-container {
    max-width: 560px;
    padding: 3.5rem 2rem 5rem;
  }

  .page-title {
    font-size: 28px; font-weight: 800; color: #1A1A1A;
    margin: 0 0 8px; line-height: 1.15;
  }
  .page-sub {
    font-size: 15px; color: #8A94A6; margin: 0 0 36px;
  }

  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white !important;
    border: 1px solid #E4E7EC !important;
    border-radius: 14px !important;
    padding: 8px 14px !important;
    margin-bottom: 16px !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">Unsubscribe</div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">INDMoney App Review Pulse</div>', unsafe_allow_html=True)

email = st.query_params.get("email", "").strip().lower()

with st.container(border=True):
    if not email:
        st.warning("No email address provided. Please use the unsubscribe link from your email.")
    else:
        try:
            from phase5.subscriber_store import get_connection, remove_subscriber
            conn = get_connection()
            removed = remove_subscriber(conn, email)
            conn.close()

            if removed:
                st.success(f"**{email}** has been unsubscribed from the weekly pulse.")
                st.markdown(
                    '<p style="font-size:13px;color:#6B7280;margin-top:8px;">'
                    'You will no longer receive the weekly app review email. '
                    'You can re-subscribe at any time from the '
                    '<a href="/" style="color:#2DB34A;">main dashboard</a>.'
                    '</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.info(f"**{email}** was not found in the subscriber list.")
                st.markdown(
                    '<p style="font-size:13px;color:#6B7280;margin-top:8px;">'
                    'This email may have already been unsubscribed.'
                    '</p>',
                    unsafe_allow_html=True,
                )
        except Exception as exc:
            st.error(f"Failed to process unsubscribe request: {exc}")
