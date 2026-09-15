import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from app.audio import fit_drums_to_duration, probe_duration


def write_tone(path: Path, seconds: float = 1.0) -> None:
    sample_rate = 44_100
    samples = array(
        "h",
        (round(8_000 * math.sin(2 * math.pi * 110 * index / sample_rate)) for index in range(round(seconds * sample_rate))),
    )
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


class AudioExtensionTests(unittest.TestCase):
    def test_short_recording_is_repeated_to_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.wav"
            destination = root / "fitted.wav"
            write_tone(source)

            result = fit_drums_to_duration(source, destination, 2.5)

            self.assertTrue(result["extended"])
            self.assertEqual(result["repeats"], 3)
            self.assertAlmostEqual(probe_duration(destination), 2.5, places=2)
            with wave.open(str(destination), "rb") as wav_file:
                wav_file.setpos(wav_file.getnframes() - 2_000)
                tail = array("h")
                tail.frombytes(wav_file.readframes(1_000))
                self.assertGreater(max(abs(value) for value in tail), 100)


if __name__ == "__main__":
    unittest.main()
