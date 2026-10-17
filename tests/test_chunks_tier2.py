"""Slice 2 Tier 2 chunk tests.

Each new high-difficulty chunk is checked with the same baseline pattern as
Tier 1:

* isolated construction validates on its own;
* its declared max_w is an honest cursor-advance bound;
* it is selectable at its min_difficulty and can appear in a real generated
  level;
* generated levels containing it are deterministic.

The risky Tier 2 designs also get targeted property tests:
* vertical bridge must create y-axis mover ride edges;
* lava island chain must refuse lava cells and provide a solid island;
* double gate must keep every switch strictly before its own door.
"""

import random

import pytest

from src import config
from src.level import generator as gen
from src.level import tiles as T
from src.level.objects import GoalGate
from src.level.validator import build_graph, collect_standables, validate

TIER2 = [
    (gen.chunk_gap_triple, 0.50, 22),
    (gen.chunk_lava_island_chain, 0.55, 24),
    (gen.chunk_double_gate, 0.45, 22),
    (gen.chunk_vertical_bridge, 0.60, 20),
    (gen.chunk_spiker_double, 0.60, 20),
    (gen.chunk_bomb_battlement, 0.65, 18),
]

_FIRST_CHOICE_CACHE = {}


def _first_choice_seed(chunk, min_diff):
    """Find a seed whose first generated-level chunk choice is `chunk`."""
    key = (chunk, min_diff)
    if key in _FIRST_CHOICE_CACHE:
        return _FIRST_CHOICE_CACHE[key]

    w = (config.level_length_screens(
        config.zone_of(0), config.zone_level_of(0))
         * config.TILES_PER_SCREEN + 18)
    remaining = w - 24 - 8
    for seed in range(10000):
        rng = random.Random(seed)
        if gen._choose_chunk(rng, min_diff, None, remaining) is chunk:
            _FIRST_CHOICE_CACHE[key] = seed
            return seed
    _FIRST_CHOICE_CACHE[key] = None
    return None


def _isolated_chunk(chunk, max_w, seed, diff):
    """Build a small validator-passing harness around one chunk."""
    width = max_w + 40
    b = gen.Builder(width, config.LEVEL_H_TILES, 0)

    b.ground(8)
    b.level.spawn = (2 * config.TILE + 2,
                     config.GROUND_ROW * config.TILE - config.PLAYER_H)
    b.level.respawn = b.level.spawn

    start = b.x
    chunk(b, random.Random(seed), diff)
    advance = b.x - start

    while b.floor < config.GROUND_ROW:
        b.step_down()
        b.ground(2)
    while b.floor > config.GROUND_ROW:
        b.step_up()
        b.ground(2)
    b.ground(max(0, width - b.x))
    b.level.goal = GoalGate(width - 6, config.GROUND_ROW - 1)
    return b.level, advance


def _measure_advance(chunk, max_w, seed, diff):
    """Measure only the chunk's cursor advance, without validating it."""
    width = max_w + 40
    b = gen.Builder(width, config.LEVEL_H_TILES, 0)
    b.ground(8)
    start = b.x
    chunk(b, random.Random(seed), diff)
    return b.x - start


