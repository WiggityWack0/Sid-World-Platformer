"""Hearts/HP (D1): damage, i-frames, knockback, death at zero, wiring."""

import pygame  # noqa: F401  (conftest sets dummy drivers first)

from src import config
from src.player import Player


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


# ------------------------------------------------------------ unit (Player)
def test_damage_reduces_hearts_and_applies_iframes():
    p = Player(100, 100)
    hearts_before = p.hearts
    assert p.damage(200.0) is True           # source on the right -> knock left
    assert p.hearts == hearts_before - 1
    assert p.invuln == config.HURT_INVULN
    assert p.vx < 0 and p.vy < 0


def test_damage_knockback_direction_flips():
    p = Player(100, 100)
    assert p.damage(0.0) is True             # source on the left -> knock right
    assert p.vx > 0


def test_damage_blocked_during_iframes_and_after_death():
    p = Player(100, 100)
    assert p.damage(0.0) is True
    hearts = p.hearts
    assert p.damage(0.0) is False, "i-frames must block re-damage"
    assert p.hearts == hearts
    p.invuln = 0
    p.die("enemy")
    assert p.damage(0.0) is False, "dead players cannot be damaged"


def test_damage_at_zero_hearts_dies():
    p = Player(100, 100)
    p.hearts = 1
    assert p.damage(0.0) is True
    assert p.dead and p.hearts == 0


def test_respawn_refills_hearts():
    p = Player(100, 100)
    p.hearts = 1
    p.respawn_at(32, 64)
    assert p.hearts == p.max_hearts == config.HEARTS_START


# ------------------------------------------------- wiring (PlayingState)
def test_walker_contact_damages_not_kills(pygame_ready):
    from src.enemies import Walker
    from src.player import Input
    game, state = _playing()
    player = state.player
    player.invuln = 0                           # no spawn/respawn i-frames
    walker = Walker(int(player.x) + 2, int(player.y) + 8)
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    hearts_before = player.hearts
    state._combat(Input())
    assert player.hearts == hearts_before - 1
    assert not player.dead, "side contact must damage, not kill (D1)"
    assert player.invuln > 0


def test_contact_during_iframes_is_harmless(pygame_ready):
    from src.enemies import Walker
    from src.player import Input
    game, state = _playing()
    player = state.player
    player.invuln = 0
    walker = Walker(int(player.x) + 2, int(player.y) + 8)
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    state._combat(Input())                      # hit 1: 3 -> 2 hearts
    hearts = player.hearts
    state._combat(Input())                      # still overlapping, i-frames
    assert player.hearts == hearts


def test_spike_hazard_damages_not_kills(pygame_ready):
    from src.level import tiles as T
    game, state = _playing()
    player = state.player
    player.invuln = 0
    tx = player.rect.centerx // config.TILE
    ty = (player.rect.bottom - 4) // config.TILE
    state.level.tiles.set(tx, ty, T.SPIKE)
    hearts_before = player.hearts
    state.update()
    assert state.level.overlaps_hazard(player.rect)
    assert player.hearts == hearts_before - 1
    assert not player.dead, "spikes must hurt, not instantly kill"


def test_pit_still_kills(pygame_ready):
    game, state = _playing()
    player = state.player
    player.y = float(state.level.height + 10)
    state.update()
    assert player.dead, "pit falls must remain instant death"


def test_zero_hearts_flows_to_respawn_with_full_hearts(pygame_ready):
    from src.config import DEATH_ANIM_FRAMES
    game, state = _playing()
    player = state.player
    player.invuln = 0
    player.hearts = 1
    assert player.damage(player.cx + 10.0)
    assert player.dead
    for _ in range(DEATH_ANIM_FRAMES + 4):
        game.state.update()
        if game.state_name != "playing":
            break
    assert game.state_name == "playing"
    new_player = game.state.player
    assert new_player.hearts == config.HEARTS_START
    assert not new_player.dead


# -------------------------------------------------------------------- HUD
def test_hud_draws_hearts_headless(pygame_ready):
    from src.hud import Hud
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    surf.fill((0, 0, 0))
    Hud().draw(surf, 0, 0, 3, 400, "1-1", hearts=2, max_hearts=3)
    region = pygame.Rect(14, 31, 3 * 11, 9)
    found_red = any(surf.get_at((x, y))[0] > 180
                    and surf.get_at((x, y))[1] < 120
                    for x in range(region.x, region.right)
                    for y in range(region.y, region.bottom))
    found_empty = any(surf.get_at((x, y))[:3] == (52, 56, 72)
                      for x in range(region.x, region.right)
                      for y in range(region.y, region.bottom))
    assert found_red, "full heart not drawn"
    assert found_empty, "empty heart not drawn"


def test_hud_without_hearts_arg_still_works(pygame_ready):
    from src.hud import Hud
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    Hud().draw(surf, 0, 0, 3, 400, "1-1")       # backward-compatible signature
