"""
Seeded procedural level generator.

Levels are composed from a library of hand-authored chunks. Every chunk
respects the jump envelope derived from config physics (gaps <= SAFE_GAP_TILES,
step-ups <= SAFE_STEP_TILES), so composed levels are traversable by
construction; validator.py proves it afterwards with reachability search.

Determinism: same (seed, difficulty, level_index) -> identical level.
"""

import random

from src import config
from src.config import TILE, LEVEL_H_TILES, GROUND_ROW, MIN_FLOOR_ROW
from src.config import MAX_FLOOR_ROW, SAFE_GAP_TILES, SAFE_STEP_TILES
from src.level.level import Level
from src.level.objects import (Checkpoint, Coin, FloorSpiker, GoalGate,
                               KeyShard, LatchedDoor, MovingPlatform, Pipe,
                               PowerUp, PressurePlate, Switch, TimedDoor)
from src.level import tiles as T


def pick_enemy_kind(rng, diff, idx=0):
    """Choose an enemy kind appropriate for the difficulty.

    5a intro schedule: new types join the pool only once the run reaches
    their intro level (plan §5.5: Shieldkin 1-4 = idx 3, Bomber 2-1 = 5,
    Wallcrawler 2-3 = 7, Charger 3-1 = 10, Needler 3-3 = 12) AND the
    difficulty gate is met. Still exactly ONE rng.choice call, so the
    RNG stream consumption is unchanged.
    """
    pool = ["walker"]
    if diff >= 0.20:
        pool.append("shellback")
    if diff >= 0.35:
        pool.append("flyer")
    if diff >= 0.45:
        pool.append("spitter")
    if diff >= 0.50:
        pool.append("jumper")
    if diff >= 0.60:
        pool.append("chaser")
    if idx >= 3 and diff >= 0.25:
        pool.append("shieldkin")
    if idx >= 5 and diff >= 0.35:
        pool.append("bomber")
    if idx >= 7 and diff >= 0.40:
        pool.append("wallcrawler")
    if idx >= 10 and diff >= 0.50:
        pool.append("charger")
    if idx >= 12 and diff >= 0.55:
        pool.append("needler")
    return rng.choice(pool)


class Builder:
    """Cursor-based authoring helper writing into a Level."""

    def __init__(self, w, h, idx=0):
        self.level = Level(w, h)
        self.idx = idx              # level index for intro-schedule gates
        self.w = w
        self.h = h
        self.x = 0
        self.floor = GROUND_ROW
        self.warp_counter = 1

    # ------------------------------------------------------------ terrain
    def ground(self, n):
        for tx in range(self.x, min(self.x + n, self.w)):
            for ty in range(self.floor, self.h):
                self.level.tiles.set(tx, ty, T.SOLID)
        self.x = min(self.x + n, self.w)

    def pit(self, n):
        self.x = min(self.x + n, self.w)

    def step_up(self, rows=1):
        self.floor = max(MIN_FLOOR_ROW, self.floor - rows)

    def step_down(self, rows=1):
        self.floor = min(MAX_FLOOR_ROW, self.floor + rows)

    # ------------------------------------------------------------ objects
    def coin(self, tx, ty):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            self.level.coins.append(Coin(tx, ty))

    def coins_arc(self, tx0, n, base_row):
        """Coin arc rising over a gap of n columns starting at tx0."""
        for i in range(n):
            phase = (i + 0.5) / n
            lift = int(round(4 * phase * (1 - phase) * 4))  # 0..4 bump
            self.coin(tx0 + i, base_row - 2 - lift)

    def coins_row(self, tx0, n, row):
        for i in range(n):
            self.coin(tx0 + i, row)

    def enemy(self, kind, tx, solid_row=None):
        self.level.enemy_spawns.append((kind, tx, self.floor
                                        if solid_row is None else solid_row))

    def pipe(self, height, warp_id=None):
        top = self.floor - height
        if top < 2:
            top = 2
            height = self.floor - top
        tx = self.x
        for ty in range(self.floor, self.h):        # support under the pipe
            self.level.tiles.set(tx, ty, T.SOLID)
            self.level.tiles.set(tx + 1, ty, T.SOLID)
        self.level.tiles.set(tx, top, T.PIPE_TL)
        self.level.tiles.set(tx + 1, top, T.PIPE_TR)
        for ty in range(top + 1, self.floor):
            self.level.tiles.set(tx, ty, T.PIPE_BL)
            self.level.tiles.set(tx + 1, ty, T.PIPE_BR)
        self.level.pipes.append(Pipe(tx, top, height, warp_id))
        self.x = min(self.x + 2, self.w)
        return self.level.pipes[-1]

    def _fill_col(self, tx):
        for ty in range(self.floor, self.h):
            if self.level.tiles.get(tx, ty) == T.EMPTY:
                self.level.tiles.set(tx, ty, T.SOLID)

    def spikes(self, n):
        row = self.floor - 1
        for _ in range(n):
            if self.x < self.w:
                self._fill_col(self.x)
                self.level.tiles.set(self.x, row, T.SPIKE)
                self.x += 1

    def trench(self, n):
        """1-deep spike trench: digging one row down, spikes on the bottom."""
        for _ in range(n):
            if self.x < self.w:
                self._fill_col(self.x)
                self.level.tiles.set(self.x, self.floor, T.SPIKE)
                self.x += 1

    def platform(self, n, row):
        for i in range(n):
            tx = self.x + i
            for ty in range(row, row + 1):
                self.level.tiles.set(tx, ty, T.SOLID)
        self.x = min(self.x + n, self.w)

    def floating(self, tx0, n, row):
        for i in range(n):
            self.level.tiles.set(tx0 + i, row, T.SOLID)

    def mover(self, row, length_tiles, span_tiles, speed):
        m = MovingPlatform(self.x * TILE, row * TILE,
                           length_tiles * TILE, "x", span_tiles * TILE, speed)
        self.level.movers.append(m)
        return m

    def mover_y(self, row, length_tiles, span_tiles, speed):
        m = MovingPlatform(self.x * TILE, row * TILE,
                           length_tiles * TILE, "y", span_tiles * TILE, speed)
        self.level.movers.append(m)
        return m

    def flat(self, n, decor=True, rng=None):
        start = self.x
        if decor and rng is not None and n >= 4:
            if rng.random() < 0.35:
                bn = min(n - 3, rng.randint(3, 5))
                for i in range(bn):
                    tid = T.QUESTION if rng.random() < 0.45 else T.BRICK
                    self.level.tiles.set(start + 1 + i, self.floor - 4, tid)
            elif rng.random() < 0.5:
                self.coins_row(start + 1, min(n - 2, 4), self.floor - 3)
        self.ground(n)

    # ------------------------------------------------- switches and doors
    def switch(self, tx, row, switch_id):
        """Floor switch on an open standable cell (3a-2)."""
        if 0 <= tx < self.w and 1 <= row < self.h - 1:
            self.level.switches.append(Switch(tx, row, switch_id))

    def plate(self, tx, row, plate_id):
        """Pressure plate on an open standable cell (3b-1)."""
        if 0 <= tx < self.w and 1 <= row < self.h - 1:
            self.level.plates.append(PressurePlate(tx, row, plate_id))

    def lava_pit(self, n):
        """Lethal pool: LAVA at the floor surface over a solid base.

        Worst-case by construction: lava is never solid, so cells above a
        pool are unstandable and walk/fall edges refuse them (§8).
        """
        end = min(self.x + n, self.w)
        for tx in range(self.x, end):
            for ty in range(self.floor + 1, self.h):
                self.level.tiles.set(tx, ty, T.SOLID)
            self.level.tiles.set(tx, self.floor, T.LAVA)
        self.x = end

    def door_wall(self, col, y0, y1, door_id, switch_id):
        """Full-height wall at `col` (rows 0..floor-1) with a door slab
        y0..y1. Soundness: nothing may be jumped over a full-height wall
        (validator 3a-1 conditional edges enforce switch order)."""
        for ty in range(0, self.floor):
            self.level.tiles.set(col, ty, T.SOLID)
        for ty in range(y0, y1 + 1):
            self.level.tiles.set(col, ty, T.DOOR)
        self.level.doors.append(
            LatchedDoor(col, y0, col, y1, door_id, switch_id))

