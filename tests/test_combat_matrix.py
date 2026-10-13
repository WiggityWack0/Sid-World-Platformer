"""Combat matrix (Phase 2d): explicit form/star/stomp × enemy-state outcomes.

Pins the audited matrix so later phases cannot silently change it:
  fire   -> kills anything but STOMP_PROOF (deflects off those), despawns
  ice    -> freezes any living enemy (slide stops), despawns
  star   -> contact kills unless STOMP_PROOF (then the player is hurt)
  lightning -> kills up to 3 in range, incl. STOMP_PROOF (elemental beats spikes)
  stomp  -> unchanged everywhere, incl. frozen enemies (R3)
  projectiles -> player attack and enemy shot mutually destroy
"""

import pygame  # noqa: F401  (conftest sets dummy drivers first)

from src import config
from src.attacks import AttackProjectile
from src.enemies import Shellback, Walker
from src.enemies.base import Enemy
from src.player import Input, Player


class Spiky(Enemy):
    """Test-only STOMP_PROOF enemy (same pattern as test_enemies.py)."""

    STOMP_PROOF = True


class _EnemyShot:
    """Duck-typed stand-in for the spitter's Projectile (rect/life/dead)."""

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 6, 6)
        self.life = 100

    @property
    def dead(self):
        return self.life <= 0


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def _fire_at(state, enemy):
    """Place an enemy to the player's right and fire one fireball at it."""
    player = state.player
    state.enemies.enemies.insert(0, enemy)
    state.attacks.append(
        AttackProjectile("fire", player.x + 24, player.cy - 4, 1))


def _tick_attacks(state, n=40):
    for _ in range(n):
        state._update_attacks()


# ------------------------------------------------------------- fire cells
def test_fireball_vs_walker_kills(pygame_ready):
    game, state = _playing()
    player = state.player
    walker = Walker(int(player.x) + 40, int(player.y))
    walker.active = True
    _fire_at(state, walker)
    _tick_attacks(state)
    assert walker.state == "dying"
    assert state.attacks == []


def test_fireball_vs_spiky_deflects(pygame_ready):
    game, state = _playing()
    player = state.player
    spiky = Spiky(int(player.x) + 40, int(player.y))
    spiky.active = True
    _fire_at(state, spiky)
    _tick_attacks(state)
    assert spiky.alive, "fireball must not kill STOMP_PROOF"
    assert state.attacks == [], "deflected fireball still despawns"


def test_fireball_vs_sliding_shell_kills(pygame_ready):
    game, state = _playing()
    player = state.player
    shell = Shellback(int(player.x) + 40, int(player.y))
    shell.state = "shell"
    shell.vx = config.SHELL_SLIDE_SPEED            # sliding
    shell.active = True
    _fire_at(state, shell)
    _tick_attacks(state)
    assert shell.state == "dying", "fire must kill a sliding shell"
    assert state.attacks == []


def test_fireball_vs_walking_shellback_kills(pygame_ready):
    game, state = _playing()
    player = state.player
    sb = Shellback(int(player.x) + 40, int(player.y))
    sb.active = True
    _fire_at(state, sb)
    _tick_attacks(state)
    assert sb.state == "dying", "fire must kill a walking shellback outright"


def test_fireball_vs_enemy_projectile_mutual_destruction(pygame_ready):
    game, state = _playing()
    player = state.player
    shot = _EnemyShot(int(player.x) + 30, int(player.cy))
    state.enemies.projectiles.append(shot)
    state.attacks.append(
        AttackProjectile("fire", player.x + 24, player.cy, 1))
    _tick_attacks(state, 5)
    assert shot.dead, "enemy shot must be destroyed"
    assert state.attacks == [], "player attack must be spent too"


# -------------------------------------------------------------- ice cells
def test_ice_vs_sliding_shell_stops_slide_then_thaws(flat_level, pygame_ready):
    from src.enemy_manager import EnemyManager
    mgr = EnemyManager([("shellback", 10, 12)])
    shell = mgr.enemies[0]
    shell.state = "shell"
    shell.vx = config.SHELL_SLIDE_SPEED
    shell.frozen = 30
    player = Player(32, 12 * 16 - 26)

    class _Cam:
        x = 0.0
        y = 0.0

        def visible(self, rect, margin=32):
            return True

    cam = _Cam()
    x0 = shell.x
    for _ in range(30):
        mgr.update(flat_level, player, cam)
    assert shell.x == x0, "frozen shell must not slide"
    assert shell.frozen == 0
    for _ in range(10):                             # thaw: slide resumes
        mgr.update(flat_level, player, cam)
    assert shell.x != x0, "thawed shell must slide again"


# -------------------------------------------------------------- star cells
def test_star_vs_frozen_walker_kills(pygame_ready):
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    player.invuln = 0
    player.apply_powerup("star")
    walker = Walker(int(player.x) + 2, int(player.y) + 8)
    walker.frozen = 30
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    hearts_before = player.hearts
    state._combat(Input())
    assert walker.state == "dying"
    assert player.hearts == hearts_before


def test_star_vs_spiky_deflects_and_hurts_player(pygame_ready):
    game, state = _playing()
    player = state.player
    player.invuln = 0
    player.apply_powerup("star")
    spiky = Spiky(int(player.x) + 2, int(player.y) + 8)
    spiky.active = True
    state.enemies.enemies.insert(0, spiky)
    hearts_before = player.hearts
    state._combat(Input())
    assert spiky.alive, "star must not kill STOMP_PROOF"
    assert player.hearts == hearts_before - 1, "deflected star still hurts"


# --------------------------------------------------------- lightning cells
def test_lightning_vs_frozen_and_spiky_kills(pygame_ready):
    game, state = _playing()
    player = state.player
    player.form = "lightning"
    frozen = Walker(int(player.x) + 30, int(player.y))
    frozen.frozen = 50
    frozen.active = True
    spiky = Spiky(int(player.x) + 55, int(player.y))
    spiky.active = True
    state.enemies.enemies.extend([frozen, spiky])
    state._try_attack()
    assert frozen.state == "dying"
    assert spiky.state == "dying", "elemental beats STOMP_PROOF"


# ------------------------------------------------------------- stomp cells
def test_stomp_vs_frozen_walker_still_bounces(pygame_ready):
    """R3: freezing never changes stomp semantics."""
    from src.enemies import Walker
    game, state = _playing()
    player = state.player
    walker = Walker(int(player.x), int(player.y) + 40)
    walker.frozen = 60
    walker.active = True
    state.enemies.enemies.insert(0, walker)
    player.y = float(walker.y - 20)
    player.vy = 4.0
    state._combat(Input())
    assert walker.state == "dying"
    assert player.vy < -1


# ---------------------------------------------------------- balance (2d)
def test_scoring_ladder_is_monotone():
    """coin < stomp < kick <= form/star kills (audited ladder in config)."""
    assert config.COIN_SCORE < config.STOMP_SCORE < config.KICK_SCORE
    assert config.KICK_SCORE < config.FORM_KILL_SCORE
    assert config.FORM_KILL_SCORE == config.STAR_KILL_SCORE


def test_attack_pacing_constants_sane():
    """Freeze lasts multiple cooldown cycles; shots live long enough to
    cross at least a full screen at their speed (walls kill them first)."""
    assert config.ICE_FREEZE_TICKS >= 3 * config.ATTACK_COOLDOWN
    assert config.FIREBALL_LIFE * config.FIREBALL_SPEED >= config.VIEW_W + 100
    assert config.FIREBALL_SPEED > config.ICE_SHARD_SPEED

