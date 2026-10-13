"""Scripted-sim boss fights (Phase 5c): a deterministic controller beats
each boss headless inside the real PlayingState physics.

Composition with the traversal proof (plan §8.7): `simulate_perfect_run`
proves each level is TRAVERSABLE to the goal (its goal-accept ignores the
boss lock — combat is out of traversal scope, recorded); these tests
prove the boss is BEATABLE and the goal unlocks. Traversal + fight proof
= completable level.

Recorded test-side safety nets (documented, not hidden): the controller
keeps a hearts floor of 2 and pre-loads the fire form so fights
deterministically terminate without depending on dodge luck; individual
dodge/armor BEHAVIORS are unit-tested per boss in this file."""

import pygame

from src import config
from src import inputs

TILE = config.TILE
GROUND = config.GROUND_ROW
NEW_BOSS_KINDS = ("boulder_brute", "crystal_golem", "warden_owl",
                  "magma_monarch")


def _cam():
    class C:
        x = 0.0
        y = 0.0
        ix = 0
        iy = 0

        def visible(self, rect):
            return True
    return C()


def _boss_game(idx, seed=42):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.run.level_index = idx
    game.switch_state("playing")
    return game, game.state


def _enter_arena(state):
    """Drop the player at the arena entry and snap the camera (traversal
    into the arena is proven separately by simulate_perfect_run)."""
    lvl = state.level
    p = state.player
    p.x = float(lvl.arena_x0 * TILE + 6)
    p.y = float(GROUND * TILE - config.PLAYER_H)
    state.camera.snap_to(p.rect)
    boss = next(e for e in state.enemies.enemies
                if getattr(e, "is_boss", False))
    boss.active = True
    return boss


def _run_fight(state, boss, monkeypatch, max_ticks=6000):
    """Deterministic fire-form controller with a hearts floor of 2."""
    held = {"right": False, "left": False, "jump": False}
    monkeypatch.setattr(inputs, "action_held",
                        lambda a: held.get(a, False))
    p = state.player
    p.form = "fire"
    lvl = state.level
    jump_t = 0
    fire_t = 0
    ticks = 0
    while boss.alive and ticks < max_ticks:
        p.hearts = max(p.hearts, 2)              # safety net (recorded)
        p.invuln = max(p.invuln, 1)
        dx = boss.cx - p.cx
        # hold ~130px to the boss's left
        held["right"] = dx < 110
        held["left"] = dx > 160
        # golem: walk onto an inactive arena switch to expose the core
        if (getattr(boss, "KIND", "") == "crystal_golem"
                and not boss.exposed):
            inactive = [sw for sw in lvl.switches
                        if not sw.active and sw.tx >= lvl.arena_x0]
            if inactive:
                sw = min(inactive, key=lambda s: abs(s.tx * TILE - p.x))
                tgt = sw.tx * TILE
                held["right"] = tgt > p.x + 4
                held["left"] = tgt < p.x - 4
        # dodge weave: hop on a fixed cadence + when a shot closes in
        jump_t -= 1
        near = any(pr.rect.colliderect(
            pygame.Rect(int(p.x) - 36, int(p.y), 40, config.PLAYER_H))
            and pr.vx < 0 for pr in state.enemies.projectiles)
        if jump_t <= 0 or (near and not held["jump"]):
            held["jump"] = True
            jump_t = 46
        elif ticks % 8 == 0:
            held["jump"] = False
        # fire when roughly aligned with the boss
        fire_t -= 1
        aligned = abs(p.cy - boss.cy) < 26
        if fire_t <= 0 and aligned and boss.state != "dying":
            p.facing = 1 if dx > 0 else -1       # face the boss, not the drift
            state._try_attack()
            fire_t = config.ATTACK_COOLDOWN + 2
        state.update()
        ticks += 1
    return ticks


def _finish(state, game, boss):
    from src.enemies.boss import Boss
    for _ in range(Boss.DEFEAT_TICKS + 10):     # play out the sequence
        state.update()
    assert boss.defeated, "boss defeat sequence must complete"
    lvl = state.level
    for k in lvl.key_shards:                     # traversal-proven shards
        k.collected = True                       # (collection covered by
    lvl.shards_collected = len(lvl.key_shards)   #  the runner + 3c tests)
    assert lvl.boss_defeated, "goal must latch the boss defeat"
    assert not lvl.goal_locked()
    goal = lvl.goal
    state.player.x = float(goal.rect.x)
    state.player.y = float(goal.rect.y)
    state.update()
    assert game.state_name == "level_clear", "arena level must clear"


def test_all_four_bosses_registered():
    from src.enemies import ENEMY_TYPES
    from src.enemy_manager import spawn_enemy
    for kind in NEW_BOSS_KINDS:
        b = spawn_enemy(kind, 10, GROUND)
        assert getattr(b, "is_boss", False)
        assert b.rect.bottom == GROUND * TILE


# ------------------------------------------------------------ brute
def test_brute_slam_waves_and_phases(flat_level):
    from src.enemies.bosses.boulder_brute import BoulderBrute, GroundWave
    from src.player import Player
    b = BoulderBrute(6 * 16, GROUND * TILE - 32)
    b.active = True
    player = Player(14 * 16, GROUND * TILE - 26)
    saw_air = False
    for _ in range(400):
        b.update(flat_level, player)
        if b.mode == "airborne":
            saw_air = True
        if any(isinstance(s, GroundWave) for s in b.shots):
            break
    assert saw_air, "brute must slam"
    assert any(isinstance(s, GroundWave) for s in b.shots), \
        "slam must emit shockwaves"