# ------------------------------------------------------------------ chunks
# Each chunk advances b.x and may adjust b.floor. Widths are hard-capped
# so the generator always keeps room for the goal area.

def chunk_flat(b, rng, diff):
    b.flat(rng.randint(5, 9), decor=True, rng=rng)


def chunk_gap(b, rng, diff):
    b.ground(rng.randint(2, 3))
    gap = rng.randint(2, min(SAFE_GAP_TILES, 2 + int(diff * 4)))
    start = b.x
    b.pit(gap)
    b.coins_arc(start, gap, b.floor)
    b.ground(rng.randint(4, 6))
    if diff > 0.35 and rng.random() < 0.5:
        b.enemy("walker", b.x - 2)


def chunk_steps_up(b, rng, diff):
    span = b.floor - MIN_FLOOR_ROW
    if span < 2:
        b.flat(5, decor=True, rng=rng)
        return
    n = rng.randint(2, min(SAFE_STEP_TILES, span))
    for _ in range(n):
        b.step_up()
        b.ground(rng.randint(2, 3))
    b.ground(2)


def chunk_steps_down(b, rng, diff):
    span = MAX_FLOOR_ROW - b.floor
    if span < 2:
        b.flat(5, decor=True, rng=rng)
        return
    n = rng.randint(2, min(SAFE_STEP_TILES, span))
    for _ in range(n):
        b.step_down()
        b.ground(rng.randint(2, 3))
    b.ground(2)


def chunk_pipes(b, rng, diff):
    b.ground(rng.randint(2, 3))
    do_warp = rng.random() < 0.5 and diff < 0.75
    warp = b.warp_counter if do_warp else None
    if do_warp:
        b.warp_counter += 1
    b.pipe(rng.randint(2, 3), warp)
    b.ground(rng.randint(3, 4))
    b.pipe(rng.randint(2, 3), warp)
    b.ground(rng.randint(3, 5))


def chunk_platform_steps(b, rng, diff):
    start = b.x
    total = rng.randint(9, 12)
    b.ground(total)
    p1 = b.floor - 4
    b.floating(start + 1, 3, p1)
    b.coins_row(start + 1, 3, p1 - 2)
    if total >= 9:
        b.floating(start + 5, 3, p1 - 1)
        b.coins_row(start + 5, 3, p1 - 3)


def chunk_island_chain(b, rng, diff):
    b.ground(rng.randint(2, 3))
    b.pit(rng.randint(2, 4))                 # ground -> island 1
    i1 = b.x
    h1 = rng.randint(2, 3)
    b.platform(h1, b.floor - 2)
    b.coins_row(i1, h1, b.floor - 4)
    b.pit(rng.randint(2, 4))                 # island 1 -> island 2
    h2 = rng.randint(2, 3)
    b.platform(h2, b.floor - 3)
    b.pit(rng.randint(2, 4))                 # island 2 -> landing
    b.ground(rng.randint(5, 6))
    if diff > 0.35 and rng.random() < 0.6:
        b.enemy("flyer", i1 + h1 + 1, b.floor - 3)


def chunk_spikes(b, rng, diff):
    b.ground(rng.randint(2, 3))
    if rng.random() < 0.5:
        n = rng.randint(1, 2)
        start = b.x
        b.spikes(n)
        b.coins_row(start, n, b.floor - 3)
    else:
        n = rng.randint(2, min(SAFE_GAP_TILES, 3 + int(diff * 3)))
        b.trench(n)
    b.ground(rng.randint(4, 6))
    if diff > 0.5 and rng.random() < 0.4:
        b.enemy("walker", b.x - 2)


