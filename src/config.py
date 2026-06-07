"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback for bare environments
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False


def _get_env_value(name: str | tuple[str, ...], default: str) -> str:
    names = (name,) if isinstance(name, str) else name
    for env_name in names:
        value = os.getenv(env_name)
        if value is not None:
            return value
    return default


def _env_label(name: str | tuple[str, ...]) -> str:
    return name if isinstance(name, str) else "/".join(name)


def _parse_int(name: str | tuple[str, ...], default: int, minimum: int = 1) -> int:
    raw_value = _get_env_value(name, str(default)).strip()
    label = _env_label(name)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer, got {raw_value!r}") from exc
    if value < minimum:
        raise ValueError(f"{label} must be >= {minimum}, got {value}")
    return value


def _parse_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got {raw_value!r}")


def parse_allowed_user_ids(raw_value: str | None) -> set[int] | None:
    """Parse a comma-separated allowlist of Telegram user IDs."""
    if raw_value is None:
        return None

    parts = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not parts:
        return None

    parsed: set[int] = set()
    for part in parts:
        try:
            parsed.add(int(part))
        except ValueError as exc:
            raise ValueError(
                f"TELEGRAM_ALLOWED_USER_IDS contains a non-integer value: {part!r}"
            ) from exc
    return parsed


def resolve_transcription_model() -> str:
    """Resolve local whisper model name with backwards-compatible fallback."""
    transcription_model = os.getenv("TRANSCRIPTION_MODEL", "").strip()
    if transcription_model:
        return transcription_model

    whisper_model = os.getenv("WHISPER_MODEL", "").strip()
    if whisper_model:
        return whisper_model

    legacy_model = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "").strip()
    legacy_lower = legacy_model.lower()
    if legacy_model and not (legacy_lower.startswith("gpt-") or legacy_lower == "whisper-1"):
        return legacy_model

    return "turbo"


def normalize_summary_language(raw_value: str | None) -> str | None:
    """Normalize summary language aliases to internal language codes."""
    if raw_value is None:
        return None

    value = raw_value.strip().lower()
    if value in {"en", "english"}:
        return "en"
    if value in {"de", "german"}:
        return "de"
    return None


