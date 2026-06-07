"""Local faster-whisper transcription integration."""

from __future__ import annotations

import asyncio
from pathlib import Path

from faster_whisper import WhisperModel

from src.config import Settings
from src.services.errors import TranscriptionError


class TranscriptionService:
    """Transcribe normalized audio files locally with faster-whisper."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: WhisperModel | None = None
        self._job_semaphore = asyncio.Semaphore(1)

    def is_model_loaded(self) -> bool:
        return self._model is not None

    async def prepare_model(self) -> None:
        try:
            async with self._job_semaphore:
                await asyncio.wait_for(
                    asyncio.to_thread(self._get_model),
                    timeout=self._settings.transcription_timeout_sec,
                )
        except asyncio.TimeoutError as exc:
            raise TranscriptionError(
                "Transcription model loading timed out.",
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise TranscriptionError("Transcription model failed to load.", detail=str(exc)) from exc

    async def transcribe(self, audio_path: Path) -> str:
        try:
            async with self._job_semaphore:
                transcript = await asyncio.wait_for(
                    asyncio.to_thread(self._transcribe_sync, audio_path),
                    timeout=self._settings.transcription_timeout_sec,
                )
        except asyncio.TimeoutError as exc:
            raise TranscriptionError("Transcription timed out.", detail=str(exc)) from exc

        cleaned = transcript.strip()
        if not cleaned:
            raise TranscriptionError("Transcription returned empty text.")
        return cleaned

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                self._settings.transcription_model,
                device=self._settings.whisper_device,
                compute_type=self._settings.whisper_compute_type,
                cpu_threads=self._settings.whisper_cpu_threads,
                num_workers=self._settings.whisper_num_workers,
            )
        return self._model

    def _transcribe_sync(self, audio_path: Path) -> str:
        model = self._get_model()
        configured_language = self._settings.whisper_language.strip()
        language_arg = (
            None if configured_language.lower() in {"", "auto"} else configured_language
        )
        try:
            segments, _info = model.transcribe(
                str(audio_path),
                language=language_arg,
                beam_size=self._settings.whisper_beam_size,
                best_of=self._settings.whisper_best_of,
                vad_filter=self._settings.whisper_vad_filter,
                vad_parameters={
                    "min_silence_duration_ms": self._settings.whisper_vad_min_silence_duration_ms
                },
                condition_on_previous_text=self._settings.whisper_condition_on_previous_text,
            )
        except Exception as exc:
            raise TranscriptionError("Transcription failed.", detail=str(exc)) from exc

        text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        text = " ".join(text_parts).strip()
        if not text:
            raise TranscriptionError("Transcription response missing text.")
        return text
