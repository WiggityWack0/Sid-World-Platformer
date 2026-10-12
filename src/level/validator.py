"""
Completable-ness validator.

Builds a reachability graph over standable tiles using the SAME physics
constants the game runs on (jump envelope derived from config) and proves
a path from spawn to goal via BFS. Also validates entity placement rules
and provides ensure_level() which regenerates on failure and falls back
to a known-good template level.
"""

import math

from src import config

EPS = 1e-7
from src.config import TILE, UP_TILES, DIST_TILES, MAX_FALL_DRIFT_TILES


def standable(tiles, tx, ty):
    """A cell where the player can stand (feet cell)."""
    if ty < 1 or ty >= tiles.h:
        return False
    if tiles.solid_at(tx, ty) or tiles.solid_at(tx, ty - 1):
        return False
    if not tiles.solid_at(tx, ty + 1):
        return False
    if tiles.hazard_at(tx, ty) or tiles.hazard_at(tx, ty - 1):
        return False
    return True


def collect_standables(level):
    tiles = level.tiles
    return {(tx, ty)
            for ty in range(1, tiles.h)
            for tx in range(tiles.w)
            if standable(tiles, tx, ty)}


def _clear(tiles, tx, ty0, ty1):
    """Column tx has no solid/hazard in rows ty0..ty1."""
    if ty0 > ty1:
        return True
    for ty in range(max(0, ty0), min(tiles.h, ty1 + 1)):
        if tiles.solid_at(tx, ty) or tiles.hazard_at(tx, ty):
            return False
    return True


def _arc_vy(surface, target_surface, dist_px):
    """Initial upward speed (px/tick) to land at dist_px on target_surface."""
    t = dist_px / config.MAX_RUN
    if t <= 0.0:
        return None
    dy_up = surface - target_surface
    vy = (dy_up + 0.5 * config.GRAVITY * t * t) / t
    if vy < 0.3 or vy > abs(config.JUMP_VELOCITY) + 1e-6:
        return None
    return vy


