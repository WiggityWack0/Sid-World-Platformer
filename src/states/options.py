"""Options menu (6a): volumes / mute / tutorial, persisted live via the
D3 settings schema (4c) and applied through the AudioManager."""

import pygame

from src import inputs
from src import progress
from src.config import VOLUME_STEP, VIEW_H, VIEW_W
from src.states.base import State


class OptionsState(State):
    name = "options"

    ROWS = ("master_volume", "music_volume", "sfx_volume",
            "muted", "tutorial_enabled")
    LABELS = {
        "master_volume": "MASTER VOLUME",
        "music_volume": "MUSIC VOLUME",
        "sfx_volume": "SFX VOLUME",
        "muted": "MUTE",
        "tutorial_enabled": "TUTORIAL",
    }

    def on_enter(self, **kwargs):
        self.sel = 0
        self.game.audio.play_sfx("select")

    # ------------------------------------------------------------ helpers
    def _settings(self):
        return self.game.progress["settings"]

    def _apply(self):
        self.game.audio.apply_settings(self._settings())
        progress.save(self.game.progress)

    def _adjust(self, key, direction):
        st = self._settings()
        if key in ("master_volume", "music_volume", "sfx_volume"):
            st[key] = round(min(1.0, max(0.0,
                              st[key] + direction * VOLUME_STEP)), 2)
        else:
            st[key] = not st[key]
        self.game.audio.play_sfx("select", vol=0.5)
        self._apply()

    def _leave(self):
        game = self.game
        if game._paused is not None:            # came from the pause menu
            from src.states.paused import PausedState
            game.state = PausedState(game, game._paused)
            game.state_name = "paused"
            game.state.on_enter()
        else:                                   # came from the title
            game.switch_state("title")

    # -------------------------------------------------------------- input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.game.audio.play_sfx("select")
            self._leave()
            return
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            d = -1 if event.key == pygame.K_UP else 1
            self.sel = max(0, min(len(self.ROWS) - 1, self.sel + d))
            self.game.audio.play_sfx("select", vol=0.5)
            return
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._adjust(self.ROWS[self.sel],
                         1 if event.key == pygame.K_RIGHT else -1)
            return
        if inputs.key_to_action(event.key) == "confirm":
            self._adjust(self.ROWS[self.sel], 1)   # Enter = adjust right

    def update(self):
        pass

    # --------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill((16, 20, 40))
        hud = self.game.hud
        hud.text_center(surf, VIEW_W // 2, 34, "OPTIONS",
                        (255, 226, 96), hud.big_font)
        st = self._settings()
        for i, key in enumerate(self.ROWS):
            y = 84 + i * 22
            label = self.LABELS[key]
            if key in ("master_volume", "music_volume", "sfx_volume"):
                value = f"{st[key]:.2f}"
            else:
                value = "ON" if st[key] else "OFF"
            color = (255, 255, 255) if i == self.sel else (150, 156, 175)
            prefix = "> " if i == self.sel else "  "
            hud.text(surf, VIEW_W // 2 - 90, y, f"{prefix}{label}",
                     color)
            hud.text(surf, VIEW_W // 2 + 40, y, value, color)
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 26,
                        "ARROWS ADJUST   ENTER TOGGLES")
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 12, "ESC = BACK")