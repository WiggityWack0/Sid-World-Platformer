"""Physics: landing, walls, jump-envelope consistency, feel, platforms."""

import pygame

from src import config
from src.level import tiles as T
from src.level.level import Level
from src.level.objects import MovingPlatform
from src.player import Input, Player


def _level_with_wall():
    lvl = Level(30, 18)
    for tx in range(30):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    lvl.tiles.set(10, 11, T.SOLID)
    lvl.tiles.set(10, 10, T.SOLID)
    return lvl


def test_player_lands_on_ground(flat_level):
    p = Player(32, 40)
    inp = Input()
    for _ in range(150):
        p.update(inp, flat_level)
    assert p.on_ground
    expected = 12 * 16 - config.PLAYER_H
    assert abs(p.y - expected) < 0.5


def test_player_cannot_pass_wall():
    lvl = _level_with_wall()
    p = Player(48, 12 * 16 - config.PLAYER_H)
    inp = Input()
    inp.right = True
    inp.run = True
    for _ in range(200):
        p.update(inp, lvl)
    wall_rect = pygame.Rect(10 * 16, 10 * 16, 16, 32)
    assert not p.rect.colliderect(wall_rect)
    assert p.x <= 10 * 16 - config.PLAYER_W + 0.01


def test_jump_envelope_matches_generator_constants(flat_level):
    """Measured jump must stay within the envelope the validator uses."""
    launch_y = 12 * 16 - config.PLAYER_H
    p = Player(32, launch_y)
    inp = Input()
    inp.right = True
    inp.run = True
    for _ in range(40):
        p.update(inp, flat_level)
    assert p.vx >= config.MAX_RUN * 0.9 - 0.01

    start_x = p.x
    p.queue_jump()
    inp.jump_held = True
    top = p.y
    landed_at = None
    was_airborne = False
    for _ in range(140):
        p.update(inp, flat_level)
        if not p.on_ground:
            was_airborne = True
        elif was_airborne:
            landed_at = p.x
            top = min(top, p.y)
            break
        top = min(top, p.y)
    assert landed_at is not None, "never landed"
    rise = launch_y - top
    distance = landed_at - start_x
    # theoretical envelope (generator + validator derive from these)
    assert rise <= config.MAX_JUMP_HEIGHT + 0.01
    assert distance <= config.MAX_JUMP_DISTANCE + 0.01
    # and comfortably inside the tile-quantised envelope
    assert rise <= config.UP_TILES * config.TILE
    assert distance <= config.DIST_TILES * config.TILE


def test_coyote_time_allows_late_jump():
    lvl = Level(30, 18)
    for tx in range(10, 30):              # ground only on the right side
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    p = Player(20 * 16, 12 * 16 - config.PLAYER_H)
    inp = Input()
    inp.left = True                       # walk toward the ledge
    for _ in range(150):
        p.update(inp, lvl)
        if not p.on_ground:
            break
    assert not p.on_ground, "never walked off the ledge"
    p.queue_jump()                        # within coyote window
    inp.jump_held = True
    p.update(inp, lvl)
    assert p.vy < -1, "coyote jump failed"


def test_jump_buffer_triggers_on_landing(flat_level):
    p = Player(32, 12 * 16 - config.PLAYER_H - 70)
    inp = Input()
    for _ in range(80):
        p.update(inp, flat_level)
        if p.on_ground:
            break
    assert p.on_ground
    p.queue_jump()                        # press just before/at touchdown
    for _ in range(8):
        p.update(inp, flat_level)
        if p.vy < 0:
            break
    assert p.vy < 0, "buffered jump did not fire on landing"


def test_variable_jump_height(flat_level):
    """Releasing jump early cuts the velocity (short hop)."""
    p = Player(32, 12 * 16 - config.PLAYER_H)
    inp = Input()
    for _ in range(4):
        p.update(inp, flat_level)         # settle on the ground first
    assert p.on_ground
    inp.jump_held = True
    p.queue_jump()
    p.update(inp, flat_level)            # jump starts here
    assert p.vy < 0
    for _ in range(3):
        p.update(inp, flat_level)
    vy_before = p.vy
    assert vy_before < 0
    inp.jump_held = False                # release early
    p.update(inp, flat_level)
    assert p.vy <= vy_before * config.JUMP_CUT_FACTOR + 0.6


def test_moving_platform_carries_player(flat_level):
    # carve a pit in the flat level and bridge it with a mover
    for tx in range(10, 17):
        for ty in range(12, 18):
            flat_level.tiles.set(tx, ty, T.EMPTY)
    mover = MovingPlatform(10 * 16, 12 * 16, 48, "x", 5 * 16, 2.0)
    flat_level.movers.append(mover)
    start_x = 10 * 16 + 18
    p = Player(start_x, 12 * 16 - config.PLAYER_H)
    inp = Input()
    for _ in range(40):
        flat_level.update()
        p.update(inp, flat_level)
    assert p.on_ground
    assert p.x > start_x + 20, "player was not carried by the platform"


def test_player_crouch_hitbox(flat_level):
    p = Player(32, 12 * 16 - config.PLAYER_H)
    inp = Input()
    for _ in range(5):
        p.update(inp, flat_level)
    assert p.on_ground
    inp.down = True
    p.update(inp, flat_level)
    assert p.crouching and p.h == config.PLAYER_CROUCH_H
    inp.down = False
    p.update(inp, flat_level)
    assert not p.crouching and p.h == config.PLAYER_H
