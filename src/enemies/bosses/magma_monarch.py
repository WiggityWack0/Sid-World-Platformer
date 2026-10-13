"""Magma Monarch (5c, Molten Keep): fireball volleys; the final phase adds
lava blobs that leave short-lived lava puddles (runtime tile edits with
deterministic cleanup — charger-brick precedent)."""

import pygame

from src import config
from src.config import TILE
from src.enemies.boss import Boss
from src.level import tiles as T

FIRE_BODY = (255, 140, 40)


class MonarchFire:
    """Aimed fireball; final-phase lava blobs leave a lava puddle on
    impact with the floor."""
    W = 10
    H = 10
    LIFE = 140

    def __init__(self, x, y, vx, vy, lava=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.life = self.LIFE
        self.lava = lava
        self.owner = None                   # set by the monarch

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
        tx = int(r.centerx // TILE)
        ty = int(r.centery // TILE)
        floor_ty = int((r.bottom + 2) // TILE)
        hit_floor = level.solid_at(tx, floor_ty) \
            and not level.tiles.hazard_at(tx, floor_ty)
        if self.lava and self.owner is not None and self.vy > 0 \
                and hit_floor:
            self.life = 0
            self.owner.puddle_at(level, tx, floor_ty - 1)
        elif level.solid_at(tx, ty):
            self.life = 0
        if self.x < -32 or self.x > level.width + 32 \
                or self.y > level.height + 32:
            self.life = 0

    def draw(self, surf, cam, assets, tick):
        body = (255, 90, 30) if self.lava else FIRE_BODY
        pygame.draw.circle(surf, body,
                           (int(self.x) + 5 - cam.ix, int(self.y) + 5 - cam.iy),
                           5)
        pygame.draw.circle(surf, (140, 40, 20),
                           (int(self.x) + 5 - cam.ix, int(self.y) + 5 - cam.iy),
                           5, 1)


class MagmaMonarch(Boss):
    KIND = "magma_monarch"
    name = "MAGMA MONARCH"
    MAX_HP = config.MONARCH_HP
    W = 32
    H = 36

    def __init__(self, x, y):
        super().__init__(x, y)
        self.volley_cd = 90
        self.shots = []
        self.puddles = []                   # [tx, ty, ticks_left]

    def think(self, level, player):
        self.vx = 0.0
        if not player.dead:
            dx = player.cx - self.cx
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        # tick down lava puddles (deterministic cleanup)
        if self.puddles:
            keep = []
            for p in self.puddles:
                p[2] -= 1
                if p[2] > 0:
                    keep.append(p)
                elif level.tiles.get(p[0], p[1]) == T.LAVA:
                    level.tiles.set(p[0], p[1], T.EMPTY)
            self.puddles = keep
        self.volley_cd -= 1
        if self.volley_cd <= 0 and not player.dead:
            n = 3 + min(2, self.phase)       # 3 / 4 / 5 shot fan
            spread = 0.9
            for i in range(n):
                t = -spread + (2 * spread) * (i / max(1, n - 1))
                speed = config.FIREBALL_SPEED * 0.62
                lava = self.phase >= 2 and i == n // 2
                fire = MonarchFire(self.cx, self.cy - 4,
                                   0.0, speed, lava=lava)
                # aim the fan at the player (pure math)
                import math
                dx = player.cx - self.cx
                dy = player.cy - (self.cy - 4)
                base = math.atan2(dy, dx)
                fire.vx = math.cos(base + t) * speed
                fire.vy = math.sin(base + t) * speed
                fire.owner = self if lava else None
                self.shots.append(fire)
            self.volley_cd = max(56, config.MONARCH_VOLLEY_CD
                                 - 24 * self.phase)

    def puddle_at(self, level, tx, ty):
        """Leave a short-lived lava puddle (runtime tile edit)."""
        if 0 <= tx < level.tiles.w and 0 <= ty < level.tiles.h \
                and level.tiles.get(tx, ty) == T.EMPTY:
            level.tiles.set(tx, ty, T.LAVA)
            self.puddles.append([tx, ty, config.MONARCH_PUDDLE_TICKS])

    def draw(self, surf, cam, assets, tick):
        r = self.rect
        body = (200, 60, 40)
        if self.phase >= 2 and (tick // 5) % 2 == 0:
            body = (255, 100, 50)            # molten at low HP
        pygame.draw.rect(surf, body,
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h))
        pygame.draw.rect(surf, (90, 24, 20),
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h), 2)
        # crown spikes
        for ox in (4, 12, 20):
            pygame.draw.polygon(surf, (255, 210, 90), [
                (r.x - cam.ix + ox, r.y - cam.iy),
                (r.x - cam.ix + ox + 3, r.y - cam.iy - 7),
                (r.x - cam.ix + ox + 6, r.y - cam.iy)])
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + 7, r.y - cam.iy + 12,
                                     5, 4))
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + r.w - 12,
                                     r.y - cam.iy + 12, 5, 4))