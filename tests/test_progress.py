"""Progress save/load (Phase 4c): schema v1, tolerant loads, atomic writes,
unlock rules, Continue wiring. D3: never touch the real save/ — the
autouse `_isolated_save` fixture in conftest.py points SAVE_PATH at tmp."""

import json
import os
import random

import pygame

from src import config
from src import progress


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


# ------------------------------------------------------------ load / save
def test_roundtrip_save_load():
    p = progress.default_progress()
    progress.record_clear(p, 2, 1500)
    p["settings"]["muted"] = True
    assert progress.save(p)
    loaded = progress.load()
    assert loaded["schema_version"] == config.SCHEMA_VERSION
    assert loaded["unlocked_level_index"] == 3
    assert loaded["best_scores"] == {"2": 1500}
    assert loaded["settings"]["muted"] is True


def test_write_leaves_valid_json_and_no_tmp():
    assert progress.save(progress.default_progress())
    with open(config.SAVE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["schema_version"] == config.SCHEMA_VERSION
    assert not os.path.exists(config.SAVE_PATH + ".tmp")


def test_missing_file_yields_defaults():
    assert progress.load(os.path.join(
        str(os.path.dirname(config.SAVE_PATH)), "nope", "gone.json")) \
        == progress.default_progress()


def test_corrupt_files_never_raise():
    for junk in ("{not json", "[]", '"hi"', "null", "{}",
                 '{"schema_version": "x"}', '{"schema_version": -3}'):
        with open(config.SAVE_PATH, "w", encoding="utf-8") as fh:
            fh.write(junk)
        assert progress.load() == progress.default_progress(), junk


def test_newer_schema_yields_defaults():
    with open(config.SAVE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"schema_version": config.SCHEMA_VERSION + 5,
                   "unlocked_level_index": 9}, fh)
    assert progress.load() == progress.default_progress()


def test_migration_hook_runs(monkeypatch):
    """Older schema -> MIGRATIONS applied in order during load."""
    def to_v2(data):
        data = dict(data)
        data["migrated"] = True
        return data

    monkeypatch.setitem(progress.MIGRATIONS, 1, to_v2)
    monkeypatch.setattr(config, "SCHEMA_VERSION", 2)
    with open(config.SAVE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"schema_version": 1, "unlocked_level_index": 4}, fh)
    loaded = progress.load()
    assert loaded["schema_version"] == 2
    assert loaded["unlocked_level_index"] == 4


def test_save_io_failure_swallowed(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a dir")
    assert progress.save(progress.default_progress(),
                         str(blocker / "sub" / "p.json")) is False


# ---------------------------------------------------------- unlock rules
def test_record_clear_monotone_and_best_max():
    p = progress.default_progress()
    progress.record_clear(p, 2, 1500)
    assert p["unlocked_level_index"] == 3
    progress.record_clear(p, 0, 9999)               # older level, big score
    assert p["unlocked_level_index"] == 3, "unlock must be monotone"
    assert p["best_scores"]["0"] == 9999
    progress.record_clear(p, 2, 10)                 # worse score on level 2
    assert p["best_scores"]["2"] == 1500, "best score keeps the max"


def test_is_unlocked_bounds():
    p = progress.default_progress()
    p["unlocked_level_index"] = 3
    assert progress.is_unlocked(p, 0)
    assert progress.is_unlocked(p, 3)
    assert not progress.is_unlocked(p, 4)
    assert not progress.is_unlocked(p, -1)


# ----------------------------------------------------------- Game wiring
def test_game_loads_progress_defaults(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    assert game.progress == progress.default_progress()


def test_level_clear_persists_unlock(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.new_run(seed=7)
    game.switch_state("level_clear")
    game.state.phase = "done"
    _press(game.state, pygame.K_RETURN)
    assert game.run.level_index == 1
    saved = progress.load()
    assert saved["unlocked_level_index"] == 1
    assert saved["best_scores"] == {"0": game.run.score}


def test_continue_starts_at_unlocked_level(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.progress["unlocked_level_index"] = 3
    _press(game.state, pygame.K_c)                  # title state
    assert game.state_name == "playing"
    assert game.run.level_index == 3


def test_continue_locked_when_nothing_unlocked(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    _press(game.state, pygame.K_c)
    assert game.state_name == "title"


# ----------------------------------------------------------- determinism
def test_progress_io_consumes_no_rng():
    random.seed(1234)
    marker = random.getstate()
    p = progress.default_progress()
    progress.record_clear(p, 1, 100)
    progress.save(p)
    progress.load()
    assert random.getstate() == marker, \
        "progress I/O must not consume the gameplay RNG"
