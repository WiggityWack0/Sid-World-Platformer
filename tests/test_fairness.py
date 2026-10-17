"""Slice 5 fairness: length-scaled timers and checkpoint scaling."""

import pygame
import pytest

from src import config


EXPECTED_TIME_BY_INDEX = [
    400, 436, 472, 508, 544,
    400, 436, 472, 508, 544,
    448, 508, 568, 628, 688,
    448, 508, 568, 628, 688,
]


def _screens_for(idx):
    return config.level_length_screens(
        config.zone_of(idx), config.zone_level_of(idx))


def _expected_checkpoint_count(idx):
    return 3 if _screens_for(idx) > 10 else 2


# ---------------------------------------------------------------- timer
def test_time_for_matches_d2_table():
    """The length-scaled timer is a pure, deterministic function of level_index."""
    assert [config.time_for(i) for i in range(config.LEVELS_PER_RUN)] == EXPECTED_TIME_BY_INDEX


def test_time_for_is_monotone_within_each_zone_and_clamped():
    for zone in range(len(config.ZONES)):
        vals = [config.time_for(zone * config.LEVELS_PER_ZONE + zl)
                for zl in range(config.LEVELS_PER_ZONE)]
        assert vals == sorted(vals), vals
        assert all(config.START_TIME <= value <= config.TIME_MAX
                   for value in vals), vals


def test_time_for_clamps_to_configured_maximum(monkeypatch):
    monkeypatch.setattr(
        config,
        "level_length_screens",
        lambda zone, zone_level: 100,
    )
    assert config.time_for(0) == config.TIME_MAX


@pytest.mark.parametrize("idx", [0, 4])
def test_playing_state_uses_length_scaled_timer(pygame_ready, idx):
    """PlayingState no longer hard-codes START_TIME for every level."""
    from src.game import Game

    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.run.level_index = idx
    game.switch_state("playing")

    assert game.state.time_left == config.time_for(idx)


# ---------------------------------------------------------- checkpoints
@pytest.mark.parametrize("idx", [0, 4, 9, 10, 14, 19])
def test_checkpoint_count_scales_with_level_width(idx):
    """Short levels keep two checkpoints; levels longer than 10 screens get three."""
    from src.level.generator import generate_level

    expected = _expected_checkpoint_count(idx)
    for seed in range(2):
        lvl = generate_level(seed * 37 + 5, config.difficulty_for(idx), idx)
        cols = [cp.tx for cp in lvl.checkpoints]

        assert len(cols) == expected, (idx, seed, cols)
        assert cols == sorted(cols), (idx, seed, cols)
        assert all(8 <= c < lvl.goal.tx - 3 for c in cols), (idx, seed, cols)

        if expected == 3:
            w = lvl.tiles.w
            assert cols[0] > w * 0.15, (idx, seed, cols)
            assert cols[1] > w * 0.40, (idx, seed, cols)
            assert cols[2] > w * 0.65, (idx, seed, cols)

        if lvl.has_arena:
            assert all(c < lvl.arena_x0 for c in cols), (idx, seed, cols)


def test_checkpoint_targets_switch_at_ten_screens():
    from src.level.generator import _checkpoint_targets

    short = _checkpoint_targets(268, 262, 10)
    long = _checkpoint_targets(293, 287, 11)

    assert len(short) == 2
    assert len(long) == 3
    assert [int(268 * r) for r in (0.38, 0.70)] == short
    assert [int(293 * r) for r in (0.25, 0.50, 0.75)] == long


def test_hud_draws_scaled_time_without_overflow(pygame_ready):
    """HUD already renders three-digit time values; verify the new 688 cap works."""
    from src.hud import Hud

    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    hud = Hud()
    hud.draw(surf, 0, 0, 3, config.time_for(19), "4-5")
