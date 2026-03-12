"""
Phase 2 configuration.
"""

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2000
MAX_REVIEWS_IN_PROMPT = 500   # cap to keep prompt size manageable
REVIEW_TEXT_TRUNCATE = 300    # chars per review in the prompt
TOP_THEMES = 5
