"""
Game: owns the fixed-timestep loop (60 Hz accumulator), the state
machine, and all services (assets, audio, HUD). States are created
lazily on switch and receive the Game for access to services.
"""

import random

import pygame

from src import inputs
from src import progress as progress_mod
from src.config import (FIXED_DT, FPS, GRADE_TINTS, LEVELS_PER_RUN,
                        START_LIVES,
                        VIEW_H, VIEW_W, WINDOW_H, WINDOW_W, zone_of)
from src.render import Presentation
from src.transition import Transition


class RunContext:
    """Progress through a single play-through (carried across levels)."""

    def __init__(self, seed):
        self.seed = seed
        self.level_index = 0
        self.score = 0
        self.coins = 0
        self.lives = START_LIVES
        self.zones_seen = set()      # per-run zone-primer tracking (6c)

    @property
    def finished(self):
        return self.level_index >= LEVELS_PER_RUN


class Game:
    def __init__(self, seed=None, max_frames=None, transitions=False):
        # transitions default OFF (6b recorded): synchronous flow tests
        # keep exact timing; the shipped game (main.py) opts in.
        pygame.init()
        self.window = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Sid's World")
        inputs.controller.open()      # attach the first pad, if any (hot-plug ok)
        self.surface = pygame.Surface((VIEW_W, VIEW_H))
        self.clock = pygame.time.Clock()
        from src.assets import AssetFactory
        from src.audio import AudioManager
        from src.effects import Effects
        from src.hud import Hud
        from src.render.menu import MenuPanel
        self.assets = AssetFactory()
        self.audio = AudioManager()
        self.hud = Hud()
        self.fx = Effects()
        self.menu = MenuPanel(self.hud)   # shared menu component (Phase 4)
        self.presentation = Presentation()   # post-processing (Phase 1)
        self.seed = seed if seed is not None else random.randrange(100000)
        self.progress = progress_mod.load()   # tolerant; never crashes (4c)
        self.audio.apply_settings(self.progress["settings"])  # live (6a)
        self.presentation.apply_settings(self.progress["settings"])
        self.refresh_window()                 # honor saved window_scale
        self.run = None
        self.state = None
        self.state_name = ""
        self.running = True
        self.tick = 0
        self.max_frames = max_frames       # automated/headless runs
        self._updates = 0
        self.transition = Transition() if transitions else None
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
        from src.states.level_select import LevelSelectState
        from src.states.options import OptionsState
        self._state_classes = {
            "title": TitleState,
            "playing": PlayingState,
            "paused": PausedState,
            "level_clear": LevelClearState,
            "game_over": GameOverState,
            "victory": VictoryState,
            "level_select": LevelSelectState,
            "options": OptionsState,
        }

    def switch_state(self, name, **kwargs):
        if (self.transition is not None and self.state is not None
                and not self.transition.active):
            style, tint = self._transition_style(name)
            # deferred to black (6b); style is draw-shape only (Phase 5 T4)
            self.transition.start((name, kwargs), style=style, tint=tint)
            return
        self._switch_state_now(name, **kwargs)

    def _transition_style(self, name):
        """(style, tint) for a pending switch — pure visual mapping.
        level_clear -> wipe; game_over (the death screen) -> iris; zone
        change on level entry -> zone_fade tinted with the new zone;
        everything else -> plain fade."""
        if name == "level_clear":
            return "wipe", None
        if name == "game_over":
            return "iris", None
        if name == "playing" and self.run is not None:
            zone = zone_of(self.run.level_index)
            if zone != getattr(self, "_last_zone", 0):
                tint = GRADE_TINTS[zone] if zone < len(GRADE_TINTS) else None
                return "zone_fade", tint
        return "fade", None

    def _switch_state_now(self, name, **kwargs):
        if self.state is not None:
            self.state.on_exit()
        cls = self._state_classes[name]
        self.state = cls(self)
        self.state_name = name
        if name == "playing" and self.run is not None:
            # remember the zone for the next entry (Phase 5 T4 zone_fade)
            self._last_zone = zone_of(self.run.level_index)
        self.state.on_enter(**kwargs)

    def tick_transition(self):
        """One fixed tick of the fade (6b); swaps at black exactly once."""
        if self.transition is None or not self.transition.active:
            return
        if self.transition.step() == "swap":
            name, kwargs = self.transition.pending
            self._switch_state_now(name, **kwargs)

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

    def refresh_window(self):
        """Re-create the window at the presentation layer's saved scale."""
        scale = self.presentation.window_scale
        self.window = pygame.display.set_mode((VIEW_W * scale, VIEW_H * scale))

    # ---------------------------------------------------------------- input
    def _dispatch(self, event):
        """Global mute intercept, then route the event to the active state."""
        if event.type == pygame.KEYDOWN \
                and inputs.key_to_action(event.key) == "mute":
            self.audio.toggle_mute()
            # persist the mute with the other settings (6a)
            self.progress["settings"]["muted"] = self.audio.muted
            progress_mod.save(self.progress)
            return
        self.state.handle_event(event)

    def _pump(self, event):
        """One input event: controller translation + keyboard dispatch."""
        self._dispatch(event)
        for synth in inputs.controller.process_event(event):
            self._dispatch(synth)

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
                self._pump(event)

            while accumulator >= FIXED_DT and self.running:
                self.tick_transition()
                self.state.update()
                if self.state_name == "playing":
                    self.fx.update()
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
            # post-process before the upscale; zone grade only in play (1)
            zone = (zone_of(self.run.level_index)
                    if self.run is not None
                    and self.state_name in ("playing", "paused") else 0)
            self.presentation.apply(self.surface, zone)
            scaled = pygame.transform.scale(self.surface,
                                            self.window.get_size())
            self.window.blit(scaled, (0, 0))
            if self.transition is not None:
                self.transition.draw(self.window)
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
