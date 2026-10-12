"""
Typed world objects: Pipe, Coin, Checkpoint, GoalGate, MovingPlatform.

Bricks / question blocks are tile types (see tiles.py) with behaviour
handled by Level.bump(); pipes are tiles for collision plus this object
for warp links.
"""

import pygame

from src.config import TILE, PLAYER_H


class Pipe:
    """A 2-tile-wide pipe; tiles are in the TileMap, this carries the warp."""

    def __init__(self, tx, top_row, height_tiles, warp_id=None):
        self.tx = tx
        self.top_row = top_row
        self.height = height_tiles
        self.warp_id = warp_id
        self.rect = pygame.Rect(tx * TILE, top_row * TILE,
                                TILE * 2, height_tiles * TILE)
        self.entry = None          # (x, y) where the linked pipe drops you

    @property
    def top_center(self):
        return (self.rect.centerx, self.rect.top)


class Coin:
    ANIM_SPEED = 8

    def __init__(self, tx, ty):
        self.tx, self.ty = tx, ty
        self.x = tx * TILE + TILE // 2
        self.y = ty * TILE + TILE // 2
        self.rect = pygame.Rect(tx * TILE + 3, ty * TILE + 1, 10, 14)
        self.collected = False

    def frame(self, tick):
        return (tick // self.ANIM_SPEED) % 4

    def draw(self, surf, cam, assets, tick):
        if self.collected:
            return
        img = assets.coin(self.frame(tick))
        surf.blit(img, (int(self.x - cam.x) - img.get_width() // 2,
                        int(self.y - cam.y) - img.get_height() // 2))


class Checkpoint:
    def __init__(self, tx, feet_row):
        self.tx = tx
        self.feet_row = feet_row
        y = (feet_row + 1) * TILE - 40
        self.rect = pygame.Rect(tx * TILE + 4, y, 8, 40)
        self.active = False
        self.respawn = (tx * TILE, (feet_row + 1) * TILE - PLAYER_H)

    def draw(self, surf, cam, assets, tick):
        img = assets.checkpoint(self.active)
        surf.blit(img, (int(self.tx * TILE - cam.x),
                        int((self.feet_row + 1) * TILE - img.get_height()
                            - cam.y)))


class GoalGate:
    """Flag pole at the end of the level; touching it clears the course."""

    def __init__(self, tx, feet_row):
        self.tx = tx
        self.feet_row = feet_row
        y = (feet_row + 1) * TILE - 52
        self.rect = pygame.Rect(tx * TILE + 3, y, 10, 52)

    def draw(self, surf, cam, assets, tick):
        img = assets.goal_gate()
        surf.blit(img, (int(self.tx * TILE - 3 - cam.x),
                        int((self.feet_row + 1) * TILE - img.get_height()
                            - cam.y)))


class MovingPlatform:
    """Ping-pong platform; exposes dx/dy so the player can be carried."""

    H = 12

    def __init__(self, x, y, length_px, axis, span_px, speed):
        self.length = length_px
        self.axis = axis                      # 'x' or 'y'
        self.speed = speed
        if axis == "x":
            self.start = x
            self.min, self.max = x, x + span_px
        else:
            self.start = y
            self.min, self.max = y, y + span_px
        self.pos = float(self.start)
        self.dir = 1
        self.dx = 0.0
        self.dy = 0.0
        if axis == "x":
            self.rect = pygame.Rect(int(self.pos), int(y), length_px, self.H)
        else:
            self.rect = pygame.Rect(int(x), int(self.pos), length_px, self.H)

    @property
    def solid_rect(self):
        return self.rect

    def update(self):
        self.dx = self.dy = 0.0
        prev = self.pos
        self.pos += self.dir * self.speed
        if self.pos >= self.max:
            self.pos = self.max
            self.dir = -1
        elif self.pos <= self.min:
            self.pos = self.min
            self.dir = 1
        delta = self.pos - prev
        if self.axis == "x":
            self.rect.x = int(round(self.pos))
            self.dx = delta
        else:
            self.rect.y = int(round(self.pos))
            self.dy = delta

    def draw(self, surf, cam, assets, tick):
        seg = assets.platform_seg()
        x = int(self.rect.x - cam.x)
        y = int(self.rect.y - cam.y)
        for i in range(0, self.length, TILE):
            surf.blit(seg, (x + i, y))
