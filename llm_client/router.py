"""
LLM router — maps each pipeline call to the correct provider.

  Phase 2 calls (1 & 2): Groq
  Phase 3 calls (3 & 4): Gemini
"""

from llm_client.groq_client import get_groq_client, chat as groq_chat
from llm_client.gemini_client import get_gemini_client


def get_phase2_client():
    """Return the Groq client used by Phase 2."""
    return get_groq_client()


def get_phase3_client():
    """Return the Gemini client used by Phase 3."""
    return get_gemini_client()
