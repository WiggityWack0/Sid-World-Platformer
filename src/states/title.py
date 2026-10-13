"""Title screen: animated backdrop, logo, and a real menu (6a) —
New Game / Continue / Level Select / Options. Every legacy key binding
stays live as a shortcut (Enter/C/L/S)."""

import random

import pygame

from src import inputs
from src import progress
from src.config import LEVELS_PER_RUN, VIEW_H, VIEW_W
from src.states.base import State


class TitleState(State):
    name = "title"
    ROWS = ("new_game", "continue", "level_select", "options")

    def on_enter(self, **kwargs):
        self.t = 0
        self.sel = 0
        self.game.audio.play_music("title")

    # -------------------------------------------------------------- action
    def _activate(self):
        game = self.game
        row = self.ROWS[self.sel]
        if row == "new_game":
            game.audio.play_sfx("confirm")
            game.new_run()
            game.switch_state("playing")
        elif row == "continue":
            if progress.is_unlocked(game.progress, 1):
                game.audio.play_sfx("confirm")
                game.new_run()
                game.run.level_index = min(
                    game.progress["unlocked_level_index"],
                    LEVELS_PER_RUN - 1)
                game.switch_state("playing")
            else:
                game.audio.play_sfx("select", vol=0.5)   # denied
        elif row == "level_select":
            game.audio.play_sfx("select")
            game.switch_state("level_select")
        else:                                           # options
            game.audio.play_sfx("select")
            game.switch_state("options")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        action = inputs.key_to_action(event.key)
        if action == "confirm":
            self._activate()
            return
        if event.key == pygame.K_c \
                and progress.is_unlocked(self.game.progress, 1):
            self.sel = 1
            self._activate()
            return
        elif event.key == pygame.K_l:
            self.sel = 2
            self._activate()
            return
        elif event.key == pygame.K_s:
            self.game.seed = random.randrange(100000)
            self.game.audio.play_sfx("select")
            return
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            d = -1 if event.key == pygame.K_UP else 1
            self.sel = max(0, min(len(self.ROWS) - 1, self.sel + d))
            self.game.audio.play_sfx("select", vol=0.5)

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

        can_continue = progress.is_unlocked(game.progress, 1)
        labels = ("NEW GAME",
                  (f"CONTINUE (LEVEL "
                   f"{game.progress['unlocked_level_index'] + 1})")
                  if can_continue else "CONTINUE -",
                  "LEVEL SELECT", "OPTIONS")
        for i, label in enumerate(labels):
            color = (255, 255, 255) if i == self.sel else (150, 156, 175)
            if i == 1 and not can_continue:
                color = (90, 94, 110)
            prefix = "> " if i == self.sel else "  "
            hud.text_center(surf, VIEW_W // 2, 96 + i * 17,
                            f"{prefix}{label}", color, hud.mid_font)
        hud.text_center(surf, VIEW_W // 2, 176,
                        f"SEED {self.game.seed}   (S = NEW SEED)")
        hud.text_center(surf, VIEW_W // 2, 196,
                        "ARROWS MOVE   Z/SPACE JUMP   X RUN")
        hud.text_center(surf, VIEW_W // 2, 212,
                        "P PAUSE   R RESTART   M MUTE   DOWN ENTER PIPES")