def chunk_enemy_pack(b, rng, diff):
    start = b.x
    n = rng.randint(8, 10)
    b.ground(n)
    count = 1 + int(diff * 2.0)
    cols = (start + 2, start + 5, start + 8)
    for i in range(count):
        col = cols[i]
        if col < start + n - 1:
            b.enemy(pick_enemy_kind(rng, diff, b.idx), col)
    if rng.random() < 0.4:
        bn = min(4, n - 4)
        for i in range(bn):
            tid = T.QUESTION if rng.random() < 0.5 else T.BRICK
            b.level.tiles.set(start + 1 + i, b.floor - 4, tid)


def chunk_overhead(b, rng, diff):
    start = b.x
    n = rng.randint(6, 8)
    b.ground(n)
    bn = rng.randint(3, 5)
    for i in range(bn):
        tid = T.QUESTION if rng.random() < 0.5 else T.BRICK
        b.level.tiles.set(start + 2 + i, b.floor - 4, tid)
    b.coins_row(start + 2, bn, b.floor - 6)
    if diff > 0.25:
        b.enemy("walker", start + n - 2)


def chunk_moving_bridge(b, rng, diff):
    b.ground(rng.randint(2, 3))
    pit = rng.randint(7, 10)
    length = 3
    speed = round(1.0 + diff * 0.8 + rng.random() * 0.4, 2)
    start = b.x
    b.mover(b.floor, length, pit - length, speed)
    b.pit(pit)
    b.ground(rng.randint(5, 6))
    b.coins_row(start + 2, 3, b.floor - 3)


def chunk_door_gate(b, rng, diff):
    """Switch on the open floor latches open a full-height door wall.

    Soundness (3a-1): the switch sits BEFORE the wall on reachable ground,
    the wall blocks rows 0..floor-1 (nothing jumps over), and the slab
    matches the LatchedDoor footprint exactly.
    """
    b.ground(5)
    sw_col = b.x - 2
    sid = f"s{b.x}"
    did = f"d{b.x}"
    wall_col = b.x
    b.door_wall(wall_col, 9, b.floor - 1, did, sid)
    b.ground(1)                                # ground under the wall column
    b.switch(sw_col, b.floor - 1, sid)
    b.coins_row(wall_col + 1, 2, b.floor - 3)  # reward nudge behind the door
    b.ground(rng.randint(3, 5))


def chunk_door_switchback(b, rng, diff):
    """Door in a raised wall; its switch on the raised floor before it."""
    b.ground(3)
    b.step_up(2)
    b.ground(3)
    sw_col = b.x - 2
    sid = f"s{b.x}"
    did = f"d{b.x}"
    wall_col = b.x
    b.door_wall(wall_col, 9, b.floor - 1, did, sid)
    b.ground(1)
    b.switch(sw_col, b.floor - 1, sid)
    b.coins_row(wall_col + 1, 2, b.floor - 3)
    b.ground(rng.randint(3, 4))
    if diff > 0.5 and rng.random() < 0.5:
        b.step_down(2)
        b.ground(2)
        b.enemy("walker", b.x - 2)


def chunk_lava_crossing(b, rng, diff):
    """Leap a lava pool (<= SAFE_GAP). Lava is worst-case lethal (§8):
    cells above the pool are unstandable, so the proof only allows arcs
    that genuinely clear it."""
    b.ground(rng.randint(2, 3))
    n = rng.randint(3, 6)
    start = b.x
    b.lava_pit(n)
    b.coins_arc(start, n, b.floor)
    b.ground(rng.randint(4, 5))
    if diff > 0.6 and rng.random() < 0.4:
        b.enemy("walker", b.x - 3)


def chunk_floor_spiker(b, rng, diff):
    """A spiked slab patrols a short floor track; jump the whole band.

    Worst-case proof: the entire track is a hazard band (unstandable) —
    identical semantics to a static spike strip, so the fuzz proves it.
    Track span + 1 <= SAFE_GAP so the leap stays inside the envelope.
    """
    b.ground(rng.randint(2, 3))
    track = rng.randint(3, 5)                    # span+1 cols to cross: 4-6
    start = b.x
    b.ground(track + 1)
    speed = round(0.9 + diff * 0.5 + rng.random() * 0.3, 2)
    b.level.dynamic_hazards.append(
        FloorSpiker(start * TILE, b.floor * TILE - 16,
                    track * TILE - TILE, speed))
    b.coins_arc(start, track, b.floor)
    b.ground(rng.randint(4, 6))


def chunk_bonus_cache(b, rng, diff):
    """Floating loot island behind a timed door + pressure plate (D5).

    The flat goal path runs underneath and never needs the door; the
    validator treats the timed door as solid forever, so this content can
    never sit on the required path."""
    b.ground(10)
    plate_id = f"p{b.x}"
    did = f"td{b.x}"
    b.plate(b.x - 7, b.floor - 1, plate_id)
    ax = b.x - 5                                   # island columns ax..ax+3
    for tx in range(ax, ax + 4):
        for ty in (b.floor - 5, b.floor - 4):      # top cell = floor-6
            if 0 <= tx < b.w and 2 <= ty < b.h:
                b.level.tiles.set(tx, ty, T.SOLID)
    b.level.doors.append(TimedDoor(ax, b.floor - 7, ax, b.floor - 6,
                                   did, plate_id))
    b.level.tiles.set(ax, b.floor - 7, T.DOOR)
    b.level.tiles.set(ax, b.floor - 6, T.DOOR)
    b.coins_row(ax + 1, 2, b.floor - 6)


def chunk_rolling_hills(b, rng, diff):
    """Gentle one-row undulations with coin arcs on the crests."""
    b.ground(rng.randint(2, 3))
    steps = 1 if rng.random() < 0.5 else 2
    for _ in range(steps):
        b.step_up()
        b.coins_row(b.x, 2, b.floor - 3)
        b.ground(2)
    for _ in range(steps):
        b.step_down()
        b.ground(2)
    b.ground(2)


def chunk_twin_gaps(b, rng, diff):
    """Two short gaps with a safe landing pad between them."""
    b.ground(2)
    for _ in range(2):
        gap = rng.randint(2, 3)
        start = b.x
        b.pit(gap)
        b.coins_arc(start, gap, b.floor)
        b.ground(rng.randint(3, 4))
    b.ground(2)
    if diff > 0.35 and rng.random() < 0.5:
        kind = pick_enemy_kind(rng, diff, b.idx)
        b.enemy(kind, b.x - 2, b.floor - 3 if kind == "flyer" else None)


