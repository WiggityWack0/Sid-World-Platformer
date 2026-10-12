"""
Tile-map collision helpers.

Axis-separated resolution in FLOAT coordinates (sub-pixel velocities must
not be lost to integer truncation): move X first (clamped against solids),
then Y. Movement larger than a tile is sub-stepped so nothing tunnels.

A "world" is any object exposing:
    solid_at(tx, ty) -> bool
    in_bounds(tx, ty) -> bool
"""

import math

import pygame

from src.config import TILE, TERMINAL_VY

EPS = 1e-7


def clamp_velocity(vy):
    return max(-TERMINAL_VY, min(TERMINAL_VY, vy))


def _overlapping_tiles(left, top, w, h):
    """Yield (tx, ty) for every tile cell the float box overlaps."""
    x0 = int(math.floor(left / TILE))
    x1 = int(math.floor((left + w - EPS) / TILE))
    y0 = int(math.floor(top / TILE))
    y1 = int(math.floor((top + h - EPS) / TILE))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            yield tx, ty


def _find_blocker(world, left, top, w, h, solids):
    for tx, ty in _overlapping_tiles(left, top, w, h):
        if world.in_bounds(tx, ty) and world.solid_at(tx, ty):
            return (tx * TILE, ty * TILE,
                    (tx + 1) * TILE, (ty + 1) * TILE)
    for s in solids:
        if left < s.right and left + w > s.left \
                and top < s.bottom and top + h > s.top:
            return (s.left, s.top, s.right, s.bottom)
    return None


def _as_rect(box):
    return pygame.Rect(box[0], box[1],
                       box[2] - box[0], box[3] - box[1])


def move_x(left, top, w, h, vx, world, solids=()):
    """Move horizontally; returns (new_left, hit) where hit is -1/1/0."""
    if abs(vx) < EPS:
        return left, 0
    sign = 1 if vx > 0 else -1
    remaining = vx
    hit = 0
    while abs(remaining) > EPS:
        step = max(-TILE + 1.0, min(TILE - 1.0, remaining))
        new_left = left + step
        blocker = _find_blocker(world, new_left, top, w, h, solids)
        if blocker is None:
            left = new_left
            remaining -= step
        else:
            hit = sign
            left = (blocker[0] - w) if sign > 0 else float(blocker[2])
            break
    return left, hit


def move_y(left, top, w, h, vy, world, solids=(), one_ways=()):
    """Move vertically.

    one_ways: rects only collided with when falling from above, so moving
    platforms can be stepped onto from the side.

    Returns (new_top, landed, head_hit, landed_surface)
      head_hit      -- pygame.Rect of tile hit while moving up, or None
      landed_surface-- pygame.Rect of surface landed on, or None
    """
    landed = False
    head_hit = None
    landed_surface = None
    if abs(vy) > EPS:
        remaining = vy
        direction = 1 if vy > 0 else -1
        while abs(remaining) > EPS:
            step = max(-TILE + 1.0, min(TILE - 1.0, remaining))
            new_top = top + step
            new_bottom = new_top + h
            if direction > 0:
                for ow in one_ways:
                    if (top + h <= ow.top + EPS and new_bottom > ow.top
                            and left + w > ow.left and left < ow.right):
                        top = ow.top - h
                        landed = True
                        landed_surface = ow
                        remaining = 0.0
                        break
                if landed:
                    break
            blocker = _find_blocker(world, left, new_top, w, h, solids)
            if blocker is None:
                top = new_top
                remaining -= step
            elif direction > 0:
                top = blocker[1] - h
                landed = True
                landed_surface = _as_rect(blocker)
                break
            else:
                top = float(blocker[3])
                head_hit = _as_rect(blocker)
                break

    if not landed:
        # standing probe (2px) keeps on_ground stable at vy == 0
        blocker = _find_blocker(world, left, top + 2, w, h, solids)
        if blocker is not None and blocker[1] >= top + h - 1:
            landed = True
            landed_surface = _as_rect(blocker)
        else:
            for ow in one_ways:
                if (top + h <= ow.top + EPS and top + h + 2 > ow.top
                        and left + w > ow.left and left < ow.right):
                    landed = True
                    landed_surface = ow
                    break
    return top, landed, head_hit, landed_surface
