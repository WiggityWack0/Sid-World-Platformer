"""Spitter: stationary turret that fires slow projectiles when the player
is roughly level with it and in range."""

import pygame

from src import config
from src.config import TILE
from src.enemies.base import Enemy


class Projectile:
    W = 8
    H = 8
    SPEED = config.PROJECTILE_SPEED

    def __init__(self, x, y, direction):
        self.x = float(x)
        self.y = float(y)
        self.vx = self.SPEED * direction
        self.life = config.PROJECTILE_LIFE
        self.direction = direction

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def update(self, level):
        self.life -= 1
        self.x += self.vx
        r = self.rect
        tx = int(r.centerx // TILE)
        ty = int(r.centery // TILE)
        if level.solid_at(tx, ty) or self.life <= 0:
            self.life = 0
        if self.x < -32 or self.x > level.width + 32:
            self.life = 0

    @property
    def dead(self):
        return self.life <= 0

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.projectile(tick),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))


class Spitter(Enemy):
    KIND = "spitter"
    W = 16
    H = 20

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cooldown = 50
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
        dy = abs(player.cy - self.cy)
        if abs(dx) > 1:
            self.facing = 1 if dx > 0 else -1
        if (self.cooldown <= 0
                and abs(dx) <= config.SPITTER_RANGE
                and dy <= config.SPITTER_VY_TOL):
            self.shots.append(Projectile(
                self.cx + self.facing * 10, self.cy - 4, self.facing))
            self.cooldown = config.SPITTER_COOLDOWN
            self.flash = 10

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))
