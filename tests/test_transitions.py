"""Transitions + end-screen upgrades (Phase 6b): deterministic fade,
deferred switch_state (opt-in), NEW BEST flags, persisted bosses
counter, game-over stats. Headless-safe via conftest."""

import random

import pygame

from src import config
from src import progress
from src.transition import Transition


def _press(state, key):
    state.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


def _game(seed=7, transitions=False, **kw):
    from src.game import Game
    return Game(seed=seed, max_frames=None, transitions=transitions, **kw)


def _playing(seed=7):
    game = _game(seed)
    game.new_run(seed=seed)
    game.switch_state("playing")
    return game, game.state


# -------------------------------------------------------------- fade math
def test_fade_math_deterministic_and_swaps_once():
    a, b = Transition(ticks=5), Transition(ticks=5)
    a.start(("title", {}))
    b.start(("title", {}))
    results_a, results_b = [], []
    for _ in range(30):
        results_a.append((a.step(), a.alpha()))
        results_b.append((b.step(), b.alpha()))
    assert results_a == results_b, "pure tick math"
    swaps = [r for r, _ in results_a if r == "swap"]
    assert len(swaps) == 1, "exactly one swap per fade"
    assert a.phase is None and not a.active, "fade ends inactive"


def test_fade_draw_headless(pygame_ready):
    tr = Transition(ticks=4)
    surf = pygame.Surface((config.VIEW_W, config.VIEW_H))
    tr.start(("title", {}))
    for _ in range(8):
        tr.step()
        tr.draw(surf)                            # headless ok


def test_fade_consumes_no_rng():
    random.seed(5)
    marker = random.getstate()
    tr = Transition(ticks=3)
    tr.start(("title", {}))
    for _ in range(10):
        tr.step()
        tr.draw(pygame.Surface((config.VIEW_W, config.VIEW_H)))
    assert random.getstate() == marker


# -------------------------------------------------------- deferred switch
def test_game_default_has_no_transition(pygame_ready):
    """Recorded: transitions default OFF so synchronous tests keep timing."""
    game = _game()
    assert game.transition is None
    old = game.state_name
    game.switch_state("level_select")
    assert game.state_name == "level_select", "instant when disabled"


def test_deferred_switch_swaps_at_black(pygame_ready):
    game = _game(transitions=True)
    old = game.state
    game.switch_state("level_select")
    assert game.state_name == "title", "switch defers into the fade-out"
    assert game.transition.active
    for _ in range(config.FADE_TICKS - 1):
        game.tick_transition()
    assert game.state_name == "title", "not swapped before black"
    game.tick_transition()                       # the swap tick
    assert game.state_name == "level_select"
    assert game.state is not old
    for _ in range(config.FADE_TICKS):
        game.tick_transition()
    assert not game.transition.active, "fade-in completes"


# ------------------------------------------------------ end-screen flags
def test_level_clear_new_best_flag(pygame_ready):
    game, state = _playing()
    game.progress["best_scores"]["0"] = 10
    game.run.score = 500
    game.switch_state("level_clear")
    assert game.state.new_best is True
    game.run.score = 5
    game.switch_state("level_clear")
    assert game.state.new_best is False
    game.state.draw(game.surface)                # headless


def test_victory_shows_bosses_and_new_best(pygame_ready):
    game = _game()
    game.new_run(seed=7)
    game.progress["play_stats"]["bosses_defeated"] = 3
    game.switch_state("victory", new_best=True)
    assert game.state.new_best is True
    game.state.draw(game.surface)                # headless
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "title"


def test_game_over_shows_level_reached(pygame_ready):
    game, state = _playing()
    game.run.level_index = 7
    game.run.score = 1234
    game.switch_state("game_over")
    game.state.draw(game.surface)                # headless (stats render)
    _press(game.state, pygame.K_RETURN)
    assert game.state_name == "title"


# ----------------------------------------------------- bosses-deeated count
def test_boss_defeat_bumps_persisted_counter(pygame_ready):
    from src.enemies.boss import Boss

    class TinyBoss(Boss):
        KIND = "tinyboss"
        MAX_HP = 1

        def think(self, level, player):
            self.vx = 0.0

    game, state = _playing()
    lvl = state.level
    lvl.boss_required = True
    b = TinyBoss(int(state.player.x) + 40,
                 config.GROUND_ROW * config.TILE - 32)
    b.active = True
    state.enemies.enemies.insert(0, b)
    before = game.progress["play_stats"].get("bosses_defeated", 0)
    b.take_damage(b.hp)
    for _ in range(Boss.DEFEAT_TICKS + 4):
        state.update()
    assert lvl.boss_defeated
    after = game.progress["play_stats"]["bosses_defeated"]
    assert after == before + 1
    assert progress.load()["play_stats"]["bosses_defeated"] == after
    # no double count on further ticks
    for _ in range(20):
        state.update()
    assert game.progress["play_stats"]["bosses_defeated"] == after
