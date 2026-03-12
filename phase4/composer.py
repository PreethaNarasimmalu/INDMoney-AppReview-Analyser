"""
Phase 4 — Email Composer.

Wraps the weekly_pulse.md markdown into a MIMEMultipart email with:
  - Plain text body (the raw markdown)
  - HTML body (markdown wrapped in styled <pre> block)

No LLM calls. No credentials needed here — credentials are in sender.py.

IN:  markdown string, week_label, recipient_name, recipient_email, sender_address
OUT: EmailMessage ready to be passed to sender.create_draft()
"""

from email.message import EmailMessage

from phase4.config import EMAIL_SUBJECT_PREFIX

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: 'Courier New', Courier, monospace;
      background: #f9f9f9;
      padding: 24px;
    }}
    .container {{
      background: #ffffff;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 24px 32px;
      max-width: 720px;
      margin: auto;
    }}
    pre {{
      white-space: pre-wrap;
      word-wrap: break-word;
      font-size: 14px;
      line-height: 1.6;
      color: #1a1a1a;
    }}
  </style>
</head>
<body>
  <div class="container">
    <pre>{body}</pre>
  </div>
</body>
</html>
"""


def compose(
    markdown: str,
    week_label: str,
    recipient_name: str,
    recipient_email: str,
    sender_address: str,
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
        EmailMessage with plain text + HTML alternative parts, ready for draft creation.
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

    # Plain text (fallback)
    msg.set_content(markdown)

    # HTML alternative
    html_body = _HTML_TEMPLATE.format(body=_escape_html(markdown))
    msg.add_alternative(html_body, subtype="html")

    return msg


def _escape_html(text: str) -> str:
    """Escape characters that would break HTML inside a <pre> block."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
