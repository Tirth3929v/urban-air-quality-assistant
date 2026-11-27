"""Security utilities for input validation and prompt-injection defense."""

import html
import re

import requests

CITY_PATTERN = re.compile(r"^[a-zA-Z\s,.-]{2,60}$")
URL_PATTERN = re.compile(r"https?://\S+")


def sanitize_city_name(city: str) -> str:
    """Validate and clean a city name input."""
    cleaned = " ".join(city.strip().split())
    if not cleaned or not CITY_PATTERN.match(cleaned):
        raise ValueError(
            "Enter a valid city name (2-60 characters, letters, spaces, commas, or hyphens only)."
        )
    return cleaned


def sanitize_free_text(
    text: str, max_length: int = 250, allow_newlines: bool = False
) -> str:
    """Strip control characters, truncate, and neutralize XML delimiter tags."""
    if not text:
        return "None specified"
    cleaned = "".join(
        ch for ch in text if ch.isprintable() or (allow_newlines and ch == "\n")
    ).strip()
    cleaned = cleaned[:max_length]
    # Prevent closing XML boundary tags used in prompts
    cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;")
    return cleaned or "None specified"


def escape_for_display(text: str) -> str:
    """Escape text safely before rendering in any HTML context."""
    return html.escape(str(text), quote=True)


def sanitize_error_message(exc: Exception) -> str:
    """Return a safe, user-friendly error message without leaking internal traces or URLs."""
    if isinstance(exc, ValueError):
        return URL_PATTERN.sub("[redacted-url]", str(exc))
    if isinstance(exc, requests.RequestException):
        return "Unable to reach the air quality telemetry service. Please try again shortly."
    if isinstance(exc, RuntimeError):
        msg = str(exc)
        if "GEMINI_API_KEY" in msg or "empty response" in msg.lower():
            return msg
    return "An unexpected service error occurred while generating your plan. Please try again."
