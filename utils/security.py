"""Security utilities for input validation and prompt-injection defense."""

import html
import re

CITY_PATTERN = re.compile(r"^[a-zA-Z\s,.-]{2,60}$")


def sanitize_city_name(city: str) -> str:
    """Validate and clean a city name input."""
    cleaned = " ".join(city.strip().split())
    if not cleaned or not CITY_PATTERN.match(cleaned):
        raise ValueError(
            "Enter a valid city name (2-60 characters, letters, spaces, commas, or hyphens only)."
        )
    return cleaned


def sanitize_free_text(text: str, max_length: int = 250) -> str:
    """Strip control characters, truncate, and neutralize XML delimiter tags."""
    if not text:
        return "None specified"
    cleaned = "".join(ch for ch in text if ch.isprintable()).strip()
    cleaned = cleaned[:max_length]
    # Prevent closing XML boundary tags used in prompts
    cleaned = cleaned.replace("<", "&lt;").replace(">", "&gt;")
    return cleaned or "None specified"


def escape_for_display(text: str) -> str:
    """Escape text safely before rendering in any HTML context."""
    return html.escape(str(text), quote=True)
