"""
Phase 4 — Email Composer.

Converts weekly_pulse.md into a well-structured HTML email with:
  - Plain text body (the raw markdown)
  - HTML body with styled sections for Top Themes, User Voices, Action Ideas

No LLM calls. No credentials needed here — credentials are in sender.py.

IN:  markdown string, week_label, recipient_name, recipient_email, sender_address
OUT: EmailMessage ready to be passed to sender.send_email()
"""

import re
from email.message import EmailMessage

from phase4.config import EMAIL_SUBJECT_PREFIX


# ---------------------------------------------------------------------------
# HTML template pieces
# ---------------------------------------------------------------------------

_HTML_WRAPPER = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      margin: 0; padding: 0;
      background-color: #f4f6f8;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #1a1a2e;
    }}
    .wrapper {{
      max-width: 640px;
      margin: 32px auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      padding: 36px 40px 28px;
      color: #ffffff;
    }}
    .header .brand {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: #e94560;
      margin-bottom: 8px;
    }}
    .header h1 {{
      margin: 0 0 6px;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.3;
      color: #ffffff;
    }}
    .header .week {{
      font-size: 13px;
      color: rgba(255,255,255,0.6);
    }}
    .body {{
      padding: 32px 40px;
    }}
    .section-title {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #888;
      margin: 0 0 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid #f0f0f0;
    }}
    .section {{
      margin-bottom: 32px;
    }}
    /* What's Working */
    .working-card {{
      display: flex;
      align-items: flex-start;
      padding: 14px 16px;
      margin-bottom: 10px;
      background: #fdf4ff;
      border-left: 4px solid #a855f7;
      border-radius: 0 8px 8px 0;
    }}
    .working-num {{
      font-size: 13px;
      font-weight: 700;
      color: #9333ea;
      min-width: 24px;
      margin-top: 1px;
    }}
    .working-text {{
      font-size: 13px;
      color: #1a1a2e;
      line-height: 1.5;
    }}
    /* Top Themes */
    .theme-card {{
      display: flex;
      align-items: flex-start;
      padding: 14px 16px;
      margin-bottom: 10px;
      background: #f8f9ff;
      border-left: 4px solid #0f3460;
      border-radius: 0 8px 8px 0;
    }}
    .theme-num {{
      font-size: 13px;
      font-weight: 700;
      color: #0f3460;
      min-width: 24px;
      margin-top: 1px;
    }}
    .theme-content {{}}
    .theme-label {{
      font-size: 14px;
      font-weight: 600;
      color: #1a1a2e;
      margin-bottom: 3px;
    }}
    .theme-summary {{
      font-size: 13px;
      color: #555;
      line-height: 1.5;
    }}
    /* User Voices */
    .quote-card {{
      padding: 14px 18px;
      margin-bottom: 10px;
      background: #fffaf3;
      border-left: 4px solid #f5a623;
      border-radius: 0 8px 8px 0;
    }}
    .quote-text {{
      font-size: 14px;
      font-style: italic;
      color: #333;
      line-height: 1.5;
      margin-bottom: 6px;
    }}
    .quote-meta {{
      font-size: 12px;
      color: #999;
    }}
    .stars {{
      color: #f5a623;
    }}
    /* Action Ideas */
    .action-card {{
      display: flex;
      align-items: flex-start;
      padding: 14px 16px;
      margin-bottom: 10px;
      background: #f0fdf4;
      border-left: 4px solid #22c55e;
      border-radius: 0 8px 8px 0;
    }}
    .action-num {{
      font-size: 13px;
      font-weight: 700;
      color: #16a34a;
      min-width: 24px;
      margin-top: 1px;
    }}
    .action-text {{
      font-size: 13px;
      color: #1a1a2e;
      line-height: 1.5;
    }}
    .footer {{
      padding: 20px 40px;
      background: #f8f9fa;
      border-top: 1px solid #eee;
      font-size: 11px;
      color: #aaa;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div class="brand">INDMoney &bull; App Intelligence</div>
      <h1>Weekly App Review Pulse</h1>
      <div class="week">{week_label}</div>
    </div>
    <div class="body">
      {themes_section}
      {voices_section}
      {working_section}
      {actions_section}
    </div>
    <div class="footer">
      Auto-generated from Google Play reviews &bull; {week_label}{unsubscribe_html}
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def _parse_sections(markdown: str) -> dict:
    """Extract TOP THEMES, USER VOICES, WHAT'S WORKING, ACTION IDEAS lines from markdown."""
    sections = {"TOP THEMES": [], "USER VOICES": [], "WHAT'S WORKING": [], "ACTION IDEAS": []}
    current = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped in sections:
            current = stripped
        elif current and stripped and not set(stripped) <= {"─", "-", "="}:
            sections[current].append(stripped)
    return sections


def _build_themes_html(lines: list[str]) -> str:
    items = []
    for line in lines:
        m = re.match(r"^(\d+)\.\s+(.+?)\s+[—–-]\s+(.+)$", line)
        if m:
            num, label, summary = m.group(1), _escape_html(m.group(2)), _escape_html(m.group(3))
        else:
            # fallback: no em-dash separator
            m2 = re.match(r"^(\d+)\.\s+(.+)$", line)
            if m2:
                num, label, summary = m2.group(1), _escape_html(m2.group(2)), ""
            else:
                continue
        summary_html = f'<div class="theme-summary">{summary}</div>' if summary else ""
        items.append(
            f'<div class="theme-card">'
            f'<div class="theme-num">{num}.</div>'
            f'<div class="theme-content">'
            f'<div class="theme-label">{label}</div>'
            f'{summary_html}'
            f'</div></div>'
        )
    if not items:
        return ""
    return (
        '<div class="section">'
        '<div class="section-title">Top Themes</div>'
        + "".join(items)
        + "</div>"
    )


def _build_voices_html(lines: list[str]) -> str:
    items = []
    for line in lines:
        # "quote text"  — Platform, N★
        m = re.match(r'^"(.+)"\s+[—–-]\s+(.+),\s*(\d+)★$', line)
        if m:
            quote, platform, rating = _escape_html(m.group(1)), _escape_html(m.group(2)), m.group(3)
            stars = "★" * int(rating) + "☆" * (5 - int(rating))
            items.append(
                f'<div class="quote-card">'
                f'<div class="quote-text">&ldquo;{quote}&rdquo;</div>'
                f'<div class="quote-meta"><span class="stars">{stars}</span> &bull; {platform}</div>'
                f'</div>'
            )
        else:
            # fallback: just show the line
            items.append(
                f'<div class="quote-card">'
                f'<div class="quote-text">{_escape_html(line)}</div>'
                f'</div>'
            )
    if not items:
        return ""
    return (
        '<div class="section">'
        '<div class="section-title">User Voices</div>'
        + "".join(items)
        + "</div>"
    )


def _build_working_html(lines: list[str]) -> str:
    items = []
    for line in lines:
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            num = m.group(1)
            rest = m.group(2)
            # Parse "Short Title: description" format
            colon_m = re.match(r"^(.+?):\s+(.+)$", rest)
            if colon_m:
                title = _escape_html(colon_m.group(1))
                desc = _escape_html(colon_m.group(2))
                text_html = f'<strong style="color:#7e22ce;">{title}:</strong> {desc}'
            else:
                text_html = _escape_html(rest)
            items.append(
                f'<div class="working-card">'
                f'<div class="working-num">{num}.</div>'
                f'<div class="working-text">{text_html}</div>'
                f'</div>'
            )
    if not items:
        return ""
    return (
        '<div class="section">'
        '<div class="section-title">What\'s Working</div>'
        + "".join(items)
        + "</div>"
    )


def _build_actions_html(lines: list[str]) -> str:
    items = []
    for line in lines:
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            num, text = m.group(1), _escape_html(m.group(2))
            items.append(
                f'<div class="action-card">'
                f'<div class="action-num">{num}.</div>'
                f'<div class="action-text">{text}</div>'
                f'</div>'
            )
    if not items:
        return ""
    return (
        '<div class="section">'
        '<div class="section-title">Action Ideas</div>'
        + "".join(items)
        + "</div>"
    )


def _markdown_to_html(markdown: str, week_label: str, recipient_email: str = "", include_unsubscribe: bool = False) -> str:
    sections = _parse_sections(markdown)
    if include_unsubscribe and recipient_email:
        unsubscribe_html = (
            f' &bull; <a href="https://indmoney-appreview-analyser.streamlit.app/Unsubscribe'
            f'?email={_escape_html(recipient_email)}"'
            f' style="color:#666;text-decoration:underline;">Unsubscribe</a>'
        )
    else:
        unsubscribe_html = ""
    return _HTML_WRAPPER.format(
        week_label=_escape_html(week_label),
        unsubscribe_html=unsubscribe_html,
        themes_section=_build_themes_html(sections["TOP THEMES"]),
        voices_section=_build_voices_html(sections["USER VOICES"]),
        working_section=_build_working_html(sections["WHAT'S WORKING"]),
        actions_section=_build_actions_html(sections["ACTION IDEAS"]),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose(
    markdown: str,
    week_label: str,
    recipient_name: str,
    recipient_email: str,
    sender_address: str,
    include_unsubscribe: bool = False,
) -> EmailMessage:
    """
    Build an EmailMessage from the weekly pulse markdown.

    Args:
        markdown:         rendered markdown from phase3.assembler.assemble()
        week_label:       e.g. "Week of 2026-03-09" — used in subject line
        recipient_name:   display name of the recipient
        recipient_email:  email address of the recipient
        sender_address:   Gmail address used as From (from .env)

    Returns:
        EmailMessage with plain text + HTML alternative parts.
    """
    if not markdown or not markdown.strip():
        raise ValueError("markdown is empty — nothing to compose")
    if not recipient_email or not recipient_email.strip():
        raise ValueError("recipient_email must not be empty")
    if not sender_address or not sender_address.strip():
        raise ValueError("sender_address must not be empty")

    subject = f"{EMAIL_SUBJECT_PREFIX} — {week_label}"

    to_header = (
        f"{recipient_name} <{recipient_email}>"
        if recipient_name and recipient_name.strip()
        else recipient_email
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_address
    msg["To"] = to_header

    plain = markdown
    if include_unsubscribe and recipient_email:
        plain += (
            f"\n\n---\nTo unsubscribe, visit: "
            f"https://indmoney-appreview-analyser.streamlit.app/Unsubscribe"
            f"?email={recipient_email}"
        )
    msg.set_content(plain)
    msg.add_alternative(_markdown_to_html(markdown, week_label, recipient_email, include_unsubscribe), subtype="html")

    return msg


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
