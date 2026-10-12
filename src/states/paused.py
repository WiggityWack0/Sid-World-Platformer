"""Pause overlay drawn on top of the frozen playing state."""

import pygame

from src import inputs
from src.config import VIEW_H, VIEW_W
from src.states.base import State


class PausedState(State):
    name = "paused"

    def __init__(self, game, underlying):
        super().__init__(game)
        self.underlying = underlying

    def on_enter(self, **kwargs):
        self.game.audio.duck_music(True)
        self.game.audio.play_sfx("select")

    def on_exit(self):
        self.game.audio.duck_music(False)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "pause" or event.key == pygame.K_ESCAPE:
            self.game.audio.play_sfx("select")
            self.game.resume()
        elif event.key == pygame.K_q:
            self.game._paused = None
            self.game.switch_state("title")

    def update(self):
        pass                                  # frozen

    def draw(self, surf):
        self.underlying.draw(surf)
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surf.blit(dim, (0, 0))
        hud = self.game.hud
        hud.text_center(surf, VIEW_W // 2, 88, "PAUSED",
                        (255, 226, 96), hud.big_font)
        hud.text_center(surf, VIEW_W // 2, 140,
                        "P / ESC = RESUME     Q = QUIT TO TITLE")
        hud.text_center(surf, VIEW_W // 2, 164, "M = MUTE")
