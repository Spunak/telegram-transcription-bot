"""Validation and extraction helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

URL_REGEX = re.compile(r"(https?://[^\s<>\")\]]+)")


def extract_first_url(text: str) -> str | None:
    """Extract the first HTTP(S) URL from text."""
    match = URL_REGEX.search(text)
    if not match:
        return None
    return match.group(1).rstrip(".,!?")


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_instagram_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host == "instagram.com" or host.endswith(".instagram.com")

