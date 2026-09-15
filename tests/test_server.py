import unittest

from app.server import extension_for, validate_options


class ServerValidationTests(unittest.TestCase):
    def test_valid_options(self) -> None:
        self.assertEqual(validate_options({"bpm": ["96"], "bars": ["8"], "style": ["neo-soul"]}), (96, 8, "neo-soul"))

    def test_invalid_bpm_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "от 70 до 160"):
            validate_options({"bpm": ["200"]})

    def test_invalid_bars_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "8, 16 или 32"):
            validate_options({"bars": ["4"]})

    def test_32_bar_result_is_supported(self) -> None:
        self.assertEqual(validate_options({"bpm": ["100"], "bars": ["32"], "style": ["indie"]}), (100, 32, "indie"))

    def test_browser_audio_extensions(self) -> None:
        self.assertEqual(extension_for("audio/webm;codecs=opus"), ".webm")
        self.assertEqual(extension_for("audio/mp4"), ".m4a")


if __name__ == "__main__":
    unittest.main()
