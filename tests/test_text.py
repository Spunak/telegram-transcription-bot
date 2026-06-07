import unittest

from src.utils.text import build_transcript_file_content, chunk_text


class TextTests(unittest.TestCase):
    def test_chunk_text_preserves_content(self) -> None:
        original = "a" * 10050
        chunks = chunk_text(original, 1000)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in chunks))
        self.assertEqual("".join(chunks), original)

    def test_build_transcript_file_content(self) -> None:
        content = build_transcript_file_content(
            "hello world",
            source_type="url",
            source_url="https://example.com/video",
            model="gpt-4o-mini-transcribe",
        )
        self.assertIn("source_type: url", content)
        self.assertIn("source_url: https://example.com/video", content)
        self.assertTrue(content.endswith("hello world"))


if __name__ == "__main__":
    unittest.main()

