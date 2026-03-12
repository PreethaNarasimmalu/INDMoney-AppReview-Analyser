"""
Shared Gemini API wrapper — placeholder for Phase 3.
"""

import os


def get_gemini_client():
    """Build and return a Gemini client. Raises if GEMINI_API_KEY is not set."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    # Import here so missing package only fails if Gemini is actually used
    import google.generativeai as genai  # noqa: F401
    genai.configure(api_key=api_key)
    return genai
