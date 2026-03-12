"""
Phase 2 configuration — Groq LLM settings.
"""

GROQ_MODEL = "llama3-70b-8192"
MAX_TOKENS = 2048

# Theme discovery
MIN_THEMES = 3
MAX_THEMES = 5

# Classifier
CLASSIFIER_BATCH_SIZE = 30       # reviews per Groq call
REVIEW_TEXT_TRUNCATE = 200       # chars per review in prompts
MAX_REVIEWS_FOR_DISCOVERY = 500  # cap reviews fed to theme discovery

# Validator
MIN_REVIEWS_PER_THEME = 2        # themes with fewer reviews get merged
