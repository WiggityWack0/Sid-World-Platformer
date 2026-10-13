"""Spatial SFX + tutorial + zone primers (Phase 6c). Headless-safe."""

import pygame

from src import config
from src import progress


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


def _playing(seed=7, idx=0):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.run.level_index = idx
    game.switch_state("playing")
    return game, game.state


# --------------------------------------------------------- spatial math
def test_pan_gains_math():
    from src.audio.mixer_manager import AudioManager
    pan = AudioManager._pan_gains
    b, g = pan(100.0, 100.0)
    assert b == 0.0 and g == 1.0, "centered: no pan, full gain"
    b, g = pan(100.0 + config.SPATIAL_PAN_PX, 100.0)
    assert b == 1.0 and 0.0 < g < 1.0, "full right pan, falloff applied"
    b, g = pan(100.0 - config.SPATIAL_PAN_PX, 100.0)
    assert b == -1.0
    b, _ = pan(1e6, 100.0)
    assert b == 1.0, "balance clamps"
    _, g = pan(100.0 + config.SPATIAL_RANGE, 100.0)
    assert g == 0.0, "silence at range edge"
    _, g2 = pan(100.0 + config.SPATIAL_RANGE + 50, 100.0)
    assert g2 == 0.0, "beyond range stays silent"


def test_play_sfx_at_far_and_muted(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    far = config.SPATIAL_RANGE + 10
    assert game.audio.play_sfx_at("coin", far, 0.0) is None, "beyond range"
    game.audio.muted = True
    assert game.audio.play_sfx_at("coin", 10.0, 0.0) is None, "muted"
    game.audio.muted = False
    game.audio.play_sfx_at("coin", 10.0, 0.0)    # in range: no crash


def test_checkpoint_sound_is_spatial(pygame_ready):
    game, state = _playing()
    calls = []
    real = game.audio.play_sfx_at
    game.audio.play_sfx_at = lambda name, x, lx, vol=1.0: (
        calls.append((name, x, lx)) or real(name, x, lx, vol))
    cp = state.level.checkpoints[0]
    state.player.x = float(cp.tx * config.TILE)
    state.player.y = float((cp.feet_row) * config.TILE - config.PLAYER_H)
    state.update()
    assert any(name == "checkpoint" and abs(x - cp.rect.centerx) < 4
               for name, x, _ in calls), "checkpoint chime is positional"


# -------------------------------------------------------------- tutorial
def test_tutorial_hint_shows_once_and_persists(pygame_ready):
    game, state = _playing(idx=0)
    for _ in range(50):
        state.update()
    assert "jump" in game.progress["tutorial_seen"]
    assert "jump" in progress.load()["tutorial_seen"], "persisted via D3"
    # a fresh state in the same save must NOT repeat it
    game.switch_state("playing")
    state2 = game.state
    seen_before = list(game.progress["tutorial_seen"])
    for _ in range(60):
        state2.update()
    assert game.progress["tutorial_seen"] == seen_before


def test_tutorial_hidden_when_disabled(pygame_ready):
    game, state = _playing(idx=0)
    game.progress["settings"]["tutorial_enabled"] = False
    for _ in range(60):
        state.update()
    assert "jump" not in game.progress["tutorial_seen"]
    state.draw(game.surface)                     # headless ok either way


def test_tutorial_switch_hint(pygame_ready):
    from src.level.objects import Switch
    game, state = _playing(idx=3)
    game.progress["tutorial_seen"].clear()
    state.level.switches.append(Switch(4, 11, "tut_sw"))
    for _ in range(40):
        state.update()
    assert "switch" in game.progress["tutorial_seen"]


# ----------------------------------------------------------- zone primers
def test_zone_primer_once_per_run(pygame_ready):
    game, state = _playing(idx=5)                # zone 1
    assert state._primer_t > 0, "primer shows on first zone entry"
    assert 1 in game.run.zones_seen
    state.draw(game.surface)                     # headless banner
    game.switch_state("playing")                 # next level, same zone
    assert game.state._primer_t == 0, "no repeat within the run"
    game.run.level_index = 10                    # zone 2
    game.switch_state("playing")
    assert game.state._primer_t > 0, "new zone shows again"


def test_zone_primer_respects_config(pygame_ready):
    for zone, z in enumerate(config.ZONES):
        assert z.get("primer"), f"zone {zone} missing a primer string"
