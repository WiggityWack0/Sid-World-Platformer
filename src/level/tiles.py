"""
Tile map, tile types and autotiling helpers.
"""

import pygame

from src.config import TILE

# ------------------------------------------------------------ tile type ids
EMPTY = 0
SOLID = 1        # terrain (grass-topped dirt via autotiling)
BRICK = 2        # breakable when bumped from below
QUESTION = 3     # bumped once -> coin, becomes USED
USED = 4
PIPE_TL = 5      # pipe lip, left half
PIPE_TR = 6      # pipe lip, right half
PIPE_BL = 7      # pipe body, left half
PIPE_BR = 8      # pipe body, right half
SPIKE = 9        # hazard, NOT solid (sits on the floor below)

SOLID_IDS = frozenset({SOLID, BRICK, QUESTION, USED,
                       PIPE_TL, PIPE_TR, PIPE_BL, PIPE_BR})
HAZARD_IDS = frozenset({SPIKE})
PIPE_IDS = frozenset({PIPE_TL, PIPE_TR, PIPE_BL, PIPE_BR})


def is_solid_id(tid):
    return tid in SOLID_IDS


def is_hazard_id(tid):
    return tid in HAZARD_IDS


def terrain_mask(tiles, tx, ty, w, h):
    """4-neighbour mask (N=1, E=2, S=4, W=8) for autotiling."""
    mask = 0
    if ty > 0 and is_solid_id(tiles.get(tx, ty - 1)):
        mask |= 1
    if tx < w - 1 and is_solid_id(tiles.get(tx + 1, ty)):
        mask |= 2
    if ty < h - 1 and is_solid_id(tiles.get(tx, ty + 1)):
        mask |= 4
    if tx > 0 and is_solid_id(tiles.get(tx - 1, ty)):
        mask |= 8
    return mask


class TileMap:
    """Dense tile grid with world-boundary semantics.

    Outside horizontally -> solid (invisible walls at level edges).
    Outside vertically   -> empty (open sky above, fatal pit below).
    """

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.data = bytearray(w * h)

    # ---------------------------------------------------------- queries
    def get(self, tx, ty):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.data[ty * self.w + tx]
        return EMPTY

    def set(self, tx, ty, tid):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            self.data[ty * self.w + tx] = tid

    def solid_at(self, tx, ty):
        if tx < 0 or tx >= self.w:
            return True          # level side walls
        if ty < 0:
            return False         # open sky
        if ty >= self.h:
            return False         # pit bottom -> fall to death
        return is_solid_id(self.data[ty * self.w + tx])

    def in_bounds(self, tx, ty):
        return True              # solid_at handles world edges

    def hazard_at(self, tx, ty):
        return is_hazard_id(self.get(tx, ty))

    def remove(self, tx, ty):
        """Clear a tile; returns the removed tile id."""
        tid = self.get(tx, ty)
        self.set(tx, ty, EMPTY)
        return tid

    def fill(self, x0, y0, x1, y1, tid):
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                self.set(tx, ty, tid)

    def any_solid_rect(self, rect):
        """True when rect overlaps at least one solid tile."""
        x0 = rect.left // TILE
        x1 = (rect.right - 1) // TILE
        y0 = rect.top // TILE
        y1 = (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.solid_at(tx, ty):
                    return True
        return False

    def copy(self):
        m = TileMap(self.w, self.h)
        m.data = bytearray(self.data)
        return m
