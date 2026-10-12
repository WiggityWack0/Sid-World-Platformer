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
from src.level.objects import Checkpoint, Coin, GoalGate, MovingPlatform, Pipe
from src.level import tiles as T


def pick_enemy_kind(rng, diff):
    """Choose an enemy kind appropriate for the difficulty."""
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
    return rng.choice(pool)


class Builder:
    """Cursor-based authoring helper writing into a Level."""

    def __init__(self, w, h):
        self.level = Level(w, h)
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
            b.enemy(pick_enemy_kind(rng, diff), col)
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


# (fn, min difficulty, weight, max width in tiles)
CHUNK_TABLE = [
    (chunk_flat,          0.00, 3.0,  9),
    (chunk_gap,           0.00, 3.0, 15),
    (chunk_steps_up,      0.00, 2.0, 16),
    (chunk_steps_down,    0.00, 2.0, 16),
    (chunk_pipes,         0.10, 2.0, 17),
    (chunk_platform_steps,0.15, 2.0, 12),
    (chunk_overhead,      0.15, 2.0,  8),
    (chunk_enemy_pack,    0.25, 3.0, 10),
    (chunk_spikes,        0.30, 2.0, 15),
    (chunk_island_chain,  0.45, 2.0, 27),
    (chunk_moving_bridge, 0.55, 2.0, 19),
]

def _choose_chunk(rng, diff, last_fn, remaining):
    """Weighted random chunk choice restricted by remaining budget."""
    options = []
    for fn, min_diff, weight, max_w in CHUNK_TABLE:
        if max_w > remaining and fn is not chunk_flat:
            continue
        if diff < min_diff and fn is not chunk_flat:
            continue
        if fn is chunk_flat and remaining < 4:
            continue
        if fn is last_fn:
            weight *= 0.35                      # avoid repetition streaks
        options.append((fn, weight))
    if not options:
        return None
    total = sum(w for _, w in options)
    pick = rng.random() * total
    acc = 0.0
    for fn, weight in options:
        acc += weight
        if pick <= acc:
            return fn
    return options[-1][0]


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


def _place_checkpoints(b, goal_tx):
    level = b.level
    w = level.tiles.w
    for col in (int(w * 0.38), int(w * 0.70)):
        if col >= goal_tx - 5:
            continue
        for c in range(col, min(col + 8, goal_tx - 3)):
            for r in range(3, level.tiles.h - 2):
                if (not level.tiles.solid_at(c, r)
                        and not level.tiles.solid_at(c, r - 1)
                        and level.tiles.solid_at(c, r + 1)
                        and not level.tiles.hazard_at(c, r)
                        and not level.tiles.hazard_at(c, r - 1)):
                    level.checkpoints.append(Checkpoint(c, r))
                    break
            else:
                continue
            break


def generate_level(seed, difficulty, level_index=0):
    """Build a deterministic level. Same inputs -> byte-identical level."""
    rng = random.Random(seed)
    diff = max(0.0, min(1.0, float(difficulty)))
    target = (config.START_LEN_SCREENS
              + level_index * config.LEN_GROWTH) * config.TILES_PER_SCREEN
    w = target + 18
    b = Builder(w, LEVEL_H_TILES)

    # --- safe start area -------------------------------------------------
    b.ground(8)
    b.level.spawn = (2 * TILE + 2, GROUND_ROW * TILE - config.PLAYER_H)
    b.level.respawn = b.level.spawn

    # --- stitch chunks ---------------------------------------------------
    last_fn = None
    while b.x < w - 24:
        remaining = (w - 24) - b.x
        fn = _choose_chunk(rng, diff, last_fn, remaining)
        if fn is None:
            break
        fn(b, rng, diff)
        last_fn = fn

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

    b.level.seed = seed
    b.level.difficulty = diff
    b.level.level_index = level_index
    return b.level


def template_level(difficulty=0.5, level_index=0):
    """Known-good hand-authored fallback; guaranteed validator-passing."""
    w = (config.START_LEN_SCREENS
         + level_index * config.LEN_GROWTH) * config.TILES_PER_SCREEN + 18
    b = Builder(w, LEVEL_H_TILES)
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
    b.level.seed = -1
    b.level.difficulty = max(0.0, min(1.0, difficulty))
    b.level.level_index = level_index
    return b.level