def _level_signature(lvl):
    """Comparable tiles plus object lists for determinism checks."""
    return (
        bytes(lvl.tiles.data),
        [(c.tx, c.ty) for c in lvl.coins],
        [(kind, tx, srow) for kind, tx, srow in lvl.enemy_spawns],
        [(p.tx, p.top_row, p.height, p.warp_id) for p in lvl.pipes],
        [(m.rect.x, m.rect.y, m.length, m.axis, m.min, m.max, m.speed)
         for m in lvl.movers],
        [(d.door_id, d.switch_id, d.x0, d.y0, d.x1, d.y1) for d in lvl.doors],
        [(s.switch_id, s.tx, s.feet_row) for s in lvl.switches],
        [(p.plate_id, p.tx, p.feet_row) for p in lvl.plates],
        [(k.tx, k.ty) for k in lvl.key_shards],
        lvl.required,
    )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_chunks_validate_in_isolation(chunk, min_diff, max_w):
    """Each chunk must be traversable when inserted into a minimal harness."""
    for seed in range(4):
        for diff in (min_diff, 1.0):
            lvl, advance = _isolated_chunk(chunk, max_w, seed, diff)
            assert advance <= max_w, (
                f"{chunk.__name__} seed={seed} diff={diff}: "
                f"advance {advance} exceeds max_w {max_w}"
            )
            ok, reason = validate(lvl)
            assert ok, (
                f"{chunk.__name__} seed={seed} diff={diff}: {reason}"
            )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_chunk_max_width_is_honest(chunk, min_diff, max_w):
    """_choose_chunk budgets on max_w; actual cursor advance must obey it."""
    for seed in range(24):
        for diff in (min_diff, min(1.0, min_diff + 0.2), 1.0):
            advance = _measure_advance(chunk, max_w, seed, diff)
            assert advance <= max_w, (
                f"{chunk.__name__} seed={seed} diff={diff}: "
                f"advance {advance} exceeds max_w {max_w}"
            )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_chunks_are_selectable_at_their_gate(chunk, min_diff, max_w):
    """The chunk appears in the chooser at its declared min_difficulty."""
    seed = _first_choice_seed(chunk, min_diff)
    assert seed is not None, (
        f"{chunk.__name__} never selectable at diff={min_diff}"
    )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_chunks_not_available_below_gate(chunk, min_diff, max_w):
    """Difficulty gates are real: below min_diff the chunk is not offered."""
    if min_diff <= 0.01:
        return
    w = (config.level_length_screens(
        config.zone_of(0), config.zone_level_of(0))
         * config.TILES_PER_SCREEN + 18)
    remaining = w - 24 - 8
    for seed in range(50):
        rng = random.Random(seed)
        chosen = gen._choose_chunk(rng, min_diff - 0.01, None, remaining)
        assert chosen is not chunk, (
            f"{chunk.__name__} leaked below its gate at diff="
            f"{min_diff - 0.01}, seed={seed}"
        )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_chunks_appear_in_generated_levels(chunk, min_diff, max_w):
    """A real generated level can contain the chunk and still validates."""
    seed = _first_choice_seed(chunk, min_diff)
    assert seed is not None, (
        f"{chunk.__name__} never selectable at diff={min_diff}"
    )
    lvl = gen.generate_level(seed, min_diff, 0)
    ok, reason = validate(lvl)
    assert ok, f"{chunk.__name__} generated seed={seed}: {reason}"


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER2)
def test_tier2_generated_levels_are_deterministic(chunk, min_diff, max_w):
    """Same seed/diff/idx twice -> identical tiles and object lists."""
    seed = _first_choice_seed(chunk, min_diff)
    assert seed is not None, (
        f"{chunk.__name__} never selectable at diff={min_diff}"
    )
    a = gen.generate_level(seed, min_diff, 0)
    b = gen.generate_level(seed, min_diff, 0)
    assert _level_signature(a) == _level_signature(b), (
        f"{chunk.__name__} seed={seed} is not self-consistent"
    )



def test_vertical_bridge_has_y_axis_ride_edges():
    """The vertical bridge must exercise the validator's y-axis ride edges."""
    for seed in range(4):
        lvl, _ = _isolated_chunk(gen.chunk_vertical_bridge, 20, seed, 1.0)
        ok, reason = validate(lvl)
        assert ok, f"seed={seed}: {reason}"

        y_movers = [m for m in lvl.movers if m.axis == "y"]
        assert y_movers, "vertical bridge did not create a y-axis mover"

        _, adj = build_graph(lvl)
        for i, mover in enumerate(lvl.movers):
            if mover.axis != "y":
                continue
            left = ("mv", i, "L")
            right = ("mv", i, "R")
            assert left in adj and right in adj
            assert any(isinstance(n[0], int) for n in adj[left]), (
                "y-axis ride edge is not connected to a real standable cell"
            )
            assert any(isinstance(n[0], int) for n in adj[right]), (
                "y-axis ride edge is not connected to a real standable cell"
            )