def chunk_high_ledge(b, rng, diff):
    """Floating ledge reached by a short staircase of step platforms."""
    start = b.x
    b.ground(3)
    b.pit(1)
    b.platform(2, b.floor - 2)
    b.platform(2, b.floor - 3)
    b.platform(3, b.floor - 4)
    b.coins_row(start + 8, 3, b.floor - 6)
    b.ground(2)


def chunk_pipe_trio(b, rng, diff):
    """Three pipes: a warp pair followed by a tall obstacle pipe."""
    b.ground(2)
    warp = b.warp_counter
    b.warp_counter += 1
    b.pipe(rng.randint(2, 3), warp)
    b.ground(rng.randint(3, 4))
    b.pipe(rng.randint(2, 3), warp)
    b.ground(rng.randint(3, 4))
    b.pipe(3, None)
    b.ground(rng.randint(3, 4))


def chunk_spike_trench_pair(b, rng, diff):
    """Two short spike trenches separated by safe pads."""
    b.ground(2)
    for _ in range(2):
        n = rng.randint(2, 3)
        start = b.x
        b.trench(n)
        b.coins_arc(start, n, b.floor)
        b.ground(rng.randint(3, 4))
    if diff > 0.35 and rng.random() < 0.6:
        kind = pick_enemy_kind(rng, diff, b.idx)
        b.enemy(kind, b.x - 2, b.floor - 3 if kind == "flyer" else None)


def chunk_ambush_steps(b, rng, diff):
    """Step up to a plateau holding an ambush, then step back down."""
    b.ground(2)
    steps = rng.randint(1, 2)
    for _ in range(steps):
        b.step_up()
        b.ground(2)
    plateau = rng.randint(4, 6)
    plateau_start = b.x
    b.ground(plateau)
    count = 1 + int(diff * 2.0)
    cols = (plateau_start + 1, plateau_start + 3, plateau_start + 5)
    for i in range(count):
        col = cols[i]
        if col < b.x - 1:
            kind = pick_enemy_kind(rng, diff, b.idx)
            b.enemy(kind, col, b.floor - 3 if kind == "flyer" else None)
    for _ in range(steps):
        b.step_down()
        b.ground(2)
    b.ground(2)


def chunk_gap_triple(b, rng, diff):
    """Three short gaps with short run-up pads between them."""
    b.ground(2)
    for _ in range(3):
        gap = rng.randint(2, 3)
        start = b.x
        b.pit(gap)
        b.coins_arc(start, gap, b.floor)
        b.ground(2)
    b.ground(2)


def chunk_lava_island_chain(b, rng, diff):
    """Lava pool, solid island, lava pool.

    The island is ordinary solid ground. The validator refuses cells above
    lava because lava is neither solid nor standable, so the only proven
    route is a real landing on the island.
    """
    b.ground(3)
    for i in range(2):
        n = rng.randint(3, 4)
        start = b.x
        b.lava_pit(n)
        b.coins_arc(start, n, b.floor)
        b.ground(3 if i == 0 else 4)


def chunk_double_gate(b, rng, diff):
    """Two latched door walls, each with its switch strictly before it."""
    b.ground(4)
    for _ in range(2):
        sid = f"s{b.x}"
        did = f"d{b.x}"
        wall_col = b.x
        b.door_wall(wall_col, 9, b.floor - 1, did, sid)
        b.ground(1)
        b.switch(wall_col - 2, b.floor - 1, sid)
        b.coins_row(wall_col + 1, 2, b.floor - 3)
        b.ground(3)


def chunk_vertical_bridge(b, rng, diff):
    """A y-axis moving lift connecting a low shelf to a high shelf.

    The validator already creates conservative ride edges for y-axis movers.
    This chunk deliberately leaves a one-column lift shaft so those virtual
    ride edges are present and connected to real standable cells.
    """
    b.ground(rng.randint(2, 3))
    b.step_down(4)
    lower_floor = b.floor
    b.ground(rng.randint(3, 4))

    lift_col = b.x
    upper_floor = max(MIN_FLOOR_ROW, lower_floor - 4)
    span = lower_floor - upper_floor
    if span <= 0:
        b.ground(4)
        return

    speed = round(0.8 + diff * 0.4 + rng.random() * 0.3, 2)
    b.mover_y(upper_floor, 3, span, speed)
    b.pit(1)
    b.step_up(span)
    b.ground(rng.randint(3, 4))


def chunk_spiker_double(b, rng, diff):
    """Two floor-spiker tracks separated by safe pads."""
    b.ground(2)
    for _ in range(2):
        track = rng.randint(3, 4)
        start = b.x
        b.ground(track + 1)
        speed = round(0.9 + diff * 0.5 + rng.random() * 0.3, 2)
        b.level.dynamic_hazards.append(
            FloorSpiker(start * TILE, b.floor * TILE - 16,
                        track * TILE - TILE, speed))
        b.coins_arc(start, track, b.floor)
        b.ground(2)


def _ground_enemy_kind(rng, diff, idx):
    """pick_enemy_kind() restricted to ground-safe kinds for showcase chunks."""
    kind = pick_enemy_kind(rng, diff, idx)
    if kind == "flyer":
        return "shellback" if diff >= 0.20 else "walker"
    return kind


def _battlement_enemy_kind(rng, diff, idx):
    """Prefer the intended battlement enemies when their intro gates allow."""
    if idx >= 5 and diff >= 0.35 and rng.random() < 0.5:
        return "bomber"
    if idx >= 3 and diff >= 0.25 and rng.random() < 0.5:
        return "shieldkin"
    return _ground_enemy_kind(rng, diff, idx)


