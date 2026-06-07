"""Telegram update handlers and end-to-end processing workflows."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from telegram import InputFile, Message, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.config import Settings, normalize_summary_language
from src.services.download_service import DownloadService
from src.services.errors import (
    BotError,
    SummaryError,
    TelegramDownloadError,
    TranscriptTooLongError,
)
from src.services.media_service import MediaService
from src.services.summary_service import SummaryService
from src.services.transcription_service import TranscriptionService
from src.utils.text import build_transcript_file_content, chunk_text
from src.utils.validation import extract_first_url

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TelegramMediaPayload:
    file_id: str
    file_name: str
    source_type: str
    duration_seconds: int | None
    size_bytes: int | None


class TelegramHandlers:
    """Register and execute Telegram bot handlers."""

    def __init__(
        self,
        settings: Settings,
        download_service: DownloadService,
        media_service: MediaService,
        transcription_service: TranscriptionService,
        summary_service: SummaryService | None,
    ) -> None:
        self._settings = settings
        self._download_service = download_service
        self._media_service = media_service
        self._transcription_service = transcription_service
        self._summary_service = summary_service
        self._allowlist_warning_logged = False
        self._pending_summary_by_user_id: dict[int, float] = {}
        self._summary_language_by_user_id: dict[int, str] = {}

    def register(self, application: Application) -> None:
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("health", self.health))
        application.add_handler(CommandHandler(["sum", "summarize"], self.summarize))
        application.add_handler(CommandHandler("sumlang", self.sumlang))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        media_filter = filters.VOICE | filters.AUDIO | filters.VIDEO | filters.Document.ALL
        application.add_handler(MessageHandler(media_filter, self.on_media))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not await self._authorize(update):
            return
        message = update.effective_message
        if message:
            await message.reply_text("Send one link or one voice/audio/video file.")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not await self._authorize(update):
            return
        message = update.effective_message
        if message:
            await message.reply_text(
                "Send one URL or one media file for transcript. Use /sum for summary, /sumlang to set language."
            )

    async def health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        del context
        if not await self._authorize(update):
            return
        message = update.effective_message
        if not message:
            return
        allowlist_status = (
            "configured" if self._settings.telegram_allowed_user_ids is not None else "missing"
        )
        await message.reply_text(
            "ok\n"
            f"model={self._settings.openai_transcription_model}\n"
            f"allowlist={allowlist_status}\n"
            f"summary={'enabled' if self._settings.enable_summary else 'disabled'}"
        )

    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._authorize(update):
            return
        message = update.effective_message
        user = update.effective_user
        if not message or not message.text or user is None:
            return

        url = extract_first_url(message.text)
        if not url:
            return

        summary_mode = self._consume_pending_summary(user.id)
        summary_language = self._get_user_summary_language(user.id) if summary_mode else None
        await self._handle_url_message(
            message,
            context,
            url,
            summary_mode=summary_mode,
            summary_language=summary_language,
        )

    async def on_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._authorize(update):
            return
        message = update.effective_message
        user = update.effective_user
        if not message or user is None:
            return

        payload = self._extract_media_payload(message)
        if payload is None:
            return

        summary_mode = self._consume_pending_summary(user.id)
        summary_language = self._get_user_summary_language(user.id) if summary_mode else None
        await self._handle_media_message(
            message,
            context,
            payload,
            summary_mode=summary_mode,
            summary_language=summary_language,
        )

    async def summarize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._authorize(update):
            return

        message = update.effective_message
        user = update.effective_user
        if message is None or user is None:
            return
        if not self._settings.enable_summary:
            await message.reply_text("Summary feature is disabled.")
            return

        self._pending_summary_by_user_id.pop(user.id, None)
        summary_language = self._get_user_summary_language(user.id)

        inline_url = extract_first_url(" ".join(context.args)) if context.args else None
        if inline_url:
            await self._handle_url_message(
                message,
                context,
                inline_url,
                summary_mode=True,
                summary_language=summary_language,
            )
            return

        if message.reply_to_message:
            reply_url = extract_first_url(
                message.reply_to_message.text or message.reply_to_message.caption or ""
            )
            if reply_url:
                await self._handle_url_message(
                    message,
                    context,
                    reply_url,
                    summary_mode=True,
                    summary_language=summary_language,
                )
                return

            reply_payload = self._extract_media_payload(message.reply_to_message)
            if reply_payload:
                await self._handle_media_message(
                    message,
                    context,
                    reply_payload,
                    summary_mode=True,
                    summary_language=summary_language,
                )
                return

        self._set_pending_summary(user.id)
        await message.reply_text("Send me a link, voice, audio, or video for summary.")

    async def sumlang(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._authorize(update):
            return

        message = update.effective_message
        user = update.effective_user
        if message is None or user is None:
            return
        if not self._settings.enable_summary:
            await message.reply_text("Summary feature is disabled.")
            return

        if not context.args:
            current = self._get_user_summary_language(user.id)
            await message.reply_text(
                f"Current summary language: {self._summary_language_label(current)}."
            )
            return

        normalized = normalize_summary_language(context.args[0])
        if normalized is None:
            await message.reply_text("Use /sumlang en or /sumlang de.")
            return

        self._summary_language_by_user_id[user.id] = normalized
        await message.reply_text(
            f"Summary language set to {self._summary_language_label(normalized)}."
        )

    async def _authorize(self, update: Update) -> bool:
        message = update.effective_message
        user = update.effective_user
        if message is None or user is None:
            return False

        allowed_user_ids = self._settings.telegram_allowed_user_ids
        if allowed_user_ids is None:
            if not self._allowlist_warning_logged:
                LOGGER.error("TELEGRAM_ALLOWED_USER_IDS is not configured.")
                self._allowlist_warning_logged = True
            await message.reply_text("Server misconfigured: user whitelist is missing.")
            return False

        if user.id not in allowed_user_ids:
            await message.reply_text("Unauthorized.")
            return False
        return True

    async def _handle_url_message(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        url: str,
        *,
        summary_mode: bool = False,
        summary_language: str | None = None,
    ) -> None:
        del context
        status_message = await message.reply_text("Processing...")

        try:
            with tempfile.TemporaryDirectory(
                prefix="tg_transcribe_",
                dir=str(self._settings.temp_dir),
            ) as temp_dir:
                job_dir = Path(temp_dir)
                download_result = await self._download_service.download_from_url(url, job_dir)
                wav_path = await self._media_service.convert_to_wav(
                    download_result.downloaded_path,
                    job_dir / "audio.wav",
                )
                if summary_mode:
                    await self._update_status(status_message, "Transcribing...")
                transcript = await self._transcription_service.transcribe(wav_path)
                if summary_mode:
                    summary_service = self._require_summary_service()
                    if not transcript.strip():
                        raise SummaryError("Transcript unavailable for summary.")
                    LOGGER.info(
                        "Summary mode transcript ready: source_type=%s chars=%d",
                        download_result.source_type,
                        len(transcript),
                    )
                    await self._update_status(status_message, "Summarizing...")
                    summary = await summary_service.summarize_transcript(
                        transcript,
                        target_language=summary_language or self._settings.summary_default_language,
                    )
                    await self._send_summary(message, summary)
                else:
                    await self._send_transcript(
                        message,
                        transcript,
                        job_dir=job_dir,
                        source_type=download_result.source_type,
                        source_url=download_result.source_url,
                    )
        except BotError as exc:
            LOGGER.warning("URL processing error: %s detail=%s", exc.user_message, exc.detail)
            await message.reply_text(exc.user_message)
        except Exception:
            LOGGER.exception("Unhandled URL processing failure.")
            await message.reply_text("Processing failed.")

    async def _handle_media_message(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE,
        payload: TelegramMediaPayload,
        *,
        summary_mode: bool = False,
        summary_language: str | None = None,
    ) -> None:
        try:
            self._media_service.enforce_duration_limit(payload.duration_seconds)
            self._media_service.enforce_size_limit(payload.size_bytes)
            status_message = await message.reply_text("Processing...")

            with tempfile.TemporaryDirectory(
                prefix="tg_transcribe_",
                dir=str(self._settings.temp_dir),
            ) as temp_dir:
                job_dir = Path(temp_dir)
                input_path = job_dir / payload.file_name
                await self._download_telegram_file(context, payload.file_id, input_path)
                wav_path = await self._media_service.convert_to_wav(
                    input_path,
                    job_dir / "audio.wav",
                )
                if summary_mode:
                    await self._update_status(status_message, "Transcribing...")
                transcript = await self._transcription_service.transcribe(wav_path)
                if summary_mode:
                    summary_service = self._require_summary_service()
                    if not transcript.strip():
                        raise SummaryError("Transcript unavailable for summary.")
                    LOGGER.info(
                        "Summary mode transcript ready: source_type=%s chars=%d",
                        payload.source_type,
                        len(transcript),
                    )
                    await self._update_status(status_message, "Summarizing...")
                    summary = await summary_service.summarize_transcript(
                        transcript,
                        target_language=summary_language or self._settings.summary_default_language,
                    )
                    await self._send_summary(message, summary)
                else:
                    await self._send_transcript(
                        message,
                        transcript,
                        job_dir=job_dir,
                        source_type=payload.source_type,
                        source_url=None,
                    )
        except BotError as exc:
            LOGGER.warning("Media processing error: %s detail=%s", exc.user_message, exc.detail)
            await message.reply_text(exc.user_message)
        except Exception:
            LOGGER.exception("Unhandled media processing failure.")
            await message.reply_text("Processing failed.")

    async def _download_telegram_file(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        file_id: str,
        destination: Path,
    ) -> None:
        try:
            telegram_file = await context.bot.get_file(file_id)
            await asyncio.wait_for(
                telegram_file.download_to_drive(custom_path=str(destination)),
                timeout=self._settings.download_timeout_sec,
            )
        except Exception as exc:
            raise TelegramDownloadError(
                "Failed to download Telegram file.",
                detail=str(exc),
            ) from exc

    async def _send_transcript(
        self,
        message: Message,
        transcript: str,
        *,
        job_dir: Path,
        source_type: str,
        source_url: str | None,
    ) -> None:
        if len(transcript) > self._settings.max_transcript_chars:
            raise TranscriptTooLongError("Transcript too long to send.")

        for chunk in chunk_text(transcript, self._settings.telegram_message_chunk_size):
            await message.reply_text(chunk)

        transcript_file_name = (
            f"transcript_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
        )
        transcript_file_path = job_dir / transcript_file_name
        transcript_file_path.write_text(
            build_transcript_file_content(
                transcript,
                source_type=source_type,
                source_url=source_url,
                model=self._settings.openai_transcription_model,
            ),
            encoding="utf-8",
        )

        with transcript_file_path.open("rb") as file_handle:
            await message.reply_document(document=InputFile(file_handle, filename=transcript_file_name))

    async def _send_summary(self, message: Message, summary: str) -> None:
        cleaned = summary.strip()
        if not cleaned:
            raise SummaryError("Summary unavailable.")
        for chunk in chunk_text(cleaned, self._settings.telegram_message_chunk_size):
            await message.reply_text(chunk)

    def _require_summary_service(self) -> SummaryService:
        if self._summary_service is None:
            raise SummaryError("Summary feature is disabled.")
        return self._summary_service

    async def _update_status(self, status_message: Message, text: str) -> None:
        try:
            await status_message.edit_text(text)
        except Exception:
            LOGGER.debug("Status message edit skipped.")

    def _set_pending_summary(self, user_id: int) -> None:
        self._pending_summary_by_user_id[user_id] = (
            time.monotonic() + self._settings.summary_pending_ttl_sec
        )

    def _consume_pending_summary(self, user_id: int) -> bool:
        expires_at = self._pending_summary_by_user_id.get(user_id)
        if expires_at is None:
            return False
        if expires_at <= time.monotonic():
            self._pending_summary_by_user_id.pop(user_id, None)
            return False
        self._pending_summary_by_user_id.pop(user_id, None)
        return True

    def _get_user_summary_language(self, user_id: int) -> str:
        return self._summary_language_by_user_id.get(
            user_id,
            self._settings.summary_default_language,
        )

    @staticmethod
    def _summary_language_label(language_code: str) -> str:
        return "German" if language_code == "de" else "English"

    @staticmethod
    def _extract_media_payload(message: Message) -> TelegramMediaPayload | None:
        if message.voice:
            return TelegramMediaPayload(
                file_id=message.voice.file_id,
                file_name=f"voice_{message.voice.file_unique_id}.ogg",
                source_type="telegram_voice",
                duration_seconds=message.voice.duration,
                size_bytes=message.voice.file_size,
            )

        if message.audio:
            return TelegramMediaPayload(
                file_id=message.audio.file_id,
                file_name=message.audio.file_name or f"audio_{message.audio.file_unique_id}.bin",
                source_type="telegram_audio",
                duration_seconds=message.audio.duration,
                size_bytes=message.audio.file_size,
            )

        if message.video:
            return TelegramMediaPayload(
                file_id=message.video.file_id,
                file_name=f"video_{message.video.file_unique_id}.mp4",
                source_type="telegram_video",
                duration_seconds=message.video.duration,
                size_bytes=message.video.file_size,
            )

        if message.document and message.document.mime_type:
            mime_type = message.document.mime_type.lower()
            if mime_type.startswith("audio/") or mime_type.startswith("video/"):
                return TelegramMediaPayload(
                    file_id=message.document.file_id,
                    file_name=message.document.file_name
                    or f"document_{message.document.file_unique_id}.bin",
                    source_type="telegram_document",
                    duration_seconds=None,
                    size_bytes=message.document.file_size,
                )

        return None
