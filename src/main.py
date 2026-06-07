"""Program entrypoint for long-polling Telegram transcription bot."""

from __future__ import annotations

import logging
import shutil
import sys

from telegram import Update

from src.bot import build_application
from src.config import Settings
from src.utils.logging import configure_logging

LOGGER = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_env()
    configure_logging(
        settings.log_level,
        secrets=(settings.telegram_bot_token, settings.openai_api_key),
    )

    if settings.log_level == "DEBUG":
        LOGGER.warning(
            "LOG_LEVEL=DEBUG enabled. Third-party HTTP/Telegram loggers are forced to WARNING."
        )

    missing = settings.missing_required_values()
    if missing:
        LOGGER.error("Missing required environment variables: %s", ", ".join(missing))
        raise SystemExit(1)

    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which(settings.ffmpeg_bin) is None:
        LOGGER.warning(
            "ffmpeg binary not found (%s). Media conversion will fail until installed.",
            settings.ffmpeg_bin,
        )

    LOGGER.info("Starting Telegram transcription bot with long polling.")
    application = build_application(settings)
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
