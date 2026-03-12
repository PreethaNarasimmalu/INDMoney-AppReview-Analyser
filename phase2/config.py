"""
Phase 2 configuration — Groq LLM settings.
"""

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 2048

# Theme discovery
MIN_THEMES = 3
MAX_THEMES = 5

# Classifier
CLASSIFIER_BATCH_SIZE = 20       # reviews per Groq call
REVIEW_TEXT_TRUNCATE = 150       # chars per review in prompts
MAX_REVIEWS_FOR_DISCOVERY = 150  # cap reviews fed to theme discovery (~8k tokens, under 12k TPM limit)

# Validator
MIN_REVIEWS_PER_THEME = 2        # themes with fewer reviews get merged

# Review filter (applied before any LLM call)
MIN_WORD_COUNT = 5               # reviews with fewer words are too short
MIN_ALPHA_RATIO = 0.4            # < 40% alphabetic chars = emoji/number spam
MAX_UPPERCASE_RATIO = 0.8        # > 80% uppercase letters = all-caps spam
