"""Menus (Phase 6a): pause menu, options persistence/live-apply, title
menu rework. Legacy key bindings stay live. Headless-safe via conftest."""

import pygame

from src import config
from src import progress


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


def _playing(seed=7):
    from src.game import Game
    game = Game(seed=seed, max_frames=None)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


def _paused(seed=7):
    game, state = _playing(seed)
    game.pause()
    assert game.state_name == "paused"
    return game, state


# ------------------------------------------------------------ pause menu
def test_pause_menu_navigation_and_resume(pygame_ready):
    game, _state = _paused()
    st = game.state
    assert st.sel == 0
    _press(st, pygame.K_DOWN)
    assert st.sel == 1
    _press(st, pygame.K_UP)
    _press(st, pygame.K_RETURN)                  # row 0 = resume
    assert game.state_name == "playing"


def test_pause_menu_restart_level(pygame_ready):
    game, state = _paused()
    old_id = id(state)
    game.state.sel = 1
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "playing"
    assert id(game.state) != old_id, "restart rebuilds the state"


def test_pause_menu_options_round_trip(pygame_ready):
    game, state = _paused()
    game.state.sel = 2
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "options"
    _press(game.state, pygame.K_ESCAPE)           # back to the pause overlay
    assert game.state_name == "paused"
    assert game._paused is state, "frozen playing state survives options"
    _press(game.state, pygame.K_ESCAPE)           # legacy Esc = resume
    assert game.state_name == "playing"


def test_pause_menu_level_select_and_quit(pygame_ready):
    game, _state = _paused()
    game.state.sel = 3
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "level_select"
    game, _state = _paused()
    game.state.sel = 4
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "title"
    game, _state = _paused()
    _press(game.state, pygame.K_q)                # legacy Q shortcut
    assert game.state_name == "title"


# --------------------------------------------------------------- options
def test_options_volume_adjust_clamp_and_persist(pygame_ready):
    game, _state = _playing()
    game.switch_state("options")
    st = game.state
    before = game.progress["settings"]["master_volume"]
    _press(st, pygame.K_RIGHT)                    # +VOLUME_STEP
    after = game.progress["settings"]["master_volume"]
    assert round(after - before, 2) == config.VOLUME_STEP
    assert abs(game.audio.master_volume - after) < 1e-6, "applied live"
    for _ in range(12):                           # clamp at 1.0
        _press(st, pygame.K_RIGHT)
    assert game.progress["settings"]["master_volume"] == 1.0
    for _ in range(25):                           # clamp at 0.0
        _press(st, pygame.K_LEFT)
    assert game.progress["settings"]["master_volume"] == 0.0
    saved = progress.load()
    assert saved["settings"]["master_volume"] == 0.0, "persisted via D3"


def test_options_mute_and_tutorial_toggles(pygame_ready):
    game, _state = _playing()
    game.switch_state("options")
    st = game.state
    muted_before = game.audio.muted
    st.sel = 3                                    # MUTE row
    _press(st, pygame.K_RIGHT)
    assert game.audio.muted != muted_before
    assert progress.load()["settings"]["muted"] == game.audio.muted
    tut_before = game.progress["settings"]["tutorial_enabled"]
    st.sel = 4                                    # TUTORIAL row
    _press(st, pygame.K_RIGHT)
    assert game.progress["settings"]["tutorial_enabled"] != tut_before
    assert progress.load()["settings"]["tutorial_enabled"] \
        != tut_before, "tutorial persisted"


def test_options_nav_and_draw(pygame_ready):
    game, _state = _playing()
    game.switch_state("options")
    st = game.state
    _press(st, pygame.K_DOWN)
    assert st.sel == 1
    for _ in range(10):
        _press(st, pygame.K_DOWN)
    assert st.sel == len(st.ROWS) - 1, "clamp at the last row"
    _press(st, pygame.K_UP)
    assert st.sel == len(st.ROWS) - 2
    st.draw(game.surface)                         # headless


def test_settings_apply_at_game_start(pygame_ready):
    data = progress.default_progress()
    data["settings"]["music_volume"] = 0.25
    progress.save(data)
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    assert abs(game.audio.music_volume - 0.25) < 1e-6


# ----------------------------------------------------------- title menu
def test_title_menu_rows_and_activation(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    st = game.state
    assert st.sel == 0
    _press(st, pygame.K_DOWN)
    assert st.sel == 1                            # continue (locked)
    _press(st, pygame.K_RETURN)
    assert game.state_name == "title", "locked continue is denied"
    _press(st, pygame.K_DOWN)
    _press(st, pygame.K_RETURN)                   # level select row
    assert game.state_name == "level_select"
    game = Game(seed=7, max_frames=None)
    st = game.state
    for _ in range(3):
        _press(st, pygame.K_DOWN)
    _press(st, pygame.K_RETURN)                   # options row
    assert game.state_name == "options"
    _press(game.state, pygame.K_ESCAPE)           # no pause underneath
    assert game.state_name == "title"


def test_title_continue_row_when_unlocked(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    game.progress["unlocked_level_index"] = 5
    st = game.state
    _press(st, pygame.K_DOWN)
    _press(st, pygame.K_RETURN)
    assert game.state_name == "playing"
    assert game.run.level_index == 5


def test_title_legacy_shortcuts_still_work(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    _press(game.state, pygame.K_s)                # seed roll
    game = Game(seed=7, max_frames=None)
    _press(game.state, pygame.K_l)                # level select
    assert game.state_name == "level_select"
    game = Game(seed=7, max_frames=None)
    _press(game.state, pygame.K_RETURN)           # Enter = row 0 = new game
    assert game.state_name == "playing"
    game = Game(seed=7, max_frames=None)
    game.progress["unlocked_level_index"] = 2
    _press(game.state, pygame.K_c)                # C shortcut
    assert game.state_name == "playing" and game.run.level_index == 2


def test_title_draw_headless(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    for _ in range(5):
        game.state.update()
    game.state.draw(game.surface)
