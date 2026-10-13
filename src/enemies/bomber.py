"""Bomber (5a): slow patrol that lobs arcing bombs at the player.

The Bomb is a two-phase projectile: ballistic flight, then a short AoE
burst whose rect expands so the existing projectile/hurt loop applies
splash damage. Drained by EnemyManager via the generic `shots` hook.
"""

import pygame

from src import config
from src.config import TILE
from src.enemies.base import Enemy, ledge_ahead


class Bomb:
    W = 10
    H = 10

    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.life = config.BOMB_LIFE
        self.burst = 0              # 0 = flying, >0 = AoE ticking, -1 = done

    @property
    def rect(self):
        if self.burst > 0:
            grow = 4                              # splash margin
            return pygame.Rect(int(self.x) - grow, int(self.y) - grow,
                               self.W + grow * 2, self.H + grow * 2)
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def dead(self):
        return self.burst == -1 or (self.burst == 0 and self.life <= 0)

    def update(self, level):
        self.life -= 1
        if self.burst == -1:
            return
        if self.burst > 0:
            self.burst -= 1
            if self.burst == 0:
                self.burst = -1
            return
        self.vy += config.BOMB_GRAV
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        below = level.solid_at(int(r.centerx // TILE),
                               int((r.bottom + 2) // TILE))
        if below or self.life <= 0:
            self.burst = config.BOMB_BURST        # detonate
        elif self.x < -32 or self.x > level.width + 32:
            self.burst = -1                        # lost off-screen

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.projectile(tick),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))


class Bomber(Enemy):
    KIND = "bomber"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.cooldown = config.BOMBER_COOLDOWN // 2
        self.shots = []

    def think(self, level, player):
        self.vx = self.facing * config.BOMBER_SPEED
        if self.on_ground and not ledge_ahead(level, self):
            self.facing = -self.facing
            self.vx = self.facing * config.BOMBER_SPEED
        self.cooldown -= 1
        if player.dead:
            return
        dx = player.cx - self.cx
        if abs(dx) > 1:
            self.facing = 1 if dx > 0 else -1
        if (self.cooldown <= 0
                and abs(dx) <= config.BOMBER_RANGE
                and abs(player.cy - self.cy) <= config.BOMBER_ARC_TOL):
            t = max(18.0, abs(dx) / 3.0)          # lob flight time (pure math)
            self.shots.append(Bomb(self.cx, self.y - 4, dx / t,
                                   config.BOMB_VY0))
            self.cooldown = config.BOMBER_COOLDOWN

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))