"""
Chiptune SFX synthesizer: builds every sound effect from scratch using
stdlib arrays (square/triangle/sine/noise + envelopes + pitch sweeps).
Pure sample generation; pygame.mixer.Sound creation happens in the
mixer manager so generation logic stays testable without audio hardware.
"""

import array
import math
import random

from src.config import AUDIO_RATE

TWO_PI = 2.0 * math.pi


def _osc(phase, wave, noise_state=[0]):
    if wave == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if wave == "pulse25":
        frac = (phase % TWO_PI) / TWO_PI
        return 1.0 if frac < 0.25 else -1.0
    if wave == "triangle":
        frac = (phase % TWO_PI) / TWO_PI
        return 4.0 * abs(frac - 0.5) - 1.0
    if wave == "saw":
        frac = (phase % TWO_PI) / TWO_PI
        return 2.0 * frac - 1.0
    if wave == "sine":
        return math.sin(phase)
    noise_state[0] = random.randint(-32767, 32767)
    return noise_state[0] / 32767.0


def note(freq, dur, wave="square", vol=0.6, attack=0.004, release=0.05,
         sweep_to=None, slide_curve="lin"):
    """Render one note; sweep_to glides frequency over the note."""
    n = max(1, int(AUDIO_RATE * dur))
    out = array.array("h", bytes(n * 2))
    phase = 0.0
    a_n = max(1, int(AUDIO_RATE * attack))
    r_n = max(1, int(AUDIO_RATE * release))
    f0 = float(freq)
    f1 = float(sweep_to if sweep_to else freq)
    for i in range(n):
        if slide_curve == "exp" and f0 != f1 and f0 > 0 and f1 > 0:
            f = f0 * ((f1 / f0) ** (i / n))
        else:
            f = f0 + (f1 - f0) * (i / n)
        phase += TWO_PI * f / AUDIO_RATE
        v = _osc(phase, wave)
        env = 1.0
        if i < a_n:
            env = i / a_n
        if i > n - r_n:
            env = min(env, (n - i) / r_n)
        out[i] = int(v * vol * env * 32767)
    return out


def noise_hit(dur, vol=0.5, release=None, highpass_tilt=0.0):
    n = max(1, int(AUDIO_RATE * dur))
    out = array.array("h", bytes(n * 2))
    r_n = int(AUDIO_RATE * (release if release is not None else dur * 0.8))
    prev = 0.0
    rnd = random.Random(1234)
    for i in range(n):
        v = rnd.uniform(-1.0, 1.0)
        v = v * (1.0 - highpass_tilt) + prev * highpass_tilt
        prev = v
        env = 1.0
        if i > n - r_n:
            env = max(0.0, (n - i) / r_n)
        out[i] = int(v * vol * env * 32767)
    return out


def concat(*parts):
    out = array.array("h")
    for p in parts:
        out.extend(p)
    return out


def mix_at(base, offset, part, gain=1.0):
    """Mix `part` into `base` starting at sample `offset` (clamped)."""
    for i, s in enumerate(part):
        idx = offset + i
        if idx >= len(base):
            break
        base[idx] += int(s * gain)


def silence(dur):
    n = max(1, int(AUDIO_RATE * dur))
    return array.array("h", bytes(n * 2))


def _finalize(samples, peak=0.92):
    """Normalize to peak and return raw stereo 16-bit bytes."""
    m = max(1, max((abs(s) for s in samples), default=1))
    if m > 32767 * peak:
        scale = (32767 * peak) / m
        for i in range(len(samples)):
            samples[i] = int(samples[i] * scale)
    raw = samples.tobytes()
    stereo = bytearray(len(raw) * 2)
    stereo[0::4] = raw[0::2]
    stereo[1::4] = raw[1::2]
    stereo[2::4] = raw[0::2]
    stereo[3::4] = raw[1::2]
    return bytes(stereo)


# ------------------------------------------------------------ named SFX

