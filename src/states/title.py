"""Title screen: animated backdrop, logo, start/seed/mute prompts."""

import random

import pygame

from src import inputs
from src.config import VIEW_H, VIEW_W
from src.states.base import State


class TitleState(State):
    name = "title"

    def on_enter(self, **kwargs):
        self.t = 0
        self.game.audio.play_music("title")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "confirm":
            self.game.audio.play_sfx("confirm")
            self.game.new_run()
            self.game.switch_state("playing")
        elif event.key == pygame.K_s:
            self.game.seed = random.randrange(100000)
            self.game.audio.play_sfx("select")

    def update(self):
        self.t += 1

    def draw(self, surf):
        game = self.game
        surf.blit(game.assets.sky(), (0, 0))
        clouds = game.assets.clouds()
        drift = int(self.t * 0.12) % (VIEW_W + 80)
        surf.blit(clouds, (-drift, 0))
        surf.blit(clouds, (VIEW_W + 80 - drift, 0))
        far = game.assets.hills_far()
        for x in range(-far.get_width(), VIEW_W + far.get_width(),
                       far.get_width()):
            surf.blit(far, (x, VIEW_H - 80))
        near = game.assets.hills_near()
        for x in range(-near.get_width(), VIEW_W + near.get_width(),
                       near.get_width()):
            surf.blit(near, (x, VIEW_H - 64))

        hud = game.hud
        hud.text_center(surf, VIEW_W // 2, 46, "SID'S WORLD",
                        (255, 226, 96), hud.big_font)
        hud.text_center(surf, VIEW_W // 2, 78, "A PROCEDURAL PLATFORMER",
                        (255, 255, 255), hud.font)

        if (self.t // 30) % 2 == 0:
            hud.text_center(surf, VIEW_W // 2, 132, "PRESS ENTER TO START",
                            (255, 255, 255), hud.mid_font)
        hud.text_center(surf, VIEW_W // 2, 168,
                        f"SEED {self.game.seed}   (S = NEW SEED)")
        hud.text_center(surf, VIEW_W // 2, 190,
                        "ARROWS MOVE   Z/SPACE JUMP   X RUN")
        hud.text_center(surf, VIEW_W // 2, 206,
                        "P PAUSE   R RESTART   M MUTE   DOWN ENTER PIPES")
