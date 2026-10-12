"""Audio: synthesis output validity + graceful degradation."""

import array

import pygame
import pytest

from src.config import AUDIO_RATE
from src.audio import music_synthesizer as music
from src.audio import sfx_synthesizer as sfx


def test_note_length_and_amplitude():
    samples = sfx.note(440, 0.1, "square", 0.5)
    assert len(samples) == int(AUDIO_RATE * 0.1)
    assert max(abs(s) for s in samples) > 1000          # audible amplitude
    assert max(samples) <= 32767


def test_finalize_produces_stereo_16bit_bytes():
    data = sfx.sfx_coin()
    assert isinstance(data, bytes)
    assert len(data) % 4 == 0                           # L+R frames of int16
    n_frames = len(data) // 4
    assert n_frames > 1000
    # both channels carry the same content (mono duplicated)
    frame0_l = int.from_bytes(data[0:2], "little", signed=True)
    frame0_r = int.from_bytes(data[2:4], "little", signed=True)
    assert frame0_l == frame0_r


@pytest.mark.parametrize("name", sorted(sfx.SFX_BUILDERS))
def test_all_sfx_build_non_empty(name):
    data = sfx.SFX_BUILDERS[name]()
    assert len(data) > 2000
    # non-silent: some frame differs from zero
    assert any(b != 0 for b in data[:2000])


@pytest.mark.parametrize("name", ["title", "level_a", "level_b", "clear",
                                  "game_over"])
def test_music_tracks_build(name):
    data = music.MUSIC_BUILDERS[name]()
    assert len(data) > 10000
    assert len(data) % 4 == 0


def test_looping_tracks_are_grid_aligned():
    """Looping tracks must be exact multiples of their step grid."""
    step = 60.0 / 148 / 4.0
    data = music.track_level_a()
    seconds = (len(data) // 4) / AUDIO_RATE
    bars_seconds = step * 64          # 4 bars * 16 steps
    assert abs(seconds - bars_seconds) < 0.05


def test_music_freq_table():
    assert abs(music.freq("A4") - 440.0) < 0.01
    assert abs(music.freq("C4") - 261.63) < 0.05


def test_audio_manager_degrades_without_mixer(monkeypatch):
    """Game must run muted when the mixer cannot initialize."""

    def boom(*args, **kwargs):
        raise pygame.error("no audio device")

    from src.audio.mixer_manager import AudioManager
    monkeypatch.setattr(pygame.mixer, "init", boom)
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    mgr = AudioManager()
    assert mgr.enabled is False
    assert mgr.play_sfx("jump") is None      # no crash
    mgr.play_music("title")                  # no crash
    mgr.stop_music()
    assert mgr.toggle_mute() is True
    assert mgr.toggle_mute() is False
    mgr.duck_music(True)
