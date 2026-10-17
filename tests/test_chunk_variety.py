"""Slice 3 pacing/variety tests.

These tests pin the anti-fatigue guarantees introduced with chunk tracing:

* generated levels record an informational `chunk_trace`;
* the trace is deterministic but not part of level hashes or validation;
* no chunk is used more than three times in one level;
* long levels contain enough distinct chunk types;
* long levels contain a breather;
* `diff = 0.0` levels remain free of showcase mechanics.
"""

import hashlib
from collections import Counter

import pytest

from src import config
from src.level import generator as gen
from src.level.validator import validate

LONG_SCREEN_COUNT = 10

LOW_DIFF_TRACE_NAMES = {
    "chunk_flat",
    "chunk_gap",
    "chunk_steps_up",
    "chunk_steps_down",
    "chunk_rolling_hills",
}

LONG_LEVEL_CASES = [
    (0, 0.0),
    (5, 0.25),
    (10, 0.5),
    (15, 0.75),
    (19, 1.0),
]

VARIETY_CASES = [
    (5, 0.35),
    (10, 0.5),
    (15, 0.75),
    (19, 1.0),
]


def _level_hash(lvl):
    """Local copy of the generator hash used by determinism tests."""
    h = hashlib.md5()
    h.update(bytes(lvl.tiles.data))
    for c in lvl.coins:
        h.update(f"c{c.tx},{c.ty};".encode())
    for e in lvl.enemy_spawns:
        h.update(repr(e).encode())
    if lvl.goal:
        h.update(f"g{lvl.goal.tx},{lvl.goal.feet_row};".encode())
    for m in lvl.movers:
        h.update(f"m{m.rect.x},{m.rect.y},{m.length},{m.axis};".encode())
    for p in lvl.pipes:
        h.update(f"p{p.tx},{p.top_row},{p.warp_id};".encode())
    for cp in lvl.checkpoints:
        h.update(f"k{cp.tx},{cp.feet_row};".encode())
    return h.hexdigest()


def _trace_counts(lvl):
    return Counter(lvl.chunk_trace)


def _assert_trace_bounds(lvl):
    counts = _trace_counts(lvl)
    assert all(count <= gen.MAX_CHUNK_USES for count in counts.values()), (
        f"chunk overuse in {lvl.level_index}: {dict(counts)}"
    )


def _generate_long_level(monkeypatch, seed, diff, level_index):
    """Generate a deterministic 10-screen level without changing config.py."""
    monkeypatch.setattr(
        config,
        "level_length_screens",
        lambda zone, zone_level: LONG_SCREEN_COUNT,
    )
    return gen.generate_level(seed, diff, level_index)


def test_chunk_trace_is_recorded_and_deterministic():
    """Same inputs produce the same informational trace."""
    for idx, diff in LONG_LEVEL_CASES:
        seed = 12345 + idx
        a = gen.generate_level(seed, diff, idx)
        b = gen.generate_level(seed, diff, idx)
        assert a.chunk_trace == b.chunk_trace
        assert a.chunk_trace, "generator did not record any chunks"


def test_chunk_trace_is_not_hashed_or_validator_visible():
    """`chunk_trace` is telemetry only and cannot affect proof/hash."""
    lvl = gen.generate_level(12345, 0.5, 2)
    ok_before, reason_before = validate(lvl)
    hash_before = _level_hash(lvl)

    lvl.chunk_trace = ["chunk_not_real", "chunk_fake"]

    assert _level_hash(lvl) == hash_before
    ok_after, reason_after = validate(lvl)
    assert ok_before == ok_after
    assert reason_before == reason_after


@pytest.mark.parametrize("idx", [0, 4, 9, 14, 19])
def test_no_chunk_used_more_than_three_times_in_normal_levels(idx):
    """Current generated levels obey the anti-fatigue hard cap."""
    screens = config.level_length_screens(
        config.zone_of(idx), config.zone_level_of(idx))
    for seed in range(4):
        lvl = gen.generate_level(seed * 37 + 5, config.difficulty_for(idx), idx)
        ok, reason = validate(lvl)
        assert ok, f"idx={idx} seed={seed}: {reason}"
        _assert_trace_bounds(lvl)

        if screens >= 10:
            distinct = set(lvl.chunk_trace)
            assert len(distinct) >= 8, (
                f"idx={idx} seed={seed}: only {len(distinct)} chunk types "
                f"used in a {screens}-screen level: {sorted(distinct)}"
            )
            assert "chunk_flat" in lvl.chunk_trace, (
                f"idx={idx} seed={seed}: no flat breather in a "
                f"{screens}-screen level"
            )


@pytest.mark.parametrize("idx,diff", VARIETY_CASES)
def test_variety_floor_in_10_screen_levels(monkeypatch, idx, diff):
    """Long mid/high levels must not be built from a tiny repeated vocabulary."""
    for seed in range(3):
        lvl = _generate_long_level(
            monkeypatch, seed * 104729 + 11, diff, idx)
        ok, reason = validate(lvl)
        assert ok, f"idx={idx} diff={diff} seed={seed}: {reason}"
        assert lvl.tiles.w == (
            LONG_SCREEN_COUNT * config.TILES_PER_SCREEN + 18)

        distinct = set(lvl.chunk_trace)
        assert len(distinct) >= 8, (
            f"idx={idx} diff={diff} seed={seed}: only {len(distinct)} "
            f"chunk types used: {sorted(distinct)}"
        )
        _assert_trace_bounds(lvl)


@pytest.mark.parametrize("idx,diff", LONG_LEVEL_CASES)
def test_breather_appears_in_10_screen_levels(monkeypatch, idx, diff):
    """Long levels must contain a literal flat breather."""
    for seed in range(3):
        lvl = _generate_long_level(
            monkeypatch, seed * 31337 + 17, diff, idx)
        ok, reason = validate(lvl)
        assert ok, f"idx={idx} diff={diff} seed={seed}: {reason}"
        assert "chunk_flat" in lvl.chunk_trace, (
            f"idx={idx} diff={diff} seed={seed}: no flat breather in trace"
        )
        _assert_trace_bounds(lvl)


@pytest.mark.parametrize("seed", range(15))
def test_diff_zero_levels_remain_showcase_free(seed):
    """Slice 3 selection changes must not leak showcase content into diff 0."""
    idx = seed % config.LEVELS_PER_ZONE
    lvl = gen.generate_level(seed * 7919 + 13, 0.0, idx)
    ok, reason = validate(lvl)
    assert ok, f"seed={seed} idx={idx}: {reason}"

    assert set(lvl.chunk_trace) <= LOW_DIFF_TRACE_NAMES, (
        f"non-teaching chunk leaked into diff=0.0 idx={idx}: "
        f"{sorted(set(lvl.chunk_trace))}"
    )
    assert lvl.doors == [], f"doors leaked into diff=0.0 seed={seed}"
    assert lvl.switches == [], f"switches leaked into diff=0.0 seed={seed}"
    assert lvl.plates == [], f"plates leaked into diff=0.0 seed={seed}"
    assert not any(t == 11 for t in lvl.tiles.data), (
        f"lava leaked into diff=0.0 seed={seed}")
    assert lvl.dynamic_hazards == [], (
        f"moving hazards leaked into diff=0.0 seed={seed}")
    assert lvl.key_shards == [] and lvl.required == 0, (
        f"objective shards leaked into diff=0.0 seed={seed}")

