"""Power-ups (Phase 2b): pickup, timers, star combat, determinism (D6)."""

import pygame  # noqa: F401  (conftest sets dummy drivers first)

from src import config
from src.level.generator import generate_level
from src.player import Input, Player


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def _flat_level():
    from src.level.level import Level
    from src.level import tiles as T
    lvl = Level(40, 18)
    for tx in range(40):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    lvl.spawn = (32, 12 * 16 - 26)
    lvl.respawn = lvl.spawn
    return lvl


# -------------------------------------------------------------- unit (Player)
def test_timed_powerup_sets_state_and_timer():
    p = Player(0, 0)
    assert p.apply_powerup("speed") is True
    assert p.active_powerup == "speed"
    assert p.powerup_timer == config.POWERUP_DURATION


def test_speed_raises_effective_max_and_jump_envelope_unchanged():
    p = Player(0, 0)
    assert p.max_run == config.MAX_RUN
    p.apply_powerup("speed")
    assert p.max_run == config.MAX_RUN * config.POWERUP_SPEED_MULT
    p2 = Player(0, 0)                       # fresh player = base envelope
    env = config.jump_envelope()
    assert env["max_height"] == config.JUMP_VELOCITY ** 2 / (2 * config.GRAVITY)
    assert p2.max_run == config.MAX_RUN and p2.max_walk == config.MAX_WALK
    assert p2.jump_velocity == config.JUMP_VELOCITY


def test_jump_enhance_scales_takeoff_and_gravity():
    p = Player(0, 0)
    p.apply_powerup("jump")
    assert p.jump_velocity == config.JUMP_VELOCITY * config.POWERUP_JUMP_MULT
    assert p.gravity == config.GRAVITY * config.POWERUP_JUMP_GRAV_MULT


def test_powerup_timer_expires_and_clears_effect():
    p = Player(0, 0)
    p.apply_powerup("star")
    assert p.star_active
    p.powerup_timer = 1
    level = _flat_level()
    for _ in range(3):
        p.update(Input(), level)
    assert p.active_powerup is None and not p.star_active


def test_heart_container_raises_max_and_refills():
    p = Player(0, 0)
    p.hearts = 1
    assert p.apply_powerup("heart") is False, "heart is not timed"
    assert p.max_hearts == config.HEARTS_START + 1
    assert p.hearts == p.max_hearts
    p.max_hearts = config.HEARTS_MAX
    p.hearts = 2
    p.apply_powerup("heart")
    assert p.max_hearts == config.HEARTS_MAX, "cap at HEARTS_MAX"
    assert p.hearts == config.HEARTS_MAX


def test_respawn_clears_powerup():
    p = Player(0, 0)
    p.apply_powerup("jump")
    p.respawn_at(0, 0)
    assert p.active_powerup is None and p.powerup_timer == 0


# ------------------------------------------------------------ generator (D6)
def test_generated_levels_have_powerups_and_are_deterministic():
    a = generate_level(12345, 0.5, 2)
    b = generate_level(12345, 0.5, 2)
    assert a.powerups, "generator should place at least one power-up"
    assert [(p.tx, p.ty, p.kind) for p in a.powerups] == \
           [(p.tx, p.ty, p.kind) for p in b.powerups]
    for p in a.powerups:
        assert p.kind in config.POWERUP_KINDS


def test_powerup_placement_is_additive_to_geometry():
    """Placement only reads the finished tile map — never mutates geometry."""
    from src.level.generator import _place_powerups
    lvl = generate_level(999, 0.5, 1)
    tiles_before = bytes(lvl.tiles.data)
    coins_before = len(lvl.coins)

    class _B:                                # duck-typed builder view
        level = lvl

    _place_powerups(_B(), 424242)
    assert bytes(lvl.tiles.data) == tiles_before
    assert len(lvl.coins) == coins_before


# ------------------------------------------------- wiring (PlayingState)
def test_pickup_applies_effect(pygame_ready):
    from src.level.objects import PowerUp
    game, state = _playing()
    player = state.player
    player.invuln = 0
    pu = PowerUp(player.rect.centerx // 16, player.rect.centery // 16, "speed")
    state.level.powerups.append(pu)
    state.update()
    assert pu.collected
    assert player.active_powerup == "speed"


def test_star_kills_walker_without_damage(pygame_ready):
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    player.invuln = 0
    player.apply_powerup("star")
    walker = Walker(int(player.x) + 2, int(player.y) + 8)
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    hearts_before = player.hearts
    score_before = game.run.score
    state._combat(Input())
    assert walker.state == "dying"
    assert player.hearts == hearts_before, "star must prevent contact damage"
    assert game.run.score >= score_before + config.STAR_KILL_SCORE


def test_stomp_semantics_unchanged_under_star(pygame_ready):
    """R3: stomping still works normally while a star is active."""
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    player.invuln = 0
    player.apply_powerup("star")
    walker = Walker(int(player.x), int(player.y) + 40)
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    player.y = float(walker.y - 20)
    player.vy = 4.0
    state._combat(Input())
    assert walker.state == "dying"
    assert player.vy < -1, "stomp bounce must still apply under a star"


def test_hud_draws_powerup_bar_headless(pygame_ready):
    from src.hud import Hud
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    surf.fill((0, 0, 0))
    Hud().draw(surf, 0, 0, 3, 400, "1-1", hearts=3, max_hearts=3,
               powerup=("speed", 0.5))
    found = any(surf.get_at((x, y))[:3] != (0, 0, 0)
                for x in range(24, 65) for y in range(40, 48))
    assert found, "power-up bar not drawn"

