"""Effects layer: particle pooling/cap, shake model, floaters, wiring.

Headless-safe: no display/audio device required (conftest sets dummy drivers).
"""

import pygame

from src import config
from src.camera import Camera
from src.effects import Effects
from src.effects.floaters import Floaters
from src.effects.particles import ParticleSystem
from src.effects.shake import Shake


class FakeCam:
    x = 0.0
    y = 0.0
    ix = 0
    iy = 0


# ---------------------------------------------------------------- particles
def test_particles_cap_under_spam():
    ps = ParticleSystem()
    for _ in range(200):
        ps.dust(0, 0)
        ps.explosion(0, 0)
    assert len(ps) <= config.PARTICLE_CAP


def test_particles_pool_reuses_objects():
    ps = ParticleSystem()
    before = {id(p) for p in ps._pool}
    for _ in range(10):
        for _ in range(50):
            ps.debris(10, 10)
        for _ in range(200):
            ps.update()
    assert len(ps) == 0, "particles leaked past their lifetime"
    assert {id(p) for p in ps._pool} == before, "pool allocated new objects"


def test_particles_update_moves_and_expires():
    ps = ParticleSystem()
    ps._spawn(0.0, 0.0, 1.0, 0.0, 5, (255, 0, 0), 2, 0.0)
    p = ps._pool[0]
    assert len(ps) == 1
    ps.update()
    assert p.x == 1.0 and p.life == 4
    for _ in range(4):
        ps.update()
    assert len(ps) == 0
    assert p.active() is False


def test_particles_draw_headless(pygame_ready):
    ps = ParticleSystem()
    ps._spawn(20.0, 20.0, 0.0, 0.0, 10, (255, 255, 255), 2, 0.0)
    surf = pygame.Surface((64, 64))
    ps.draw(surf, FakeCam())
    assert len(ps) == 1, "draw must not mutate the system"


# ------------------------------------------------------------------- shake
def test_shake_zero_without_trauma():
    s = Shake()
    assert s.offset() == (0, 0)


def test_shake_scales_clamps_and_decays():
    s = Shake()
    s.add(5.0)                                  # clamped to 1.0
    assert s.trauma == 1.0
    s.update()
    dx, dy = s.offset()
    assert abs(dx) <= config.SHAKE_MAX_OFFSET
    assert abs(dy) <= config.SHAKE_MAX_OFFSET
    assert (dx, dy) != (0, 0), "full trauma must produce a visible offset"
    for _ in range(200):
        s.update()
        dx, dy = s.offset()
        assert abs(dx) <= config.SHAKE_MAX_OFFSET
        assert abs(dy) <= config.SHAKE_MAX_OFFSET
    assert s.trauma == 0.0
    assert s.offset() == (0, 0)


def test_shake_add_never_negative():
    s = Shake()
    s.add(-1.0)
    assert s.trauma == 0.0


# ------------------------------------------------------------------ camera
def test_camera_shake_is_view_only():
    cam = Camera(1000, 2000)
    cam.x, cam.y = 100.0, 50.0
    cam.set_shake(3, -2)
    assert (cam.x, cam.y) == (100.0, 50.0), "shake must not move gameplay x/y"
    assert cam.ix == 103 and cam.iy == 48
    assert cam.apply(0, 0) == (-103, -48)
    cam.set_shake(0, 0)
    assert cam.ix == 100 and cam.iy == 50


def test_camera_shake_clamped_at_level_edges():
    cam = Camera(400, 240)                      # level exactly one screen
    assert cam.max_x == 0 and cam.max_y == 0
    cam.set_shake(-3, -5)                       # would reveal void
    assert (cam.shake_dx, cam.shake_dy) == (0, 0)
    cam = Camera(1000, 2000)
    cam.x = float(cam.max_x)
    cam.set_shake(4, 1)                         # at right edge: no rightward
    assert cam.shake_dx == 0


# ---------------------------------------------------------------- floaters
def test_floaters_rise_and_expire():
    fl = Floaters()
    f = fl.spawn(10.0, 20.0, "+100")
    y0 = f.y
    fl.update()
    assert f.y == y0 - config.FLOATER_RISE
    assert len(fl) == 1
    for _ in range(config.FLOATER_LIFE):
        fl.update()
    assert len(fl) == 0


def test_floaters_cap_recycles_oldest():
    fl = Floaters()
    for i in range(config.FLOATER_CAP + 10):
        fl.spawn(float(i), 0.0, str(i))
    assert len(fl) == config.FLOATER_CAP


