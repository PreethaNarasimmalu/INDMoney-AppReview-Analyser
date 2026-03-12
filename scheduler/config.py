"""
Scheduler configuration.

All settings can be overridden with environment variables.
Defaults are conservative: 3 weeks of data, 200 reviews — appropriate for
an unattended weekly run where LLM token costs matter.
"""

import os

# Analysis window for the automated run
SCHEDULER_WEEKS: int = int(os.getenv("SCHEDULER_WEEKS", "3"))

# Max reviews to scrape per run
SCHEDULER_MAX_REVIEWS: int = int(os.getenv("SCHEDULER_MAX_REVIEWS", "200"))

# Fixed recipient for the automated email (required — no UI to enter it)
SCHEDULER_RECIPIENT_EMAIL: str = os.getenv("SCHEDULER_RECIPIENT_EMAIL", "")
SCHEDULER_RECIPIENT_NAME: str = os.getenv("SCHEDULER_RECIPIENT_NAME", "")
