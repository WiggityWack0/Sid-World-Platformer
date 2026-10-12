"""Game over screen."""

import pygame

from src import inputs
from src.config import VIEW_H, VIEW_W
from src.states.base import State


class GameOverState(State):
    name = "game_over"

    def on_enter(self, **kwargs):
        self.t = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        if inputs.key_to_action(event.key) == "confirm":
            self.game.audio.play_sfx("confirm")
            self.game.switch_state("title")

    def update(self):
        self.t += 1

    def draw(self, surf):
        if self.game.playing is not None:
            self.game.playing.draw(surf)
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((20, 0, 0, 190))
        surf.blit(dim, (0, 0))
        hud = self.game.hud
        hud.text_center(surf, VIEW_W // 2, 80, "GAME OVER",
                        (255, 96, 88), hud.big_font)
        run = self.game.run
        if run is not None:
            hud.text_center(surf, VIEW_W // 2, 132,
                            f"FINAL SCORE {run.score:06d}",
                            (255, 255, 255), hud.mid_font)
        if (self.t // 30) % 2 == 0:
            hud.text_center(surf, VIEW_W // 2, 186,
                            "PRESS ENTER FOR TITLE",
                            (255, 255, 255), hud.mid_font)