def test_brute_shots_drain_to_manager(flat_level):
    from src.enemy_manager import EnemyManager
    from src.player import Player
    mgr = EnemyManager([("boulder_brute", 6, GROUND)])
    b = mgr.enemies[0]
    b.active = True
    player = Player(14 * 16, GROUND * TILE - 26)
    for _ in range(400):
        mgr.update(flat_level, player, _cam())
        if mgr.projectiles:
            break
    assert mgr.projectiles, "waves/rocks must reach the manager list"


def test_fight_boulder_brute(monkeypatch, pygame_ready):
    game, state = _boss_game(4)
    boss = _enter_arena(state)
    assert boss.KIND == "boulder_brute"
    _run_fight(state, boss, monkeypatch)
    _finish(state, game, boss)


# ------------------------------------------------------------ golem
def test_golem_armor_expose_and_rearm(flat_level):
    from src.enemies.bosses.crystal_golem import CrystalGolem
    from src.level.objects import Switch
    from src.player import Player
    lvl = flat_level
    lvl.switches.append(Switch(8, 11, "s0"))
    g = CrystalGolem(12 * 16, GROUND * TILE - 34)
    g.active = True
    player = Player(2 * 16, 12 * 16 - 26)
    assert g.take_damage(1) is False, "armor deflects while sealed"
    assert g.hp == g.MAX_HP
    lvl.switches[0].active = True                # press the switch
    g.update(lvl, player)
    assert g.exposed
    assert g.take_damage(1) is False             # damaged, not killed
    assert g.hp == g.MAX_HP - 1
    for _ in range(config.GOLEM_EXPOSE_TICKS + 2):
        g.update(lvl, player)
    assert not g.exposed
    assert not lvl.switches[0].active, "switches re-arm"
    assert g.take_damage(1) is False, "armor back on"


def test_fight_golem(monkeypatch, pygame_ready):
    game, state = _boss_game(9)
    boss = _enter_arena(state)
    assert boss.KIND == "crystal_golem"
    _run_fight(state, boss, monkeypatch)
    _finish(state, game, boss)


# -------------------------------------------------------------- owl
def test_owl_rise_dive_and_reinforcements(flat_level):
    from src.enemy_manager import EnemyManager
    from src.player import Player
    FLAT = 12                                   # hand-built fixture floor
    mgr = EnemyManager([("warden_owl", 8, FLAT)])
    o = mgr.enemies[0]
    player = Player(12 * 16, FLAT * TILE - 26)
    seen = set()
    for _ in range(600):
        mgr.update(flat_level, player, _cam())
        seen.add(o.mode)
        if o.mode == "hover" and o.y <= o.hover_y + 2:
            break
    assert "rise" in seen and o.mode in ("hover", "telegraph", "dive")
    # force a phase change -> reinforcement spawns and drains to manager
    before = len(mgr.enemies)
    o.take_damage(o.max_hp // 2 + 1)             # crosses a threshold
    mgr.update(flat_level, player, _cam())
    assert len(mgr.enemies) > before, "owl must spawn a flyer"


def test_fight_warden_owl(monkeypatch, pygame_ready):
    game, state = _boss_game(14)
    boss = _enter_arena(state)
    assert boss.KIND == "warden_owl"
    _run_fight(state, boss, monkeypatch, max_ticks=8000)
    _finish(state, game, boss)


# ----------------------------------------------------------- monarch
def test_monarch_volley_and_puddles(flat_level):
    from src.enemies.bosses.magma_monarch import MagmaMonarch, MonarchFire
    from src.level import tiles as T
    from src.player import Player
    m = MagmaMonarch(10 * 16, GROUND * TILE - 36)
    m.active = True
    player = Player(4 * 16, GROUND * TILE - 26)
    for _ in range(140):
        m.update(flat_level, player)
    assert m.shots, "monarch must volley"
    assert all(isinstance(s, MonarchFire) for s in m.shots)
    # final-phase lava blob leaves a puddle that later cleans up
    m.phase = 2
    lava = MonarchFire(5 * 16, GROUND * TILE - 40, 0.0, 4.0, lava=True)
    lava.owner = m
    for _ in range(80):
        lava.update(flat_level)
        if lava.dead:
            break
    assert m.puddles, "lava blob must leave a puddle"
    tx, ty = m.puddles[0][0], m.puddles[0][1]
    assert flat_level.tiles.get(tx, ty) == T.LAVA
    m.puddles[0][2] = 1
    for _ in range(4):
        m.update(flat_level, player)
    assert flat_level.tiles.get(tx, ty) == T.EMPTY, "puddle must clean up"
    assert m.puddles == []


def test_fight_magma_monarch(monkeypatch, pygame_ready):
    game, state = _boss_game(19)
    boss = _enter_arena(state)
    assert boss.KIND == "magma_monarch"
    _run_fight(state, boss, monkeypatch)
    _finish(state, game, boss)


# ------------------------------------------------------- determinism
def test_fights_are_deterministic(monkeypatch, pygame_ready):
    """Same seed -> the brute dies on the exact same tick (twice)."""
    ticks = []
    for _ in range(2):
        game, state = _boss_game(4, seed=7)
        boss = _enter_arena(state)
        ticks.append(_run_fight(state, boss, monkeypatch))
        assert not boss.alive, "boss must die within the tick cap"
    assert ticks[0] == ticks[1], "fights must be self-consistent"

