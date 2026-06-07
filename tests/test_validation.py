import unittest

from src.utils.validation import extract_first_url, is_http_url, is_instagram_url


class ValidationTests(unittest.TestCase):
    def test_extract_first_url(self) -> None:
        text = "Check this https://example.com/a?b=1 now."
        self.assertEqual(extract_first_url(text), "https://example.com/a?b=1")

    def test_extract_first_url_none(self) -> None:
        self.assertIsNone(extract_first_url("no links here"))

    def test_is_instagram_url(self) -> None:
        self.assertTrue(is_instagram_url("https://www.instagram.com/reel/abc123/"))
        self.assertFalse(is_instagram_url("https://www.youtube.com/watch?v=1"))

    def test_is_http_url(self) -> None:
        self.assertTrue(is_http_url("https://example.com/path"))
        self.assertFalse(is_http_url("ftp://example.com/path"))


if __name__ == "__main__":
    unittest.main()

