"""Boss framework (Phase 5b): Boss base HP/phase/stagger/defeat, arena
template invariants, boss bar/banner/music wiring. A test-double boss
stands in for the concrete bosses that arrive in 5c."""

import pygame

from src import config
from src.enemies.boss import Boss
from src.level import tiles as T

GROUND_ROW = config.GROUND_ROW          # generator levels: solid begins here
FLAT_ROW = 12                           # hand-built flat_level fixture row


class BossDouble(Boss):
    """Minimal concrete boss for the framework tests (not shipped)."""
    KIND = "BossDouble"
    name = "TEST BOSS"
    MAX_HP = 4
    PHASE_THRESHOLDS = (0.5,)

    def think(self, level, player):
        self.vx = 0.0


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


# ------------------------------------------------------- HP / phases
def test_boss_hp_phases_and_stagger():
    b = BossDouble(100, 100)
    assert b.hp == 4 and b.phase == 0 and b.is_boss
    assert b.take_damage(1) is False            # 3/4 > 0.5 -> still phase 0
    assert b.phase == 0 and b.hp == 3
    assert b.take_damage(1) is False            # 2/4 <= 0.5 -> phase 1
    assert b.phase == 1
    assert b.stagger == BossDouble.STAGGER, "phase change opens a stagger"


def test_boss_stomp_bounce_vs_stagger():
    b = BossDouble(100, 100)
    assert b.stomped(None) == "bounce"          # armored outside stagger
    assert b.hp == BossDouble.MAX_HP
    b.stagger = 5
    assert b.stomped(None) == "stomp"
    assert b.hp == BossDouble.MAX_HP - 1


def test_boss_defeat_sequence_and_reset():
    b = BossDouble(100, 100)
    assert b.take_damage(b.hp) is True          # killing blow
    assert b.state == "dying"
    for _ in range(BossDouble.DEFEAT_TICKS + 2):
        b.update(_flat(), _player())
    assert b.defeated
    b.reset()
    assert b.hp == b.max_hp and b.state == "patrol" and not b.defeated