@dataclass(slots=True)
class Settings:
    """Runtime settings for the bot."""

    telegram_bot_token: str
    openai_api_key: str
    enable_summary: bool
    telegram_allowed_user_ids: set[int] | None
    transcription_model: str
    whisper_device: str
    whisper_compute_type: str
    whisper_cpu_threads: int
    whisper_num_workers: int
    whisper_language: str
    whisper_beam_size: int
    whisper_best_of: int
    whisper_vad_filter: bool
    whisper_vad_min_silence_duration_ms: int
    whisper_condition_on_previous_text: bool
    openai_summary_model: str
    summary_default_language: str
    max_media_minutes: int
    max_file_mb: int
    max_transcript_chars: int
    temp_dir: Path
    log_level: str
    ffmpeg_bin: str
    download_timeout_sec: int
    conversion_timeout_sec: int
    transcription_timeout_sec: int
    summary_timeout_sec: int
    summary_direct_max_chars: int
    summary_chunk_chars: int
    summary_chunk_overlap_chars: int
    summary_max_output_tokens: int
    summary_pending_ttl_sec: int
    telegram_message_chunk_size: int
    instagram_cookie_file: str | None
    instagram_cookies_from_browser: str | None
    instagram_cookies_txt: str | None

    @property
    def max_media_seconds(self) -> int:
        return self.max_media_minutes * 60

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    def missing_required_values(self) -> list[str]:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if self.telegram_allowed_user_ids is None:
            missing.append("TELEGRAM_ALLOWED_USER_IDS")
        if self.enable_summary and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if self.enable_summary and not self.openai_summary_model:
            missing.append("SUMMARY_MODEL")
        return missing

    @classmethod
    def from_env(cls, *, load_env_file: bool = True) -> "Settings":
        if load_env_file:
            load_dotenv()

        summary_default_language = normalize_summary_language(
            os.getenv("SUMMARY_DEFAULT_LANGUAGE", "en")
        )
        if summary_default_language is None:
            raise ValueError("SUMMARY_DEFAULT_LANGUAGE must be one of: en, de, english, german")

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            enable_summary=_parse_bool("ENABLE_SUMMARY", False),
            telegram_allowed_user_ids=parse_allowed_user_ids(
                os.getenv("TELEGRAM_ALLOWED_USER_IDS")
            ),
            transcription_model=resolve_transcription_model(),
            whisper_device=os.getenv("WHISPER_DEVICE", "cpu").strip(),
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip(),
            whisper_cpu_threads=_parse_int("WHISPER_CPU_THREADS", 4),
            whisper_num_workers=_parse_int("WHISPER_NUM_WORKERS", 1),
            whisper_language=os.getenv("WHISPER_LANGUAGE", "auto").strip(),
            whisper_beam_size=_parse_int("WHISPER_BEAM_SIZE", 5),
            whisper_best_of=_parse_int("WHISPER_BEST_OF", 1),
            whisper_vad_filter=_parse_bool("WHISPER_VAD_FILTER", True),
            whisper_vad_min_silence_duration_ms=_parse_int(
                "WHISPER_VAD_MIN_SILENCE_DURATION_MS", 700
            ),
            whisper_condition_on_previous_text=_parse_bool(
                "WHISPER_CONDITION_ON_PREVIOUS_TEXT", False
            ),
            openai_summary_model=_get_env_value(
                ("SUMMARY_MODEL", "OPENAI_SUMMARY_MODEL"),
                "",
            ).strip(),
            summary_default_language=summary_default_language,
            max_media_minutes=_parse_int("MAX_MEDIA_MINUTES", 30),
            max_file_mb=_parse_int(("MAX_FILE_SIZE_MB", "MAX_FILE_MB"), 25),
            max_transcript_chars=_parse_int("MAX_TRANSCRIPT_CHARS", 120000),
            temp_dir=Path(os.getenv("TEMP_DIR", "/tmp")).resolve(),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            ffmpeg_bin=os.getenv("FFMPEG_BIN", "ffmpeg").strip(),
            download_timeout_sec=_parse_int("DOWNLOAD_TIMEOUT_SEC", 600),
            conversion_timeout_sec=_parse_int("CONVERSION_TIMEOUT_SEC", 300),
            transcription_timeout_sec=_parse_int("TRANSCRIPTION_TIMEOUT_SECONDS", 1800),
            summary_timeout_sec=_parse_int("SUMMARY_TIMEOUT_SEC", 120),
            summary_direct_max_chars=_parse_int("SUMMARY_DIRECT_MAX_CHARS", 11000),
            summary_chunk_chars=_parse_int("SUMMARY_CHUNK_CHARS", 6000),
            summary_chunk_overlap_chars=_parse_int("SUMMARY_CHUNK_OVERLAP_CHARS", 300, minimum=0),
            summary_max_output_tokens=_parse_int("SUMMARY_MAX_OUTPUT_TOKENS", 800),
            summary_pending_ttl_sec=_parse_int("SUMMARY_PENDING_TTL_SEC", 900),
            telegram_message_chunk_size=_parse_int("TELEGRAM_MESSAGE_CHUNK_SIZE", 3900),
            instagram_cookie_file=os.getenv("INSTAGRAM_COOKIE_FILE", "").strip() or None,
            instagram_cookies_from_browser=os.getenv(
                "INSTAGRAM_COOKIES_FROM_BROWSER", ""
            ).strip()
            or None,
            instagram_cookies_txt=(
                os.getenv("INSTAGRAM_COOKIES_TXT")
                if (os.getenv("INSTAGRAM_COOKIES_TXT") or "").strip()
                else None
            ),
        )
