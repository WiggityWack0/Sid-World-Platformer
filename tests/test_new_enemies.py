"""5 new enemy types (Phase 5a): behavior, combat semantics, intro
schedule, manager integration, frames. Headless-safe via conftest."""

import random

import pygame

from src import config


GROUND_Y = 12 * 16            # flat_level fixture: solid row 12
NEW_KINDS = ("shieldkin", "bomber", "wallcrawler", "charger", "needler")


class FakeCam:
    x = 0.0
    y = 0.0
    ix = 0
    iy = 0

    def visible(self, rect):
        return True


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def _game_input():
    from src.player import Input
    return Input()


# --------------------------------------------------------------- registry
def test_registry_has_15_types():
    """Registry grew to 15 (5c semantic update): the 4 bosses are
    spawnable via the arena generator but NEVER join the RNG pools."""
    from src.enemies import ENEMY_TYPES
    from src.enemy_manager import spawn_enemy
    assert len(ENEMY_TYPES) == 15
    for kind in NEW_KINDS:
        e = spawn_enemy(kind, 5, 12)
        assert e.rect.bottom == GROUND_Y


def test_new_enemy_frames_exist(pygame_ready):
    from src.assets import AssetFactory
    from src.enemy_manager import spawn_enemy
    fac = AssetFactory()
    for kind in NEW_KINDS:
        e = spawn_enemy(kind, 5, 12)
        assert fac.enemy_frame(e) is not None
        if kind in ("charger", "needler"):
            e.flash = 5
            e.windup = 5
            assert fac.enemy_frame(e) is not None
        e.start_dying()
        assert fac.enemy_frame(e) is not None


# ------------------------------------------------------------- shieldkin
def _shieldkin_at(col, facing):
    from src.enemies.shieldkin import Shieldkin
    s = Shieldkin(col * 16, GROUND_Y - 16)
    s.facing = facing
    return s


def test_shieldkin_front_stomp_blocked(flat_level, pygame_ready):
    game, state = _playing()
    player = state.player
    s = _shieldkin_at(8, facing=1)              # shield faces right
    s.active = True
    state.enemies.enemies.insert(0, s)
    player.x = float(s.x + 2)                   # center on the shield side
    player.y = float(s.y - 20)
    player.vy = 4.0
    score_before = game.run.score
    state._combat(_game_input())
    assert s.alive, "frontal stomp must bounce off the shield"
    assert game.run.score == score_before, "blocked stomp scores nothing"
    assert player.vy < -1, "player must still bounce"


def test_shieldkin_back_stomp_kills(flat_level, pygame_ready):
    game, state = _playing()
    player = state.player
    s = _shieldkin_at(8, facing=1)              # shield right; player left
    s.active = True
    state.enemies.enemies.insert(0, s)
    player.x = float(s.x - 6)
    player.y = float(s.y - 20)
    player.vy = 4.0
    score_before = game.run.score
    state._combat(_game_input())
    assert s.state == "dying"
    assert game.run.score > score_before


def test_shieldkin_form_attack_ignores_shield(flat_level, pygame_ready):
    _game, state = _playing()
    s = _shieldkin_at(8, facing=1)
    assert state._attack_kill(s) is True
    assert s.state == "dying"


# --------------------------------------------------------------- bomber
def test_bomber_lob_and_bomb_burst(flat_level, pygame_ready):
    from src.enemies.bomber import Bomber
    from src.player import Player
    b = Bomber(5 * 16, GROUND_Y - 16)
    b.active = True
    player = Player(12 * 16, GROUND_Y - 26)
    for _ in range(config.BOMBER_COOLDOWN + 10):
        b.update(flat_level, player)
    assert b.shots, "bomber must lob a bomb when the player is in range"
    bomb = b.shots[0]
    flight_w = bomb.rect.width
    saw_burst = False
    for _ in range(config.BOMB_LIFE + 60):
        bomb.update(flat_level)
        if bomb.burst > 0:
            saw_burst = True
            break
    assert saw_burst, "bomb must detonate on the ground"
    assert bomb.rect.width > flight_w, "burst rect grows (AoE)"
    for _ in range(config.BOMB_BURST + 2):
        bomb.update(flat_level)
    assert bomb.dead, "bomb dies after its burst"


