import os
import unittest
from unittest.mock import patch

from src.config import Settings, parse_allowed_user_ids, resolve_transcription_model


class ConfigTests(unittest.TestCase):
    def test_parse_allowed_user_ids(self) -> None:
        self.assertEqual(parse_allowed_user_ids("1, 2,3"), {1, 2, 3})
        self.assertIsNone(parse_allowed_user_ids(""))
        self.assertIsNone(parse_allowed_user_ids(None))

    def test_parse_allowed_user_ids_invalid(self) -> None:
        with self.assertRaises(ValueError):
            parse_allowed_user_ids("123,abc")

    def test_settings_from_env(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "token-1",
            "TELEGRAM_ALLOWED_USER_IDS": "10,20",
            "MAX_MEDIA_MINUTES": "15",
            "MAX_FILE_SIZE_MB": "25",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env(load_env_file=False)
        self.assertEqual(settings.telegram_bot_token, "token-1")
        self.assertEqual(settings.openai_api_key, "")
        self.assertFalse(settings.enable_summary)
        self.assertEqual(settings.telegram_allowed_user_ids, {10, 20})
        self.assertEqual(settings.max_media_minutes, 15)
        self.assertEqual(settings.max_file_mb, 25)
        self.assertEqual(settings.transcription_model, "turbo")
        self.assertEqual(settings.whisper_language, "auto")
        self.assertEqual(settings.missing_required_values(), [])

    def test_missing_required_values_require_allowlist(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "token-1",
            "TELEGRAM_ALLOWED_USER_IDS": "",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env(load_env_file=False)
        self.assertEqual(settings.missing_required_values(), ["TELEGRAM_ALLOWED_USER_IDS"])

    def test_summary_requires_openai_key_and_model_when_enabled(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "token-1",
            "TELEGRAM_ALLOWED_USER_IDS": "10",
            "ENABLE_SUMMARY": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings.from_env(load_env_file=False)
        self.assertEqual(settings.missing_required_values(), ["OPENAI_API_KEY", "SUMMARY_MODEL"])

    def test_resolve_transcription_model_defaults_to_turbo(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_transcription_model(), "turbo")

    def test_resolve_transcription_model_keeps_legacy_local_model(self) -> None:
        env = {"OPENAI_TRANSCRIPTION_MODEL": "large-v3"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(resolve_transcription_model(), "large-v3")

    def test_resolve_transcription_model_ignores_legacy_openai_api_models(self) -> None:
        for legacy_model in ("whisper-1", "gpt-4o-mini-transcribe"):
            with self.subTest(legacy_model=legacy_model):
                with patch.dict(
                    os.environ,
                    {"OPENAI_TRANSCRIPTION_MODEL": legacy_model},
                    clear=True,
                ):
                    self.assertEqual(resolve_transcription_model(), "turbo")


if __name__ == "__main__":
    unittest.main()
