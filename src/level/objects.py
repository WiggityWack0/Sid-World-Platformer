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
        surf.blit(img, (int(self.x - cam.ix) - img.get_width() // 2,
                        int(self.y - cam.iy) - img.get_height() // 2))


class PowerUp:
    """Timed bonus pickup (Phase 2b).

    D6: purely additive like coins — the validator never sees power-ups, so
    a no-power-up run is always completable.
    """

    ANIM_SPEED = 8

    def __init__(self, tx, ty, kind):
        self.tx, self.ty, self.kind = tx, ty, kind
        self.x = tx * TILE + TILE // 2
        self.y = ty * TILE + TILE // 2
        self.rect = pygame.Rect(tx * TILE + 1, ty * TILE + 2,
                                TILE - 2, TILE - 4)
        self.collected = False

    def draw(self, surf, cam, assets, tick):
        if self.collected:
            return
        img = assets.powerup(self.kind, (tick // self.ANIM_SPEED) % 2)
        bob = 1 if (tick // self.ANIM_SPEED) % 2 else 0
        surf.blit(img, (int(self.x - cam.ix) - img.get_width() // 2,
                        int(self.y - cam.iy) - img.get_height() // 2 + bob))


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
        surf.blit(img, (int(self.tx * TILE - cam.ix),
                        int((self.feet_row + 1) * TILE - img.get_height()
                            - cam.iy)))


class GoalGate:
    """Flag pole at the end of the level; touching it clears the course."""

    def __init__(self, tx, feet_row):
        self.tx = tx
        self.feet_row = feet_row
        y = (feet_row + 1) * TILE - 52
        self.rect = pygame.Rect(tx * TILE + 3, y, 10, 52)

    def draw(self, surf, cam, assets, tick):
        img = assets.goal_gate()
        surf.blit(img, (int(self.tx * TILE - 3 - cam.ix),
                        int((self.feet_row + 1) * TILE - img.get_height()
                            - cam.iy)))


class KeyShard:
    """Objective shard (3c): the goal stays locked until `required` of
    these are collected (item-flag BFS proves the count is reachable)."""

    ANIM_SPEED = 8

    def __init__(self, tx, ty):
        self.tx, self.ty = tx, ty
        self.x = tx * TILE + TILE // 2
        self.y = ty * TILE + TILE // 2
        self.rect = pygame.Rect(tx * TILE + 3, ty * TILE + 1, 10, 14)
        self.collected = False

    def draw(self, surf, cam, assets, tick):
        if self.collected:
            return
        img = assets.shard((tick // self.ANIM_SPEED) % 2)
        surf.blit(img, (int(self.x - cam.ix) - img.get_width() // 2,
                        int(self.y - cam.iy) - img.get_height() // 2))


class Switch:
    """Floor switch (Phase 3a): touching it latches its linked door(s) open.

    Validator contract: activating requires reaching the standable cell at
    (tx, feet_row); doors referencing this switch_id become passable only
    after that (conditional edges, §8.2).
    """

    def __init__(self, tx, feet_row, switch_id):
        self.tx = tx
        self.feet_row = feet_row
        self.switch_id = switch_id
        self.rect = pygame.Rect(tx * TILE + 2, (feet_row + 1) * TILE - 8,
                                TILE - 4, 8)
        self.active = False

    def draw(self, surf, cam, assets, tick):
        img = assets.switch_plate(self.active)
        surf.blit(img, (int(self.tx * TILE - cam.ix),
                        int((self.feet_row + 1) * TILE - 8 - cam.iy)))


class LatchedDoor:
    """A slab of DOOR tiles that opens permanently when its switch fires.

    The open/closed state lives in the object; `apply(level)` writes it into
    the tile map (same data-mutation pattern as Level.bump for bricks).
    """

    solver_opens = True         # validator may clear it in the proof graph

    def __init__(self, x0, y0, x1, y1, door_id, switch_id, opened=False):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.door_id = door_id
        self.switch_id = switch_id
        self.open = opened

    def cells(self):
        for ty in range(self.y0, self.y1 + 1):
            for tx in range(self.x0, self.x1 + 1):
                yield tx, ty

    def apply(self, level):
        """Write current open/closed state into the tile map."""
        from src.level import tiles as T
        tid = T.EMPTY if self.open else T.DOOR
        for tx, ty in self.cells():
            level.tiles.set(tx, ty, tid)

    def tick(self, level):
        """Latched doors never expire (uniform door contract)."""


class PressurePlate:
    """Floor plate (3b-1): touching it fires its plate_id — refreshing
    linked timed-door windows and latching linked doors open.

    Validator contract: plates share the switch press-cell space (a plate
    cell counts as a press point), but timed doors ignore the solver
    entirely (worst-case closed, D5).
    """

    def __init__(self, tx, feet_row, plate_id):
        self.tx = tx
        self.feet_row = feet_row
        self.plate_id = plate_id
        self.rect = pygame.Rect(tx * TILE + 1, (feet_row + 1) * TILE - 8,
                                TILE - 2, 8)
        self.active = False

    def draw(self, surf, cam, assets, tick):
        img = assets.plate(self.active)
        surf.blit(img, (int(self.tx * TILE - cam.ix),
                        int((self.feet_row + 1) * TILE - 8 - cam.iy)))


class FloorSpiker:
    """Spiked slab sliding along a floor track (3b-2 moving hazard).

    Spikes HURT (same as static spikes — playing routes non-lethal
    hazards to `_hurt`). Solver model: worst case = the slab is always
    somewhere on its track; `hazard_cells()` returns the full track band,
    which the validator overlays as a hazard (unstandable, walk edges
    refused, arcs must pass above — exactly the static-spike semantics).
    """

    lethal = False                 # uniform dynamic-hazard contract
    W = 16
    H = 16

    def __init__(self, x, y, span_px, speed):
        self.min = float(x)
        self.max = float(x) + span_px
        self.pos = float(x)
        self.y = float(y)
        self.speed = speed
        self.dir = 1

    def update(self):
        """Ping-pong along the track (mirrors MovingPlatform)."""
        self.pos += self.dir * self.speed
        if self.pos >= self.max:
            self.pos = self.max
            self.dir = -1
        elif self.pos <= self.min:
            self.pos = self.min
            self.dir = 1

    @property
    def rect(self):
        return pygame.Rect(int(self.pos), int(self.y), self.W, self.H)

    def hit_rect(self):
        """Runtime truth: where the slab is RIGHT NOW."""
        return self.rect

    def hazard_cells(self):
        """Worst-case band: every tile the slab can ever occupy."""
        x0, x1 = int(self.min), int(self.max) + self.W - 1
        y0, y1 = int(self.y), int(self.y) + self.H - 1
        cells = set()
        for ty in range(y0 // TILE, y1 // TILE + 1):
            for tx in range(x0 // TILE, x1 // TILE + 1):
                cells.add((tx, ty))
        return cells

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.spiker(tick // 6),
                  (int(self.pos) - cam.ix, int(self.y) - cam.iy))


class TimedDoor:
    """Door slab that opens for a window after its plate is pressed.

    D5: bonus loot only, NEVER on the required goal path — enforced by the
    validator (solver_opens=False: the proof treats it as solid forever).
    """

    solver_opens = False        # worst-case closed in the proof (D5)

    def __init__(self, x0, y0, x1, y1, door_id, plate_id,
                 duration=None):
        from src import config
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.door_id = door_id
        self.switch_id = plate_id      # shared id space for entity checks
        self.plate_id = plate_id
        self.duration = (config.TIMED_DOOR_TICKS if duration is None
                         else duration)
        self.open_until = 0
        self.open = False

    def cells(self):
        for ty in range(self.y0, self.y1 + 1):
            for tx in range(self.x0, self.x1 + 1):
                yield tx, ty

    def apply(self, level):
        from src.level import tiles as T
        tid = T.EMPTY if self.open else T.DOOR
        for tx, ty in self.cells():
            level.tiles.set(tx, ty, tid)

    def open_window(self, level):
        """(Re)start the open window and write it into the tiles."""
        self.open = True
        self.open_until = self.duration
        self.apply(level)

    def tick(self, level):
        if self.open:
            self.open_until -= 1
            if self.open_until <= 0:
                self.open = False
                self.apply(level)


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
        x = int(self.rect.x - cam.ix)
        y = int(self.rect.y - cam.iy)
        for i in range(0, self.length, TILE):
            surf.blit(seg, (x + i, y))