def chunk_bomb_battlement(b, rng, diff):
    """Raised step with overhead bricks/coins and ground enemies on top."""
    b.ground(rng.randint(2, 3))
    b.step_up()
    step_len = rng.randint(4, 6)
    start = b.x
    b.ground(step_len)

    bn = rng.randint(3, 5)
    for i in range(bn):
        tid = T.QUESTION if rng.random() < 0.5 else T.BRICK
        b.level.tiles.set(start + 1 + i, b.floor - 4, tid)
    b.coins_row(start + 1, bn, b.floor - 6)

    count = 1 + int(diff * 2.0)
    cols = (start + 2, start + 4, start + 6)
    for i in range(count):
        col = cols[i]
        if col < start + step_len - 1:
            b.enemy(_battlement_enemy_kind(rng, diff, b.idx), col)

    b.ground(rng.randint(3, 4))
    b.step_down()
    b.ground(2)


# (fn, min difficulty, weight, max width in tiles)
# Slice 3 retunes these weights for pacing: low-difficulty levels are biased
# toward flat/gap/step teaching chunks, while high-difficulty levels lean on
# showcase/Tier 2 chunks. `_difficulty_weight()` applies the dynamic part;
# these table weights are the static baseline.
CHUNK_TABLE = [
    (chunk_flat,          0.00, 4.0,  9),
    (chunk_gap,           0.00, 3.0, 15),
    (chunk_steps_up,      0.00, 2.5, 16),
    (chunk_steps_down,    0.00, 2.5, 16),
    (chunk_pipes,         0.10, 1.5, 17),
    (chunk_platform_steps,0.15, 1.5, 12),
    (chunk_overhead,      0.15, 1.5,  8),
    (chunk_enemy_pack,    0.25, 2.5, 10),
    (chunk_spikes,        0.30, 1.5, 15),
    (chunk_island_chain,  0.45, 2.0, 27),
    (chunk_moving_bridge, 0.55, 2.0, 19),
    (chunk_door_gate,     0.25, 2.0, 12),
    (chunk_door_switchback, 0.35, 2.0, 15),
    (chunk_lava_crossing, 0.3, 1.5, 14),
    (chunk_bonus_cache,   0.35, 1.0, 12),
    (chunk_floor_spiker,  0.45, 1.5, 14),
    (chunk_rolling_hills, 0.00, 2.0, 14),
    (chunk_twin_gaps,     0.20, 1.5, 18),
    (chunk_high_ledge,    0.20, 1.5, 14),
    (chunk_pipe_trio,     0.15, 1.5, 20),
    (chunk_spike_trench_pair, 0.35, 1.5, 16),
    (chunk_ambush_steps,  0.30, 1.5, 18),
    (chunk_gap_triple,     0.50, 2.0, 22),
    (chunk_lava_island_chain, 0.55, 2.0, 24),
    (chunk_double_gate,    0.45, 2.0, 22),
    (chunk_vertical_bridge, 0.60, 2.0, 20),
    (chunk_spiker_double,  0.60, 2.0, 20),
    (chunk_bomb_battlement, 0.65, 2.0, 18),
]

MAX_CHUNK_USES = 3

TEACHING_CHUNKS = {
    chunk_flat,
    chunk_gap,
    chunk_steps_up,
    chunk_steps_down,
    chunk_rolling_hills,
}

BREATHER_CHUNKS = {
    chunk_flat,
    chunk_rolling_hills,
}

BREATHER_FALLBACKS = (
    chunk_flat,
    chunk_rolling_hills,
    chunk_steps_up,
    chunk_steps_down,
    chunk_gap,
)

HARD_SHOWCASE_CHUNKS = {
    fn for fn, min_diff, _weight, _max_w in CHUNK_TABLE if min_diff >= 0.45
}


def _difficulty_weight(fn, weight, diff):
    """Bias selection toward teaching early and showcase later."""
    if fn in TEACHING_CHUNKS:
        weight *= max(0.25, 1.0 - 0.75 * diff)
    elif fn in HARD_SHOWCASE_CHUNKS:
        weight *= 0.75 + 0.75 * diff
    return weight


def _used_weight(fn, weight, used):
    """Strong anti-fatigue penalty for chunks already used in this level."""
    if used >= MAX_CHUNK_USES:
        return 0.0
    if used == 2:
        return weight * 0.15
    if used == 1:
        return weight * 0.45
    return weight


def _chunk_available(fn, min_diff, max_w, diff, remaining, used):
    """Common availability rules for normal and forced chunk selection."""
    if used >= MAX_CHUNK_USES:
        return False
    if max_w > remaining and fn is not chunk_flat:
        return False
    if diff < min_diff and fn is not chunk_flat:
        return False
    if fn is chunk_flat and remaining < 4:
        return False
    return True


def _weighted_choice(rng, options):
    if not options:
        return None
    total = sum(weight for _, weight in options)
    if total <= 0:
        return None
    pick = rng.random() * total
    acc = 0.0
    for fn, weight in options:
        acc += weight
        if pick <= acc:
            return fn
    return options[-1][0]


def _choose_chunk(rng, diff, last_fn, remaining, used_counts=None):
    """Weighted random chunk choice restricted by budget and used counts."""
    used_counts = used_counts or {}
    options = []
    for fn, min_diff, weight, max_w in CHUNK_TABLE:
        used = used_counts.get(fn, 0)
        if not _chunk_available(fn, min_diff, max_w, diff, remaining, used):
            continue
        weight = _difficulty_weight(fn, weight, diff)
        weight = _used_weight(fn, weight, used)
        if fn is last_fn:
            weight *= 0.35                      # avoid repetition streaks
        if weight > 0:
            options.append((fn, weight))
    return _weighted_choice(rng, options)


def _choose_breather(rng, diff, last_fn, remaining, used_counts):
    """Force a low-intensity breather after a long non-flat run."""
    if remaining >= 4 and used_counts.get(chunk_flat, 0) < MAX_CHUNK_USES:
        return chunk_flat

    for fn in BREATHER_FALLBACKS:
        entry = next((row for row in CHUNK_TABLE if row[0] is fn), None)
        if entry is None:
            continue
        _fn, min_diff, _weight, max_w = entry
        used = used_counts.get(fn, 0)
        if _chunk_available(fn, min_diff, max_w, diff, remaining, used):
            return fn
    return None