def sfx_jump():
    return _finalize(note(300, 0.16, "square", 0.5, sweep_to=760,
                          slide_curve="exp", release=0.04))


def sfx_bounce():
    return _finalize(note(420, 0.10, "square", 0.5, sweep_to=880,
                          slide_curve="exp", release=0.03))


def sfx_coin():
    a = note(988, 0.07, "square", 0.5, release=0.01)     # B5
    b = note(1319, 0.22, "square", 0.5, release=0.10)    # E6
    return _finalize(concat(a, b))


def sfx_stomp():
    body = note(180, 0.09, "triangle", 0.7, sweep_to=70,
                slide_curve="exp", release=0.05)
    hit = noise_hit(0.07, vol=0.4, highpass_tilt=0.4)
    mix_at(body, 0, hit)
    return _finalize(body)


def sfx_kick():
    body = note(700, 0.14, "square", 0.55, sweep_to=240,
                slide_curve="exp", release=0.07)
    click = noise_hit(0.04, vol=0.35, highpass_tilt=0.2)
    mix_at(body, 0, click)
    return _finalize(body)


def sfx_hurt():
    return _finalize(note(500, 0.20, "saw", 0.5, sweep_to=180,
                          slide_curve="exp", release=0.10))


def sfx_death():
    parts = [
        note(660, 0.12, "square", 0.5, release=0.02),
        silence(0.05),
        note(520, 0.12, "square", 0.5, release=0.02),
        silence(0.05),
        note(390, 0.34, "square", 0.55, sweep_to=140,
             slide_curve="exp", release=0.18),
    ]
    return _finalize(concat(*parts))


def sfx_one_up():
    seq = [(784, 0.10), (1047, 0.10), (1319, 0.10), (1568, 0.24)]
    parts = [note(f, d, "square", 0.5, release=0.03) for f, d in seq]
    return _finalize(concat(*parts))


def sfx_powerup():
    steps = [523, 659, 784, 1047, 1319, 1568]
    parts = [note(f, 0.06, "square", 0.45, release=0.01) for f in steps]
    return _finalize(concat(*parts))


def sfx_warp():
    a = note(880, 0.30, "square", 0.5, sweep_to=180, slide_curve="exp",
             release=0.12)
    b = note(1100, 0.30, "triangle", 0.4, sweep_to=220,
             slide_curve="exp", release=0.14)
    mix_at(a, int(AUDIO_RATE * 0.05), b)
    return _finalize(a)


def sfx_checkpoint():
    a = note(659, 0.10, "square", 0.5, release=0.02)
    b = note(880, 0.16, "square", 0.5, release=0.06)
    return _finalize(concat(a, b))


def sfx_brick():
    body = noise_hit(0.16, vol=0.6, release=0.13, highpass_tilt=0.55)
    thump = note(140, 0.08, "triangle", 0.5, sweep_to=60, release=0.05)
    mix_at(body, 0, thump)
    return _finalize(body)


def sfx_bump():
    return _finalize(note(200, 0.07, "triangle", 0.6, sweep_to=120,
                          slide_curve="exp", release=0.04))


def sfx_select():
    return _finalize(note(880, 0.06, "square", 0.45, release=0.02))


def sfx_confirm():
    a = note(659, 0.07, "square", 0.5, release=0.01)
    b = note(988, 0.14, "square", 0.5, release=0.05)
    return _finalize(concat(a, b))


SFX_BUILDERS = {
    "jump": sfx_jump,
    "bounce": sfx_bounce,
    "coin": sfx_coin,
    "stomp": sfx_stomp,
    "kick": sfx_kick,
    "hurt": sfx_hurt,
    "death": sfx_death,
    "one_up": sfx_one_up,
    "powerup": sfx_powerup,
    "warp": sfx_warp,
    "checkpoint": sfx_checkpoint,
    "brick": sfx_brick,
    "bump": sfx_bump,
    "select": sfx_select,
    "confirm": sfx_confirm,
}

EAGER_SFX = ("jump", "coin", "stomp", "bump", "select")

