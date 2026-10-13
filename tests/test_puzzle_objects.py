"""Switch/door mechanics (Phase 3a-1): conditional-edge validation (§8.2).

Hand-built levels only — the generator gets no door content until 3a-2
(R1: validator rules land BEFORE content that uses them).
"""

from src import config
from src.level import tiles as T
from src.level.level import Level
from src.level.objects import (FloorSpiker, GoalGate, KeyShard,
                               LatchedDoor, PressurePlate, Switch,
                               TimedDoor)
from src.level.validator import validate

GROUND_ROW = 12
LEVEL_W = 40


def _flat(w=LEVEL_W):
    lvl = Level(w, 18)
    for tx in range(w):
        for ty in range(GROUND_ROW, 18):
            lvl.tiles.set(tx, ty, T.SOLID)
    lvl.spawn = (32, GROUND_ROW * 16 - 26)
    lvl.respawn = lvl.spawn
    return lvl


def _door_level(switch_cols, door_specs):
    """Flat level with full-height walls at the door columns.

    switch_cols: list of (col, switch_id); door_specs: list of
    (col, door_id, switch_id). Walls rise rows 0..11 so nothing can be
    jumped over; the door slab replaces rows 9..11 of its column.
    """
    lvl = _flat()
    for col, door_id, switch_id in door_specs:
        for ty in range(0, GROUND_ROW):
            lvl.tiles.set(col, ty, T.SOLID)
        for ty in range(9, GROUND_ROW):
            lvl.tiles.set(col, ty, T.DOOR)
        lvl.doors.append(LatchedDoor(col, 9, col, GROUND_ROW - 1,
                                     door_id, switch_id))
    for col, switch_id in switch_cols:
        lvl.switches.append(Switch(col, GROUND_ROW - 1, switch_id))
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    return lvl


# ------------------------------------------------------- validator (core)
def test_switch_before_door_validates():
    lvl = _door_level(switch_cols=[(10, "s1")],
                      door_specs=[(20, "d1", "s1")])
    ok, reason = validate(lvl)
    assert ok, reason


def test_plain_flat_level_still_validates():
    """Control: no switches/doors -> original plain-BFS path unchanged."""
    lvl = _flat()
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    ok, reason = validate(lvl)
    assert ok, reason


def test_switch_behind_own_door_fails():
    """Soundness: a switch past its own door can never be pressed."""
    lvl = _door_level(switch_cols=[(30, "s1")],
                      door_specs=[(20, "d1", "s1")])
    ok, reason = validate(lvl)
    assert not ok, "unsound proof: switch is behind its own door"
    assert "switch-ordered" in reason


def test_door_without_reachable_switch_fails():
    lvl = _flat()
    for ty in range(0, GROUND_ROW):
        lvl.tiles.set(20, ty, T.SOLID)
    for ty in range(9, GROUND_ROW):
        lvl.tiles.set(20, ty, T.DOOR)
    lvl.doors.append(LatchedDoor(20, 9, 20, GROUND_ROW - 1, "d1", "s1"))
    # NO switches at all
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    ok, reason = validate(lvl)
    assert not ok
    assert "unknown switch" in reason or "switch-ordered" in reason


def test_two_doors_sequential_order_validates():
    """d2's switch sits between d1 and d2: order s1 then s2."""
    lvl = _door_level(switch_cols=[(8, "s1"), (22, "s2")],
                      door_specs=[(15, "d1", "s1"), (30, "d2", "s2")])
    ok, reason = validate(lvl)
    assert ok, reason


def test_one_switch_opens_two_doors_validates():
    lvl = _door_level(switch_cols=[(8, "s1")],
                      door_specs=[(15, "d1", "s1"), (25, "d2", "s1")])
    ok, reason = validate(lvl)
    assert ok, reason


# -------------------------------------------------- entity sanity checks
def test_door_referencing_unknown_switch_rejected():
    lvl = _door_level(switch_cols=[], door_specs=[(20, "d1", "ghost")])
    ok, reason = validate(lvl)
    assert not ok and "unknown switch" in reason


def test_duplicate_switch_ids_rejected():
    lvl = _door_level(switch_cols=[(8, "s1"), (12, "s1")],
                      door_specs=[(20, "d1", "s1")])
    ok, reason = validate(lvl)
    assert not ok and "duplicate switch" in reason


def test_door_tile_mismatch_rejected():
    lvl = _door_level(switch_cols=[(10, "s1")],
                      door_specs=[(20, "d1", "s1")])
    lvl.tiles.set(20, 10, T.EMPTY)                 # vandalise the slab
    ok, reason = validate(lvl)
    assert not ok and "tile mismatch" in reason