def _body_hits(tiles, left, feet_y, w, h):
    """Does a w x h body at (left, feet_y-h) overlap any solid tile?"""
    top = feet_y - h
    x0 = int(left // TILE)
    x1 = int((left + w - 1) // TILE)
    y0 = int(top // TILE)
    y1 = int((feet_y - 1) // TILE)
    for ty in range(max(0, y0), min(tiles.h, y1 + 1)):
        for tx in range(x0, x1 + 1):
            if tiles.solid_at(tx, ty):
                return True
    return False


def _jump_ok(tiles, x, r, nx, nr):
    """Trajectory-verified jump edge: simulate the arc with config physics."""
    if abs(nx - x) > DIST_TILES or nx == x:
        return False
    if nr <= r and r - nr > UP_TILES:
        return False
    if nr > r and nr - r > 4:
        return False

    w, h = config.PLAYER_W, config.PLAYER_H
    surface = (r + 1) * TILE
    tsurf = (nr + 1) * TILE
    direction = 1 if nx > x else -1
    # launch from the cell end in the direction of travel (matches how
    # the scripted runner accelerates to the cell edge before jumping)
    x0 = float(x * TILE + (TILE - w if direction > 0 else 0))
    target_center = nx * TILE + (TILE - w) / 2.0
    dist = abs(target_center - x0)
    vy = _arc_vy(surface, tsurf, dist)
    if vy is None:
        return False

    dy_up = surface - tsurf
    speed = config.MAX_RUN
    x_sim = x0
    max_rise = 0.0
    max_t = int(dist / speed) + 24
    for tick in range(0, max_t):
        feet = surface - (vy * tick - 0.5 * config.GRAVITY * tick * tick)
        rise = surface - feet
        if rise > max_rise:
            max_rise = rise
        # land on whatever floor the body has penetrated (tick quantisation)
        foot_row = int(feet // TILE)
        lx0 = int(x_sim // TILE)
        lx1 = int((x_sim + w - 1) // TILE)
        penetrates = feet > foot_row * TILE and any(
            tiles.solid_at(c, foot_row) for c in range(lx0, lx1 + 1))
        if penetrates:
            feet = float(foot_row * TILE)
            mid_col = int((x_sim + w / 2.0) // TILE)
            if mid_col not in (x, nx):
                return False                  # landed short on other ground
            over_target = lx0 <= nx <= lx1
            return over_target
        if _body_hits(tiles, x_sim, feet, w, h):
            return False                      # clipped geometry: infeasible
        # spikes hurt even though they are not solid
        h0 = int(math.floor((feet - h) / TILE))
        h1 = int(math.floor((feet - EPS) / TILE))
        for c in range(lx0, lx1 + 1):
            for hr in range(max(0, h0), min(tiles.h, h1 + 1)):
                if tiles.hazard_at(c, hr) and feet > hr * TILE + 7:
                    return False
        # advance, blocked by walls (wall-assisted climb)
        trial = x_sim + direction * speed
        if not _body_hits(tiles, trial, feet, w, h):
            x_sim = trial
        # success: at target height while over the target cell
        over_target = int(x_sim // TILE) <= nx <= int((x_sim + w - 1) // TILE)
        at_height = feet >= tsurf - 0.5
        peaked = dy_up <= 0 or max_rise > dy_up + 1
        if over_target and at_height and peaked:
            if _body_hits(tiles, x_sim, feet, w, h):
                return False
            return True
    return False



def _fall_ok(tiles, x, r, nx, nr):
    if nr <= r or nx == x:
        return False
    # how far a running player can drift while falling nr - r rows
    d_r = nr - r
    t_fall = math.sqrt(2.0 * d_r * TILE / config.GRAVITY)
    max_drift = max(1, int(math.ceil(config.MAX_RUN * t_fall / TILE)))
    if abs(nx - x) > max_drift:
        return False
    if not _clear(tiles, x, r - 1, r - 1):      # headroom at the ledge
        return False
    step = 1 if nx > x else -1
    for cx in range(x + step, nx, step):         # intermediate columns
        if not _clear(tiles, cx, r - 1, nr - 1):
            return False
    if not _clear(tiles, nx, r - 1, nr - 1):     # target column
        return False
    return True


# ------------------------------------------------------------- graph/BFS

def spawn_cell(level):
    x, y = level.spawn
    tx = int(x + config.PLAYER_W // 2) // TILE
    ty = int(y + config.PLAYER_H) // TILE - 1
    return tx, ty


def goal_cell(level):
    if level.goal is None:
        return None
    return level.goal.tx, level.goal.feet_row


def build_graph(level):
    """Reachability graph: dict node -> list of reachable nodes.

    Real nodes are (tx, ty) standable cells; moving platforms add virtual
    nodes ("mv", index, end) representing riding the platform.
    """
    tiles = level.tiles
    cells = collect_standables(level)
    adj = {c: [] for c in cells}

    for x, r in cells:
        for nx in (x - 1, x + 1):                # walking
            if (nx, r) in cells:
                adj[(x, r)].append((nx, r))
        for nx in range(x - DIST_TILES, x + DIST_TILES + 1):   # jumping
            if nx == x:
                continue
            for nr in range(max(0, r - UP_TILES), min(tiles.h, r + 5)):
                if (nx, nr) in cells and _jump_ok(tiles, x, r, nx, nr):
                    adj[(x, r)].append((nx, nr))
            for nr in range(r + 1, min(tiles.h, r + 7)):          # falling
                if (nx, nr) in cells and _fall_ok(tiles, x, r, nx, nr):
                    adj[(x, r)].append((nx, nr))

    # moving platforms: ride edges (time-independent conservative model)
    for i, m in enumerate(level.movers):
        v_left = ("mv", i, "L")
        v_right = ("mv", i, "R")
        adj.setdefault(v_left, []).append(v_right)
        adj.setdefault(v_right, []).append(v_left)
        if m.axis == "x":
            left_col = int(m.min) // TILE
            right_col = int(m.max + m.length - 1) // TILE
            rf = m.rect.y // TILE - 1
            ends = ((left_col, rf, v_left), (right_col, rf, v_right))
        else:
            col = m.rect.x // TILE
            r_top = int(m.min) // TILE - 1
            r_bot = int(m.max) // TILE - 1
            ends = ((col, r_top, v_left), (col, r_bot, v_right))
        for cx, cr, node in ends:
            for sx, sr in cells:
                if abs(sx - cx) <= 2 and abs(sr - cr) <= 1:
                    adj[(sx, sr)].append(node)
                    adj[node].append((sx, sr))
    return cells, adj


def path_between(adj, start, goal):
    """BFS path start -> goal as a list of nodes, or None."""
    if start == goal:
        return [start]
    from collections import deque
    prev = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in adj.get(node, ()):
            if nxt in prev:
                continue
            prev[nxt] = node
            if nxt == goal:
                path = [goal]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                path.reverse()
                return path
            queue.append(nxt)
    return None

    return True


# ------------------------------------------------------- entity validation

def _check_entities(level):
    tiles = level.tiles
    goal = goal_cell(level)
    goal_tx = goal[0] if goal else tiles.w - 6

    for pipe in level.pipes:
        bottom = pipe.top_row + pipe.height
        if not (tiles.solid_at(pipe.tx, bottom)
                and tiles.solid_at(pipe.tx + 1, bottom)):
            return f"pipe at col {pipe.tx} floating"
        if pipe.warp_id is not None:
            partners = [p for p in level.pipes
                        if p.warp_id == pipe.warp_id and p is not pipe]
            if not partners:
                return f"warp pipe {pipe.warp_id} unpaired"

    for kind, tx, srow in level.enemy_spawns:
        if not (0 <= tx < tiles.w and 1 <= srow < tiles.h):
            return f"enemy out of bounds at {tx},{srow}"
        if tx == goal_tx:
            return f"enemy on goal at {tx},{srow}"
        if kind == "flyer":
            if any(tiles.solid_at(tx + dx, srow + dy)
                   for dx in (-1, 0, 1) for dy in (-3, -2, -1, 0, 1)):
                return f"flyer blocked at {tx},{srow}"
        else:
            if not tiles.solid_at(tx, srow):
                return f"enemy floating at {tx},{srow}"
            if tiles.solid_at(tx, srow - 1) or tiles.solid_at(tx, srow - 2):
                return f"enemy inside wall at {tx},{srow}"
            if tiles.hazard_at(tx, srow - 1):
                return f"enemy on hazard at {tx},{srow}"

    for coin in level.coins:
        if tiles.solid_at(coin.tx, coin.ty):
            return f"coin inside wall at {coin.tx},{coin.ty}"

    for m in level.movers:
        if m.rect.left < 0 or m.rect.right > level.width:
            return "moving platform out of bounds"

    if tiles.w < 30:
        return "level too short"
    return None


def validate(level):
    """Return (ok, reason): is the level provably start->goal completable?"""
    if level.goal is None:
        return False, "no goal gate"
    err = _check_entities(level)
    if err is not None:
        return False, err

    cells, adj = build_graph(level)
    start = spawn_cell(level)
    goal = goal_cell(level)
    if start not in cells:
        return False, f"spawn not standable {start}"
    if goal not in cells:
        return False, f"goal not standable {goal}"
    if path_between(adj, start, goal) is None:
        return False, "no path from spawn to goal"
    return True, ""


def ensure_level(seed, difficulty, level_index=0, attempts=20):
    """Generate with retries; fall back to the known-good template."""
    from src.level.generator import generate_level, template_level

    for i in range(attempts):
        lvl = generate_level(seed + i * 7919, difficulty, level_index)
        ok, _reason = validate(lvl)
        if ok:
            lvl.validated = True
            return lvl
    lvl = template_level(difficulty, level_index)
    ok, reason = validate(lvl)
    if not ok:                                   # pragma: no cover - fatal
        raise RuntimeError(f"template level invalid: {reason}")
    lvl.validated = True
    lvl.used_fallback = True
    return lvl


# ------------------------------------------------- headless physics playtest

def simulate_perfect_run(level, max_frames=30000, verbose=False):
    """Scripted runner driving the REAL Player physics to the goal.

    Uses the validator's BFS path as waypoints and picks an initial jump
    velocity from the closed-form ballistic solution of config physics, so
    this verifies actual collision/integration behaviour end to end.
    """
    from src.player import Player, Input

    cells, adj = build_graph(level)
    start = spawn_cell(level)
    goal = goal_cell(level)
    if start not in cells or goal not in cells:
        return False

    player = Player(*level.spawn)
    inp = Input()
    inp.right = True
    inp.run = True
    goal_rect = level.goal.rect

    cached_cell, cached_path = None, None
    mode = "run"                 # run | wait_board
    blocked_frames = 0
    no_progress = 0
    last_x = player.x
    history = []
    stuck_anchor = player.x
    jump_armed = True

    def feet_cell():
        cx = int(player.x + config.PLAYER_W // 2) // TILE
        cy = int(player.y + config.PLAYER_H) // TILE - 1
        if (cx, cy) in cells:
            return (cx, cy)
        for dx in (1, -1, 2, -2):
            for dy in (0, -1, 1):
                if (cx + dx, cy + dy) in cells:
                    return (cx + dx, cy + dy)
        return None

    def platform_under():
        for m in level.movers:
            if (player.rect.bottom == m.rect.top
                    and player.rect.right > m.rect.left
                    and player.rect.left < m.rect.right):
                return m
        return None

    frames = 0
    while frames < max_frames:
        frames += 1
        level.update()                      # moving platforms advance
        if player.rect.colliderect(goal_rect):
            return True

        if player.on_ground or player.coyote > 0:
            if player.on_ground:
                jump_armed = True
            m = platform_under()
            if m is not None:
                # ---- riding: hug right edge, step off when a ledge is near
                inp.left = False
                if m.axis == "x":
                    p_row = m.rect.y // TILE - 1
                    disembark = any(
                        sr == p_row and -8 <= sx * TILE - m.rect.right <= 12
                        for sx, sr in cells)
                    at_edge = player.rect.right >= m.rect.right - 6
                    inp.right = (not at_edge) or disembark
                    mode = "riding"
                else:                              # vertical platform
                    near_end = (abs(m.pos - m.min) < m.speed + 1
                                or abs(m.pos - m.max) < m.speed + 1)
                    inp.right = near_end
                events = player.update(inp, level)
                if events and any(e[0] in ("pit", "hazard") for e in events):
                    return False
                if player.dead:
                    return False
                continue

            cell = feet_cell()
            if cell is None:
                inp.right = True                # recovering: shuffle
                inp.left = False
                events = player.update(inp, level)
                if player.dead:
                    return False
                continue
            if cell != cached_cell:
                cached_cell = cell
                cached_path = path_between(adj, cell, goal)
                mode = "run"
            path = cached_path
            if not path:
                return False
            nxt = path[1] if len(path) > 1 else path[-1]

            if isinstance(nxt[0], str):            # board a moving platform
                mode = "wait_board"
                i, end = nxt[1], nxt[2]
                mv = level.movers[i]
                if mv.axis == "y":
                    inp.right = False
                else:
                    if end == "L":
                        pit_edge = mv.min
                        gap = mv.rect.left - player.rect.right
                    else:
                        pit_edge = mv.max + mv.length
                        gap = pit_edge - player.rect.right
                    # only step off when the platform is basically touching
                    # the lip (within a small step); the gap is empty air
                    can_board = -8 <= gap <= 6
                    if can_board:
                        inp.right, inp.left = True, False
                    elif player.rect.right > pit_edge - 6:
                        inp.right, inp.left = False, True   # brake at the lip
                    else:
                        inp.right, inp.left = True, False   # approach the lip
                events = player.update(inp, level)
                if events and any(e[0] in ("pit", "hazard") for e in events):
                    return False
                if player.dead:
                    return False
                continue

            # ---- normal waypoint steering
            mode = "run"
            tx, tr = nxt
            target_cx = tx * TILE + (TILE - config.PLAYER_W) / 2.0
            going_right = target_cx >= player.cx - 4
            inp.right = going_right
            inp.left = not going_right
            same = (tx, tr) == cell
            dx = abs(tx - cell[0])
            needs_jump = not same and (
                tr < cell[1]                                  # higher
                or (tr == cell[1] and dx >= 2)                # gap/hazard
                or (tr > cell[1]                              # lower, far
                    and dx > config.MAX_FALL_DRIFT_TILES))
            if needs_jump:
                # only launch from the cell edge (matches validator's arc)
                launch_x = cell[0] * TILE + (
                    TILE - config.PLAYER_W if going_right else 0)
                at_launch = (player.x >= launch_x - 6 if going_right
                             else player.x <= launch_x + 6)
                d_px = abs(target_cx - player.x)
                if d_px < 8.0:
                    d_px = 8.0
                dy_up = (cell[1] - tr) * TILE
                # ballistic vy for the CURRENT horizontal speed so the
                # landing point matches even at partial speed
                sp = min(max(abs(player.vx), 1.0), config.MAX_RUN)
                vy = (dy_up * sp / d_px
                      + 0.5 * config.GRAVITY * d_px / sp)
                vy = min(vy + 0.25, abs(config.JUMP_VELOCITY))
                adjacent = dx <= 2
                fast = (abs(player.vx) >= config.MAX_RUN * 0.9
                        and (player.vx >= 0) == going_right)
                if (at_launch and jump_armed
                        and (adjacent or fast or blocked_frames >= 3)):
                    player.vy = -vy - config.GRAVITY
                    blocked_frames = 0
                    jump_armed = False       # one launch per airtime
            # nearby lower targets: walk off, air-brake handles landing
        else:
            # descending to a lower waypoint: brake once over a landing cell
            if (cached_path and len(cached_path) > 1 and player.vy > 0):
                c0, r0 = cached_path[0]
                nxt0 = cached_path[1]
                if (isinstance(c0, int) and isinstance(nxt0[0], int)
                        and nxt0[1] > r0):
                    tr2 = nxt0[1]
                    b0 = int(player.x // TILE)
                    b1 = int((player.x + player.w - 1) // TILE)
                    if any((c, tr2) in cells for c in range(b0, b1 + 1)):
                        if player.vx > 0.3:
                            inp.right, inp.left = False, True
                        elif player.vx < -0.3:
                            inp.right, inp.left = True, False
                        else:
                            inp.right = inp.left = False

        events = player.update(inp, level)
        if verbose:
            history.append((frames, round(player.x, 1), round(player.y, 1),
                            player.on_ground, inp.right, inp.left,
                            round(level.movers[0].pos, 1)
                            if level.movers else -1))
            if len(history) > 16:
                history.pop(0)
        if verbose and (frames % 120 == 0 or frames % 8 == 0 and frames <= 80):
            print(f"  f{frames} x={player.x:.0f} y={player.y:.0f} "
                  f"vx={player.vx:.1f} vy={player.vy:.1f} "
                  f"gnd={player.on_ground} cell={cached_cell} "
                  f"r={inp.right} mv={(level.movers[0].pos if level.movers else 0):.0f} "
                  f"nxt={cached_path[1] if cached_path and len(cached_path) > 1 else cached_path}")
        if events and any(e[0] in ("pit", "hazard") for e in events):
            if verbose:
                for row in history:
                    print("   hist f=%d x=%s y=%s gnd=%s r=%s l=%s mv=%s"
                          % row)
                print(f"  DIED {events} f{frames} x={player.x:.0f} "
                      f"y={player.y:.0f} cell={cached_cell} "
                      f"nxt={cached_path[1] if cached_path and len(cached_path) > 1 else cached_path}")
            return False
        if player.dead:
            return False

        # progress bookkeeping
        if player.x > last_x + 0.05:
            no_progress = 0
        else:
            no_progress += 1
            if mode == "run" and no_progress > 200:
                if verbose:
                    print(f"stuck at x={player.x:.0f}")
                return False
        last_x = player.x
        if abs(player.x - stuck_anchor) < 0.5:
            blocked_frames += 1                # pressing into a wall
        else:
            blocked_frames = 0
        stuck_anchor = player.x
    if verbose:
        print(f"timeout at x={player.x:.0f}")
    return False

