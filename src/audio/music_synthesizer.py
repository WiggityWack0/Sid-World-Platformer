"""
Original chiptune music synthesizer.

Composes simple, on-key loops (C major for bright tracks, A minor for the
hard track) from lead/bass voices rendered with the shared SFX primitives.
Tracks are returned as raw stereo sample bytes and cached by the mixer
manager; loops are exact multiples of the step grid so they repeat
seamlessly.
"""

import array
import math

from src.config import AUDIO_RATE
from src.audio.sfx_synthesizer import _finalize, mix_at, note

_SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def freq(name):
    """'C5' -> Hz (C4 = middle C = MIDI 60)."""
    letter = name[0]
    octave = int(name[-1])
    midi = (octave + 1) * 12 + _SEMI[letter]
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _render(bpm, bars, voices, fade_out=0.04):
    """voices: list of (wave, volume, [(step, note, dur_steps), ...])."""
    step_sec = 60.0 / bpm / 4.0                 # one 16th note
    total_steps = bars * 16
    total_n = int(AUDIO_RATE * step_sec * total_steps)
    buf = array.array("h", bytes(total_n * 2))
    for wave, vol, events in voices:
        for start, name, dur in events:
            if name is None:
                continue
            dur_sec = step_sec * dur * 0.96
            part = note(freq(name), dur_sec, wave, vol,
                        attack=0.005, release=min(0.06, dur_sec * 0.5))
            mix_at(buf, int(start * step_sec * AUDIO_RATE), part)
    # short fade so loops don't click
    fade_n = int(AUDIO_RATE * fade_out)
    if fade_n and fade_n < total_n:
        for i in range(fade_n):
            g = i / fade_n
            idx = total_n - fade_n + i
            buf[idx] = int(buf[idx] * g)
    return _finalize(buf)


def _bar_roots(roots, oct_note_len=16, hits=(0, 4, 8, 12), dur=2):
    events = []
    for bar, root in enumerate(roots):
        for h in hits:
            events.append((bar * oct_note_len + h, root, dur))
    return events


# ---------------------------------------------------------------- tracks

def track_title():
    lead = [
        (0, "C5", 4), (4, "E5", 4), (8, "G5", 6), (14, "E5", 2),
        (16, "D5", 4), (20, "F5", 4), (24, "A5", 6), (30, "G5", 2),
        (32, "E5", 4), (36, "G5", 4), (40, "C6", 8),
        (48, "B5", 4), (52, "A5", 4), (56, "G5", 8),
    ]
    bass_roots = ["C3", "G2", "A2", "F2"]
    bass = []
    for bar, root in enumerate(bass_roots):
        bass.append((bar * 16, root, 8))
        bass.append((bar * 16 + 8, root, 8))
    return _render(110, 4, [
        ("square", 0.30, lead),
        ("triangle", 0.42, bass),
    ])


def track_level_a():
    lead = [
        (0, "G4", 2), (2, "A4", 2), (4, "C5", 2), (6, "A4", 2),
        (8, "G4", 2), (10, "E4", 2), (12, "G4", 4),
        (16, "A4", 2), (18, "C5", 2), (20, "D5", 4), (24, "C5", 4),
        (28, "E5", 4),
        (32, "D5", 2), (34, "C5", 2), (36, "A4", 2), (38, "G4", 2),
        (40, "E4", 4), (44, "G4", 4),
        (48, "C5", 8), (56, "G4", 4), (60, "A4", 4),
    ]
    bass = _bar_roots(["C2", "C2", "F2", "G2"])
    return _render(148, 4, [
        ("square", 0.34, lead),
        ("triangle", 0.44, bass),
    ])


def track_level_b():
    lead = [
        (0, "A4", 2), (2, "C5", 2), (4, "E5", 2), (6, "C5", 2),
        (8, "D5", 4), (12, "E5", 2), (14, "F5", 2),
        (16, "E5", 4), (20, "C5", 4), (24, "D5", 2), (26, "E5", 2),
        (28, "A4", 4),
        (32, "G4", 2), (34, "A4", 2), (36, "C5", 2), (38, "D5", 2),
        (40, "E5", 8),
        (48, "F5", 4), (52, "E5", 4), (56, "D5", 8),
    ]
    bass = _bar_roots(["A2", "A2", "F2", "G2"])
    return _render(154, 4, [
        ("square", 0.34, lead),
        ("triangle", 0.46, bass),
    ])


def track_clear():
    lead = [
        (0, "C5", 2), (2, "E5", 2), (4, "G5", 2), (6, "C6", 4),
        (12, "B5", 2), (14, "C6", 6),
    ]
    bass = [(0, "C3", 8), (8, "G3", 4), (12, "C3", 8)]
    return _render(132, 2, [
        ("square", 0.40, lead),
        ("triangle", 0.45, bass),
    ])


def track_game_over():
    lead = [
        (0, "A4", 4), (4, "G4", 4), (8, "F4", 4), (12, "E4", 6),
        (20, "A3", 10),
    ]
    bass = [(0, "A2", 16), (16, "E2", 14)]
    return _render(88, 2, [
        ("triangle", 0.50, lead),
        ("sine", 0.50, bass),
    ], fade_out=0.35)


MUSIC_BUILDERS = {
    "title": track_title,
    "level_a": track_level_a,
    "level_b": track_level_b,
    "clear": track_clear,
    "game_over": track_game_over,
}

LOOPING_MUSIC = {"title", "level_a", "level_b"}