def _flat():
    from src.level.level import Level
    lvl = Level(40, 18)
    for tx in range(40):
        for ty in range(12, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    return lvl


def _player():
    from src.player import Player
    return Player(32, 12 * 16 - 26)


# -------------------------------------------------- combat integration
def test_attack_kill_routes_boss_damage(flat_level, pygame_ready):
    _game, state = _playing()
    b = BossDouble(100, 100)
    assert state._attack_kill(b) is False       # damaged, not killed
    assert b.hp == BossDouble.MAX_HP - 1
    while b.alive:                              # drain to death
        state._attack_kill(b)
    assert b.state == "dying"


def test_lightning_routes_boss_damage(flat_level, pygame_ready):
    game, state = _playing()
    b = BossDouble(int(state.player.x) + 10, int(state.player.y) - 8)
    b.active = True
    state.enemies.enemies.insert(0, b)
    score_before = game.run.score
    state._lightning()
    assert b.alive, "lightning must not instakill a boss"
    assert b.hp == BossDouble.MAX_HP - 1
    assert game.run.score == score_before, "no kill score on a survivor"


def test_sliding_shell_never_crushes_boss(flat_level):
    from src.enemy_manager import EnemyManager
    from src.player import Player
    mgr = EnemyManager([("shellback", 6, 12)])
    b = BossDouble(8 * 16, 12 * 16 - 32)
    mgr.enemies.append(b)
    shell = mgr.enemies[0]
    shell.state = "shell"
    shell.vx = 5.0
    shell.shell_timer = 999
    shell.x = float(b.x - 14)
    player = Player(2 * 16, 12 * 16 - 26)
    for _ in range(30):
        mgr.update(flat_level, player, _cam())
        if shell.rect.colliderect(b.rect):
            break
    assert b.alive, "sliding shells must not crush bosses (5b)"


class _cam:
    x = 0.0
    y = 0.0
    ix = 0
    iy = 0

    def visible(self, rect):
        return True


# ------------------------------------------------------ arena invariants
def _arena_level(seed=5, idx=4):
    from src.level.generator import generate_level
    return generate_level(seed, 1.0, idx)


def test_arena_only_on_zone_finals():
    from src.level.generator import generate_level
    for idx in range(20):
        lvl = generate_level(11, 1.0, idx)
        assert lvl.has_arena == (idx % 5 == 4), f"idx={idx}"


def test_arena_width_unchanged():
    from src.config import LEN_GROWTH, START_LEN_SCREENS, TILE, TILES_PER_SCREEN
    lvl = _arena_level()
    zl = config.zone_level_of(4)
    assert lvl.tiles.w == (START_LEN_SCREENS + zl * LEN_GROWTH) \
        * TILES_PER_SCREEN + 18, "arena carve must not change width"


def test_arena_invariants():
    """Plan §5.6: entry corridor, >=2 jump-heights dodge space, >=6-tile
    runway, no soft-lock geometry."""
    from src.config import TILE
    lvl = _arena_level()
    x0 = lvl.arena_x0
    w = lvl.tiles.w
    ground = GROUND_ROW
    # entry corridor: open at the carve edge, floor beneath
    assert not lvl.tiles.solid_at(x0 - 1, ground - 1)
    assert not lvl.tiles.solid_at(x0, ground - 1)
    assert lvl.tiles.solid_at(x0, ground)
    # vertical dodge space: rows 2..8 clear across the whole arena
    # (>= 7 rows = 112 px + the walk-under gap; perch adds one row only)
    perch = set(range(x0 + (config.ARENA_COLS - 4) // 2,
                      x0 + (config.ARENA_COLS + 4) // 2))
    clear_rows = 0
    for ty in range(2, ground):
        for tx in range(x0, w):
            solid = lvl.tiles.solid_at(tx, ty)
            if ty == ground - 3 and tx in perch:
                assert solid, "perch exists"
                continue
            assert not solid, f"row {ty} col {tx} must be clear"
        clear_rows += 1
    assert clear_rows >= 10                    # 11 clear rows (>=2 jumps)
    # >=6-tile flat runway: ground solid + headroom across >= 6 cols
    runway = 0
    for tx in range(x0, w):
        if (lvl.tiles.solid_at(tx, ground)
                and not lvl.tiles.solid_at(tx, ground - 1)
                and not lvl.tiles.solid_at(tx, ground - 2)):
            runway += 1
        else:
            runway = 0
    assert runway >= 6
    # no soft-lock: goal sits on the arena floor, reachable corridor
    assert lvl.goal is not None
    assert lvl.goal.rect.bottom == ground * TILE


def test_arena_levels_validate_and_are_deterministic():
    from src.level.generator import generate_level
    from src.level.validator import validate
    for idx in (4, 9, 14, 19):
        a = generate_level(21, 1.0, idx)
        b = generate_level(21, 1.0, idx)
        assert bytes(a.tiles.data) == bytes(b.tiles.data), f"idx={idx}"
        assert a.enemy_spawns == b.enemy_spawns
        ok, reason = validate(a)
        assert ok, f"idx={idx}: {reason}"


def test_arena_has_no_dangling_door_ids():
    seen_arena = 0
    for seed in range(8):
        lvl = generate_level_safe(seed, 1.0, 4)
        if not lvl.has_arena:
            continue
        seen_arena += 1
        ids = {s.switch_id for s in lvl.switches} \
            | {p.plate_id for p in lvl.plates}
        for d in lvl.doors:
            assert d.switch_id in ids, "arena carve left a dangling id"
    assert seen_arena > 0


def generate_level_safe(seed, diff, idx):
    from src.level.generator import generate_level
    return generate_level(seed, diff, idx)


# ------------------------------------------------------ HUD / music / bar
def test_boss_music_registered():
    from src.audio.music_synthesizer import LOOPING_MUSIC, MUSIC_BUILDERS
    assert "boss" in MUSIC_BUILDERS and "boss" in LOOPING_MUSIC
    assert len(MUSIC_BUILDERS["boss"]()) > 1000


def test_boss_bar_draws_headless(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.hud.draw_boss_bar(game.surface, "TEST BOSS", 0.5)


def test_goal_locked_boss_clause():
    from src.level.level import Level
    lvl = Level(40, 18)
    assert not lvl.goal_locked(), "defaults must keep identity (5b)"
    lvl.boss_required = True
    assert lvl.goal_locked()
    lvl.boss_defeated = True
    assert not lvl.goal_locked()


# ---------------------------------------------- playing-state integration
def test_playing_boss_banner_damage_and_unlock(flat_level, pygame_ready):
    game, state = _playing()
    lvl = state.level
    lvl.boss_required = True
    b = BossDouble(int(state.player.x) + 40, 12 * 16 - 32)
    b.active = True
    state.enemies.enemies.insert(0, b)
    state.update()
    assert state._boss is b
    assert state._boss_seen and state._banner_t > 0, "intro banner once"
    assert lvl.goal_locked(), "boss lock holds while the boss lives"
    # kill the boss; the defeat sequence unlocks the goal
    b.take_damage(b.hp)
    state.player.x = 32.0                       # stay clear of the corpse
    for _ in range(BossDouble.DEFEAT_TICKS + 4):
        state.update()
    assert b.defeated and lvl.boss_defeated
    assert not lvl.goal_locked()
    state.draw(game.surface)                    # bar + banner headless ok


def test_playing_bar_only_for_living_active_boss(flat_level, pygame_ready):
    game, state = _playing()
    state.update()
    assert state._boss is None
    state.draw(game.surface)                    # no boss -> no bar, no crash

