"""Needler (5a): long-range turret that LEADS its aimed shot.

Contrast with the spitter's straight horizontal shots: the needler
solves a pure-math intercept (no RNG) using the player's velocity.
Drained by EnemyManager via the generic `shots` hook.
"""

import math

import pygame

from src import config
from src.config import TILE
from src.enemies.base import Enemy


class NeedlerShot:
    W = 8
    H = 4

    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.life = config.PROJECTILE_LIFE

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def dead(self):
        return self.life <= 0

    def update(self, level):
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        if level.solid_at(int(r.centerx // TILE), int(r.centery // TILE)):
            self.life = 0
        if (self.x < -32 or self.x > level.width + 32
                or self.y < -32 or self.y > level.height + 32):
            self.life = 0

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.projectile(tick),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))


class Needler(Enemy):
    KIND = "needler"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cooldown = config.NEEDLER_COOLDOWN
        self.shots = []
        self.flash = 0

    def think(self, level, player):
        self.vx = 0.0
        self.cooldown -= 1
        if self.flash > 0:
            self.flash -= 1
        if player.dead:
            return
        dx = player.cx - self.cx
        dy = player.cy - self.cy
        if abs(dx) > 1:
            self.facing = 1 if dx > 0 else -1
        if (self.cooldown <= 0
                and abs(dx) <= config.NEEDLER_RANGE
                and abs(dy) <= config.NEEDLER_VY_TOL):
            # Lead the target: aim at where it will be when the shot
            # arrives. Pure math — consumes no RNG (determinism-safe).
            dist = max(24.0, abs(dx))
            t = dist / config.NEEDLER_SHOT_SPEED
            ax = (player.cx + player.vx * t * config.NEEDLER_LEAD
                  - self.cx)
            lead_vy = max(-14.0, min(14.0, player.vy * t * 0.6))
            ay = (player.cy + lead_vy) - (self.cy - 4)
            mag = math.hypot(ax, ay) or 1.0
            speed = config.NEEDLER_SHOT_SPEED
            self.shots.append(NeedlerShot(
                self.cx + self.facing * 8, self.cy - 4,
                ax / mag * speed, ay / mag * speed))
            self.cooldown = config.NEEDLER_COOLDOWN
            self.flash = 8

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))