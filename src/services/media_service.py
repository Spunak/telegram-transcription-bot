"""Media conversion and limit checks."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.config import Settings
from src.services.errors import ConversionError, MediaDurationError, MediaSizeError


class MediaService:
    """Handle ffmpeg conversion and media-level guards."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def enforce_duration_limit(self, duration_seconds: int | None) -> None:
        if duration_seconds is None:
            return
        if duration_seconds > self._settings.max_media_seconds:
            raise MediaDurationError(
                f"Media too long. Max is {self._settings.max_media_minutes} minutes.",
                detail=f"duration={duration_seconds}",
            )

    def enforce_size_limit(self, size_bytes: int | None) -> None:
        if size_bytes is None:
            return
        if size_bytes > self._settings.max_file_bytes:
            raise MediaSizeError(
                f"Media too large. Max is {self._settings.max_file_mb} MB.",
                detail=f"size={size_bytes}",
            )

    async def convert_to_wav(self, input_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            self._settings.ffmpeg_bin,
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(output_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ConversionError("Server misconfigured: ffmpeg unavailable.", detail=str(exc)) from exc

        try:
            _stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._settings.conversion_timeout_sec,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ConversionError("Media conversion timed out.", detail=str(exc)) from exc

        if process.returncode != 0 or not output_path.exists():
            stderr_text = stderr.decode("utf-8", errors="ignore")
            raise ConversionError("Failed to convert media.", detail=stderr_text[:500])

        return output_path