# ------------------------------------------------- runtime (tiles/physics)
def test_door_tiles_solid_closed_then_passable_open():
    lvl = _door_level(switch_cols=[(10, "s1")],
                      door_specs=[(20, "d1", "s1")])
    assert lvl.tiles.solid_at(20, GROUND_ROW - 1), "closed door must be solid"
    assert lvl.open_doors_for("s1") == 1
    assert lvl.doors[0].open
    assert not lvl.tiles.solid_at(20, GROUND_ROW - 1), "open door must clear"
    assert lvl.open_doors_for("nope") == 0, "unknown switch opens nothing"


def test_closed_door_blocks_player_passage(flat_level):
    """Real physics: the player cannot walk through closed DOOR tiles."""
    from src.player import Input, Player
    lvl = flat_level
    for ty in range(9, GROUND_ROW):
        lvl.tiles.set(10, ty, T.DOOR)
    player = Player(2 * 16, GROUND_ROW * 16 - 26)
    inp = Input()
    for _ in range(30):                            # settle on the ground
        player.update(inp, lvl)
    start_x = player.x
    inp.right = True
    for _ in range(120):
        player.update(inp, lvl)
    assert player.x < 10 * 16, "player walked through a closed door"
    lvl.tiles.set(10, 9, T.EMPTY)                  # open it manually
    lvl.tiles.set(10, 10, T.EMPTY)
    lvl.tiles.set(10, 11, T.EMPTY)
    for _ in range(120):
        player.update(inp, lvl)
    assert player.x > start_x
    assert player.x > 11 * 16, "player could not walk through the open door"


def test_draw_headless(pygame_ready):
    import pygame
    from src.assets import AssetFactory
    surf = pygame.Surface((64, 64))
    lvl = _door_level(switch_cols=[(2, "s1")],
                      door_specs=[(6, "d1", "s1")])

    class _Cam:
        x = y = 0.0
        ix = iy = 0

        def visible(self, rect, margin=32):
            return True

    lvl.draw(surf, _Cam(), AssetFactory(), tick=0)  # doors+switches render