def _sanitize(b, goal_tx):
    """Post-generation validity passes (spawn safety, clearance, dedupe)."""
    level = b.level
    tiles = level.tiles
    spawn_col = 2

    kept = []
    seen_cols = set()
    for kind, tx, srow in level.enemy_spawns:
        if not (spawn_col + 7 <= tx <= goal_tx - 3):
            continue
        if tx in seen_cols:
            continue
        if kind == "flyer":
            ok = all(not tiles.solid_at(tx + dx, srow + dy)
                     for dx in (-1, 0, 1) for dy in (-3, -2, -1, 0, 1))
        else:
            ok = (tiles.solid_at(tx, srow)
                  and not tiles.solid_at(tx, srow - 1)
                  and not tiles.solid_at(tx, srow - 2)
                  and not tiles.hazard_at(tx, srow - 1)
                  and not tiles.hazard_at(tx, srow))
        if ok:
            kept.append((kind, tx, srow))
            seen_cols.add(tx)
    level.enemy_spawns = kept

    # coins must not sit inside solid tiles
    seen = set()
    uniq = []
    for c in level.coins:
        key = (c.tx, c.ty)
        if key in seen or tiles.solid_at(c.tx, c.ty):
            continue
        seen.add(key)
        uniq.append(c)
    level.coins = uniq

    # warp exits: guarantee clear air above every pipe
    for pipe in level.pipes:
        for dy in (1, 2):
            for dx in (0, 1):
                if tiles.get(pipe.tx + dx, pipe.top_row - dy) in (
                        T.BRICK, T.QUESTION, T.USED):
                    tiles.set(pipe.tx + dx, pipe.top_row - dy, T.EMPTY)


def _place_powerups(b, seed):
    """Add bonus power-up pickups on a SEPARATE derived RNG stream.

    Determinism (D6/determinism contract): this runs after all geometry is
    finalised and reads the finished tile map only — it never consumes the
    geometry RNG, so the level hash is byte-identical with or without it.
    Power-ups are purely additive objects (like coins); the validator never
    sees them, so a no-power-up run stays completable by construction.
    """
    rng = random.Random(seed ^ 0x900D)
    level = b.level
    w, h = level.tiles.w, level.tiles.h
    count = rng.randint(1, 3)
    placed_cols = []
    attempts = 0
    while len(placed_cols) < count and attempts < 600:
        attempts += 1
        tx = rng.randint(12, max(12, w - 12))
        if any(abs(tx - c) < 6 for c in placed_cols):
            continue
        for r in range(4, h - 2):
            if (not level.tiles.solid_at(tx, r)
                    and not level.tiles.solid_at(tx, r - 1)
                    and level.tiles.solid_at(tx, r + 1)
                    and not level.tiles.hazard_at(tx, r)
                    and not level.tiles.hazard_at(tx, r - 1)):
                if rng.randint(1, config.POWERUP_HEART_CHANCE) == 1:
                    kind = "heart"
                else:
                    kind = rng.choice(("star", "speed", "jump"))
                level.powerups.append(PowerUp(tx, r, kind))
                placed_cols.append(tx)
                break


