from __future__ import annotations

import math
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path


SAMPLE_RATE = 44_100
BEATS_PER_BAR = 4


@dataclass(frozen=True)
class Style:
    slug: str
    name: str
    description: str
    key: str
    chords: tuple[tuple[int, ...], ...]
    bass_pattern: tuple[tuple[float, int], ...]
    keys_level: float
    bass_level: float


STYLES: dict[str, Style] = {
    "indie": Style(
        slug="indie",
        name="Indie rock",
        description="Прямой бас и раскрытые аккорды — партия остаётся в центре.",
        key="E minor",
        chords=((52, 55, 59), (48, 52, 55), (55, 59, 62), (50, 54, 57)),
        bass_pattern=((0.0, 0), (1.5, 0), (2.0, 7), (3.0, 0)),
        keys_level=0.24,
        bass_level=0.48,
    ),
    "neo-soul": Style(
        slug="neo-soul",
        name="Neo-soul",
        description="Мягкие септаккорды и подвижный бас с паузами.",
        key="D minor",
        chords=((50, 53, 57, 60), (55, 58, 62, 65), (48, 52, 55, 58), (53, 57, 60, 64)),
        bass_pattern=((0.0, 0), (1.75, 7), (2.5, 12), (3.5, 7)),
        keys_level=0.21,
        bass_level=0.42,
    ),
    "electronic": Style(
        slug="electronic",
        name="Electronic",
        description="Пульсирующий бас и короткие синтезаторные аккорды.",
        key="A minor",
        chords=((57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)),
        bass_pattern=((0.0, 0), (0.5, 0), (1.0, 7), (1.5, 0), (2.0, 0), (2.5, 12), (3.0, 7), (3.5, 0)),
        keys_level=0.18,
        bass_level=0.38,
    ),
}


def midi_frequency(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def duration_seconds(bpm: int, bars: int) -> float:
    if bpm <= 0 or bars <= 0:
        raise ValueError("bpm and bars must be positive")
    return bars * BEATS_PER_BAR * 60.0 / bpm


def _write_mono_wav(path: Path, samples: array) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())


def _bass_note(style: Style, beat_in_bar: float, root: int) -> tuple[int, float]:
    selected_offset = style.bass_pattern[0][1]
    selected_start = style.bass_pattern[0][0]
    for start, offset in style.bass_pattern:
        if start <= beat_in_bar:
            selected_start = start
            selected_offset = offset
        else:
            break
    return root - 24 + selected_offset, beat_in_bar - selected_start


def _render_bass(style: Style, bpm: int, bars: int, path: Path) -> None:
    seconds = duration_seconds(bpm, bars)
    beat_seconds = 60.0 / bpm
    total_samples = round(seconds * SAMPLE_RATE)
    pcm = array("h")

    for index in range(total_samples):
        t = index / SAMPLE_RATE
        beat_position = t / beat_seconds
        bar_index = int(beat_position // BEATS_PER_BAR)
        beat_in_bar = beat_position % BEATS_PER_BAR
        chord = style.chords[bar_index % len(style.chords)]
        note, note_phase_beats = _bass_note(style, beat_in_bar, chord[0])
        frequency = midi_frequency(note)
        phase = 2.0 * math.pi * frequency * t
        attack = min(1.0, note_phase_beats * 22.0)
        if style.slug == "indie":
            envelope = attack * math.exp(-0.75 * note_phase_beats)
            voice = math.sin(phase) + 0.46 * math.sin(2 * phase) + 0.16 * math.sin(3 * phase)
        elif style.slug == "neo-soul":
            envelope = attack * math.exp(-1.55 * note_phase_beats)
            vibrato = 1.0 + 0.004 * math.sin(2.0 * math.pi * 4.5 * t)
            voice = math.sin(phase * vibrato) + 0.11 * math.sin(2 * phase)
        else:
            envelope = attack * math.exp(-2.7 * note_phase_beats)
            voice = math.sin(phase) + 0.34 * math.sin(3 * phase) + 0.16 * math.sin(5 * phase)
        value = voice * envelope * style.bass_level / 1.35
        pcm.append(max(-32767, min(32767, round(value * 32767))))

    _write_mono_wav(path, pcm)


def _render_keys(style: Style, bpm: int, bars: int, path: Path) -> None:
    seconds = duration_seconds(bpm, bars)
    beat_seconds = 60.0 / bpm
    total_samples = round(seconds * SAMPLE_RATE)
    pcm = array("h")

    for index in range(total_samples):
        t = index / SAMPLE_RATE
        beat_position = t / beat_seconds
        bar_index = int(beat_position // BEATS_PER_BAR)
        beat_in_bar = beat_position % BEATS_PER_BAR
        chord = style.chords[bar_index % len(style.chords)]

        if style.slug == "electronic":
            pulse_phase = beat_in_bar % 0.5
            envelope = min(1.0, pulse_phase * 30.0) * math.exp(-8.5 * pulse_phase)
            chord = (chord[int((beat_in_bar * 2) % len(chord))],)
        elif style.slug == "neo-soul":
            hit_phase = beat_in_bar if beat_in_bar < 2.5 else beat_in_bar - 2.5
            envelope = min(1.0, hit_phase * 18.0) * math.exp(-2.4 * hit_phase)
            envelope *= 0.88 + 0.12 * math.sin(2.0 * math.pi * 4.2 * t)
        else:
            attack = min(1.0, beat_in_bar * 5.0)
            release = max(0.0, min(1.0, (BEATS_PER_BAR - beat_in_bar) * 2.0))
            envelope = attack * release * (0.78 + 0.14 * math.sin(2.0 * math.pi * 5.2 * t))

        voice = 0.0
        for note in chord:
            frequency = midi_frequency(note)
            phase = 2.0 * math.pi * frequency * t
            if style.slug == "indie":
                voice += math.sin(phase) + 0.32 * math.sin(2.002 * phase)
            elif style.slug == "neo-soul":
                voice += math.sin(phase) + 0.22 * math.sin(2 * phase) * math.exp(-1.5 * (beat_in_bar % 2.5))
            else:
                voice += math.sin(phase) + 0.38 * math.sin(2 * phase) + 0.12 * math.sin(4 * phase)
        voice /= len(chord) * 1.4
        value = voice * envelope * style.keys_level
        pcm.append(max(-32767, min(32767, round(value * 32767))))

    _write_mono_wav(path, pcm)


def render_accompaniment(bpm: int, bars: int, style_slug: str, output_dir: Path) -> dict[str, object]:
    try:
        style = STYLES[style_slug]
    except KeyError as exc:
        raise ValueError(f"unknown style: {style_slug}") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    bass_path = output_dir / "bass.wav"
    keys_path = output_dir / "keys.wav"
    _render_bass(style, bpm, bars, bass_path)
    _render_keys(style, bpm, bars, keys_path)

    return {
        "bpm": bpm,
        "bars": bars,
        "duration": duration_seconds(bpm, bars),
        "style": style.slug,
        "style_name": style.name,
        "key": style.key,
        "bass_path": bass_path,
        "keys_path": keys_path,
    }


def public_styles() -> list[dict[str, str]]:
    return [
        {
            "slug": style.slug,
            "name": style.name,
            "description": style.description,
            "key": style.key,
        }
        for style in STYLES.values()
    ]
