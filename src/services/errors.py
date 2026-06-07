"""Service and workflow errors with short user-facing messages."""

from __future__ import annotations


class BotError(Exception):
    """Base exception with a safe message for Telegram users."""

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        super().__init__(detail or user_message)
        self.user_message = user_message
        self.detail = detail


class UnauthorizedError(BotError):
    pass


class InvalidURLError(BotError):
    pass


class UnsupportedSourceError(BotError):
    pass


class InstagramAuthRequiredError(BotError):
    pass


class InstagramCookiesRequiredError(BotError):
    pass


class InstagramRateLimitError(BotError):
    pass


class DownloadError(BotError):
    pass


class TelegramDownloadError(BotError):
    pass


class MediaDurationError(BotError):
    pass


class MediaSizeError(BotError):
    pass


class ConversionError(BotError):
    pass


class TranscriptionError(BotError):
    pass


class TranscriptTooLongError(BotError):
    pass


class SummaryError(BotError):
    pass
