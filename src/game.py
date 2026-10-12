"""
Game: owns the fixed-timestep loop (60 Hz accumulator), the state
machine, and all services (assets, audio, HUD). States are created
lazily on switch and receive the Game for access to services.
"""

import random

import pygame

from src import inputs
from src.config import (FIXED_DT, FPS, LEVELS_PER_RUN, START_LIVES,
                        VIEW_H, VIEW_W, WINDOW_H, WINDOW_W)


class RunContext:
    """Progress through a single play-through (carried across levels)."""

    def __init__(self, seed):
        self.seed = seed
        self.level_index = 0
        self.score = 0
        self.coins = 0
        self.lives = START_LIVES

    @property
    def finished(self):
        return self.level_index >= LEVELS_PER_RUN


class Game:
    def __init__(self, seed=None, max_frames=None):
        pygame.init()
        self.window = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Sid's World")
        self.surface = pygame.Surface((VIEW_W, VIEW_H))
        self.clock = pygame.time.Clock()
        from src.assets import AssetFactory
        from src.audio import AudioManager
        from src.hud import Hud
        self.assets = AssetFactory()
        self.audio = AudioManager()
        self.hud = Hud()
        self.seed = seed if seed is not None else random.randrange(100000)
        self.run = None
        self.state = None
        self.state_name = ""
        self.running = True
        self.tick = 0
        self.max_frames = max_frames       # automated/headless runs
        self._updates = 0
        self._paused = None                # frozen PlayingState while paused
        self.playing = None                # last PlayingState (backdrop/refs)
        self._state_classes = {}
        self._register_states()
        self.switch_state("title")

    # -------------------------------------------------------- state mgmt
    def _register_states(self):
        from src.states.title import TitleState
        from src.states.playing import PlayingState
        from src.states.paused import PausedState
        from src.states.level_clear import LevelClearState
        from src.states.game_over import GameOverState
        from src.states.victory import VictoryState
        self._state_classes = {
            "title": TitleState,
            "playing": PlayingState,
            "paused": PausedState,
            "level_clear": LevelClearState,
            "game_over": GameOverState,
            "victory": VictoryState,
        }

    def switch_state(self, name, **kwargs):
        if self.state is not None:
            self.state.on_exit()
        cls = self._state_classes[name]
        self.state = cls(self)
        self.state_name = name
        self.state.on_enter(**kwargs)

    def new_run(self, seed=None):
        if seed is not None:
            self.seed = seed
        self.run = RunContext(self.seed)

    def pause(self):
        """Freeze the playing state underneath a pause overlay."""
        if self._paused is not None or self.state_name != "playing":
            return
        self._paused = self.state
        from src.states.paused import PausedState
        self.state = PausedState(self, self._paused)
        self.state_name = "paused"
        self.state.on_enter()

    def resume(self):
        if self._paused is None:
            return
        self.state.on_exit()
        self.state = self._paused
        self._paused = None
        self.state_name = "playing"

    def quit(self):
        self.running = False

    # -------------------------------------------------------------- loop
    def run_loop(self):
        accumulator = 0.0
        previous = pygame.time.get_ticks()
        while self.running:
            now = pygame.time.get_ticks()
            frame = min((now - previous) / 1000.0, 0.25)
            previous = now
            accumulator += frame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if inputs.key_to_action(event.key) == "mute":
                        self.audio.toggle_mute()
                        continue
                self.state.handle_event(event)

            while accumulator >= FIXED_DT and self.running:
                self.state.update()
                self.tick += 1
                self._updates += 1
                accumulator -= FIXED_DT
                if self.max_frames is not None \
                        and self._updates >= self.max_frames:
                    self.running = False
                    break

            if not self.running:
                break
            self.state.draw(self.surface)
            scaled = pygame.transform.scale(self.surface,
                                            (WINDOW_W, WINDOW_H))
            self.window.blit(scaled, (0, 0))
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