def test_lava_island_chain_refuses_lava_and_has_solid_island():
    """Lava arcs must not be standable; the island must be a real landing."""
    for seed in range(4):
        lvl, _ = _isolated_chunk(gen.chunk_lava_island_chain, 24, seed, 1.0)
        ok, reason = validate(lvl)
        assert ok, f"seed={seed}: {reason}"

        tiles = lvl.tiles
        stand = collect_standables(lvl)
        lava_cols = sorted({
            tx for tx in range(tiles.w)
            for ty in range(tiles.h)
            if tiles.get(tx, ty) == T.LAVA
        })
        assert len(lava_cols) >= 2, "lava island chain has no lava"

        for tx in lava_cols:
            for ty in range(tiles.h):
                if tiles.get(tx, ty) == T.LAVA:
                    assert (tx, ty - 1) not in stand, (
                        f"cell above lava at {tx},{ty - 1} was standable"
                    )

        found_island = False
        for a, b in zip(lava_cols, lava_cols[1:]):
            if b - a <= 1:
                continue
            for mid in range(a + 1, b):
                for ty in range(1, tiles.h):
                    if (tiles.get(mid, ty) == T.SOLID
                            and (mid, ty - 1) in stand):
                        found_island = True
                        break
                if found_island:
                    break
            if found_island:
                break
        assert found_island, "no solid standable island between lava pools"


def test_double_gate_switches_precede_their_doors():
    """Both switches must sit before their own full-height door walls."""
    for seed in range(4):
        lvl, _ = _isolated_chunk(gen.chunk_double_gate, 22, seed, 1.0)
        ok, reason = validate(lvl)
        assert ok, f"seed={seed}: {reason}"

        assert len(lvl.doors) >= 2, "double gate must contain two doors"
        switches = {s.switch_id: s for s in lvl.switches}
        assert len(switches) >= 2, "double gate must contain two switches"

        for door in lvl.doors:
            assert door.switch_id in switches, "door references unknown switch"
            switch = switches[door.switch_id]
            assert switch.tx < door.x0, (
                f"switch {switch.switch_id} at {switch.tx} is not before "
                f"door {door.door_id} at {door.x0}"
            )
            assert all(switch.tx < cx for cx, _cy in door.cells()), (
                f"switch {switch.switch_id} sits behind its own door cells"
            )


def test_spiker_double_has_two_separate_hazard_bands():
    """The double spiker chunk must create two floor-spiker bands."""
    for seed in range(4):
        lvl, _ = _isolated_chunk(gen.chunk_spiker_double, 20, seed, 1.0)
        ok, reason = validate(lvl)
        assert ok, f"seed={seed}: {reason}"
        assert len(lvl.dynamic_hazards) >= 2, (
            "chunk_spiker_double did not create two hazard bands"
        )


def test_bomb_battlement_has_overhead_and_ground_enemies():
    """The battlement must contain its overhead structure and enemies."""
    for seed in range(4):
        lvl, _ = _isolated_chunk(gen.chunk_bomb_battlement, 18, seed, 1.0)
        ok, reason = validate(lvl)
        assert ok, f"seed={seed}: {reason}"
        assert any(t in (T.BRICK, T.QUESTION) for t in lvl.tiles.data), (
            "bomb battlement did not create overhead bricks/questions"
        )
        assert lvl.enemy_spawns, "bomb battlement did not create enemies"
        assert all(kind != "flyer" for kind, _, _ in lvl.enemy_spawns), (
            "bomb battlement placed a flyer on ground"
        )

