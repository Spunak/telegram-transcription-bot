"""OpenAI-based transcript summarization service."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import OpenAI

from src.config import Settings
from src.services.errors import SummaryError

LOGGER = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You summarize transcripts for a Telegram utility bot. "
    "Use only transcript content; do not invent details. "
    "Keep output concise, practical, and structured in plain text.\n\n"
    "Return exactly these sections in this order:\n"
    "1) What it is about\n"
    "2) Key points\n"
    "3) Claims / statements\n"
    "4) Terms explained\n"
    "5) What may be unclear\n\n"
    "Rules:\n"
    "- What it is about: 1-2 sentences.\n"
    "- Key points: 3-5 bullet points.\n"
    "- Claims / statements: briefly separate likely factual claims from opinions/interpretations when relevant.\n"
    "- Terms explained: up to 5 short entries.\n"
    "- What may be unclear: 0-2 bullets when transcript seems noisy, partial, or uncertain; otherwise write '- None'.\n"
    "- Avoid fluff and avoid long essays."
)

CHUNK_SYSTEM_PROMPT = (
    "You are preparing chunk notes for a final transcript summary. "
    "Use only provided text. Keep concise."
)

CHUNK_MERGE_SYSTEM_PROMPT = (
    "You will receive chunk summaries of one transcript. "
    "Merge them into one concise final summary using the required structure, "
    "without adding facts not present in the chunk summaries."
)


class SummaryService:
    """Summarize transcripts using OpenAI chat completions."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.openai_api_key)

    async def summarize_transcript(self, transcript: str, *, target_language: str) -> str:
        cleaned = transcript.strip()
        if not cleaned:
            raise SummaryError("Transcript unavailable for summary.")

        language_name = self._language_name(target_language)
        LOGGER.info("Summary requested: transcript_chars=%d", len(cleaned))
        if len(cleaned) <= self._settings.summary_direct_max_chars:
            return await self._summarize_direct(cleaned, language_name=language_name)

        chunks = self._split_text(
            cleaned,
            chunk_size=self._settings.summary_chunk_chars,
            overlap=self._settings.summary_chunk_overlap_chars,
        )
        LOGGER.info("Using chunked summary: chunk_count=%d transcript_chars=%d", len(chunks), len(cleaned))

        chunk_summaries: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            chunk_summaries.append(await self._summarize_chunk(chunk, index=index, total=len(chunks)))

        combined_input = "\n\n".join(
            f"Chunk {idx} summary:\n{summary}" for idx, summary in enumerate(chunk_summaries, start=1)
        )
        return await self._summarize_combined(combined_input, language_name=language_name)

    async def _summarize_direct(self, transcript: str, *, language_name: str) -> str:
        user_prompt = f"Transcript:\n\n{transcript}"
        return await self._create_summary(
            system_prompt=self._final_summary_prompt(language_name),
            user_prompt=user_prompt,
            max_tokens=self._settings.summary_max_output_tokens,
        )

    async def _summarize_chunk(self, chunk: str, *, index: int, total: int) -> str:
        user_prompt = (
            f"Transcript chunk {index}/{total}:\n\n{chunk}\n\n"
            "Return short notes with:\n"
            "- What this chunk is about (1 sentence)\n"
            "- Key points (max 4 bullets)\n"
            "- Unclear/noisy parts (max 2 bullets or '- None')"
        )
        return await self._create_summary(
            system_prompt=CHUNK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=max(250, self._settings.summary_max_output_tokens // 2),
        )

    async def _summarize_combined(self, combined_chunk_summary: str, *, language_name: str) -> str:
        user_prompt = f"Chunk summaries:\n\n{combined_chunk_summary}"
        return await self._create_summary(
            system_prompt=CHUNK_MERGE_SYSTEM_PROMPT + "\n\n" + self._final_summary_prompt(language_name),
            user_prompt=user_prompt,
            max_tokens=self._settings.summary_max_output_tokens,
        )

    async def _create_summary(self, *, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        try:
            summary = await asyncio.wait_for(
                asyncio.to_thread(
                    self._create_summary_sync,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                ),
                timeout=self._settings.summary_timeout_sec,
            )
        except asyncio.TimeoutError as exc:
            raise SummaryError("Summary timed out. Try again later.", detail=str(exc)) from exc

        cleaned = summary.strip()
        if not cleaned:
            raise SummaryError("Summary unavailable.")
        return cleaned

    def _create_summary_sync(self, *, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._settings.openai_summary_model,
                temperature=0.2,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise SummaryError("Summary failed. Try again later.", detail=str(exc)) from exc

        text = self._extract_text(response)
        if text is None:
            raise SummaryError("Summary unavailable.")
        return text

    @staticmethod
    def _language_name(language_code: str) -> str:
        return "German" if language_code == "de" else "English"

    @staticmethod
    def _final_summary_prompt(language_name: str) -> str:
        return (
            SUMMARY_SYSTEM_PROMPT
            + "\n"
            + f"Write the final summary in {language_name}. Keep section headings in {language_name}."
        )

    @staticmethod
    def _extract_text(response: Any) -> str | None:
        choices = getattr(response, "choices", None)
        if not choices:
            return None
        first = choices[0]
        message = getattr(first, "message", None)
        if message is None:
            return None
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts) if parts else None
        return None

    @staticmethod
    def _split_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
        if len(text) <= chunk_size:
            return [text]

        safe_overlap = min(max(overlap, 0), max(chunk_size - 1, 0))
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - safe_overlap
        return chunks
