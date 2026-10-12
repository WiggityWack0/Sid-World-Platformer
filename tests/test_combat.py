"""Combat/lives: i-frames after respawn, checkpoint respawn, game over."""

import pygame

from src import config
from src.audio.mixer_manager import AudioManager
from src.camera import Camera
from src.config import DEATH_ANIM_FRAMES, START_LIVES
from src.enemy_manager import EnemyManager
from src.game import RunContext
from src.player import Player
from src.states.game_over import GameOverState
from src.states.playing import PlayingState


def _make_playing(game):
    game.new_run(seed=7)
    game.switch_state("playing")
    return game.state


def test_respawn_grants_invulnerability_frames(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    state = _make_playing(game)
    player = state.player
    player.die("enemy")
    for _ in range(DEATH_ANIM_FRAMES + 4):
        game.state.update()
        if game.state_name != "playing":
            break
    assert game.run.lives == START_LIVES - 1
    assert game.state_name == "playing"
    new_player = game.state.player
    assert not new_player.dead
    assert config.RESPAWN_INVULN - 10 <= new_player.invuln \
        <= config.RESPAWN_INVULN
    assert new_player.invuln > 0


def test_death_at_zero_lives_goes_to_game_over(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    state = _make_playing(game)
    game.run.lives = 0
    state.player.die("pit")
    for _ in range(DEATH_ANIM_FRAMES + 4):
        game.state.update()
        if game.state_name != "playing":
            break
    assert game.state_name == "game_over"
    assert isinstance(game.state, GameOverState)


def test_checkpoint_updates_respawn_point(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    state = _make_playing(game)
    assert state.level.checkpoints, "level has no checkpoints"
    cp = state.level.checkpoints[0]
    old_respawn = state.respawn
    state.player.x = float(cp.rect.x)
    state.player.y = float(cp.rect.y)
    state._items()
    assert cp.active
    assert state.respawn == cp.respawn
    assert state.respawn != old_respawn


def test_hazard_kills_player(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    state = _make_playing(game)
    assert not state.player.dead
    state._kill("hazard")
    assert state.player.dead
    assert state.player.death_timer == config.DEATH_ANIM_FRAMES


def test_stomp_combat_awards_score_and_bounce(pygame_ready):
    from src.game import Game
    game = Game(seed=7, max_frames=None)
    state = _make_playing(game)
    # fabricate a walker right under a falling player
    from src.enemies import Walker
    lvl = state.level
    enemy = Walker(int(state.player.x), int(state.player.y) + 40)
    enemy.active = True
    state.enemies.enemies.insert(0, enemy)
    state.player.y = float(enemy.y - 20)
    state.player.vy = 4.0
    score_before = game.run.score
    from src.player import Input
    state._combat(Input())
    assert enemy.state == "dying"
    assert game.run.score >= score_before + config.STOMP_SCORE
    assert state.player.vy < -1, "no stomp bounce applied"
