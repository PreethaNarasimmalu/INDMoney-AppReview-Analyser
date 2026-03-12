"""
Shared Groq API wrapper.

Used by Phase 2 (theme discovery + classifier).
Handles retries with exponential backoff on transient errors.
"""

import os
import time
import json
from groq import Groq, APIStatusError, APIConnectionError

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2


def get_groq_client() -> Groq:
    """Build and return a Groq client. Raises if GROQ_API_KEY is not set."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


def chat(
    client: Groq,
    prompt: str,
    model: str,
    max_tokens: int,
    json_mode: bool = True,
) -> str:
    """
    Send a single user prompt to Groq and return the response text.

    json_mode=True (default) sets response_format={"type":"json_object"} so
    the model is forced to return valid JSON — prevents unterminated-string
    and unescaped-quote parse errors.

    Retries up to MAX_RETRIES times on rate-limit (429) and server (5xx) errors
    with exponential backoff. Auth errors (401) are raised immediately.
    """
    last_exc: Exception | None = None
    fmt = {"type": "json_object"} if json_mode else None

    for attempt in range(MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                **({"response_format": fmt} if fmt else {}),
            )
            return completion.choices[0].message.content

        except APIStatusError as exc:
            if exc.status_code in (401, 403):
                raise  # auth errors — no point retrying
            last_exc = exc

        except APIConnectionError as exc:
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
