"""Integration smoke: real game loop, all states, headless-safe."""

import pygame

from src.config import LEVELS_PER_RUN
from src.game import Game


def press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))


def run_updates(game, n, draw_every=0):
    for i in range(n):
        game.state.update()
        if draw_every and i % draw_every == 0:
            game.state.draw(game.surface)
    game.state.draw(game.surface)


def _start_playing(game):
    press(game.state, pygame.K_RETURN)
    assert game.state_name == "playing"
    return game.state


def test_title_then_play_then_pause_resume(pygame_ready):
    game = Game(seed=42, max_frames=None)
    assert game.state_name == "title"
    run_updates(game, 60, draw_every=20)
    state = _start_playing(game)
    run_updates(game, 300, draw_every=60)
    assert game.state_name == "playing"

    game.pause()
    assert game.state_name == "paused"
    frozen = game.state.underlying
    x_before = frozen.player.x
    run_updates(game, 40)
    assert game.state_name == "paused"
    assert frozen.player.x == x_before, "pause did not freeze the world"
    game.state.draw(game.surface)
    game.resume()
    assert game.state_name == "playing"
    run_updates(game, 60, draw_every=30)


def test_goal_touch_clears_and_advances(pygame_ready):
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    run_updates(game, 90, draw_every=30)
    goal = state.level.goal
    state.player.x = float(goal.rect.x)
    state.player.y = float(goal.rect.y)
    state.update()
    assert game.state_name == "level_clear"
    clear = game.state
    for _ in range(6000):
        clear.update()
        if clear.phase == "done":
            break
    assert clear.phase == "done"
    clear.draw(game.surface)
    press(clear, pygame.K_RETURN)
    assert game.state_name == "playing"
    assert game.run.level_index == 1
    run_updates(game, 120, draw_every=60)


def test_full_run_reaches_victory(pygame_ready):
    game = Game(seed=42, max_frames=None)
    _start_playing(game)
    for level in range(LEVELS_PER_RUN):
        assert game.state_name == "playing"
        run_updates(game, 60, draw_every=0)
        state = game.state
        goal = state.level.goal
        state.player.x = float(goal.rect.x)
        state.player.y = float(goal.rect.y)
        state.update()
        assert game.state_name == "level_clear", f"level {level} not cleared"
        game.state.phase = "done"                 # skip tally animation
        game.state.draw(game.surface)
        press(game.state, pygame.K_RETURN)
    assert game.state_name == "victory"
    game.state.draw(game.surface)
    press(game.state, pygame.K_RETURN)
    assert game.state_name == "title"


def test_death_leads_to_game_over_and_title(pygame_ready):
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    game.run.lives = 0
    state.player.die("pit")
    for _ in range(120):
        game.state.update()
        if game.state_name != "playing":
            break
    assert game.state_name == "game_over"
    game.state.draw(game.surface)
    press(game.state, pygame.K_RETURN)
    assert game.state_name == "title"
    game.state.draw(game.surface)


def test_restart_key_rebuilds_level(pygame_ready):
    game = Game(seed=42, max_frames=None)
    state = _start_playing(game)
    old_id = id(state)
    press(game.state, pygame.K_r)
    assert game.state_name == "playing"
    assert id(game.state) != old_id
    run_updates(game, 60, draw_every=30)