def test_floaters_draw_headless(pygame_ready):
    fl = Floaters()
    fl.spawn(20.0, 20.0, "1-UP")
    surf = pygame.Surface((64, 64))
    fl.draw(surf, FakeCam())
    assert len(fl) == 1


# ----------------------------------------------------------------- facade
def test_effects_facade_ticks_all_subsystems():
    fx = Effects()
    fx.dust(5, 5)
    fx.floater(5, 5, "+100")
    fx.add_trauma(0.5)
    assert len(fx.particles) > 0
    assert len(fx.floaters) == 1
    assert fx.shake.trauma == 0.5
    fx.update()
    assert fx.shake.trauma < 0.5
    assert fx.shake_offset() != (0, 0), "active trauma must yield an offset"


# ------------------------------------------------------------- wiring (game)
def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))


def _start_playing(game):
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "playing"
    return game.state


def test_game_owns_fx_service(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    assert isinstance(game.fx, Effects)


def test_playing_spawns_coin_sparkle(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    for _ in range(30):
        state.update()                              # settle landing dust
    coin = state.level.coins[0]
    before = len(game.fx.particles)
    state.player.x = float(coin.rect.x)
    state.player.y = float(coin.rect.y)
    state.update()
    assert len(game.fx.particles) > before


def test_playing_death_burst_and_shake(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    state.update()
    state._kill("enemy")
    assert game.fx.shake.trauma > 0.0
    before = len(game.fx.particles)
    state._kill("enemy")                            # guarded: no double-kill
    assert len(game.fx.particles) == before
    # Move camera off the level edges: shake is edge-clamped by design, and
    # the camera.update() that would re-place it is skipped while dead.
    state.camera.x, state.camera.y = 100.0, 10.0
    state.update()                                  # feeds shake to camera
    assert (state.camera.shake_dx, state.camera.shake_dy) != (0, 0)


def test_playing_run_dust_spawns(pygame_ready, monkeypatch):
    from src import inputs
    from src.game import Game
    monkeypatch.setattr(inputs, "action_held", lambda a: a == "right")
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    for _ in range(30):
        state.update()
    before = len(game.fx.particles)
    for _ in range(120):
        state.update()
    assert len(game.fx.particles) <= config.PARTICLE_CAP
    assert len(game.fx.particles) > before, "running player must kick up dust"


def test_playing_land_dust_spawns(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    for _ in range(30):
        state.update()                              # settle on the ground
    assert state.player.on_ground
    before = len(game.fx.particles)
    state.player.on_ground = False
    state.player.y -= 40.0
    state.player.vy = 1.0
    for _ in range(30):
        state.update()
        if state.player.on_ground and len(game.fx.particles) > before:
            break
    assert len(game.fx.particles) > before, "landing must spawn dust"


# ------------------------------------------------- Phase 1b: hooks + sanity
def test_playing_coin_spawns_plus100_floater(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    for _ in range(30):
        state.update()
    coin = state.level.coins[0]
    before = len(game.fx.floaters)
    state.player.x = float(coin.rect.x)
    state.player.y = float(coin.rect.y)
    state.update()
    assert len(game.fx.floaters) == before + 1
    assert game.fx.floaters._pool[0].text == "+100"


def test_playing_one_up_spawns_floater(pygame_ready):
    from src.game import Game
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    state.update()
    game.run.coins = config.COINS_PER_LIFE - 1      # next coin grants a life
    coin = state.level.coins[0]
    state.player.x = float(coin.rect.x)
    state.player.y = float(coin.rect.y)
    lives_before = game.run.lives
    state.update()
    assert game.run.lives == lives_before + 1
    texts = [game.fx.floaters._pool[i].text
             for i in range(len(game.fx.floaters))]
    assert "+100" in texts and "1-UP" in texts


def test_long_run_respects_cap(pygame_ready, monkeypatch):
    """600-tick hold-right run: cap never exceeded, sim never crashes."""
    from src import inputs
    from src.game import Game
    monkeypatch.setattr(inputs, "action_held", lambda a: a == "right")
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    peak = 0
    for _ in range(600):
        if game.state_name != "playing":
            break
        state.update()
        game.fx.update()
        count = len(game.fx.particles)
        assert count <= config.PARTICLE_CAP
        peak = max(peak, count)
    assert peak > 0, "hold-right run must have produced particles"