def _place_shards(b, seed, diff):
    """Objective shards (3c): SHARDS_PLACED across thirds of the level;
    required = min(SHARDS_REQUIRED, placed). Gated at diff >= 0.25
    (showcase rule, like doors).

    Reachability filter: the plain graph closure from spawn (doors closed,
    hazards worst-case, moving-hazard bands overlaid) — shards never land
    behind timed doors, inside bands, or on unreachable islands. Uses a
    SEPARATE derived RNG (2b pattern): the geometry stream is untouched.
    The validator re-proves the full objective regardless (fail-safe).
    """
    if diff < 0.25:
        return
    from collections import deque
    from src.level.validator import dynamic_hazard_cells, spawn_cell
    level = b.level
    w, h = level.tiles.w, level.tiles.h
    goal_tx = level.goal.tx if level.goal is not None else w - 6
    lo = max(6, level.spawn[0] // TILE + 5)
    hi = goal_tx - 6
    if hi - lo < 9:
        return
    rng = random.Random(seed ^ 0x53A1)
    band = dynamic_hazard_cells(level)      # worst-case moving-hazard band

    def crossable(tx, ty):
        return ((tx, ty) not in band
                and not level.tiles.solid_at(tx, ty)
                and not level.tiles.solid_at(tx, ty - 1)
                and level.tiles.solid_at(tx, ty + 1)
                and not level.tiles.hazard_at(tx, ty)
                and level.tiles.get(tx, ty) != T.DOOR)

    # Cheap conservative reach: walk/step BFS (jump-only islands are
    # skipped — false-negative-safe, and ~10x cheaper than build_graph).
    sc = spawn_cell(level)
    reach = set()
    if sc is not None and crossable(*sc):
        q = deque([sc])
        reach.add(sc)
        while q:
            cx, cy = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nc = (cx + dx, cy + dy)
                    if nc not in reach and 0 <= nc[0] < w and 2 <= nc[1] < h \
                            and crossable(*nc):
                        reach.add(nc)
                        q.append(nc)
    third = (hi - lo) // 3
    zones = [(lo, lo + third), (lo + third, lo + 2 * third),
             (lo + 2 * third, hi)]
    placed = 0
    for a, z in zones:
        cands = []
        for tx in range(a, max(a + 1, z)):
            for ty in range(2, h - 1):
                if ((tx, ty) in reach
                        and not level.tiles.solid_at(tx, ty)
                        and not level.tiles.solid_at(tx, ty - 1)
                        and level.tiles.solid_at(tx, ty + 1)
                        and not level.tiles.hazard_at(tx, ty)
                        and level.tiles.get(tx, ty) != T.DOOR):
                    cands.append((tx, ty))
        if cands:
            tx, ty = rng.choice(cands)
            level.key_shards.append(KeyShard(tx, ty))
            placed += 1
    level.required = min(config.SHARDS_REQUIRED, placed)


def _checkpoint_targets(w, goal_tx, screens):
    """Checkpoint ratios: 2 for short levels, 3 for long levels (Slice 5 D3)."""
    if screens > 10:
        ratios = (0.25, 0.50, 0.75)
    else:
        ratios = (0.38, 0.70)

    targets = []
    for ratio in ratios:
        col = int(w * ratio)
        if col < 8 or col >= goal_tx - 5:
            continue
        targets.append(col)
    return targets


def _checkpoint_candidate_cols(start, goal_tx, used_cols, min_gap,
                              local_radius=16):
    """Yield plausible checkpoint columns, preferring near the requested target."""
    def ok(c):
        if c in used_cols:
            return False
        if min_gap and any(abs(c - u) < min_gap for u in used_cols):
            return False
        return True

    local_end = min(start + local_radius, goal_tx - 3)
    for c in range(start, local_end):
        if ok(c):
            yield c

    for c in range(start, goal_tx - 3):
        if ok(c):
            yield c

    for c in range(start - 1, 7, -1):
        if ok(c):
            yield c


def _find_checkpoint_cell(level, start, goal_tx, used_cols, min_gap):
    """Find a safe standable checkpoint cell near `start`."""
    for c in _checkpoint_candidate_cols(start, goal_tx, used_cols, min_gap):
        for r in range(3, level.tiles.h - 2):
            if (not level.tiles.solid_at(c, r)
                    and not level.tiles.solid_at(c, r - 1)
                    and level.tiles.solid_at(c, r + 1)
                    and not level.tiles.hazard_at(c, r)
                    and not level.tiles.hazard_at(c, r - 1)):
                return c, r
    return None


def _place_checkpoints(b, goal_tx):
    level = b.level
    w = level.tiles.w
    screens = config.level_length_screens(
        config.zone_of(b.idx), config.zone_level_of(b.idx))

    used_cols = []
    for target in _checkpoint_targets(w, goal_tx, screens):
        cell = _find_checkpoint_cell(level, target, goal_tx, used_cols, 8)
        if cell is None:
            cell = _find_checkpoint_cell(level, target, goal_tx, used_cols, 0)
        if cell is None:
            continue
        c, r = cell
        level.checkpoints.append(Checkpoint(c, r))
        used_cols.append(c)

    level.checkpoints.sort(key=lambda cp: cp.tx)


def append_arena(b):
    """Boss arena carved into the level TAIL (5b). Does NOT change width.

    Invariants (plan §5.6, unit-tested): open entry corridor, >=2 jump
    heights of vertical dodge space (rows 2..11 cleared = 160 px), a
    >=6-tile flat runway, and no soft-lock geometry (flat floor; goal on
    the floor; the perch sits 2 rows up so the player walks under it).
    Objects inside the carve are dropped; switches/plates removed take
    their linked doors with them (validator never sees dangling ids).
    Deterministic: no RNG consumed.
    """
    lvl = b.level
    w = b.w
    x0 = w - config.ARENA_COLS
    ground = GROUND_ROW

    lvl.coins = [c for c in lvl.coins if not (x0 <= c.tx < w)]
    lvl.powerups = [p for p in lvl.powerups if not (x0 <= p.tx < w)]
    lvl.key_shards = [k for k in lvl.key_shards if not (x0 <= k.tx < w)]
    lvl.checkpoints = [c for c in lvl.checkpoints
                       if not (x0 <= getattr(c, "tx", -9) < w)]
    lvl.enemy_spawns = [s for s in lvl.enemy_spawns
                        if not (x0 <= s[1] < w)]
    removed_ids = set()
    keep = []
    for sw in lvl.switches:
        if x0 <= sw.tx < w:
            removed_ids.add(sw.switch_id)
        else:
            keep.append(sw)
    lvl.switches = keep
    keep = []
    for pl in lvl.plates:
        if x0 <= pl.tx < w:
            removed_ids.add(pl.plate_id)
        else:
            keep.append(pl)
    lvl.plates = keep
    keep = []
    for d in lvl.doors:
        inside = any(x0 <= cx < w for cx, _cy in d.cells())
        if inside or d.switch_id in removed_ids:
            for cx, cy in d.cells():
                lvl.tiles.set(cx, cy, T.EMPTY)
        else:
            keep.append(d)
    lvl.doors = keep
    lvl.movers = [m for m in lvl.movers
                  if not (x0 * TILE <= getattr(m, "x", -999) < w * TILE)]
    lvl.dynamic_hazards = [hz for hz in lvl.dynamic_hazards
                           if not (x0 <= getattr(hz, "tx", -9) < w)]

    for tx in range(x0, w):
        for ty in range(2, ground):
            lvl.tiles.set(tx, ty, T.EMPTY)
        for ty in range(ground, lvl.tiles.h):
            lvl.tiles.set(tx, ty, T.SOLID)
    px0 = x0 + (config.ARENA_COLS - 4) // 2
    for tx in range(px0, px0 + 4):
        lvl.tiles.set(tx, ground - 3, T.SOLID)   # dodge perch (walk-under)

    lvl.has_arena = True
    lvl.arena_x0 = x0


# Zone-final bosses (5c) — original designs, spawned ONLY via arenas.
BOSS_KINDS = ("boulder_brute", "crystal_golem", "warden_owl",
              "magma_monarch")


def _place_boss(b, level_index):
    """Zone-final arenas spawn their zone's boss and lock the goal (5c).

    The validator still proves arena TRAVERSAL only — beating the boss is
    a runtime concern proven by scripted-sim fight tests (plan §8.7
    documented limitation).
    """
    lvl = b.level
    zone = config.zone_of(level_index) % len(BOSS_KINDS)
    kind = BOSS_KINDS[zone]
    cx = lvl.arena_x0 + 2          # clear of the dodge perch (cols +6..+9)
    lvl.enemy_spawns.append((kind, cx, GROUND_ROW))
    if kind == "crystal_golem":
        from src.level.objects import Switch
        lvl.switches.append(
            Switch(lvl.arena_x0 + 3, GROUND_ROW - 1, "boss_sw0"))
        lvl.switches.append(
            Switch(lvl.arena_x0 + config.ARENA_COLS - 4,
                   GROUND_ROW - 1, "boss_sw1"))
    lvl.boss_required = True


def _fill_remaining(b):
    """Last-resort safe filler when the normal chunk pool is exhausted.

    This is intentionally not part of `CHUNK_TABLE` and is not traced as a
    gameplay chunk: its only job is to avoid leaving a huge flat runway when a
    long level has legitimately used up its allowed chunk budget. It cycles a
    few conservative, validator-safe terrain variations instead of repeating one
    pattern.
    """
    pattern = 0
    while b.x < b.w - 24:
        remaining = b.w - 24 - b.x
        if remaining <= 6:
            b.ground(remaining)
            break

        # Keep the filler at the base floor so the tiny patterns below remain
        # predictable for the validator and player.
        while b.floor < GROUND_ROW:
            b.step_down()
            b.ground(2)
        while b.floor > GROUND_ROW:
            b.step_up()
            b.ground(2)

        remaining = b.w - 24 - b.x
        if remaining <= 6:
            b.ground(remaining)
            break

        # Near the reserved goal run-in, put compact safe features close to the
        # end so the filler does not hand off into another long flat runway.
        if remaining <= 16:
            if remaining >= 10:
                b.ground(2)
                b.pit(2)
                b.ground(2)
                b.pit(2)
                b.ground(remaining - 8)
            else:
                b.ground(2)
                b.pit(2)
                b.ground(remaining - 4)
            break

        kind = pattern % 4
        pattern += 1
        if kind == 0:
            # Short safe ditch.
            b.ground(2)
            b.pit(2)
            b.ground(3)
        elif kind == 1:
            # One-tile mound.
            b.ground(2)
            b.step_up()
            b.ground(2)
            b.step_down()
            b.ground(3)
        elif kind == 2:
            # Walk-under overhead bump.
            b.ground(2)
            b.floating(b.x, 3, b.floor - 3)
            b.ground(4)
        else:
            # One-tile safe trench.
            b.ground(2)
            b.step_down()
            b.ground(2)
            b.step_up()
            b.ground(3)


def generate_level(seed, difficulty, level_index=0):
    """Build a deterministic level. Same inputs -> byte-identical level."""
    rng = random.Random(seed)
    diff = max(0.0, min(1.0, float(difficulty)))
    target = (config.level_length_screens(
        config.zone_of(level_index),
        config.zone_level_of(level_index)) * config.TILES_PER_SCREEN)
    w = target + 18
    b = Builder(w, LEVEL_H_TILES, level_index)

    # --- safe start area -------------------------------------------------
    b.ground(8)
    b.level.spawn = (2 * TILE + 2, GROUND_ROW * TILE - config.PLAYER_H)
    b.level.respawn = b.level.spawn

    # --- stitch chunks ---------------------------------------------------
    last_fn = None
    used_counts = {}
    chunk_trace = []
    non_flat_streak = 0
    breathers_exhausted = False
    while b.x < w - 24:
        remaining = (w - 24) - b.x
        fn = None
        if non_flat_streak >= 5 and not breathers_exhausted:
            fn = _choose_breather(rng, diff, last_fn, remaining, used_counts)
            if fn is None:
                # Slice 8: no gentle breather is left, but the level is not
                # finished. Continue with normal chunk selection instead of
                # leaving a huge flat filler tail.
                breathers_exhausted = True
        if fn is None:
            fn = _choose_chunk(rng, diff, last_fn, remaining, used_counts)
        if fn is None:
            _fill_remaining(b)
            break
        fn(b, rng, diff)
        last_fn = fn
        used_counts[fn] = used_counts.get(fn, 0) + 1
        chunk_trace.append(fn.__name__)
        if fn in BREATHER_CHUNKS:
            non_flat_streak = 0
        else:
            non_flat_streak += 1
    b.level.chunk_trace = chunk_trace

    # --- ramp back to base ground level, then flat run-in to the goal ----
    while b.floor < GROUND_ROW:
        b.step_down()
        b.ground(2)
    while b.floor > GROUND_ROW:
        b.step_up()
        b.ground(2)
    b.ground(w - b.x)

    goal_tx = w - 6
    b.level.goal = GoalGate(goal_tx, GROUND_ROW - 1)

    _place_checkpoints(b, goal_tx)
    _sanitize(b, goal_tx)
    _place_powerups(b, seed)
    if config.zone_level_of(level_index) == config.LEVELS_PER_ZONE - 1:
        append_arena(b)              # zone-final tail (before shards so
        _place_boss(b, level_index)  # required never exceeds placement)
    _place_shards(b, seed, diff)

    b.level.seed = seed
    b.level.difficulty = diff
    b.level.level_index = level_index
    return b.level


def template_level(difficulty=0.5, level_index=0):
    """Known-good hand-authored fallback; guaranteed validator-passing."""
    w = (config.level_length_screens(
        config.zone_of(level_index),
        config.zone_level_of(level_index)) * config.TILES_PER_SCREEN + 18)
    b = Builder(w, LEVEL_H_TILES, level_index)
    b.ground(8)
    b.level.spawn = (2 * TILE + 2, GROUND_ROW * TILE - config.PLAYER_H)
    b.level.respawn = b.level.spawn

    b.ground(6)                       # flat run-in
    start = b.x
    b.pit(3)                          # simple, well within envelope
    b.coins_arc(start, 3, b.floor)
    b.ground(8)
    b.enemy("walker", b.x - 4)
    b.ground(4)
    b.step_up()
    b.ground(3)
    b.step_up()
    b.ground(5)
    b.step_down()
    b.ground(3)
    b.step_down()
    b.ground(6)
    b.spikes(2)                       # hop over
    b.ground(6)
    b.enemy("shellback", b.x - 3)
    b.ground(4)
    b.enemy("flyer", b.x - 3, b.floor - 3)
    b.ground(max(6, w - b.x))

    goal_tx = w - 6
    b.level.goal = GoalGate(goal_tx, GROUND_ROW - 1)
    _place_checkpoints(b, goal_tx)
    _sanitize(b, goal_tx)
    _place_powerups(b, -1)
    b.level.seed = -1
    b.level.difficulty = max(0.0, min(1.0, difficulty))
    b.level.level_index = level_index
    return b.level