def test_bomber_shots_drain_to_manager(flat_level):
    from src.enemies.bomber import Bomb
    from src.enemy_manager import EnemyManager
    from src.player import Player
    mgr = EnemyManager([("bomber", 5, 12)])
    b = mgr.enemies[0]
    b.active = True
    player = Player(12 * 16, GROUND_Y - 26)
    # fire shortly after the lob (cooldown starts at BOMBER_COOLDOWN // 2)
    for _ in range(config.BOMBER_COOLDOWN // 2 + 10):
        mgr.update(flat_level, player, FakeCam())
    assert any(isinstance(p, Bomb) for p in mgr.projectiles), \
        "lobbed bombs must drain into the manager's projectile list"


# ----------------------------------------------------------- wallcrawler
def test_wallcrawler_climb_ceiling_drop(flat_level, pygame_ready):
    from src.enemies.wallcrawler import Wallcrawler
    from src.level import tiles as T
    from src.player import Player
    lvl = flat_level
    # ceiling row 3 across cols 4-16; wall column 10 rows 5-11
    for tx in range(4, 17):
        lvl.tiles.set(tx, 3, T.SOLID)
    for ty in range(5, 12):
        lvl.tiles.set(10, ty, T.SOLID)
    w = Wallcrawler(6 * 16, GROUND_Y - 16)
    w.active = True
    w.facing = 1
    player = Player(2 * 16, GROUND_Y - 26)
    seen = set()
    for _ in range(600):
        w.update(lvl, player)
        seen.add(w.state)
        if w.state == "ceiling":
            break
    assert "climb" in seen and w.state == "ceiling"
    player.x = w.x + 4                           # under it -> drop
    player.y = GROUND_Y - 26
    for _ in range(240):
        w.update(lvl, player)
        if w.state == "patrol" and w.on_ground:
            break
    assert w.state == "patrol" and w.on_ground
    assert w.GRAVITY, "gravity must be restored after the drop"


def test_wallcrawler_reset_restores_gravity(flat_level):
    from src.enemies.wallcrawler import Wallcrawler
    w = Wallcrawler(5 * 16, GROUND_Y - 16)
    w.GRAVITY = False
    w.state = "ceiling"
    w.reset()
    assert w.GRAVITY and w.state == "patrol"


# --------------------------------------------------------------- charger
def test_charger_windup_then_dash_breaks_brick(flat_level):
    from src.enemy_manager import EnemyManager
    from src.level import tiles as T
    from src.player import Player
    lvl = flat_level
    lvl.tiles.set(12, 11, T.BRICK)             # breakable at body height
    mgr = EnemyManager([("charger", 5, 12)])
    c = mgr.enemies[0]
    c.active = True
    player = Player(14 * 16, GROUND_Y - config.PLAYER_H)   # in range, past wall
    saw_windup = saw_dash = False
    for _ in range(240):
        c.update(lvl, player)
        if c.windup > 0:
            saw_windup = True
        if c.state == "attack":
            saw_dash = True
    assert saw_windup and saw_dash, "acquire -> windup -> dash"
    assert lvl.tiles.get(12, 11) == T.EMPTY, "dash must break BRICK"


def test_charger_hard_wall_stops_dash(flat_level):
    from src.enemies.charger import Charger
    from src.level import tiles as T
    from src.player import Player
    lvl = flat_level
    for ty in range(8, 12):
        lvl.tiles.set(12, ty, T.SOLID)
    c = Charger(5 * 16, GROUND_Y - 16)
    c.active = True
    player = Player(14 * 16, GROUND_Y - config.PLAYER_H)   # in range, past wall
    for _ in range(240):
        c.update(lvl, player)
        if c.wall_hit != 0 and c.state != "attack":
            break                              # the bump tick ended the dash
    assert c.state == "patrol", "a hard wall must end the dash"
    assert c.facing == -1, "and the charger turns at the wall"


# --------------------------------------------------------------- needler
def test_needler_aims_at_off_level_player(flat_level):
    from src.enemies.needler import Needler
    from src.level import tiles as T
    from src.player import Player
    lvl = flat_level
    for tx in range(16, 25):
        lvl.tiles.set(tx, 8, T.SOLID)          # high platform
    n = Needler(8 * 16, GROUND_Y - 16)
    n.active = True
    player = Player(18 * 16, 8 * 16 - config.PLAYER_H)
    for _ in range(config.NEEDLER_COOLDOWN + 5):
        n.update(lvl, player)
    assert n.shots, "needler must fire at a distant, off-level player"
    shot = n.shots[0]
    assert shot.vx > 0, "shot travels toward the player"
    assert shot.vy < 0, "shot is aimed upward at the platform"


def test_needler_leads_moving_target(flat_level):
    """A shot at a receding target does NOT aim at the player's current
    center — it leads the target (pure-math intercept, no RNG)."""
    import math

    from src.enemies.needler import Needler
    from src.player import Player
    n = Needler(4 * 16, GROUND_Y - 16)
    n.active = True
    player = Player(12 * 16, GROUND_Y - 26)
    player.vx = 3.0                            # running away (right)
    for _ in range(config.NEEDLER_COOLDOWN + 5):
        n.update(flat_level, player)
    shot = n.shots[0]
    speed = config.NEEDLER_SHOT_SPEED
    assert abs(math.hypot(shot.vx, shot.vy) - speed) < 1e-6
    # aim point per the lead solve (mirrors the state's math)
    t = max(24.0, abs(player.cx - n.cx)) / speed
    aim_x = player.cx + player.vx * t * config.NEEDLER_LEAD
    aim_y = player.cy + max(-14.0, min(14.0, player.vy * t * 0.6))
    ex, ey = aim_x - n.cx, aim_y - (n.cy - 4)
    mag = math.hypot(ex, ey) or 1.0
    assert abs(shot.vx - ex / mag * speed) < 1e-6, "shot aims at the lead point"
    # ...which is NOT the player's current center
    dx0, dy0 = player.cx - n.cx, player.cy - (n.cy - 4)
    cross = abs(dx0 * shot.vy - dy0 * shot.vx)
    assert cross > 1.0, "leading means aiming away from the current center"


# ------------------------------------------------------ generator schedule
def test_pick_enemy_kind_intro_gates():
    from src.level.generator import pick_enemy_kind
    rng = random.Random(1)
    seen = {pick_enemy_kind(rng, 1.0, 0) for _ in range(150)}
    assert not seen & set(NEW_KINDS), \
        "no new types before idx 3 even at max difficulty"
    seen = {pick_enemy_kind(rng, 0.15, 3) for _ in range(150)}
    assert "shieldkin" not in seen, "difficulty gate applies at idx 3"
    seen = {pick_enemy_kind(rng, 1.0, 12) for _ in range(600)}
    assert seen >= set(NEW_KINDS) | {"walker"}, \
        "all types reachable at idx 12 / max difficulty"


def test_generated_high_levels_spawn_new_kinds_deterministically():
    from src.level.generator import generate_level
    from src.level.validator import validate
    a = generate_level(777, 1.0, 15)
    b = generate_level(777, 1.0, 15)
    assert a.enemy_spawns == b.enemy_spawns, "spawn determinism"
    ok, reason = validate(a)
    assert ok, reason
    kinds = set()
    for seed in range(8):
        lvl = generate_level(seed, 1.0, 15)
        ok, reason = validate(lvl)
        assert ok, reason
        kinds |= {k for k, _, _ in lvl.enemy_spawns}
    assert kinds & set(NEW_KINDS), "new types must actually spawn high up"


# ---------------------------------------------------------- headless draw
def test_new_enemies_draw_headless(pygame_ready):
    from src.assets import AssetFactory
    from src.enemy_manager import EnemyManager
    from src.player import Player
    surf = pygame.Surface((320, 240))
    fac = AssetFactory()
    mgr = EnemyManager([(k, 5 + i * 3, 12)
                        for i, k in enumerate(NEW_KINDS)])
    for e in mgr.enemies:
        e.active = True
    player = Player(4 * 16, GROUND_Y - 26)
    from src.level.level import Level
    lvl = Level(60, 18)
    for tx in range(60):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, 1)
    for _ in range(40):
        mgr.update(lvl, player, FakeCam())
    mgr.draw(surf, FakeCam(), fac, 0)


def test_all_new_enemies_stompable_by_star(flat_level, pygame_ready):
    """Star contact kills via the generic _attack_kill (no shield block)."""
    _game, state = _playing()
    from src.enemy_manager import spawn_enemy
    for kind in NEW_KINDS:
        e = spawn_enemy(kind, 8, 12)
        assert state._attack_kill(e) is True
        assert e.state == "dying"


