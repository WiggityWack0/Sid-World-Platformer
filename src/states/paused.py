"""Pause overlay drawn on top of the frozen playing state (6a: a real
menu — Resume / Restart / Options / Level Select / Quit; the legacy
P/Esc/Q bindings are preserved as shortcuts)."""

import pygame

from src import inputs
from src.config import VIEW_H, VIEW_W
from src.states.base import State


class PausedState(State):
    name = "paused"
    ROWS = ("resume", "restart", "options", "level_select", "quit")

    def __init__(self, game, underlying):
        super().__init__(game)
        self.underlying = underlying

    def on_enter(self, **kwargs):
        self.sel = 0
        self.game.audio.duck_music(True)
        self.game.audio.play_sfx("select")

    def on_exit(self):
        self.game.audio.duck_music(False)

    # -------------------------------------------------------------- action
    def _activate(self):
        game = self.game
        row = self.ROWS[self.sel]
        game.audio.play_sfx("confirm")
        if row == "resume":
            game.resume()
        elif row == "restart":
            game._paused = None
            game.switch_state("playing")
        elif row == "options":
            game.switch_state("options")        # _paused kept for the return
        elif row == "level_select":
            game._paused = None
            game.switch_state("level_select")
        else:                                   # quit
            game._paused = None
            game.switch_state("title")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "pause" or event.key == pygame.K_ESCAPE:
            self.game.audio.play_sfx("select")
            self.game.resume()
            return
        if event.key == pygame.K_q:             # legacy shortcut
            self.game._paused = None
            self.game.switch_state("title")
            return
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            d = -1 if event.key == pygame.K_UP else 1
            self.sel = max(0, min(len(self.ROWS) - 1, self.sel + d))
            self.game.audio.play_sfx("select", vol=0.5)
            return
        if action == "confirm":
            self._activate()

    def update(self):
        pass                                  # frozen

    def draw(self, surf):
        self.underlying.draw(surf)
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surf.blit(dim, (0, 0))
        hud = self.game.hud
        hud.text_center(surf, VIEW_W // 2, 54, "PAUSED",
                        (255, 226, 96), hud.big_font)
        labels = ("RESUME", "RESTART LEVEL", "OPTIONS",
                  "LEVEL SELECT", "QUIT TO TITLE")
        for i, label in enumerate(labels):
            color = (255, 255, 255) if i == self.sel else (150, 156, 175)
            prefix = "> " if i == self.sel else "  "
            hud.text_center(surf, VIEW_W // 2, 108 + i * 18,
                            f"{prefix}{label}", color, hud.mid_font)
        hud.text_center(surf, VIEW_W // 2, VIEW_H - 18,
                        "ARROWS + ENTER    P/ESC RESUME    M MUTE")
