import tempfile
import unittest
import wave
import hashlib
from pathlib import Path

from app.music import SAMPLE_RATE, duration_seconds, public_styles, render_accompaniment


class MusicSynthesisTests(unittest.TestCase):
    def test_duration_formula(self) -> None:
        self.assertEqual(duration_seconds(120, 1), 2.0)
        self.assertEqual(duration_seconds(120, 8), 16.0)

    def test_all_styles_have_public_metadata(self) -> None:
        styles = public_styles()
        self.assertEqual({style["slug"] for style in styles}, {"indie", "neo-soul", "electronic"})
        self.assertTrue(all(style["description"] for style in styles))

    def test_render_creates_non_empty_aligned_stems(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = render_accompaniment(120, 1, "indie", Path(temporary_directory))
            frame_counts = []
            for stem in (result["bass_path"], result["keys_path"]):
                with wave.open(str(stem), "rb") as wav_file:
                    self.assertEqual(wav_file.getframerate(), SAMPLE_RATE)
                    self.assertEqual(wav_file.getnchannels(), 1)
                    frame_counts.append(wav_file.getnframes())
                    frames = wav_file.readframes(wav_file.getnframes())
                    self.assertNotEqual(set(frames), {0})
            self.assertEqual(frame_counts[0], frame_counts[1])
            self.assertAlmostEqual(frame_counts[0] / SAMPLE_RATE, 2.0, places=2)

    def test_unknown_style_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "unknown style"):
                render_accompaniment(100, 1, "missing", Path(temporary_directory))

    def test_styles_render_different_timbres(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            hashes = set()
            root = Path(temporary_directory)
            for slug in ("indie", "neo-soul", "electronic"):
                result = render_accompaniment(100, 1, slug, root / slug)
                content = Path(result["keys_path"]).read_bytes() + Path(result["bass_path"]).read_bytes()
                hashes.add(hashlib.sha256(content).hexdigest())
            self.assertEqual(len(hashes), 3)


if __name__ == "__main__":
    unittest.main()
