"""Slice 8 regression tests for flat-tail prevention.

These tests pin the fix for the long-level flat-run bug:

* breather exhaustion must not stop chunk stitching;
* if the normal chunk pool is exhausted, the generator must use a last-resort
  safe filler instead of a huge flat runway;
* representative long levels must not end with an oversized plain-ground tail.
"""

import random

import pytest

from src import config
from src.level import generator as gen
from src.level import tiles as T
from src.level.validator import validate


MAX_TAIL_TILES = 48
MAX_FILLED_RUNWAY_TILES = 32

REPRESENTATIVE_LONG_LEVELS = [4, 9, 14, 19]

STRUCTURAL_TILE_IDS = (
    T.SOLID,
    T.PIPE_TL,
    T.PIPE_TR,
    T.PIPE_BL,
    T.PIPE_BR,
    T.DOOR,
)


def _is_plain_ground_column(lvl, tx):
    """Return True for a plain base-height ground column.

    Decorative question/brick blocks are intentionally ignored because the bug
    is about flat *terrain* runways, not incidental coin-block decor.
    """
    tiles = lvl.tiles
    ground = config.GROUND_ROW
    if tx < 0 or tx >= tiles.w:
        return False

    # A plain runway has a walkable surface at the base ground row.
    if not tiles.solid_at(tx, ground):
        return False

    # Spikes/lava on or just above the surface are gameplay features.
    for ty in range(ground - 1, ground + 1):
        if tiles.hazard_at(tx, ty):
            return False

    # Terrain, pipes, and door walls above the surface break the flat runway.
    for ty in range(0, ground):
        if tiles.get(tx, ty) in STRUCTURAL_TILE_IDS:
            return False

    return True


def _tail_flat_length(lvl):
    """Length of the plain-ground run immediately before the goal or arena."""
    if lvl.has_arena:
        stop = lvl.arena_x0 - 1
    else:
        stop = lvl.goal.tx if lvl.goal else lvl.tiles.w - 6

    tx = stop
    while tx >= 0 and _is_plain_ground_column(lvl, tx):
        tx -= 1
    return max(0, stop - tx)


def _max_flat_run(lvl):
    """Longest plain-ground run anywhere in the level."""
    best = 0
    run = 0
    for tx in range(lvl.tiles.w):
        if _is_plain_ground_column(lvl, tx):
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def test_breather_exhaustion_falls_back_to_normal_chunks():
    """A capped breather pool must not make the generator give up."""
    used = {fn: gen.MAX_CHUNK_USES for fn in gen.BREATHER_FALLBACKS}

    assert gen._choose_breather(
        random.Random(1), 0.5, None, 100, used) is None

    fn = gen._choose_chunk(random.Random(1), 0.5, None, 100, used)
    assert fn is not None, "normal chunk selection stopped after breather cap"
    assert fn not in gen.BREATHER_CHUNKS


def test_generator_does_not_stop_when_breather_choice_is_none(monkeypatch):
    """Forced breather exhaustion must continue stitching and validate."""
    monkeypatch.setattr(gen, "_choose_breather", lambda *args, **kwargs: None)

    idx = 10
    lvl = gen.generate_level(12345, config.difficulty_for(idx), idx)
    ok, reason = validate(lvl)
    assert ok, reason

    assert len(lvl.chunk_trace) > 10, (
        "generator stopped stitching too early after breather exhaustion"
    )
    tail = _tail_flat_length(lvl)
    assert tail <= MAX_TAIL_TILES, f"oversized flat tail: {tail} tiles"


def test_last_resort_filler_avoids_flat_runway(monkeypatch):
    """Even with no chunk available, the tail must not become a flat runway."""
    monkeypatch.setattr(gen, "_choose_breather", lambda *args, **kwargs: None)
    monkeypatch.setattr(gen, "_choose_chunk", lambda *args, **kwargs: None)

    idx = 10
    lvl = gen.generate_level(1, config.difficulty_for(idx), idx)
    ok, reason = validate(lvl)
    assert ok, reason

    runway = _max_flat_run(lvl)
    assert runway <= MAX_FILLED_RUNWAY_TILES, (
        f"last-resort filler left a {runway}-tile flat runway"
    )


@pytest.mark.parametrize("idx", REPRESENTATIVE_LONG_LEVELS)
def test_representative_long_levels_do_not_end_in_flat_tails(idx):
    """The bug seeds/levels must no longer end with huge flat filler."""
    diff = config.difficulty_for(idx)
    for seed in range(4):
        lvl = gen.generate_level(seed * 37 + 5, diff, idx)
        ok, reason = validate(lvl)
        assert ok, f"idx={idx} seed={seed}: {reason}"

        tail = _tail_flat_length(lvl)
        assert tail <= MAX_TAIL_TILES, (
            f"idx={idx} seed={seed}: oversized flat tail before "
            f"goal/arena: {tail} tiles"
        )
