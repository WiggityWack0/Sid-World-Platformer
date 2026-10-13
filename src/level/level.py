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
        self.powerups = []
        self.key_shards = []         # objective shards (3c)
        self.required = 0            # shards needed to unlock the goal
        self.shards_collected = 0
        self.switches = []
        self.plates = []
        self.doors = []
        self.dynamic_hazards = []
        self.pipes = []
        self.checkpoints = []
        self.movers = []
        self.enemy_spawns = []        # (kind, x_px, y_px)
        self.goal = None              # GoalGate
        self.spawn = (TILE * 2, TILE * 6)
        self.respawn = self.spawn
        self.validated = False        # set by validator.ensure_level
        self.used_fallback = False
        self.has_arena = False        # boss arena carved into tail (5b)
        self.arena_x0 = 0             # first arena column (px-free, tiles)
        self.boss_required = False    # goal stays locked until boss defeat
        self.boss_defeated = False

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
        if self._overlap_tiles(rect, T.HAZARD_IDS):
            return True
        return any(d.hit_rect().colliderect(rect)
                   for d in self.dynamic_hazards)

    def overlaps_lethal(self, rect):
        """True when rect touches a LAVA tile or lethal dynamic hazard."""
        if self._overlap_tiles(rect, T.LETHAL_IDS):
            return True
        return any(d.lethal and d.hit_rect().colliderect(rect)
                   for d in self.dynamic_hazards)

    def _overlap_tiles(self, rect, ids):
        x0 = rect.left // TILE
        x1 = (rect.right - 1) // TILE
        y0 = rect.top // TILE
        y1 = (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.tiles.get(tx, ty) in ids:
                    hit = pygame.Rect(tx * TILE + 2, (ty + 1) * TILE - 9,
                                      TILE - 4, 9)
                    if rect.colliderect(hit):
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

    # -------------------------------------------------------- doors (3a)
    def goal_locked(self):
        """True until the required key shards are collected (3c) AND any
        required boss is defeated (5b; default flags keep identity)."""
        if self.required > self.shards_collected:
            return True
        return self.boss_required and not self.boss_defeated

    def open_doors_for(self, switch_id):
        """Latch open every LATCHED door linked to switch_id; returns count.
        Timed doors are excluded — they open only via `press_plate`
        windows (uniform `solver_opens` contract, no isinstance)."""
        n = 0
        for d in self.doors:
            if not d.solver_opens:
                continue
            if d.switch_id == switch_id and not d.open:
                d.open = True
                d.apply(self)
                n += 1
        return n

    def press_plate(self, plate_id):
        """A pressure plate fired: latch linked doors + refresh timed
        windows (3b-1). Returns number of latched doors opened."""
        n = self.open_doors_for(plate_id)
        for d in self.doors:
            if not d.solver_opens and d.plate_id == plate_id:
                d.open_window(self)
        return n

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
        for d in self.doors:
            d.tick(self)                # timed doors expire; latched no-op
        for h in self.dynamic_hazards:
            h.update()

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
        if tid == T.DOOR:
            return assets.door()
        if tid == T.LAVA:
            return assets.lava((tick // 8) % 2)
        return None

    def draw(self, surf, cam, assets, tick):
        ix, iy = cam.ix, cam.iy
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
                    surf.blit(img, (int(tx * TILE - ix),
                                    int(ty * TILE - iy)))
        for coin in self.coins:
            coin.draw(surf, cam, assets, tick)
        for k in self.key_shards:
            k.draw(surf, cam, assets, tick)
        for pu in self.powerups:
            pu.draw(surf, cam, assets, tick)
        for sw in self.switches:
            sw.draw(surf, cam, assets, tick)
        for pl in self.plates:
            pl.draw(surf, cam, assets, tick)
        for cp in self.checkpoints:
            cp.draw(surf, cam, assets, tick)
        for m in self.movers:
            m.draw(surf, cam, assets, tick)
        for h in self.dynamic_hazards:
            h.draw(surf, cam, assets, tick)
        if self.goal is not None:
            self.goal.draw(surf, cam, assets, tick)
