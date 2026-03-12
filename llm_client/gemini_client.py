"""
Shared Gemini API wrapper — used by Phase 3 (note generation).

Handles retries with exponential backoff on transient errors.
Auth errors (403) and bad-request errors (400) are raised immediately.
"""

import json
import os
import time

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2


def get_gemini_client():
    """Build and return a configured genai module. Raises if GEMINI_API_KEY is not set."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai


def chat(genai, prompt: str, model: str, max_tokens: int) -> str:
    """
    Send a single user prompt to Gemini and return the response text.

    Retries up to MAX_RETRIES times on rate-limit (429) and server (5xx) errors
    with exponential backoff. Auth errors (403) and bad requests (400) raise immediately.
    """
    try:
        import google.api_core.exceptions as _gapi
        _NON_RETRYABLE = (_gapi.PermissionDenied, _gapi.InvalidArgument)
        _RETRYABLE = (_gapi.ResourceExhausted, _gapi.ServiceUnavailable, _gapi.InternalServerError)
    except ImportError:
        _NON_RETRYABLE = ()
        _RETRYABLE = ()

    last_exc: Exception | None = None
    gemini_model = genai.GenerativeModel(
        model,
        generation_config={"max_output_tokens": max_tokens},
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = gemini_model.generate_content(prompt)
            return response.text

        except _NON_RETRYABLE:
            raise  # auth / bad-request — no point retrying

        except _RETRYABLE as exc:
            last_exc = exc

        except Exception as exc:
            # Catch-all for connection errors or unexpected failures
            last_exc = exc

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BASE_SECONDS * (2 ** attempt))

    raise last_exc


def strip_code_fence(text: str) -> str:
    """Remove markdown ```json ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_json_response(text: str) -> dict:
    """Strip code fence then parse as JSON. Raises json.JSONDecodeError on failure."""
    return json.loads(strip_code_fence(text))
