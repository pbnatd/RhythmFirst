from __future__ import annotations

import shutil
import subprocess
import math
from pathlib import Path


class AudioProcessingError(RuntimeError):
    pass


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise AudioProcessingError("FFmpeg/ffprobe не найдены. Установите FFmpeg и повторите запуск.")


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown FFmpeg error"
        raise AudioProcessingError(message)


def prepare_drums(source: Path, destination: Path) -> None:
    ensure_ffmpeg()
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "2",
            "-ar",
            "44100",
            "-af",
            "highpass=f=35,lowpass=f=15000,alimiter=limit=0.9",
            str(destination),
        ]
    )


def probe_duration(path: Path) -> float:
    ensure_ffmpeg()
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AudioProcessingError("Не удалось определить длину аудио")
    try:
        return float(completed.stdout.strip())
    except ValueError as exc:
        raise AudioProcessingError("FFprobe вернул некорректную длину аудио") from exc


def fit_drums_to_duration(source: Path, destination: Path, target_duration: float) -> dict[str, float | int | bool]:
    """Trim or repeat the complete source recording to the requested duration."""
    if target_duration <= 0:
        raise ValueError("target_duration must be positive")
    source_duration = probe_duration(source)
    if source_duration <= 0.05:
        raise AudioProcessingError("Запись барабанов пуста")

    extended = source_duration + 0.05 < target_duration
    repeats = max(1, math.ceil(target_duration / source_duration))
    fade_start = max(0.0, target_duration - 0.02)
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-t",
            f"{target_duration:.4f}",
            "-af",
            f"afade=t=out:st={fade_start:.4f}:d=0.02,alimiter=limit=0.9",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )
    return {
        "source_duration": round(source_duration, 2),
        "target_duration": round(target_duration, 2),
        "extended": extended,
        "repeats": repeats,
    }


def mix_tracks(drums: Path, bass: Path, keys: Path, destination: Path, duration: float) -> None:
    ensure_ffmpeg()
    filter_graph = (
        f"[0:a]atrim=0:{duration:.4f},volume=1.0[d];"
        "[1:a]volume=0.82[b];"
        "[2:a]volume=0.64[k];"
        "[d][b][k]amix=inputs=3:duration=longest:normalize=0,alimiter=limit=0.95[out]"
    )
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(drums),
            "-i",
            str(bass),
            "-i",
            str(keys),
            "-filter_complex",
            filter_graph,
            "-map",
            "[out]",
            "-t",
            f"{duration:.4f}",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(destination),
        ]
    )
