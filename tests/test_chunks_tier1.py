"""Slice 1 Tier 1 chunk tests.

Each new low/mid chunk is checked four ways:

* isolated construction validates on its own;
* its declared max_w is an honest cursor-advance bound;
* it is selectable at its min_difficulty and can appear in a real generated
  level;
* generated levels containing it are deterministic.
"""

import random

import pytest

from src import config
from src.level import generator as gen
from src.level.objects import GoalGate
from src.level.validator import validate

TIER1 = [
    (gen.chunk_rolling_hills, 0.00, 14),
    (gen.chunk_twin_gaps, 0.20, 18),
    (gen.chunk_high_ledge, 0.20, 14),
    (gen.chunk_pipe_trio, 0.15, 20),
    (gen.chunk_spike_trench_pair, 0.35, 16),
    (gen.chunk_ambush_steps, 0.30, 18),
]


def _first_choice_seed(chunk, min_diff):
    """Find a seed whose first generated-level chunk choice is `chunk`.

    generate_level() consumes no RNG before its first _choose_chunk() call,
    so this simulated first choice is the same choice the real generator will
    make for the returned seed.
    """
    w = (config.level_length_screens(
        config.zone_of(0), config.zone_level_of(0))
         * config.TILES_PER_SCREEN + 18)
    remaining = w - 24 - 8
    for seed in range(500):
        rng = random.Random(seed)
        if gen._choose_chunk(rng, min_diff, None, remaining) is chunk:
            return seed
    return None


def _isolated_chunk(chunk, max_w, seed, diff):
    """Build a small validator-passing harness around one chunk."""
    width = max_w + 40
    b = gen.Builder(width, config.LEVEL_H_TILES, 0)

    # Safe start area, mirroring generate_level().
    b.ground(8)
    b.level.spawn = (2 * config.TILE + 2,
                     config.GROUND_ROW * config.TILE - config.PLAYER_H)
    b.level.respawn = b.level.spawn

    start = b.x
    chunk(b, random.Random(seed), diff)
    advance = b.x - start

    # Ramp back to the base ground row, then provide a flat goal run-in.
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


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_chunks_validate_in_isolation(chunk, min_diff, max_w):
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


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_chunk_max_width_is_honest(chunk, min_diff, max_w):
    """_choose_chunk budgets on max_w; actual cursor advance must obey it."""
    for seed in range(24):
        for diff in (min_diff, min(1.0, min_diff + 0.2), 1.0):
            advance = _measure_advance(chunk, max_w, seed, diff)
            assert advance <= max_w, (
                f"{chunk.__name__} seed={seed} diff={diff}: "
                f"advance {advance} exceeds max_w {max_w}"
            )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_chunks_are_selectable_at_their_gate(chunk, min_diff, max_w):
    """The chunk appears in the chooser at its declared min_difficulty."""
    seed = _first_choice_seed(chunk, min_diff)
    assert seed is not None, (
        f"{chunk.__name__} never selectable at diff={min_diff}"
    )


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_chunks_not_available_below_gate(chunk, min_diff, max_w):
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


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_chunks_appear_in_generated_levels(chunk, min_diff, max_w):
    """A real generated level can contain the chunk and still validates."""
    seed = _first_choice_seed(chunk, min_diff)
    assert seed is not None, (
        f"{chunk.__name__} never selectable at diff={min_diff}"
    )
    lvl = gen.generate_level(seed, min_diff, 0)
    ok, reason = validate(lvl)
    assert ok, f"{chunk.__name__} generated seed={seed}: {reason}"


@pytest.mark.parametrize("chunk,min_diff,max_w", TIER1)
def test_tier1_generated_levels_are_deterministic(chunk, min_diff, max_w):
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
