"""
Shared Gemini API wrapper — used by Phase 3 (note generation).

Uses the current google-genai SDK (google.genai).
Handles retries with exponential backoff on transient errors.
Auth errors (403) and bad-request errors (400) are raised immediately.
"""

import json
import os
import time

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2


def get_gemini_client():
    """Build and return a Gemini Client. Raises if GEMINI_API_KEY is not set."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    from google import genai
    return genai.Client(api_key=api_key)


def chat(client, prompt: str, model: str, max_tokens: int, json_mode: bool = True) -> str:
    """
    Send a single user prompt to Gemini and return the response text.

    json_mode=True (default) sets response_mime_type="application/json" so
    Gemini is forced to return valid JSON — prevents unterminated-string errors
    caused by verbatim user quotes containing double-quote characters.

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

    from google.genai import types

    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            config_kwargs: dict = {"max_output_tokens": max_tokens}
            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            return response.text

        except _NON_RETRYABLE:
            raise  # auth / bad-request — no point retrying

        except _RETRYABLE as exc:
            last_exc = exc

        except Exception as exc:
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


def _escape_control_chars_in_strings(text: str) -> str:
    """
    Escape raw control characters (newline, carriage return, tab) that appear
    inside JSON string values.

    Even with response_mime_type="application/json", Gemini occasionally embeds
    literal newlines from user review text directly inside JSON string values,
    making json.loads fail with "Unterminated string". This scanner walks the
    JSON character by character and escapes bare control chars only inside strings.
    """
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch == "\n":
            result.append("\\n")
        elif in_string and ch == "\r":
            result.append("\\r")
        elif in_string and ch == "\t":
            result.append("\\t")
        else:
            result.append(ch)
    return "".join(result)


def parse_json_response(text: str) -> dict:
    """
    Strip code fence then parse as JSON.

    Falls back to sanitizing raw control characters inside string values before
    retrying — handles the case where Gemini embeds literal newlines from user
    review text even when JSON mode is enabled.

    Raises json.JSONDecodeError if both attempts fail.
    """
    text = strip_code_fence(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_escape_control_chars_in_strings(text))
