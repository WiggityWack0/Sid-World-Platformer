"""Victory screen after clearing the final level."""

import pygame

from src import inputs
from src.config import VIEW_H, VIEW_W
from src.states.base import State


class VictoryState(State):
    name = "victory"

    def on_enter(self, new_best=False, **kwargs):
        self.t = 0
        self.new_best = new_best

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        if inputs.key_to_action(event.key) == "confirm":
            self.game.audio.play_sfx("confirm")
            self.game.switch_state("title")

    def update(self):
        self.t += 1

    def draw(self, surf):
        g = self.game
        surf.blit(g.assets.sky(), (0, 0))
        clouds = g.assets.clouds()
        drift = int(self.t * 0.2) % clouds.get_width()
        surf.blit(clouds, (-drift, 0))
        surf.blit(clouds, (clouds.get_width() - drift, 0))
        near = g.assets.hills_near()
        for x in range(-near.get_width(), VIEW_W + near.get_width(),
                       near.get_width()):
            surf.blit(near, (x, VIEW_H - 64))
        hud = g.hud
        hud.text_center(surf, VIEW_W // 2, 56, "YOU WIN!",
                        (255, 226, 96), hud.big_font)
        run = g.run
        if run is not None:
            hud.text_center(surf, VIEW_W // 2, 110,
                            f"FINAL SCORE {run.score:06d}",
                            (255, 255, 255), hud.mid_font)
            hud.text_center(surf, VIEW_W // 2, 136,
                            f"COINS x{run.coins:02d}   LIVES x{run.lives}")
            stats = g.progress.get("play_stats", {})            # 6b
            hud.text_center(surf, VIEW_W // 2, 158,
                            f"BOSSES DEFEATED {stats.get('bosses_defeated', 0)}"
                            f"/4")
        if self.new_best and (self.t // 15) % 2 == 0:          # 6b
            hud.text_center(surf, VIEW_W // 2, 180, "NEW BEST!",
                            (255, 240, 120), hud.mid_font)
        if (self.t // 30) % 2 == 0:
            hud.text_center(surf, VIEW_W // 2, 190,
                            "PRESS ENTER FOR TITLE",
                            (255, 255, 255), hud.mid_font)
