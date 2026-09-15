import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from app.analysis import TempoDetectionError, detect_bpm


SAMPLE_RATE = 44_100


def write_click_track(path: Path, bpm: int, seconds: float = 12.0) -> None:
    samples = array("h", [0]) * round(seconds * SAMPLE_RATE)
    beat_samples = round(SAMPLE_RATE * 60 / bpm)
    click_length = round(0.035 * SAMPLE_RATE)
    for start in range(0, len(samples), beat_samples):
        for offset in range(min(click_length, len(samples) - start)):
            envelope = math.exp(-offset / (SAMPLE_RATE * 0.008))
            samples[start + offset] = round(22_000 * envelope * math.sin(2 * math.pi * 110 * offset / SAMPLE_RATE))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())


class TempoDetectionTests(unittest.TestCase):
    def test_detects_click_track_tempo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "clicks.wav"
            write_click_track(path, 120)
            result = detect_bpm(path)
            self.assertLessEqual(abs(int(result["bpm"]) - 120), 1)
            self.assertGreater(float(result["confidence"]), 0.1)

    def test_rejects_short_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "short.wav"
            write_click_track(path, 100, seconds=1.0)
            with self.assertRaisesRegex(TempoDetectionError, "слишком короткая"):
                detect_bpm(path)


if __name__ == "__main__":
    unittest.main()
