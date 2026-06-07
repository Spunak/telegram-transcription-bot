"""Instagram-specific URL detection and error mapping."""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.services.errors import (
    DownloadError,
    InstagramAuthRequiredError,
    InstagramCookiesRequiredError,
    InstagramRateLimitError,
)
from src.utils.validation import is_instagram_url


def parse_cookies_from_browser(raw_value: str) -> tuple[str, ...]:
    """Parse browser cookie source for yt-dlp, e.g. 'chrome' or 'firefox:default'."""
    parts = tuple(part.strip() for part in raw_value.split(":") if part.strip())
    if not parts:
        raise ValueError("INSTAGRAM_COOKIES_FROM_BROWSER is empty.")
    return parts


def write_instagram_cookies_txt(cookies_txt: str, job_dir: Path) -> str:
    """Write INSTAGRAM_COOKIES_TXT to a temporary file under current job dir."""
    auth_dir = job_dir / ".auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    cookie_file = auth_dir / "instagram_cookies.txt"
    normalized = cookies_txt.replace("\r\n", "\n")
    if "\n" not in normalized and "\\n" in normalized:
        normalized = normalized.replace("\\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    cookie_file.write_text(normalized, encoding="utf-8")
    return str(cookie_file)


def build_instagram_ydl_options(
    settings: Settings, *, cookiefile_override: str | None = None
) -> dict[str, object]:
    """Build yt-dlp auth options for Instagram downloads."""
    options: dict[str, object] = {}
    if cookiefile_override:
        options["cookiefile"] = cookiefile_override
        return options

    if settings.instagram_cookie_file:
        options["cookiefile"] = settings.instagram_cookie_file
    if settings.instagram_cookies_from_browser:
        options["cookiesfrombrowser"] = parse_cookies_from_browser(
            settings.instagram_cookies_from_browser
        )
    return options


def map_instagram_download_error(error_text: str, settings: Settings) -> DownloadError:
    """Map raw extraction failures to short user-facing Instagram messages."""
    lowered = error_text.lower()
    has_auth_config = bool(
        settings.instagram_cookie_file
        or settings.instagram_cookies_from_browser
        or settings.instagram_cookies_txt
    )

    if "rate limit" in lowered or "too many requests" in lowered or "429" in lowered:
        return InstagramRateLimitError(
            "Instagram rate limit hit. Try again later.",
            detail=error_text,
        )

    if "cookie" in lowered:
        return InstagramCookiesRequiredError(
            "Instagram cookies required for this link.",
            detail=error_text,
        )

    if "login required" in lowered or "private" in lowered or "authentication" in lowered:
        if has_auth_config:
            return InstagramAuthRequiredError(
                "Instagram login required or content unavailable.",
                detail=error_text,
            )
        return InstagramCookiesRequiredError(
            "Instagram may require login/cookies.",
            detail=error_text,
        )

    if "unavailable" in lowered or "not available" in lowered:
        return DownloadError("Instagram content unavailable.", detail=error_text)

    return DownloadError("Failed to download Instagram media.", detail=error_text)
