"""Text formatting helpers for Telegram output."""

from __future__ import annotations

from datetime import datetime, timezone


def chunk_text(text: str, max_length: int) -> list[str]:
    """Split text into Telegram-safe chunks."""
    if not text:
        return [""]
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


def build_transcript_file_content(
    transcript: str,
    *,
    source_type: str,
    source_url: str | None,
    model: str,
) -> str:
    """Build transcript text with a compact metadata header."""
    timestamp = datetime.now(timezone.utc).isoformat()
    header_lines = [
        "transcript_metadata:",
        f"source_type: {source_type}",
        f"source_url: {source_url or '-'}",
        f"processed_at_utc: {timestamp}",
        f"model: {model}",
        "",
    ]
    return "\n".join(header_lines) + "\n" + transcript

