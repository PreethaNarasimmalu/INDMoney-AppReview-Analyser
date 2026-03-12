"""
Phase 3 configuration — Gemini LLM settings.
"""

GEMINI_MODEL = "gemini-2.0-flash"
MAX_TOKENS = 2048

# How many top themes to summarise
TOP_N_THEMES = 3

# Max chars of review text per review shown to Gemini in Call 3
REVIEW_TEXT_TRUNCATE = 300
