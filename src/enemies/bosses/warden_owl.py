"""Warden Owl (5c, Frost Peaks): flying boss — hovers, telegraphed dives,
and spawns flyers as reinforcements (drained by EnemyManager)."""

import math

import pygame

from src import config
from src.enemies.boss import Boss


class WardenOwl(Boss):
    KIND = "warden_owl"
    name = "WARDEN OWL"
    MAX_HP = config.OWL_HP
    W = 28
    H = 24
    GRAVITY = False

    def __init__(self, x, y):
        super().__init__(x, y)
        self.mode = "rise"         # rise -> hover -> telegraph -> dive -> recover
        self.hover_y = y - config.OWL_HOVER_RISE
        self.atk = 110
        self.hover_t = 0
        self.dive_t = 0
        self.reinforcements = []   # drained into the manager (5c)
        self._reinf_left = 2       # lifetime cap on spawned flyers

    def think(self, level, player):
        if self.mode == "rise":
            self.vy = -1.4
            self.vx = 0.0
            if self.y <= self.hover_y:
                self.mode = "hover"
            return
        if self.mode == "hover":
            self.hover_t += 1
            if not player.dead:
                self.vx = max(-1.5, min(1.5, (player.cx - self.cx) * 0.04))
                if abs(player.cx - self.cx) > 1:
                    self.facing = 1 if player.cx > self.cx else -1
            self.vy = math.sin(self.hover_t * 0.06) * 0.8
            self.atk -= 1
            if self.atk <= 0 and not player.dead:
                self.mode = "telegraph"
                self.telegraph = self.TELEGRAPH
            return
        if self.mode == "telegraph":
            self.vx *= 0.8
            self.vy *= 0.8
            if self.telegraph <= 0:
                self.mode = "dive"
                self.dive_t = 70
                dx = player.cx - self.cx
                dy = max(30.0, player.cy - self.cy)
                mag = math.hypot(dx, dy) or 1.0
                s = config.OWL_DIVE_SPEED + 0.6 * self.phase
                self.vx = dx / mag * s
                self.vy = dy / mag * s
            return
        if self.mode == "dive":
            self.dive_t -= 1
            if self.on_ground or self.dive_t <= 0:
                self.mode = "recover"
            return
        if self.mode == "recover":
            self.vx = 0.0
            self.vy = -3.4
            if self.y <= self.hover_y:
                self.mode = "hover"
                self.atk = max(50, 110 - 25 * self.phase)

    def take_damage(self, amount=1):
        phase_before = self.phase
        killed = super().take_damage(amount)
        if not killed and self.phase > phase_before \
                and self._reinf_left > 0:
            self._reinf_left -= 1
            self.reinforcements.append(
                ("flyer", int(self.cx // config.TILE), 8))
        return killed

    def draw(self, surf, cam, assets, tick):
        r = self.rect
        body = (90, 96, 140)
        if self.mode == "telegraph" and (tick // 4) % 2 == 0:
            body = (150, 160, 220)
        pygame.draw.ellipse(surf, body,
                            pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h))
        pygame.draw.ellipse(surf, (40, 44, 80),
                            pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h),
                            2)
        # wings during dive
        if self.mode == "dive":
            pygame.draw.polygon(surf, body, [
                (r.x - cam.ix, r.y - cam.iy + 6),
                (r.x - cam.ix - 8, r.y - cam.iy - 2),
                (r.x - cam.ix + 4, r.y - cam.iy + 14)])
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + 5, r.y - cam.iy + 7,
                                     4, 4))
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + r.w - 9,
                                     r.y - cam.iy + 7, 4, 4))