# --------------------------------------------------- wiring (PlayingState)
def test_switch_touch_opens_door_in_playing(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.switch_state("playing")
    state = game.state
    player = state.player
    for _ in range(30):                            # settle on the ground
        state.update()
    tx = player.rect.centerx // 16
    feet_row = player.rect.bottom // 16 - 1
    sw = Switch(tx, feet_row, "w1")
    door = LatchedDoor(tx + 6, 9, tx + 6, 11, "wd1", "w1")
    for c in door.cells():
        state.level.tiles.set(*c, T.DOOR)
    state.level.switches.append(sw)
    state.level.doors.append(door)
    state.update()
    assert sw.active, "switch was not touched by the player"
    assert door.open, "linked door did not open"
    assert not state.level.tiles.solid_at(tx + 6, 11)


# ============================================ Phase 3b-1: plate/timed/lava
def test_lava_is_hazard_but_never_solid():
    lvl = _flat()
    lvl.tiles.set(10, GROUND_ROW, T.LAVA)
    assert not lvl.tiles.solid_at(10, GROUND_ROW), "lava must never be solid"
    assert lvl.tiles.hazard_at(10, GROUND_ROW)
    from src.level.validator import standable
    assert not standable(lvl.tiles, 10, GROUND_ROW - 1), \
        "cells above lava must be unstandable (worst case)"


def test_lava_kills_player_in_playing(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.switch_state("playing")
    state = game.state
    player = state.player
    for _ in range(30):
        state.update()
    assert not player.dead
    tx = (player.rect.centerx) // 16
    state.level.tiles.set(tx, GROUND_ROW, T.LAVA)   # floor becomes lava
    state.update()
    assert state.level.overlaps_lethal(player.rect)
    assert player.dead, "lava must be lethal, not merely hurtful"


def test_plate_press_latches_and_refreshes():
    lvl = _flat()
    latched = LatchedDoor(20, 9, 20, GROUND_ROW - 1, "dl", "p1")
    for c in latched.cells():
        lvl.tiles.set(*c, T.DOOR)
    lvl.doors.append(latched)
    timed = TimedDoor(24, 9, 24, GROUND_ROW - 1, "dt", "p1", duration=5)
    for c in timed.cells():
        lvl.tiles.set(*c, T.DOOR)
    lvl.doors.append(timed)
    assert lvl.press_plate("p1") == 1
    assert latched.open and timed.open and timed.open_until == 5
    for _ in range(5):
        lvl.update()                                # window expires
    assert not timed.open, "timed door must re-seal"
    assert lvl.tiles.solid_at(24, GROUND_ROW - 1)
    assert latched.open, "latched door must stay open"


def test_plate_counts_as_press_in_proof():
    """A latched door opened ONLY by a plate still validates."""
    lvl = _door_level(switch_cols=[], door_specs=[(20, "d1", "p1")])
    lvl.plates.append(PressurePlate(10, GROUND_ROW - 1, "p1"))
    ok, reason = validate(lvl)
    assert ok, reason
    lvl2 = _door_level(switch_cols=[], door_specs=[(20, "d1", "p1")])
    # no plate at all -> unknown reference -> must fail
    ok2, reason2 = validate(lvl2)
    assert not ok2 and "unknown" in reason2


def test_goal_behind_timed_door_fails_validation():
    """D5 as a PROOF PROPERTY: a goal sealed by a timed door is unwinnable
    per the solver (timed doors are worst-case closed forever)."""
    lvl = _flat()
    for ty in range(0, GROUND_ROW):
        lvl.tiles.set(20, ty, T.SOLID)
    timed = TimedDoor(20, 1, 20, GROUND_ROW - 1, "td1", "p1")
    for c in timed.cells():
        lvl.tiles.set(*c, T.DOOR)
    lvl.doors.append(timed)
    lvl.plates.append(PressurePlate(10, GROUND_ROW - 1, "p1"))
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    ok, reason = validate(lvl)
    assert not ok, "unsound: goal passed through a timed door"
    assert "switch-ordered" in reason or "no path" in reason


def test_timed_door_window_closes_after_duration():
    lvl = _flat()
    door = TimedDoor(10, 9, 10, GROUND_ROW - 1, "td", "p9", duration=3)
    for c in door.cells():
        lvl.tiles.set(*c, T.DOOR)
    lvl.doors.append(door)
    lvl.plates.append(PressurePlate(5, GROUND_ROW - 1, "p9"))
    door.open_window(lvl)
    assert not lvl.tiles.solid_at(10, GROUND_ROW - 1)
    for _ in range(3):
        lvl.update()
    assert lvl.tiles.solid_at(10, GROUND_ROW - 1), "window must re-seal"


# ============================================ Phase 3b-2: moving hazards
def _spiker_level(track_cols=4):
    """Flat level with a FloorSpiker patrolling cols 10..(10+track-1)."""
    lvl = _flat()
    span = (track_cols - 1) * 16
    spiker = FloorSpiker(10 * 16, GROUND_ROW * 16 - 16, span, 1.0)
    lvl.dynamic_hazards.append(spiker)
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    return lvl, spiker


def test_dynamic_hazard_band_is_worst_case_unstandable():
    """The whole track band refuses standing/walking even though its
    tiles are EMPTY — and the leap over it still validates."""
    from src.level.validator import collect_standables, dynamic_hazard_cells
    lvl, spiker = _spiker_level()
    band = dynamic_hazard_cells(lvl)
    assert band, "band must not be empty"
    cells = collect_standables(lvl)
    assert not (band & cells), "band cells must be unstandable (worst case)"
    assert not lvl.tiles.solid_at(10, GROUND_ROW - 1), \
        "the overlay must not leak into the tile map"
    ok, reason = validate(lvl)
    assert ok, reason


def test_band_covers_every_animation_phase():
    """Soundness: the static band must contain the slab at ALL times."""
    from src.level.validator import dynamic_hazard_cells
    lvl, spiker = _spiker_level()
    band = dynamic_hazard_cells(lvl)
    for _ in range(240):                          # several full sweeps
        spiker.update()
        r = spiker.hit_rect()
        for tx in range(r.left // 16, (r.right - 1) // 16 + 1):
            for ty in range(r.top // 16, (r.bottom - 1) // 16 + 1):
                assert (tx, ty) in band, \
                    f"animated cell {(tx, ty)} outside the worst-case band"


def test_floor_spiker_ping_pongs_within_track():
    lvl, spiker = _spiker_level()
    flipped = False
    prev_dir = spiker.dir
    for _ in range(400):
        spiker.update()
        assert spiker.min - 0.01 <= spiker.pos <= spiker.max + 0.01
        if spiker.dir != prev_dir:
            flipped = True
            prev_dir = spiker.dir
    assert flipped, "spiker never reversed direction"


def test_dynamic_hazard_hurts_not_kills(pygame_ready):
    """Runtime: contact fires the hazard event; non-lethal -> _hurt."""
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.switch_state("playing")
    state = game.state
    player = state.player
    for _ in range(30):
        state.update()
    assert not player.dead
    player.invuln = 0
    spiker = FloorSpiker(player.rect.x, player.rect.bottom - 16, 48, 0.0)
    state.level.dynamic_hazards.append(spiker)
    assert state.level.overlaps_hazard(player.rect), "contact not detected"
    hearts_before = player.hearts
    state.update()
    assert player.hearts == hearts_before - 1
    assert not player.dead, "floor spiker must hurt, not kill"


def test_breakable_block_bump_coverage():
    """3b bullet coverage: the BASELINE breakable block still works —
    BRICK tiles break on bump from below (Level.bump -> 'break')."""
    lvl = _flat()
    lvl.tiles.set(10, GROUND_ROW - 3, T.BRICK)
    assert lvl.bump(10, GROUND_ROW - 3) == "break"
    assert lvl.tiles.get(10, GROUND_ROW - 3) == T.EMPTY


# ============================================ Phase 3c: objectives
def _shard_level(positions, required):
    lvl = _flat()
    for tx, ty in positions:
        lvl.key_shards.append(KeyShard(tx, ty))
    lvl.required = required
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    return lvl


def test_shard_requirement_validates():
    """3 shards spread over flat ground, required 2 -> proven."""
    lvl = _shard_level([(8, GROUND_ROW - 1), (18, GROUND_ROW - 1),
                        (30, GROUND_ROW - 1)], 2)
    ok, reason = validate(lvl)
    assert ok, reason


def test_required_more_than_reachable_shards_fails():
    """Two shards sealed behind a jump-proof wall; only 1 reachable and
    required is 2 -> the item-flag BFS must refuse (fail-safe)."""
    lvl = _shard_level([(8, GROUND_ROW - 1), (24, GROUND_ROW - 1),
                        (30, GROUND_ROW - 1)], 2)
    for ty in range(0, GROUND_ROW):               # full-height wall at 20
        lvl.tiles.set(20, ty, T.SOLID)
    ok, reason = validate(lvl)
    assert not ok, "unsound: sealed shards counted toward the objective"
    assert "switch-ordered" in reason or "no path" in reason


def test_shard_entity_sanity_checks():
    lvl = _shard_level([(8, GROUND_ROW - 1)], 2)  # required > placed
    lvl.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    ok, reason = validate(lvl)
    assert not ok and "requirement" in reason

    lvl2 = _flat()
    lvl2.tiles.set(8, GROUND_ROW, T.LAVA)         # floor below is lava
    lvl2.key_shards.append(KeyShard(8, GROUND_ROW - 1))
    lvl2.required = 1
    lvl2.goal = GoalGate(LEVEL_W - 4, GROUND_ROW - 1)
    ok2, reason2 = validate(lvl2)
    assert not ok2 and "hazard" in reason2


def test_goal_locked_until_shards_collected(pygame_ready):
    """Runtime: touching the goal early does NOT clear; pickups unlock."""
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.switch_state("playing")
    state = game.state
    run_updates_needed = 30
    for _ in range(run_updates_needed):
        state.update()
    lvl = state.level
    lvl.required = 1
    lvl.key_shards.clear()
    from src.level.objects import KeyShard as KS
    tx = state.player.rect.centerx // 16
    lvl.key_shards.append(KS(tx, state.player.rect.bottom // 16 - 1))
    goal = lvl.goal
    state.player.x = float(goal.rect.x)
    state.player.y = float(goal.rect.y)
    state.update()
    assert game.state_name == "playing", "locked goal must not clear"
    assert lvl.goal_locked()
    # collect the shard, then the goal opens
    shard = lvl.key_shards[0]
    state.player.x = float(shard.rect.x)
    state.player.y = float(shard.rect.y)
    state.update()
    assert shard.collected and not lvl.goal_locked()
    state.player.x = float(goal.rect.x)
    state.player.y = float(goal.rect.y)
    state.update()
    assert game.state_name == "level_clear"


def test_hud_objective_counter_headless(pygame_ready):
    import pygame
    from src.hud import Hud
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    surf.fill((0, 0, 0))
    Hud().draw(surf, 0, 0, 3, 400, "1-1", objective=(2, 3))
    found = any(surf.get_at((x, y))[:3] != (0, 0, 0)
                for x in range(72, 130) for y in range(40, 52))
    assert found, "KEYS counter not drawn"



