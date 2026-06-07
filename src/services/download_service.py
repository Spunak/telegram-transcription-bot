"""Media acquisition service for URL-based inputs using yt-dlp."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from src.config import Settings
from src.services.errors import (
    DownloadError,
    InvalidURLError,
    MediaDurationError,
    MediaSizeError,
    UnsupportedSourceError,
)
from src.services.instagram_service import (
    build_instagram_ydl_options,
    is_instagram_url,
    map_instagram_download_error,
    write_instagram_cookies_txt,
)
from src.utils.validation import is_http_url

LOGGER = logging.getLogger(__name__)
MEDIA_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".m4v",
    ".mka",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".wav",
    ".webm",
}


@dataclass(slots=True)
class DownloadResult:
    source_type: str
    source_url: str
    downloaded_path: Path
    title: str | None
    duration_seconds: int | None
    extractor: str | None


class DownloadService:
    """Download media from supported URLs via yt-dlp."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def download_from_url(self, url: str, job_dir: Path) -> DownloadResult:
        if not is_http_url(url):
            raise InvalidURLError("Invalid URL.")

        source_type = "instagram" if is_instagram_url(url) else "url"
        LOGGER.info("Starting URL processing: source_type=%s url=%s", source_type, url)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._download_sync, url, job_dir, source_type),
                timeout=self._settings.download_timeout_sec,
            )
        except asyncio.TimeoutError as exc:
            raise DownloadError("Media download timed out.", detail=str(exc)) from exc

    def _download_sync(self, url: str, job_dir: Path, source_type: str) -> DownloadResult:
        job_dir.mkdir(parents=True, exist_ok=True)
        instagram_cookiefile_override: str | None = None
        excluded_filenames: set[str] = set()

        if source_type == "instagram" and self._settings.instagram_cookies_txt:
            instagram_cookiefile_override = write_instagram_cookies_txt(
                self._settings.instagram_cookies_txt,
                job_dir,
            )
            excluded_filenames.add(Path(instagram_cookiefile_override).name)

        try:
            probe_info = self._extract_info(
                url,
                job_dir,
                source_type,
                download=False,
                instagram_cookiefile_override=instagram_cookiefile_override,
            )
            self._enforce_limits(probe_info)

            downloaded_info = self._extract_info(
                url,
                job_dir,
                source_type,
                download=True,
                instagram_cookiefile_override=instagram_cookiefile_override,
            )
            downloaded_path = self._resolve_downloaded_path(
                downloaded_info,
                job_dir,
                source_type=source_type,
                excluded_filenames=excluded_filenames,
            )
            if not downloaded_path.exists():
                raise DownloadError("Failed to download media.", detail="downloaded file missing")
            if downloaded_path.stat().st_size == 0:
                raise DownloadError("Failed to download media.", detail="downloaded file is empty")

            LOGGER.info(
                "Downloaded media file selected: name=%s ext=%s size_bytes=%d source_type=%s extractor=%s",
                downloaded_path.name,
                downloaded_path.suffix.lower(),
                downloaded_path.stat().st_size,
                source_type,
                str(downloaded_info.get("extractor_key") or ""),
            )

            duration_raw = downloaded_info.get("duration")
            duration_seconds = int(duration_raw) if isinstance(duration_raw, (int, float)) else None

            return DownloadResult(
                source_type=source_type,
                source_url=url,
                downloaded_path=downloaded_path,
                title=str(downloaded_info.get("title") or ""),
                duration_seconds=duration_seconds,
                extractor=str(downloaded_info.get("extractor_key") or ""),
            )
        except (MediaDurationError, MediaSizeError, DownloadError, UnsupportedSourceError):
            raise
        except YtDlpDownloadError as exc:
            message = str(exc)
            lowered = message.lower()
            if source_type == "instagram":
                raise map_instagram_download_error(message, self._settings) from exc
            if "unsupported url" in lowered or "no suitable extractor" in lowered:
                raise UnsupportedSourceError(
                    "Unsupported or inaccessible URL.",
                    detail=message,
                ) from exc
            if "private" in lowered or "login" in lowered:
                raise DownloadError("Source requires authentication.", detail=message) from exc
            raise DownloadError("Failed to download media.", detail=message) from exc
        except Exception as exc:
            raise DownloadError("Failed to download media.", detail=str(exc)) from exc

    def _extract_info(
        self,
        url: str,
        job_dir: Path,
        source_type: str,
        *,
        download: bool,
        instagram_cookiefile_override: str | None = None,
    ) -> dict[str, Any]:
        options = self._build_ydl_options(
            job_dir,
            source_type,
            download=download,
            instagram_cookiefile_override=instagram_cookiefile_override,
        )
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=download)
        return self._select_single_entry(info)

    def _build_ydl_options(
        self,
        job_dir: Path,
        source_type: str,
        *,
        download: bool,
        instagram_cookiefile_override: str | None = None,
    ) -> dict[str, object]:
        options: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "restrictfilenames": True,
            "socket_timeout": self._settings.download_timeout_sec,
            "outtmpl": str(job_dir / "media.%(ext)s"),
            "overwrites": True,
            "nopart": True,
        }
        if download:
            options["format"] = "bestaudio/best"
            if source_type == "instagram":
                options["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        else:
            options["skip_download"] = True

        if source_type == "instagram":
            options.update(
                build_instagram_ydl_options(
                    self._settings,
                    cookiefile_override=instagram_cookiefile_override,
                )
            )
        return options

    @staticmethod
    def _select_single_entry(info: dict[str, Any]) -> dict[str, Any]:
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            for entry in entries:
                if entry:
                    return entry
            raise UnsupportedSourceError("Unsupported or inaccessible URL.")
        return info

    def _enforce_limits(self, info: dict[str, Any]) -> None:
        if info.get("is_live"):
            raise UnsupportedSourceError("Live streams are not supported.")

        duration = info.get("duration")
        if isinstance(duration, (int, float)) and duration > self._settings.max_media_seconds:
            raise MediaDurationError(
                f"Media too long. Max is {self._settings.max_media_minutes} minutes.",
                detail=f"duration={duration}",
            )

        file_size = info.get("filesize") or info.get("filesize_approx")
        if isinstance(file_size, (int, float)) and file_size > self._settings.max_file_bytes:
            raise MediaSizeError(
                f"Media too large. Max is {self._settings.max_file_mb} MB.",
                detail=f"filesize={file_size}",
            )

    def _resolve_downloaded_path(
        self,
        info: dict[str, Any],
        job_dir: Path,
        *,
        source_type: str,
        excluded_filenames: set[str] | None = None,
    ) -> Path:
        excluded_filenames = excluded_filenames or set()
        metadata_paths = self._extract_metadata_paths(info, job_dir)
        if metadata_paths:
            for path in metadata_paths:
                if self._is_valid_media_file(path, excluded_filenames):
                    return path

            LOGGER.warning(
                "No valid media file resolved from yt-dlp metadata: source_type=%s candidate_count=%d",
                source_type,
                len(metadata_paths),
            )
            raise DownloadError(
                "Failed to download media.",
                detail="no real media file resolved from yt-dlp metadata",
            )

        # Metadata can be incomplete for some extractors. Use a strict local fallback.
        files = self._scan_media_files(job_dir, excluded_filenames)
        if not files:
            LOGGER.warning(
                "No media files found in download directory after yt-dlp: source_type=%s",
                source_type,
            )
            raise DownloadError(
                "Failed to download media.",
                detail="no downloaded media files found",
            )
        media_named_candidates = [path for path in files if path.stem == "media"]
        if media_named_candidates:
            return max(media_named_candidates, key=lambda path: path.stat().st_mtime)
        return max(files, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def _extract_metadata_paths(info: dict[str, Any], job_dir: Path) -> list[Path]:
        raw_candidates: list[str] = []

        def _append_candidate(value: object) -> None:
            if isinstance(value, str):
                candidate = value.strip()
                if candidate:
                    raw_candidates.append(candidate)

        _append_candidate(info.get("filepath"))
        _append_candidate(info.get("_filename"))

        requested_downloads = info.get("requested_downloads")
        if isinstance(requested_downloads, list):
            for entry in requested_downloads:
                if isinstance(entry, dict):
                    _append_candidate(entry.get("filepath"))
                    _append_candidate(entry.get("_filename"))

        requested_formats = info.get("requested_formats")
        if isinstance(requested_formats, list):
            for entry in requested_formats:
                if isinstance(entry, dict):
                    _append_candidate(entry.get("filepath"))
                    _append_candidate(entry.get("_filename"))

        resolved: list[Path] = []
        seen: set[str] = set()
        for raw_path in raw_candidates:
            path = Path(raw_path)
            if not path.is_absolute():
                path = job_dir / path
            path = path.resolve()
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(path)
        return resolved

    @staticmethod
    def _scan_media_files(job_dir: Path, excluded_filenames: set[str]) -> list[Path]:
        return [
            path
            for path in job_dir.iterdir()
            if path.is_file() and DownloadService._is_valid_media_file(path, excluded_filenames)
        ]

    @staticmethod
    def _is_valid_media_file(path: Path, excluded_filenames: set[str]) -> bool:
        if path.name in excluded_filenames:
            return False
        if path.suffix.lower() not in MEDIA_EXTENSIONS:
            return False
        if path.suffix.lower() in {".json", ".txt"}:
            return False
        if path.suffix.lower() in {".part", ".tmp"}:
            return False
        if not path.exists() or not path.is_file():
            return False
        if path.stat().st_size <= 0:
            return False
        return True
