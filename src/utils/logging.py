"""Structured logging configuration."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Iterable

REDACTED = "***REDACTED***"

TELEGRAM_API_URL_RE = re.compile(r"(https?://api\.telegram\.org/bot)[^/\s]+", re.IGNORECASE)
TELEGRAM_TOKEN_RE = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b")
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b")
AUTH_BEARER_RE = re.compile(r"(authorization:\s*bearer\s+)\S+", re.IGNORECASE)
TOKEN_ASSIGN_RE = re.compile(r"(TELEGRAM_BOT_TOKEN\s*=\s*)\S+", re.IGNORECASE)
OPENAI_ASSIGN_RE = re.compile(r"(OPENAI_API_KEY\s*=\s*)\S+", re.IGNORECASE)


class JsonLogFormatter(logging.Formatter):
    """Render log records as JSON for server environments."""

    def __init__(self, *, secrets: Iterable[str] | None = None) -> None:
        super().__init__()
        self._secrets = tuple(secret for secret in (secrets or ()) if secret)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = self._redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=True)

    def _redact(self, text: str) -> str:
        redacted = text
        for secret in self._secrets:
            redacted = redacted.replace(secret, REDACTED)

        redacted = TELEGRAM_API_URL_RE.sub(rf"\1{REDACTED}", redacted)
        redacted = TELEGRAM_TOKEN_RE.sub(REDACTED, redacted)
        redacted = OPENAI_KEY_RE.sub(REDACTED, redacted)
        redacted = AUTH_BEARER_RE.sub(rf"\1{REDACTED}", redacted)
        redacted = TOKEN_ASSIGN_RE.sub(rf"\1{REDACTED}", redacted)
        redacted = OPENAI_ASSIGN_RE.sub(rf"\1{REDACTED}", redacted)
        return redacted

def configure_logging(level: str, *, secrets: Iterable[str] | None = None) -> None:
    """Set root logger with a single JSON stream handler."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter(secrets=secrets))
    root_logger.addHandler(handler)

    # Keep noisy library internals out of app logs, even if app LOG_LEVEL=DEBUG.
    for logger_name in (
        "httpx",
        "httpcore",
        "telegram",
        "telegram.ext",
        "urllib3",
        "openai",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
