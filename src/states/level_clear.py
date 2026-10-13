"""Level clear banner with animated time/coin bonus tally."""

import pygame

from src import inputs
from src import progress
from src.config import (COIN_CLEAR_BONUS, LEVELS_PER_RUN, TIME_BONUS_PER_UNIT,
                        VIEW_H, VIEW_W)
from src.states.base import State


class LevelClearState(State):
    name = "level_clear"

    def on_enter(self, time_left=0, time_bonus=0, coin_bonus=0, **kwargs):
        self.t = 0
        self.tally_time = time_left
        self.tally_coins = coin_bonus // max(1, COIN_CLEAR_BONUS)
        self.time_bonus = time_bonus
        self.coin_bonus = coin_bonus
        self.phase = "time"          # time -> coins -> done
        self.tick_accum = 0
        # 6b: best-score comparison captured BEFORE record_clear updates it
        run = self.game.run
        prev_best = self.game.progress.get("best_scores", {}) \
            .get(str(run.level_index), 0)
        self.new_best = run.score > prev_best

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key == pygame.K_m:
            return
        if inputs.key_to_action(event.key) == "confirm" \
                and self.phase == "done":
            run = self.game.run
            progress.record_clear(self.game.progress, run.level_index,
                                  run.score)      # unlock + best score (4c)
            progress.save(self.game.progress)
            run.level_index += 1
            self.game.audio.play_sfx("confirm")
            if run.finished:
                self.game.audio.play_music("title")
                self.game.switch_state("victory",
                                       new_best=self.new_best)   # 6b
            else:
                self.game.switch_state("playing")

    def update(self):
        self.t += 1
        self.tick_accum += 1
        run = self.game.run
        if self.phase == "time" and self.tick_accum % 2 == 0:
            if self.tally_time > 0:
                self.tally_time -= 1
                run.score += TIME_BONUS_PER_UNIT
                if self.tally_time % 4 == 0:
                    self.game.audio.play_sfx("select", vol=0.5)
            else:
                self.phase = "coins"
        elif self.phase == "coins" and self.tick_accum % 3 == 0:
            if self.tally_coins > 0:
                self.tally_coins -= 1
                run.score += COIN_CLEAR_BONUS
                self.game.audio.play_sfx("coin", vol=0.6)
            else:
                self.phase = "done"

    def draw(self, surf):
        if self.game.playing is not None:
            self.game.playing.draw(surf)
        dim = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surf.blit(dim, (0, 0))
        hud = self.game.hud
        run = self.game.run
        hud.text_center(surf, VIEW_W // 2, 44, "COURSE CLEAR!",
                        (255, 226, 96), hud.big_font)
        hud.text_center(surf, VIEW_W // 2, 92,
                        f"WORLD 1-{run.level_index + 1}")
        hud.text_center(surf, VIEW_W // 2, 118,
                        f"TIME BONUS  {self.tally_time * TIME_BONUS_PER_UNIT:05d}")
        hud.text_center(surf, VIEW_W // 2, 140,
                        f"COIN BONUS  {self.tally_coins * COIN_CLEAR_BONUS:05d}")
        hud.text_center(surf, VIEW_W // 2, 168,
                        f"SCORE       {run.score:06d}",
                        (255, 255, 160), hud.mid_font)
        if self.phase == "done" and (self.t // 30) % 2 == 0:
            more = "VICTORY - PRESS ENTER" if (run.level_index + 1 >=
                                               LEVELS_PER_RUN) \
                else "PRESS ENTER TO CONTINUE"
            hud.text_center(surf, VIEW_W // 2, 202, more,
                            (255, 255, 255), hud.mid_font)
        if self.new_best and (self.t // 15) % 2 == 0:      # 6b
            hud.text_center(surf, VIEW_W // 2, 184, "NEW BEST!",
                            (255, 240, 120), hud.mid_font)
