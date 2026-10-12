"""
Level: owns the tile map, objects, spawn points and rendering.
"""

import pygame

from src.config import TILE, VIEW_W, VIEW_H
from src.level import tiles as T
from src.level.objects import Checkpoint, Coin, GoalGate, MovingPlatform, Pipe


class Level:
    def __init__(self, width_tiles, height_tiles, seed=0, difficulty=0.0,
                 level_index=0):
        self.seed = seed
        self.difficulty = difficulty
        self.level_index = level_index
        self.tiles = T.TileMap(width_tiles, height_tiles)
        self.coins = []
        self.pipes = []
        self.checkpoints = []
        self.movers = []
        self.enemy_spawns = []        # (kind, x_px, y_px)
        self.goal = None              # GoalGate
        self.spawn = (TILE * 2, TILE * 6)
        self.respawn = self.spawn
        self.validated = False        # set by validator.ensure_level
        self.used_fallback = False

    # ------------------------------------------------------------ geometry
    @property
    def width(self):
        return self.tiles.w * TILE

    @property
    def height(self):
        return self.tiles.h * TILE

    # ------------------------------------------------------------- physics
    def solid_at(self, tx, ty):
        return self.tiles.solid_at(tx, ty)

    def in_bounds(self, tx, ty):
        return True

    def hazard_at(self, tx, ty):
        return self.tiles.hazard_at(tx, ty)

    def mover_rects(self):
        return [m.solid_rect for m in self.movers]

    def overlaps_hazard(self, rect):
        x0 = rect.left // TILE
        x1 = (rect.right - 1) // TILE
        y0 = rect.top // TILE
        y1 = (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.hazard_at(tx, ty):
                    spike = pygame.Rect(tx * TILE + 2, (ty + 1) * TILE - 9,
                                        TILE - 4, 9)
                    if rect.colliderect(spike):
                        return True
        return False

    def pipe_at_feet(self, rect):
        """Pipe whose top surface the rect is standing on, or None."""
        for pipe in self.pipes:
            top = pipe.rect
            if (rect.bottom == top.top
                    and rect.right > top.left + 2
                    and rect.left < top.right - 2):
                return pipe
        return None

    # -------------------------------------------------------------- blocks
    def bump(self, tx, ty):
        """Player head hit a tile from below. Returns 'coin'|'break'|'hit'."""
        tid = self.tiles.get(tx, ty)
        if tid == T.QUESTION:
            self.tiles.set(tx, ty, T.USED)
            return "coin"
        if tid == T.BRICK:
            self.tiles.remove(tx, ty)
            return "break"
        if tid in (T.SOLID, T.USED, T.PIPE_TL, T.PIPE_TR,
                   T.PIPE_BL, T.PIPE_BR):
            return "hit"
        return "none"

    # -------------------------------------------------------------- update
    def update(self):
        for m in self.movers:
            m.update()

    # ---------------------------------------------------------------- draw
    def _tile_image(self, tid, tx, ty, assets, tick):
        if tid == T.SOLID:
            mask = T.terrain_mask(self.tiles, tx, ty, self.tiles.w, self.tiles.h)
            return assets.terrain(mask)
        if tid == T.BRICK:
            return assets.brick()
        if tid == T.QUESTION:
            return assets.question((tick // 7) % 4)
        if tid == T.USED:
            return assets.used_block()
        if tid in (T.PIPE_TL, T.PIPE_TR, T.PIPE_BL, T.PIPE_BR):
            return assets.pipe(tid)
        if tid == T.SPIKE:
            return assets.spike()
        return None

    def draw(self, surf, cam, assets, tick):
        tx0 = max(0, cam.x // TILE)
        tx1 = min(self.tiles.w - 1, (cam.x + VIEW_W) // TILE + 1)
        ty0 = max(0, cam.y // TILE)
        ty1 = min(self.tiles.h - 1, (cam.y + VIEW_H) // TILE + 1)
        for ty in range(int(ty0), int(ty1) + 1):
            for tx in range(int(tx0), int(tx1) + 1):
                tid = self.tiles.data[ty * self.tiles.w + tx]
                if tid == T.EMPTY:
                    continue
                img = self._tile_image(tid, tx, ty, assets, tick)
                if img is not None:
                    surf.blit(img, (int(tx * TILE - cam.x),
                                    int(ty * TILE - cam.y)))
        for coin in self.coins:
            coin.draw(surf, cam, assets, tick)
        for cp in self.checkpoints:
            cp.draw(surf, cam, assets, tick)
        for m in self.movers:
            m.draw(surf, cam, assets, tick)
        if self.goal is not None:
            self.goal.draw(surf, cam, assets, tick)
