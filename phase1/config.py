"""
Phase 1 configuration and defaults.
"""

DEFAULT_APP_ID = "in.indwealth"
DEFAULT_MAX_REVIEWS = 1000
DEFAULT_WEEKS = 8
DEFAULT_LANG = "en"
DEFAULT_COUNTRY = "in"
BATCH_SIZE = 200  # Google Play scraper max per request
REVIEW_TEXT_TRUNCATE = 300  # chars kept per review for display / analysis
RETENTION_WEEKS = 12  # reviews older than this are deleted on each run
