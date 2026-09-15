from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


class TempoDetectionError(ValueError):
    pass


def _read_mono_pcm(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise TempoDetectionError("Для анализа нужен 16-битный PCM WAV")

    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples / 32768.0, sample_rate


def detect_bpm(path: Path, minimum: int = 70, maximum: int = 160) -> dict[str, float | int]:
    """Estimate tempo from a percussive WAV using an onset-envelope autocorrelation.

    The result is deliberately presented as a suggestion: drum grooves commonly
    contain enough subdivisions to create half/double-tempo ambiguity.
    """
    samples, sample_rate = _read_mono_pcm(path)
    duration = len(samples) / sample_rate
    if duration < 2.0:
        raise TempoDetectionError("Запись слишком короткая: нужно хотя бы 2 секунды")

    envelope_rate = 200
    block_size = max(1, round(sample_rate / envelope_rate))
    usable = len(samples) - (len(samples) % block_size)
    blocks = samples[:usable].reshape(-1, block_size)
    envelope = np.sqrt(np.mean(blocks * blocks, axis=1))
    envelope = np.convolve(envelope, np.ones(5, dtype=np.float32) / 5.0, mode="same")
    onset = np.maximum(0.0, np.diff(envelope, prepend=envelope[0]))
    onset -= float(onset.mean())

    energy = float(np.dot(onset, onset))
    if energy < 1e-7:
        raise TempoDetectionError("Не удалось услышать достаточно чёткие удары")

    fft_size = 1 << (2 * len(onset) - 1).bit_length()
    spectrum = np.fft.rfft(onset, fft_size)
    correlation = np.fft.irfft(spectrum * np.conj(spectrum), fft_size)[: len(onset)]
    correlation /= max(float(correlation[0]), 1e-9)

    bpm_values = np.arange(minimum, maximum + 1)
    lags = np.rint(envelope_rate * 60.0 / bpm_values).astype(int)
    scores = correlation[lags]
    best_index = int(np.argmax(scores))
    bpm = int(bpm_values[best_index])
    best_score = float(scores[best_index])

    # Prefer the slower musical pulse when its evidence is close to a strong
    # eighth-note subdivision. The user can always correct the suggestion.
    half_bpm = round(bpm / 2)
    if bpm >= 140 and half_bpm >= minimum:
        half_lag = round(envelope_rate * 60.0 / half_bpm)
        if float(correlation[half_lag]) >= best_score * 0.74:
            bpm = half_bpm
            best_score = float(correlation[half_lag])

    sorted_scores = np.sort(scores)
    runner_up = float(sorted_scores[-2]) if len(sorted_scores) > 1 else 0.0
    separation = max(0.0, best_score - runner_up)
    confidence = float(np.clip(best_score * 1.8 + separation * 3.0, 0.05, 0.99))

    return {
        "bpm": bpm,
        "confidence": round(confidence, 2),
        "duration": round(duration, 2),
    }
