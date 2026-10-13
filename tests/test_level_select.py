"""Level select (Phase 4d): navigation, locking, deterministic seed,
boss markers, best scores, Esc/title flow. Headless-safe via conftest."""

import random

import pygame


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


def _game(seed=10):
    from src.game import Game
    return Game(seed=seed, max_frames=None)


def test_title_l_opens_level_select(pygame_ready):
    game = _game()
    _press(game.state, pygame.K_l)
    assert game.state_name == "level_select"


def test_navigation_clamps_at_edges(pygame_ready):
    game = _game()
    game.progress["unlocked_level_index"] = 19
    game.switch_state("level_select")
    st = game.state
    assert st.cursor == 19, "cursor should start at highest unlocked"
    _press(st, pygame.K_RIGHT)
    _press(st, pygame.K_DOWN)
    assert st.cursor == 19, "right/down must clamp at the grid edge"
    _press(st, pygame.K_UP)
    assert st.cursor == 14
    _press(st, pygame.K_LEFT)
    assert st.cursor == 13
    _press(st, pygame.K_LEFT)
    _press(st, pygame.K_LEFT)
    _press(st, pygame.K_LEFT)
    assert st.cursor == 10, "left must clamp at column 0"


def test_locked_node_refuses_to_start(pygame_ready):
    game = _game()
    game.switch_state("level_select")           # unlocked_level_index == 0
    game.state.cursor = 5
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "level_select"


def test_enter_unlocked_node_starts_level(pygame_ready):
    game = _game(seed=10)
    game.progress["unlocked_level_index"] = 7
    game.switch_state("level_select")
    game.state.cursor = 5
    expected_seed = (10 + 104729 * 6) % 100000   # mirrors the state's math
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "playing"
    assert game.run.level_index == 5
    assert game.seed == expected_seed


def test_esc_returns_to_title(pygame_ready):
    game = _game()
    game.switch_state("level_select")
    _press(game.state, pygame.K_ESCAPE)
    assert game.state_name == "title"


def test_boss_marker_on_zone_finals(pygame_ready):
    game = _game()
    game.switch_state("level_select")
    st = game.state
    for idx in (4, 9, 14, 19):
        assert st.is_boss(idx)
    for idx in (0, 3, 5, 18):
        assert not st.is_boss(idx)


def test_best_score_lookup(pygame_ready):
    game = _game()
    game.progress["best_scores"]["5"] = 1234
    game.switch_state("level_select")
    assert game.state.best_score(5) == 1234
    assert game.state.best_score(6) == 0


def test_draw_headless(pygame_ready):
    game = _game()
    game.progress["unlocked_level_index"] = 9
    game.switch_state("level_select")
    game.state.draw(game.surface)


def test_seed_derivation_consumes_no_rng(pygame_ready):
    random.seed(99)
    marker = random.getstate()
    game = _game(seed=10)
    game.progress["unlocked_level_index"] = 3
    game.switch_state("level_select")
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "playing"
    assert random.getstate() == marker, \
        "level-select seed derivation must be pure int math"
