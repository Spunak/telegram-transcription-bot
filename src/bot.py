"""Telegram application assembly."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

from src.config import Settings
from src.handlers import TelegramHandlers
from src.services.download_service import DownloadService
from src.services.media_service import MediaService
from src.services.summary_service import SummaryService
from src.services.transcription_service import TranscriptionService

LOGGER = logging.getLogger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback error handler for uncaught update failures."""
    LOGGER.exception("Unhandled application error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Processing failed.")
        except Exception:
            LOGGER.exception("Failed to send fallback error message.")


def build_application(settings: Settings) -> Application:
    """Create and configure telegram Application with handlers and services."""
    download_service = DownloadService(settings)
    media_service = MediaService(settings)
    transcription_service = TranscriptionService(settings)
    summary_service = SummaryService(settings) if settings.enable_summary else None
    bot_handlers = TelegramHandlers(
        settings=settings,
        download_service=download_service,
        media_service=media_service,
        transcription_service=transcription_service,
        summary_service=summary_service,
    )

    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .concurrent_updates(True)
        .build()
    )
    bot_handlers.register(application)
    application.add_error_handler(global_error_handler)
    return application
