"""
Runtime asset factory: generates every sprite/tile/background surface at
startup with pygame primitives (no external files, no downloaded art).

Art style: bold dark outlines, limited palette, light from top-left,
consistent 16px grid. Results are cached in dicts keyed by variant.
"""

import math

import pygame

from src.config import (TILE, VIEW_W, VIEW_H, FORM_COLORS, POWERUP_COLORS,
                        FG_TINTS, ZONES)
from src.level import tiles as T

# ------------------------------------------------------------------ palette
OUTLINE = (28, 24, 32)
DIRT = (150, 96, 52)
DIRT_DK = (112, 68, 36)
DIRT_LT = (178, 124, 72)
GRASS = (74, 180, 66)
GRASS_DK = (44, 132, 48)
GRASS_LT = (122, 214, 96)
BRICK = (188, 84, 60)
BRICK_DK = (130, 52, 40)
MORTAR = (238, 194, 156)
QGOLD = (246, 178, 42)
QGOLD_DK = (190, 116, 20)
USED = (168, 116, 68)
PIPE = (64, 178, 74)
PIPE_DK = (32, 118, 46)
PIPE_LT = (140, 226, 120)
SPIKE_MET = (176, 186, 202)
COIN_GOLD = (255, 208, 52)
COIN_DK = (214, 148, 20)
COIN_SHINE = (255, 246, 190)

# ----------------------------------------------------------------- palette
# The DEFAULT world palette = the legacy constants above (zone-0 identity).
# Zone themes override via AssetFactory(pal=...) / for_zone(zone) (4b).
DEFAULT_PAL = {
    "sky_top": (92, 148, 250), "sky_bottom": (172, 214, 255),
    "cloud": (252, 253, 255), "cloud_dk": (216, 228, 248),
    "hills_far_body": (94, 150, 152), "hills_far_crest": (130, 188, 178),
    "hills_near_body": (56, 138, 74), "hills_near_crest": (98, 180, 98),
    "dirt": DIRT, "dirt_dk": DIRT_DK, "dirt_lt": DIRT_LT,
    "grass": GRASS, "grass_dk": GRASS_DK, "grass_lt": GRASS_LT,
    "brick": BRICK, "brick_dk": BRICK_DK,
}
THEMED_KEYS = tuple(sorted(DEFAULT_PAL))


def make_surface(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _outline_rect(surf, rect, color=OUTLINE, width=1):
    pygame.draw.rect(surf, color, rect, width)


def _dotted(surf, color, points):
    for px, py in points:
        surf.set_at((px, py), color)


def _mix(a, b, t):
    """Channel-wise lerp between two RGB tuples (art-time only)."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ------------------------------------------------------------------- tiles

def _terrain_variant(mask, pal=None, zone=0):
    """Generate one 16x16 autotile variant for terrain (mask bits N/E/S/W).

    Phase 3 (T1): gradient dirt (lighter toward the grass line), pebble /
    clump texture, grass overhang lip with rounded corners on exposed
    sides, and a top-edge highlight. Phase 3 (T2): zone overlays — snow lip
    (Frost), ember cracks (Ember), wet sheen (Storm) — palette-derived or
    fixed tints only, never new palette keys. Mask contract unchanged."""
    pal = pal or DEFAULT_PAL
    s = make_surface(TILE, TILE)
    n, e, so, w = mask & 1, mask & 2, mask & 4, mask & 8
    # --- gradient dirt body: light near the grass line, dark at the base
    s.fill(pal["dirt"], pygame.Rect(0, 0, TILE, TILE))
    s.fill(pal["dirt_lt"], pygame.Rect(0, 0, TILE, 5))
    s.fill(_mix(pal["dirt"], pal["dirt_lt"], 0.5),
           pygame.Rect(0, 5, TILE, 2))
    s.fill(pal["dirt_dk"], pygame.Rect(0, 11, TILE, 5))
    s.fill(_mix(pal["dirt"], pal["dirt_dk"], 0.5), pygame.Rect(0, 9, TILE, 2))
    # --- pebbles + clumps (deterministic scatter)
    _dotted(s, pal["dirt_dk"], [(3, 8), (11, 12), (6, 14), (13, 7)])
    _dotted(s, pal["dirt_lt"], [(5, 10), (12, 9), (8, 13), (1, 12)])
    s.fill(_mix(pal["dirt_dk"], (0, 0, 0), 0.25),
           pygame.Rect(9, 8, 2, 2))                      # clump
    # --- zone overlays on the dirt (T2)
    if zone == 1:                                # Ember Caves: ember cracks
        _dotted(s, (104, 34, 22), [(4, 7), (5, 8), (10, 11), (11, 12),
                                   (13, 13), (2, 10)])
        s.set_at((5, 9), (150, 60, 30))                       # glowing tip
    elif zone == 3:                              # Storm Keep: wet sheen
        for px in (2, 5, 9, 12):
            py = 6 + (px * 3) % 7
            s.set_at((px, py), _mix(pal["dirt"], (200, 220, 255), 0.55))
            if py + 1 < TILE:
                s.set_at((px, py + 1), _mix(pal["dirt"], (200, 220, 255),
                                            0.25))
    # --- grass cap when no solid above
    if not n:
        s.fill(pal["grass"], pygame.Rect(0, 0, TILE, 4))
        for gx in range(0, TILE, 3):            # tufts
            s.set_at((gx, 4), pal["grass_dk"])
        s.fill(pal["grass_dk"], pygame.Rect(0, 4, TILE, 1))
        for gx in (1, 2, 6, 7, 11, 12):
            s.set_at((gx, 1), pal["grass_lt"])
        s.fill(pal["grass_lt"], pygame.Rect(2, 0, TILE - 4, 1))  # highlight
        if zone == 2:                           # Frost Peaks: snow lip
            s.fill((236, 244, 252), pygame.Rect(0, 0, TILE, 2))
            for gx in (3, 8, 13):
                s.set_at((gx, 2), (214, 228, 244))       # snow drape dots
    # exposed-side outlines
    if not w:
        s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
        if not n:
            s.fill(OUTLINE, pygame.Rect(1, 0, 1, 4))
            s.set_at((0, 1), pal["grass"])       # rounded overhang corner
    if not e:
        s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
        if not n:
            s.fill(OUTLINE, pygame.Rect(TILE - 2, 0, 1, 4))
            s.set_at((TILE - 1, 1), pal["grass"])  # rounded overhang corner
    if not so:
        s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    if not n:
        for gx in range(TILE):            # top edge outline where exposed
            if s.get_at((gx, 0))[3] == 0:
                s.set_at((gx, 0), OUTLINE)
    return s


def _make_brick(pal=None):
    pal = pal or DEFAULT_PAL
    s = make_surface(TILE, TILE)
    s.fill(pal["brick"])
    for row in range(4):
        y0 = row * 4
        s.fill(MORTAR, pygame.Rect(0, y0, TILE, 1))
        offset = 0 if row % 2 == 0 else 8
        for x in range(offset, TILE, 8):
            s.fill(MORTAR, pygame.Rect(x, y0, 1, 4))
    # Phase 3 (T1): corner chips + face speckle (derived, no new keys)
    chip = _shade(pal["brick_dk"], -20)
    s.set_at((2, 1), chip)
    s.set_at((1, 2), chip)
    s.set_at((TILE - 2, TILE - 2), chip)
    s.set_at((13, 8), _shade(pal["brick"], -26))
    s.set_at((5, 11), _shade(pal["brick"], 18))
    s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    return s


def _make_question(frame):
    """4-frame pulse for the question block."""
    s = make_surface(TILE, TILE)
    glow = (255, 214, 96) if frame in (1, 2) else QGOLD
    edge = QGOLD_DK
    s.fill(glow)
    s.fill(edge, pygame.Rect(0, TILE - 3, TILE, 3))
    s.fill(edge, pygame.Rect(TILE - 3, 0, 3, TILE))
    s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    # '?' glyph
    qcol = OUTLINE
    for px in (4, 5, 6, 7, 8, 9, 10):                    # top bar
        s.set_at((px, 4), qcol)
    s.set_at((10, 5), qcol)
    s.set_at((10, 6), qcol)
    s.set_at((9, 7), qcol)
    s.set_at((7, 8), qcol)                               # diagonal
    s.set_at((7, 9), qcol)
    for px in (6, 7, 8):                                 # stem
        s.set_at((px, 10), qcol)
    s.set_at((7, 12), qcol)                              # dot
    if frame == 3:                                       # sparkle
        s.set_at((3, 3), (255, 255, 255))
        s.set_at((12, 11), (255, 255, 255))
    return s


def _make_used():
    s = make_surface(TILE, TILE)
    s.fill(USED)
    s.fill((128, 84, 46), pygame.Rect(0, TILE - 3, TILE, 3))
    s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    for px, py in ((3, 3), (12, 3), (3, 12), (12, 12)):
        s.set_at((px, py), (90, 60, 34))
    return s


def _make_pipe(tid):
    s = make_surface(TILE, TILE)
    left = tid in (T.PIPE_TL, T.PIPE_BL)
    lip = tid in (T.PIPE_TL, T.PIPE_TR)
    s.fill(PIPE)
    if left:
        s.fill(PIPE_DK, pygame.Rect(0, 0, 2, TILE))
        s.fill(PIPE_LT, pygame.Rect(3, 0, 3, TILE))
        s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
    else:
        s.fill(PIPE_DK, pygame.Rect(TILE - 2, 0, 2, TILE))
        s.fill(PIPE_LT, pygame.Rect(TILE - 8, 0, 2, TILE))
        s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    if lip:
        s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
        s.fill(PIPE_DK, pygame.Rect(0, 12, TILE, 2))
        if left:
            s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
            s.set_at((0, 12), OUTLINE)
        else:
            s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    else:
        # subtle seam so body reads as a pipe shaft
        s.fill(PIPE_DK, pygame.Rect(0, 0, TILE, 1))
    return s


def _make_spike():
    s = make_surface(TILE, TILE)
    for i in range(3):
        bx = 1 + i * 5
        pygame.draw.polygon(s, SPIKE_MET, [
            (bx, TILE), (bx + 2, 4), (bx + 4, TILE)])
        pygame.draw.polygon(s, (230, 238, 248), [
            (bx + 2, TILE - 1), (bx + 2, 6), (bx + 3, TILE - 1)])
        pygame.draw.line(s, OUTLINE, (bx, TILE - 1), (bx + 2, 5), 1)
        pygame.draw.line(s, OUTLINE, (bx + 2, 5), (bx + 4, TILE - 1), 1)
    s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    return s


def _make_coin(frame):
    """4-frame spin: wide, medium, thin, medium."""
    s = make_surface(12, 16)
    widths = (10, 6, 2, 6)
    w = widths[frame]
    x0 = (12 - w) // 2
    rect = pygame.Rect(x0, 2, w, 12)
    pygame.draw.ellipse(s, COIN_DK, rect.inflate(2, 2))
    pygame.draw.ellipse(s, COIN_GOLD, rect)
    if w >= 6:
        pygame.draw.ellipse(s, COIN_SHINE,
                            pygame.Rect(x0 + 2, 4, max(1, w // 4), 4))
    s.set_at((6, 1), OUTLINE)
    s.set_at((5, 14), OUTLINE)
    return s


def _make_checkpoint(active):
    s = make_surface(16, 40)
    pygame.draw.rect(s, (226, 226, 234), pygame.Rect(7, 0, 2, 40))
    s.fill(OUTLINE, pygame.Rect(7, 0, 1, 40))
    if active:
        pygame.draw.polygon(s, (86, 220, 96), [
            (9, 2), (15, 5), (9, 9)])
        pygame.draw.polygon(s, OUTLINE, [(9, 2), (15, 5), (9, 9)], 1)
    else:
        pygame.draw.polygon(s, (150, 152, 164), [
            (6, 4), (1, 7), (6, 11)])
        pygame.draw.polygon(s, OUTLINE, [(6, 4), (1, 7), (6, 11)], 1)
    pygame.draw.circle(s, (250, 214, 70), (8, 1), 2)
    pygame.draw.circle(s, OUTLINE, (8, 1), 2, 1)
    return s


def _make_goal_gate():
    s = make_surface(22, 56)
    pygame.draw.rect(s, (236, 236, 244), pygame.Rect(9, 4, 3, 52))
    s.fill(OUTLINE, pygame.Rect(9, 4, 1, 52))
    s.fill(OUTLINE, pygame.Rect(11, 4, 1, 52))
    pygame.draw.circle(s, (250, 214, 70), (10, 4), 4)
    pygame.draw.circle(s, OUTLINE, (10, 4), 4, 1)
    # waving checkered flag
    pygame.draw.polygon(s, (250, 250, 250), [
        (12, 8), (21, 11), (21, 22), (12, 19)])
    pygame.draw.polygon(s, OUTLINE, [
        (12, 8), (21, 11), (21, 22), (12, 19)], 1)
    for row in range(2):
        for col in range(2):
            if (row + col) % 2 == 0:
                s.fill((60, 60, 70),
                       pygame.Rect(13 + col * 4, 10 + row * 4 + row, 4, 4))
    return s


def _make_platform_seg():
    s = make_surface(TILE, 12)
    s.fill((196, 148, 84))
    s.fill((150, 106, 56), pygame.Rect(0, 8, TILE, 4))
    s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 11, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 0, 1, 12))
    s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, 12))
    for x in (4, 11):
        s.set_at((x, 5), (230, 196, 138))
    return s


def _make_projectile(tick):
    s = make_surface(10, 10)
    phase = (tick // 5) % 3
    pygame.draw.circle(s, (255, 120, 40), (5, 5), 4)
    pygame.draw.circle(s, (255, 210, 90), (5, 5), 3)
    pygame.draw.circle(s, (255, 250, 210), (4 - phase, 4), 1)
    pygame.draw.circle(s, OUTLINE, (5, 5), 5, 1)
    return s


# ------------------------------------------------------------------ player
CAP = (36, 146, 146)
CAP_DK = (22, 98, 104)
SKIN = (246, 202, 160)
SKIN_DK = (212, 158, 118)
SHIRT = (232, 176, 56)
OVER = (46, 62, 124)
OVER_DK = (30, 42, 88)
SHOE = (94, 58, 34)
GLOVE = (244, 244, 244)


def _player_base(leg_layout, crouch=False, arms="side", eyes="open",
                 bob=0, lean=0):
    """Build one 16x26 (or 16x16 crouch) player frame, facing right."""
    h = 16 if crouch else 26
    s = make_surface(16, h)
    if crouch:
        s.fill(CAP, pygame.Rect(2 + lean, 0, 12, 4))
        s.fill(CAP_DK, pygame.Rect(2 + lean, 3, 12, 1))
        s.fill(SKIN, pygame.Rect(4 + lean, 4, 9, 5))
        s.set_at((11 + lean, 5), OUTLINE)
        s.fill(SHIRT, pygame.Rect(3 + lean, 9, 10, 2))
        s.fill(OVER, pygame.Rect(3 + lean, 10, 10, 4))
        s.fill(OVER_DK, pygame.Rect(3 + lean, 13, 10, 1))
        s.fill(SHOE, pygame.Rect(3, 14, 5, 2))
        s.fill(OUTLINE, pygame.Rect(2 + lean, 8, 11, 1))
        return s

    y = bob
    # cap + brim
    s.fill(CAP, pygame.Rect(2 + lean, y, 12, 5))
    s.fill(CAP_DK, pygame.Rect(2 + lean, y + 3, 12, 2))
    s.fill(CAP, pygame.Rect(8 + lean, y + 4, 8, 2))
    s.fill(OUTLINE, pygame.Rect(2 + lean, y, 12, 1))
    # face
    s.fill(SKIN, pygame.Rect(4 + lean, y + 5, 9, 6))
    s.fill(SKIN_DK, pygame.Rect(4 + lean, y + 10, 9, 1))
    if eyes == "x":
        s.set_at((10 + lean, y + 6), OUTLINE)
        s.set_at((12 + lean, y + 8), OUTLINE)
        s.set_at((12 + lean, y + 6), OUTLINE)
        s.set_at((10 + lean, y + 8), OUTLINE)
    else:
        s.fill(OUTLINE, pygame.Rect(11 + lean, y + 6, 2, 3))
    s.fill(OUTLINE, pygame.Rect(4 + lean, y + 5, 9, 1))
    # torso: shirt + overall straps
    s.fill(SHIRT, pygame.Rect(3 + lean, y + 11, 10, 6))
    s.fill(OVER, pygame.Rect(5 + lean, y + 11, 2, 6))
    s.fill(OVER, pygame.Rect(9 + lean, y + 11, 2, 6))
    s.fill(OVER, pygame.Rect(4 + lean, y + 16, 8, 5))
    s.fill(OUTLINE, pygame.Rect(3 + lean, y + 11, 10, 1))
    s.set_at((9, y + 13), (250, 210, 70))
    s.set_at((6, y + 13), (250, 210, 70))
    # arms
    if arms == "up":
        s.fill(SHIRT, pygame.Rect(1 + lean, y + 8, 2, 4))
        s.fill(GLOVE, pygame.Rect(1 + lean, y + 6, 2, 2))
        s.fill(SHIRT, pygame.Rect(13 + lean, y + 8, 2, 4))
        s.fill(GLOVE, pygame.Rect(13 + lean, y + 6, 2, 2))
    elif arms == "out":
        s.fill(SHIRT, pygame.Rect(1 + lean, y + 12, 2, 3))
        s.fill(GLOVE, pygame.Rect(0 + lean, y + 11, 2, 2))
        s.fill(SHIRT, pygame.Rect(13 + lean, y + 12, 2, 3))
        s.fill(GLOVE, pygame.Rect(14 + lean, y + 14, 2, 2))
    else:
        s.fill(SHIRT, pygame.Rect(2 + lean, y + 12, 2, 4))
        s.fill(GLOVE, pygame.Rect(2 + lean, y + 16, 2, 2))
        s.fill(SHIRT, pygame.Rect(12 + lean, y + 12, 2, 4))
        s.fill(GLOVE, pygame.Rect(12 + lean, y + 16, 2, 2))
    # legs from layout: (left_x, left_w, right_x, right_w, lift)
    lx, lw, rx, rw, lift = leg_layout
    s.fill(SKIN, pygame.Rect(lx, y + 21, lw, 3))
    s.fill(SKIN, pygame.Rect(rx, y + 21 - lift, rw, 3))
    s.fill(SHOE, pygame.Rect(lx - 1, y + 24, lw + 2, 2))
    s.fill(SHOE, pygame.Rect(rx - 1, y + 24 - lift, rw + 2, 2))
    s.fill(OUTLINE, pygame.Rect(lx - 1, y + 25, lw + 2, 1))
    s.fill(OUTLINE, pygame.Rect(rx - 1, y + 25 - lift, rw + 2, 1))
    return s


PLAYER_FRAMES = {}


def _build_player_frames():
    legs_idle = (4, 3, 9, 3, 0)
    run_cycle = [
        (2, 3, 10, 3, 3),       # stride
        (4, 3, 8, 3, 1),
        (9, 3, 3, 3, 3),        # opposite stride
        (5, 3, 7, 3, 0),
    ]
    PLAYER_FRAMES["idle"] = [_player_base(legs_idle)]
    PLAYER_FRAMES["run"] = [
        _player_base(run_cycle[i], bob=(i % 2)) for i in range(4)]
    PLAYER_FRAMES["skid"] = [
        _player_base(legs_idle, arms="out", lean=-2)]
    PLAYER_FRAMES["jump"] = [
        _player_base((3, 3, 10, 3, 6), arms="up")]
    PLAYER_FRAMES["fall"] = [
        _player_base((2, 3, 11, 3, 2), arms="up")]
    PLAYER_FRAMES["crouch"] = [_player_base((3, 4, 3, 4, 0), crouch=True)]
    PLAYER_FRAMES["dead"] = [
        _player_base((4, 3, 9, 3, 4), arms="up", eyes="x", bob=-1)]


# ----------------------------------------------------------------- enemies
ENEMY_FRAMES = {}
ENEMY_HIT_FRAMES = {}           # ((kind, state, idx), phase) -> recoil frame
WALK_KINDS = ("walker", "shellback", "shieldkin", "bomber", "wallcrawler")
WALKER_BODY = (168, 116, 70)
WALKER_DK = (120, 76, 44)
CHASER_RED = (214, 66, 58)
CHASER_DK = (150, 36, 34)
SHELL_GREEN = (78, 190, 84)
SHELL_DK = (40, 130, 52)
SHELL_RIM = (232, 226, 178)
WHITE = (250, 250, 250)


def _eyes(s, y, lx=4, rx=9, pupil_dx=1):
    for ex in (lx, rx):
        s.fill(WHITE, pygame.Rect(ex, y, 3, 3))
        s.fill(OUTLINE, pygame.Rect(ex, y, 3, 1))
        s.set_at((ex + pupil_dx, y + 1), OUTLINE)
        s.set_at((ex + pupil_dx, y + 2), OUTLINE)


def _mk_walker(phase):
    s = make_surface(16, 16)
    lean = (-1, 0, 1, 0)[phase % 4]              # sway with the stride (SI-B)
    bx = 1 + lean
    pygame.draw.ellipse(s, WALKER_BODY, pygame.Rect(bx, 1, 14, 11))
    pygame.draw.ellipse(s, WALKER_DK, pygame.Rect(bx, 7, 14, 5))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(bx, 1, 14, 11), 1)
    _eyes(s, 4 + lean, 4, 9, 1)
    s.fill(OUTLINE, pygame.Rect(4 + lean, 3, 3, 1))      # angry brows
    s.fill(OUTLINE, pygame.Rect(9 + lean, 3, 3, 1))
    s.set_at((6 + lean, 2), OUTLINE)
    s.set_at((9 + lean, 2), OUTLINE)
    if phase == 0:                               # left foot forward
        s.fill(WALKER_DK, pygame.Rect(1, 12, 5, 3))
        s.fill(WALKER_DK, pygame.Rect(9, 13, 5, 2))
    elif phase == 1:                             # mid-stride
        s.fill(WALKER_DK, pygame.Rect(3, 13, 5, 2))
        s.fill(WALKER_DK, pygame.Rect(8, 13, 5, 2))
    elif phase == 2:                             # right foot forward
        s.fill(WALKER_DK, pygame.Rect(1, 13, 5, 2))
        s.fill(WALKER_DK, pygame.Rect(10, 12, 5, 3))
    else:                                        # mid-stride, shifted
        s.fill(WALKER_DK, pygame.Rect(2, 13, 5, 2))
        s.fill(WALKER_DK, pygame.Rect(9, 13, 5, 2))
    s.fill(OUTLINE, pygame.Rect(2, 15, 12, 1))
    return s


def _mk_walker_squash():
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, WALKER_BODY, pygame.Rect(1, 9, 14, 6))
    pygame.draw.ellipse(s, WALKER_DK, pygame.Rect(1, 12, 14, 3))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 9, 14, 6), 1)
    s.fill(OUTLINE, pygame.Rect(1, 14, 14, 1))
    _eyes(s, 10, 4, 9, 1)
    return s


def _mk_chaser(phase, chase=False, pupil=1):
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, CHASER_RED, pygame.Rect(1, 3, 14, 10))
    pygame.draw.ellipse(s, CHASER_DK, pygame.Rect(1, 9, 14, 4))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 3, 14, 10), 1)
    _eyes(s, 6, 4, 9, pupil)                            # gaze (SI-C 4.1)
    for sx in (3, 7, 11):                             # spiky crest
        pygame.draw.polygon(s, CHASER_DK, [
            (sx, 4), (sx + 2, 0), (sx + 4, 4)])
        pygame.draw.polygon(s, OUTLINE, [
            (sx, 4), (sx + 2, 0), (sx + 4, 4)], 1)
    if chase:
        s.fill(OUTLINE, pygame.Rect(5, 10, 6, 2))
        s.fill((240, 120, 110), pygame.Rect(6, 10, 4, 1))
    if phase == 0:
        s.fill(CHASER_DK, pygame.Rect(2, 13, 5, 2))
        s.fill(CHASER_DK, pygame.Rect(9, 13, 5, 2))
    else:
        s.fill(CHASER_DK, pygame.Rect(3, 13, 4, 2))
        s.fill(CHASER_DK, pygame.Rect(8, 12, 5, 3))
    return s


def _mk_chaser_squash():
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, CHASER_RED, pygame.Rect(1, 10, 14, 5))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 10, 14, 5), 1)
    _eyes(s, 11, 4, 9, 1)
    return s


def _mk_shell(phase=0, glow=False):
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, SHELL_GREEN, pygame.Rect(1, 3, 14, 12))
    pygame.draw.ellipse(s, SHELL_DK, pygame.Rect(3, 5, 10, 8))
    pygame.draw.ellipse(s, SHELL_RIM, pygame.Rect(1, 11, 14, 4))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 3, 14, 12), 1)
    s.fill(SHELL_DK, pygame.Rect(7, 5, 2, 8))
    s.fill(SHELL_DK, pygame.Rect(3, 8, 10, 2))
    if phase:                                       # spin highlight
        hx = (phase * 4) % 12 + 2
        s.fill((226, 255, 200), pygame.Rect(hx, 6, 2, 4))
    if glow:                                        # slide danger glow (4.2)
        pygame.draw.ellipse(s, (226, 255, 200, 150),
                            pygame.Rect(0, 2, 16, 14), 1)
        s.set_at((1, 8), (240, 255, 220))
        s.set_at((14, 8), (240, 255, 220))
    return s


def _mk_shellback(phase):
    s = make_surface(16, 16)
    bob = (0, 0, 1, 0)[phase % 4]                # head bob with the stride
    s.fill(SHELL_GREEN, pygame.Rect(9, bob, 6, 6))     # head, upper-right
    s.fill((196, 226, 140), pygame.Rect(10, 2 + bob, 4, 3))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(9, bob, 6, 6), 1)
    s.fill(WHITE, pygame.Rect(12, 1 + bob, 2, 2))
    s.set_at((13, 2 + bob), OUTLINE)
    s.blit(_mk_shell(0), (0, 4))
    if phase == 0:                               # left foot forward
        s.fill(SHELL_RIM, pygame.Rect(1, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(10, 14, 4, 2))
    elif phase == 1:                             # mid-stride
        s.fill(SHELL_RIM, pygame.Rect(3, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(9, 14, 4, 2))
    elif phase == 2:                             # right foot forward
        s.fill(SHELL_RIM, pygame.Rect(2, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(11, 14, 4, 2))
    else:                                        # mid-stride, stepping
        s.fill(SHELL_RIM, pygame.Rect(2, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(10, 13, 4, 2))
    return s


def _mk_shellback_squash():
    s = make_surface(16, 16)
    shell = _mk_shell(0)
    s.blit(pygame.transform.scale(shell, (16, 8)), (0, 8))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 8, 14, 7), 1)
    return s


def _mk_flyer(phase):
    s = make_surface(16, 16)
    wing_up = phase == 0
    bob = 0 if wing_up else 1                    # body drops on downstroke
    wing_col = (198, 152, 232)
    if wing_up:
        pygame.draw.polygon(s, wing_col, [(4, 8), (0, 2), (7, 6)])
        pygame.draw.polygon(s, wing_col, [(12, 8), (16, 2), (9, 6)])
    else:
        pygame.draw.polygon(s, wing_col, [(4, 7), (0, 13), (7, 9)])
        pygame.draw.polygon(s, wing_col, [(12, 7), (16, 13), (9, 9)])
    pygame.draw.ellipse(s, (150, 88, 200), pygame.Rect(4, 4 + bob, 8, 9))
    pygame.draw.ellipse(s, (102, 54, 148), pygame.Rect(4, 9 + bob, 8, 4))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(4, 4 + bob, 8, 9), 1)
    _eyes(s, 6, 5 + bob, 9, 1)
    s.fill(WHITE, pygame.Rect(6, 11 + bob, 1, 2))
    s.fill(WHITE, pygame.Rect(9, 11 + bob, 1, 2))
    return s


def _mk_spitter(pose=0):
    """pose: 0 patrol / 1 windup / 2 execute / 3 recovery (SI-C 1.3)."""
    s = make_surface(16, 20)
    pygame.draw.rect(s, (130, 138, 154), pygame.Rect(2, 6, 12, 13))
    pygame.draw.rect(s, (84, 90, 106), pygame.Rect(2, 15, 12, 4))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(2, 6, 12, 13), 1)
    hx = (4, 3, 5, 4)[pose]                     # head tilt / lunge
    pygame.draw.rect(s, (130, 138, 154), pygame.Rect(hx, 2, 10, 5))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(hx, 2, 10, 5), 1)
    pygame.draw.rect(s, (84, 90, 106), pygame.Rect(hx + 7, 3, 3, 3))
    if pose == 1:                               # windup: mouth shut tight
        pygame.draw.rect(s, OUTLINE, pygame.Rect(hx + 8, 3, 2, 1))
    elif pose == 2:                             # execute: wide mouth + tongue
        pygame.draw.circle(s, (255, 150, 40), (hx + 9, 4), 2)
        pygame.draw.circle(s, OUTLINE, (hx + 9, 4), 2, 1)
        pygame.draw.rect(s, (255, 190, 90), pygame.Rect(hx + 10, 4, 2, 1))
    elif pose == 3:                             # recovery: half-open mouth
        pygame.draw.rect(s, OUTLINE, pygame.Rect(hx + 7, 3, 3, 2))
    else:                                       # patrol: closed mouth
        pygame.draw.rect(s, OUTLINE, pygame.Rect(hx + 8, 3, 2, 3))
    for px in (4, 8, 12):
        s.set_at((px, 12), (180, 188, 202))
        s.set_at((px, 17), (60, 66, 80))
    return s


def _mk_jumper(air=False):
    s = make_surface(16, 16)
    if air:
        pygame.draw.ellipse(s, (240, 138, 46), pygame.Rect(3, 1, 10, 10))
        pygame.draw.ellipse(s, OUTLINE, pygame.Rect(3, 1, 10, 10), 1)
        _eyes(s, 4, 5, 9, 1)
        s.fill((182, 92, 26), pygame.Rect(4, 11, 3, 4))
        s.fill((182, 92, 26), pygame.Rect(9, 11, 3, 4))
        s.fill(OUTLINE, pygame.Rect(4, 14, 3, 1))
        s.fill(OUTLINE, pygame.Rect(9, 14, 3, 1))
    else:
        pygame.draw.ellipse(s, (240, 138, 46), pygame.Rect(3, 4, 10, 8))
        pygame.draw.ellipse(s, OUTLINE, pygame.Rect(3, 4, 10, 8), 1)
        for yy in (7, 9):
            s.fill((182, 92, 26), pygame.Rect(4, yy, 8, 1))
        _eyes(s, 5, 5, 9, 1)
        s.fill((182, 92, 26), pygame.Rect(3, 12, 10, 3))
        s.fill(OUTLINE, pygame.Rect(3, 15, 10, 1))
    return s


def _mk_squash(body):
    """Generic flat death-squash blob (5a)."""
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, body, pygame.Rect(1, 10, 14, 5))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 10, 14, 5), 1)
    return s


def _mk_shieldkin(phase):
    s = make_surface(16, 16)
    body = (104, 112, 130)
    lean = (-1, 0, 1, 0)[phase % 4]              # sway with the stride (SI-B)
    pygame.draw.ellipse(s, body, pygame.Rect(1 + lean, 3, 11, 11))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1 + lean, 3, 11, 11), 1)
    # shield plate on the front (right) side; flipped with facing
    pygame.draw.rect(s, (168, 176, 196), pygame.Rect(11 + lean, 2, 4, 12))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(11 + lean, 2, 4, 12), 1)
    _eyes(s, 4 + lean, 6, 8, 2)
    if phase == 0:                               # left foot forward
        s.fill((72, 78, 94), pygame.Rect(3, 13, 3, 3))
        s.fill((72, 78, 94), pygame.Rect(9, 13, 3, 2))
    elif phase == 1:                             # mid-stride
        s.fill((72, 78, 94), pygame.Rect(4, 13, 3, 2))
        s.fill((72, 78, 94), pygame.Rect(8, 13, 3, 2))
    elif phase == 2:                             # right foot forward
        s.fill((72, 78, 94), pygame.Rect(3, 13, 3, 2))
        s.fill((72, 78, 94), pygame.Rect(10, 13, 3, 3))
    else:                                        # mid-stride, shifted
        s.fill((72, 78, 94), pygame.Rect(4, 13, 3, 2))
        s.fill((72, 78, 94), pygame.Rect(9, 13, 3, 2))
    return s


def _mk_bomber(phase):
    s = make_surface(16, 16)
    body = (72, 76, 92)
    bob = (0, -1, 0, -1)[phase % 4]              # hop with the stride (SI-B)
    pygame.draw.circle(s, body, (8, 10 + bob), 6)
    pygame.draw.circle(s, OUTLINE, (8, 10 + bob), 6, 1)
    # fuse with a spark (pulses across the 4-frame cycle)
    s.fill((120, 100, 80), pygame.Rect(9, 2 + bob, 2, 3))
    spark = ((255, 210, 90), (255, 210, 90),
             (255, 150, 60), (255, 150, 60))[phase % 4]
    s.set_at((10, 1 + bob), spark)
    s.set_at((11, 2 + bob), spark)
    _eyes(s, 5, 9 + bob, 4, 1)
    return s


def _mk_wallcrawler(phase, grip=False):
    s = make_surface(16, 16)
    body = (128, 92, 168)
    pygame.draw.ellipse(s, body, pygame.Rect(1, 5, 14, 8))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 5, 14, 8), 1)
    # legs on TOP (it crawls ceilings/walls): 4-phase stepping cycle
    stride = ((2, 6, 10, 13),                    # full contact
              (3, 6, 11, 13),                    # outer legs reach
              (2, 7, 10, 12),                    # inner legs reach
              (3, 7, 11, 12))[phase % 4]         # gathered mid-step
    for px in stride:
        s.fill(body, pygame.Rect(px, 2, 2, 3))
        s.set_at((px, 2), OUTLINE)
    if grip:                                     # claw marks (SI-C 4.6)
        for cx in (4, 10):
            s.fill((64, 42, 90), pygame.Rect(cx, 1, 2, 1))
            s.set_at((cx, 0), (64, 42, 90))
    _eyes(s, 4, 9, 8, 1)
    return s


def _mk_charger(phase, pose=0):
    """pose: 0 patrol / 1..3 wind-up horn glow / 4 execute (SI-C 4.3)."""
    s = make_surface(16, 16)
    body = (188, 108, 64) if pose != 4 else (214, 128, 74)
    dip = 1 if 1 <= pose <= 3 else 0             # head dips while coiling
    pygame.draw.ellipse(s, body, pygame.Rect(1, 4 + dip, 13, 10 - dip))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 4 + dip, 13, 10 - dip), 1)
    # horns on the front (right); brightness rises through the wind-up
    horn = ((238, 226, 200), (150, 142, 128), (196, 184, 160),
            (255, 250, 235), (255, 255, 245))[pose]
    s.fill(horn, pygame.Rect(12, 3 + dip, 3, 2))
    s.fill(horn, pygame.Rect(12, 12, 3, 2))
    _eyes(s, 8, 7, 3, 1)
    if pose == 4:                               # execute: dash speed lines
        for px in (2, 5, 8, 11):                # dash speed lines
            s.set_at((px, 15), (255, 220, 150))
    return s


def _mk_needler(pose=0):
    """pose: 0 patrol / 1 dim aim / 2 bright aim / 3 execute / 4 recovery
    (SI-C 1.3 + 4.4: barrel tint rises with the charge telegraph)."""
    s = make_surface(16, 16)
    body = (96, 150, 120)
    barrel = (body, (141, 148, 104), (200, 150, 80),
              (255, 200, 90), (160, 154, 108))[pose]
    crouch = 1 if pose in (1, 2) else 0          # coils down while aiming
    pygame.draw.rect(s, body, pygame.Rect(3, 6 + crouch, 10, 9 - crouch))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(3, 6 + crouch, 10, 9 - crouch),
                     1)
    if pose == 3:                               # execute: barrel extends
        pygame.draw.rect(s, barrel, pygame.Rect(10, 8, 6, 3))
        pygame.draw.rect(s, OUTLINE, pygame.Rect(10, 8, 6, 3), 1)
        pygame.draw.circle(s, (255, 240, 140), (16, 9), 2)
    else:
        bx = 10 if crouch else 11               # barrel pulls back when aiming
        pygame.draw.rect(s, barrel, pygame.Rect(bx, 8, 5, 3))
        pygame.draw.rect(s, OUTLINE, pygame.Rect(bx, 8, 5, 3), 1)
        if pose == 4:                           # recovery: spent-powder spark
            s.set_at((15, 9), (255, 200, 120))
    _eyes(s, 5, 9, 3, 1)
    return s


# Hit-recoil post-processing (SI-A, proposal 2.2): (tint, alpha, num, den).
# Phase 0: white at 60% alpha, squashed to 0.8x. Phase 1: pale yellow at
# 40%, 0.9x. Phase 2: normal colors at full scale.
_HIT_FLASH = (
    ((255, 255, 255), 153, 4, 5),
    ((255, 255, 200), 102, 9, 10),
    ((255, 255, 255), 0, 1, 1),
)


def _apply_hit_flash(source, phase):
    """Return a hit-flash variant of `source`, composited once at startup
    so the runtime cost is a dict lookup. Per-pixel alpha is preserved."""
    tint, alpha, num, den = _HIT_FLASH[phase]
    if (num, den) != (1, 1):
        w, h = source.get_width(), source.get_height()
        source = pygame.transform.scale(
            source, (max(1, w * num // den), max(1, h * num // den)))
    w, h = source.get_width(), source.get_height()
    s = make_surface(w, h)
    if alpha <= 0:
        s.blit(source, (0, 0))
        return s
    tr, tg, tb = tint
    f = alpha / 255.0
    for y in range(h):
        for x in range(w):
            r, g, b, a = source.get_at((x, y))
            if a:
                s.set_at((x, y), (int(r + (tr - r) * f),
                                   int(g + (tg - g) * f),
                                   int(b + (tb - b) * f), a))
    return s


# Death-sequence composition (SI-D, proposal 3.1): (scale_num, scale_den,
# alpha) per phase — topple, curl, squash, fade, remnant. Canvas size is
# preserved (content shrinks toward the ground) so blits never shift.
_DEATH = (
    (1, 1, 255),
    (17, 20, 204),      # 0.85x, 80%
    (7, 10, 153),       # 0.7x, 60%
    (1, 2, 102),        # 0.5x, 40%
    (3, 10, 51),        # 0.3x, 20%
)


def _apply_death(source, phase):
    """Return one frame of the 5-frame death sequence, composed once at
    startup. Phase 0 topples (12 deg tilt); later phases squash toward the
    bottom edge and fade out (proposal 3.1)."""
    num, den, alpha = _DEATH[phase]
    w, h = source.get_width(), source.get_height()
    img = source
    if phase == 0:
        img = pygame.transform.rotate(source, 12)
        img = pygame.transform.scale(img, (w, h))   # keep the canvas size
    if (num, den) != (1, 1):
        img = pygame.transform.scale(
            img, (max(1, w * num // den), max(1, h * num // den)))
    s = make_surface(w, h)
    s.blit(img, ((w - img.get_width()) // 2,
                 h - img.get_height()))             # anchored to the ground
    if alpha < 255:
        f = alpha / 255.0
        for y in range(h):
            for x in range(w):
                r, g, b, a = s.get_at((x, y))
                if a:
                    s.set_at((x, y), (r, g, b, int(a * f)))
    return s


# ---------------------------------------------- boss defeat sequence (SI-E)
# Proposal 3.2: 10 INLINE frames across DEFEAT_TICKS = 90 —
#   stagger 0-2 (18 ticks): reel + shake, X eyes, flavor detail ramps
#   crumble 3-6 (36 ticks): 4 body segments drift apart, fade 100% -> 30%
#   explode 7-9 (36 ticks): shrink to nothing, white flash, flavor burst
# Bosses never use ENEMY_FRAMES (their HP/phases are per-instance), so
# this composes at draw time. Flavors follow the proposal's boss-specific
# death table; duck-typed attrs: DEATH_SHAPE / DEATH_FLAVOR / DEATH_BODY.
_BOSS_DEATH_FLAVOR = {
    # stagger detail / crumble grit / burst inner / burst outer
    "dust":  ((58, 40, 26), (150, 128, 100), (208, 188, 158), (116, 96, 72)),
    "prism": ((255, 255, 255), (168, 228, 248), (255, 255, 255),
              (140, 220, 255)),
    "wind":  ((206, 220, 238), (186, 202, 224), (238, 247, 255),
              (172, 198, 228)),
    "ember": ((255, 176, 64), (255, 118, 44), (255, 214, 118), (255, 96, 36)),
}
_BOSS_DEATH_CRUMBLE_ALPHA = (255, 191, 128, 77)   # 100 / 75 / 50 / 30 %
_BOSS_DEATH_SHRINK = ((7, 10), (1, 2), (3, 10))   # explode frames 7-9


def _boss_death_frame(boss):
    """Map defeat_timer -> (frame 0..9, progress within that stage)."""
    total = getattr(boss, "DEFEAT_TICKS", 90)
    elapsed = max(0, min(total, total - boss.defeat_timer))
    if elapsed < 18:
        step = min(2, elapsed // 6)
        return step, step
    if elapsed < 54:
        p = min(3, (elapsed - 18) // 9)
        return 3 + p, p
    p = min(2, (elapsed - 54) // 12)
    return 7 + p, p


def _boss_death_x_eyes(surf, bx, by, w, h):
    """Spin-out X eyes during the stagger stage (proposal 3.2)."""
    ex_l = max(0, w // 4 - 1)
    ex_r = max(0, w - w // 4 - 4)
    ey = max(0, h // 3 - 1)
    for ex in (ex_l, ex_r):
        pygame.draw.line(surf, (255, 246, 224),
                         (bx + ex, by + ey), (bx + ex + 3, by + ey + 3), 1)
        pygame.draw.line(surf, (255, 246, 224),
                         (bx + ex + 3, by + ey), (bx + ex, by + ey + 3), 1)


def _draw_boss_death(boss, surf, cam, tick):
    """10-frame staged boss defeat, drawn inline from each concrete boss's
    draw() while state == "dying" and defeat_timer > 0 (proposal 3.2).
    Draws nothing once the timer runs out — the corpse has fully burst."""
    if boss.defeat_timer <= 0:
        return
    frame, prog = _boss_death_frame(boss)
    r = boss.rect
    x0, y0 = r.x - cam.ix, r.y - cam.iy
    name = getattr(boss, "DEATH_FLAVOR", "dust")
    detail, grit, burst_in, burst_out = _BOSS_DEATH_FLAVOR[name]
    body = getattr(boss, "DEATH_BODY", (148, 60, 72))
    outline = tuple(c * 45 // 100 for c in body)
    shape = getattr(boss, "DEATH_SHAPE", "rect")

    def _shape(s, color, x, y, w, h, width=0):
        box = pygame.Rect(int(x), int(y), int(w), int(h))
        if shape == "ellipse":
            pygame.draw.ellipse(s, color, box, width)
        else:
            pygame.draw.rect(s, color, box, width)

    if frame < 3:
        # ---- stagger: per-frame shake, X eyes, flavor detail ramps up
        bx = x0 + (2 if frame % 2 == 0 else -2)
        col = body if frame % 2 == 0 else \
            tuple(min(255, c + 70) for c in body)   # reel highlight
        _shape(surf, col, bx, y0, r.w, r.h)
        _shape(surf, outline, bx, y0, r.w, r.h, 2)
        _boss_death_x_eyes(surf, bx, y0, r.w, r.h)
        _boss_death_stagger(surf, name, detail, frame, bx, y0, r.w, r.h)
    elif frame < 7:
        # ---- crumble: quadrants drift apart while the body fades
        pad = 16
        drift = prog + 1
        qw, qh = (r.w + 1) // 2, (r.h + 1) // 2
        ov = make_surface(r.w + 2 * pad, r.h + 2 * pad)
        for sxq in (-1, 1):
            for syq in (-1, 1):
                qx = 0 if sxq < 0 else r.w - qw
                qy = 0 if syq < 0 else r.h - qh
                ov.set_clip(pygame.Rect(pad + qx, pad + qy, qw, qh))
                px, py = pad + sxq * drift, pad + syq * drift
                _shape(ov, body, px, py, r.w, r.h)
                _shape(ov, outline, px, py, r.w, r.h, 2)
                ov.set_clip(None)
        ov.set_alpha(_BOSS_DEATH_CRUMBLE_ALPHA[prog])
        surf.blit(ov, (x0 - pad, y0 - pad))
        _boss_death_debris(surf, name, grit, prog, x0, y0, r.w, r.h)
    else:
        # ---- explode: shrink behind a white flash + flavor burst
        num, den = _BOSS_DEATH_SHRINK[prog]
        w2, h2 = max(4, r.w * num // den), max(4, r.h * num // den)
        cx, cy = x0 + r.w // 2, y0 + r.h // 2
        bw, bh = w2 + 6, h2 + 6
        ov = make_surface(bw, bh)
        _shape(ov, body, 3, 3, w2, h2)
        _shape(ov, outline, 3, 3, w2, h2, 1)
        _boss_death_x_eyes(ov, 3, 3, w2, h2)
        ov.set_alpha((235, 170, 110)[prog])
        surf.blit(ov, (cx - bw // 2, cy - bh // 2))
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 5 + 3 * prog)
        pygame.draw.circle(surf, burst_out, (cx, cy), 6 + 3 * prog, 1)
        _boss_death_burst(surf, name, burst_in, burst_out, prog, cx, cy)


def _boss_death_stagger(surf, name, col, frame, bx, by, w, h):
    """Flavor detail on the reeling body; ramps across frames 0-2 so each
    stagger frame reads as accumulating damage (proposal 3.2 table)."""
    n = frame + 1
    if name == "dust":                      # cracks spread across body
        cracks = (((6, 4), (12, 10)), ((20, 5), (15, 12)),
                  ((9, 19), (15, 25)))
        for a, b in cracks[:n]:
            pygame.draw.line(surf, col,
                             (bx + a[0] * w // 32, by + a[1] * h // 32),
                             (bx + b[0] * w // 32, by + b[1] * h // 32), 1)
    elif name == "prism":                   # core glows bright white
        cx, cy = bx + w // 2, by + h // 2 + 2
        rad = 3 + 2 * frame
        pygame.draw.polygon(surf, col, [
            (cx, cy - rad), (cx + rad, cy), (cx, cy + rad), (cx - rad, cy)])
    elif name == "wind":                    # feathers ruffle upward
        for i in range(n):
            fx = bx + 5 + i * 6
            pygame.draw.line(surf, col, (fx, by + h - 8),
                             (fx + 4, by + h - 12), 1)
    else:                                   # ember: veins flare, crown tilts
        for i in range(2):
            vx = bx + 9 + i * 11
            pygame.draw.line(surf, col, (vx, by + 5),
                             (vx - 2, by + h - 5), 1)
        tilt = (frame - 1) * 3
        for ox in (4, 12, 20):
            x = bx + ox + tilt
            pygame.draw.polygon(surf, (255, 210, 90), [
                (x, by), (x + 3, by - 7), (x + 6, by)])


def _boss_death_debris(surf, name, col, prog, x0, y0, w, h):
    """Chunks separating from the body during crumble (flavor-shaped:
    rocks fall, prism shards scatter, feathers drift, molten drips)."""
    d = prog + 1
    if name == "prism":                      # shards scatter all directions
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            px = x0 + w // 2 + sx * (6 + 5 * d)
            py = y0 + h // 2 + sy * (5 + 4 * d)
            pygame.draw.polygon(surf, col, [
                (px, py - 2), (px + 2, py), (px, py + 2), (px - 2, py)])
    elif name == "wind":                     # feathers drift down slowly
        for ox in (-5, 0, 6):
            px = x0 + w // 2 + ox + prog
            py = y0 + h - 3 + 3 * d
            pygame.draw.line(surf, col, (px, py), (px + 3, py + 3), 1)
    elif name == "ember":                    # molten chunks drip downward
        for ox in (-4, 1, 5):
            pygame.draw.circle(surf, col,
                               (x0 + w // 2 + ox, y0 + h - 2 + 5 * d), 2)
    else:                                    # dust: rocks tumble down
        for ox in (-5, 0, 4):
            pygame.draw.rect(surf, col,
                             pygame.Rect(x0 + w // 2 + ox + prog,
                                         y0 + h - 2 + 6 * d, 3, 3))


def _boss_death_burst(surf, name, col_in, col_out, prog, cx, cy):
    """Radial flavor particles for the final explosion frames."""
    dist = 9 + 6 * prog
    for i in range(8):
        ang = i * math.pi / 4.0
        px = cx + int(math.cos(ang) * dist)
        py = cy + int(math.sin(ang) * dist)
        col = col_in if i % 2 == 0 else col_out
        if name == "ember":
            pygame.draw.circle(surf, col, (px, py), 2)
        elif name == "prism":
            pygame.draw.polygon(surf, col, [
                (px, py - 2), (px + 2, py), (px, py + 2), (px - 2, py)])
        elif name == "wind":                 # curved-ish motion streaks
            pygame.draw.line(surf, col, (px - 2, py - 1), (px + 2, py + 1), 1)
        else:                                # dust grit
            pygame.draw.rect(surf, col, pygame.Rect(px - 1, py - 1, 3, 3))


# Per-zone enemy palettes (SI-H): zones 1-3 get multiply-tinted copies of
# every cached frame, composed once at startup via C-speed BLEND_RGBA_MULT
# (alpha channel untouched). Zone 0 reuses the base dicts by construction
# (for_zone(0) is self), so pinned frame-identity tests stay valid.
ENEMY_ZONE_FRAMES = {}        # zone -> {key: surface} for zones 1..3
ENEMY_ZONE_HIT_FRAMES = {}    # zone -> {(key, hp): surface}
_ENEMY_ZONE_TINT = {
    1: (255, 208, 184),       # Ember Caves: warm ember wash
    2: (196, 216, 255),       # Frost Peaks: cool icy wash
    3: (212, 198, 236),       # Storm Keep: stormy violet wash
}


def _apply_zone_tint(source, tint):
    """Return a multiply-tinted copy of `source`. The tint alpha is 255 so
    BLEND_RGBA_MULT leaves per-pixel coverage exactly as composed."""
    s = source.copy()
    s.fill(tint + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def _build_enemy_frames():
    if ENEMY_FRAMES:                  # compose once; enemy art is palette-free
        return
    for phase in (0, 1):
        ENEMY_FRAMES[("walker", "patrol", phase)] = _mk_walker(phase)
        # chaser gaze variants (SI-C 4.1); 3-tuple aliases keep the
        # generic fallback path valid
        for pd in (-1, 0, 1, 2):
            ENEMY_FRAMES[("chaser", "patrol", phase, pd)] = \
                _mk_chaser(phase, False, pd)
            ENEMY_FRAMES[("chaser", "chase", phase, pd)] = \
                _mk_chaser(phase, True, pd)
        ENEMY_FRAMES[("chaser", "patrol", phase)] = \
            ENEMY_FRAMES[("chaser", "patrol", phase, 0)]
        ENEMY_FRAMES[("chaser", "chase", phase)] = \
            ENEMY_FRAMES[("chaser", "chase", phase, 2)]
        ENEMY_FRAMES[("shellback", "patrol", phase)] = _mk_shellback(phase)
        ENEMY_FRAMES[("flyer", "patrol", phase)] = _mk_flyer(phase)
    # SI-B: 4-frame stride cycles; the "patrol" keys above/below stay as
    # fallback aliases built from the first half of the same stride.
    for kind, maker in (("walker", _mk_walker), ("shellback", _mk_shellback),
                        ("shieldkin", _mk_shieldkin), ("bomber", _mk_bomber)):
        for phase in (0, 1, 2, 3):
            ENEMY_FRAMES[(kind, "walk", phase)] = maker(phase)
    for phase in (0, 1, 2, 3):                    # wallcrawler stride + grip
        ENEMY_FRAMES[("wallcrawler", "walk", phase)] = _mk_wallcrawler(phase)
    for phase in (0, 1):
        ENEMY_FRAMES[("wallcrawler", "grip", phase)] = \
            _mk_wallcrawler(phase, True)
    # SI-D: 5-frame squash-and-fade death sequences (proposal 3.1); the
    # ("kind", "dying", 0) key doubles as the generic fallback frame.
    dying = {
        "walker": _mk_walker_squash(),
        "chaser": _mk_chaser_squash(),
        "shellback": _mk_shellback_squash(),
        "flyer": _mk_flyer(0),
        "jumper": _mk_jumper(False),
        "spitter": _mk_spitter(0),
        "shieldkin": _mk_squash((104, 112, 130)),
        "bomber": _mk_squash((72, 76, 92)),
        "wallcrawler": _mk_squash((128, 92, 168)),
        "charger": _mk_squash((188, 108, 64)),
        "needler": _mk_squash((96, 150, 120)),
    }
    for kind, base in dying.items():
        for phase in range(5):
            ENEMY_FRAMES[(kind, "dying", phase)] = _apply_death(base, phase)
    ENEMY_FRAMES[("jumper", "patrol", 0)] = _mk_jumper(False)
    ENEMY_FRAMES[("jumper", "air", 0)] = _mk_jumper(True)
    ENEMY_FRAMES[("spitter", "patrol", 0)] = _mk_spitter(0)
    for pose in (1, 2, 3):                        # windup/execute/recovery
        ENEMY_FRAMES[("spitter", "attack", pose - 1)] = _mk_spitter(pose)
    for phase in (0, 1, 2):                       # spin + slide-glow (4.2)
        for glow in (0, 1):
            ENEMY_FRAMES[("shellback", "shell", phase, glow)] = \
                _mk_shell(phase, bool(glow))
    # ---- 5a: five new types ----
    for phase in (0, 1):
        ENEMY_FRAMES[("shieldkin", "patrol", phase)] = _mk_shieldkin(phase)
        ENEMY_FRAMES[("bomber", "patrol", phase)] = _mk_bomber(phase)
        ENEMY_FRAMES[("wallcrawler", "patrol", phase)] = _mk_wallcrawler(phase)
        ENEMY_FRAMES[("charger", "patrol", phase)] = _mk_charger(phase)
        ENEMY_FRAMES[("needler", "patrol", phase)] = _mk_needler(0)
    for level in (1, 2, 3):                       # charger horn coil (4.3)
        ENEMY_FRAMES[("charger", "windup", level - 1)] = \
            _mk_charger(0, level)
    ENEMY_FRAMES[("charger", "attack", 0)] = _mk_charger(0, 4)
    for pose in (1, 2, 3, 4):                     # needler aim/execute/recover
        ENEMY_FRAMES[("needler", "attack", pose - 1)] = _mk_needler(pose)

    # SI-A: every cached frame gets a 3-phase recoil variant, composed at
    # startup so enemy_frame() stays a dict lookup at runtime.
    for base_key, frame in ENEMY_FRAMES.items():
        for hp in (0, 1, 2):
            ENEMY_HIT_FRAMES[(base_key, hp)] = _apply_hit_flash(frame, hp)

    # SI-H: per-zone tinted copies for zones 1-3 (zone 0 = base identity).
    for zone, tint in _ENEMY_ZONE_TINT.items():
        ENEMY_ZONE_FRAMES[zone] = {
            key: _apply_zone_tint(frame, tint)
            for key, frame in ENEMY_FRAMES.items()}
        ENEMY_ZONE_HIT_FRAMES[zone] = {
            key: _apply_zone_tint(frame, tint)
            for key, frame in ENEMY_HIT_FRAMES.items()}


# ------------------------------------------------------------- backgrounds

# 2x2 Bayer thresholds for ordered dithering (Phase 2, T1)
_BAYER2 = ((0, 2), (3, 1))


def _shade(color, amount):
    """Fixed-offset shade of an RGB tuple (palette-safe: no new keys)."""
    return tuple(max(0, min(255, c + amount)) for c in color[:3])


def _make_sky(pal=None, bands=8):
    """Vertical gradient quantized to `bands` steps with 2x2 Bayer ordered
    dithering between adjacent bands (removes hard banding; Phase 2 T1).

    Per row the Bayer pattern yields at most two alternating colors (even
    vs odd columns), so rows are assembled as raw RGB bytes — no per-pixel
    Python set_at loop."""
    pal = pal or DEFAULT_PAL
    top = pal["sky_top"]
    bottom = pal["sky_bottom"]
    rows = []
    for y in range(VIEW_H):
        f = y / (VIEW_H - 1) * (bands - 1)
        lo = int(f)
        hi = min(bands - 1, lo + 1)
        frac = f - lo
        c_lo = tuple(int(top[i] + (bottom[i] - top[i]) * lo / (bands - 1))
                     for i in range(3))
        if hi == lo:
            rows.append(bytes(c_lo) * VIEW_W)
            continue
        c_hi = tuple(int(top[i] + (bottom[i] - top[i]) * hi / (bands - 1))
                     for i in range(3))
        t_even = (_BAYER2[y % 2][0] + 0.5) / 4.0
        t_odd = (_BAYER2[y % 2][1] + 0.5) / 4.0
        col_even = c_hi if frac > t_even else c_lo
        col_odd = c_hi if frac > t_odd else c_lo
        if col_even == col_odd:
            rows.append(bytes(col_even) * VIEW_W)
        else:
            rows.append((bytes(col_even) + bytes(col_odd)) * (VIEW_W // 2))
    s = pygame.image.frombuffer(b"".join(rows), (VIEW_W, VIEW_H), "RGB")
    return s.copy()                      # own the memory; SRCALPHA-free sky


def _make_mountains(width, base, amps, body, crest):
    """Tileable far-mountain silhouette strip (Phase 2, T2): simpler and
    darker than the hills, drawn between sky and clouds."""
    height = 90
    s = make_surface(width, height)
    for x in range(width):
        t = 2 * math.pi * x / width
        y = int(base + amps[0] * math.sin(t)
                + amps[1] * math.sin(3 * t + 0.9)
                + amps[2] * math.sin(5 * t + 2.4))
        pygame.draw.line(s, body, (x, y), (x, height - 1), 1)
        s.set_at((x, y), crest)
    return s


def _make_celestial(zone):
    """Small original sun (zones 0-1) or moon (zones 2-3) disc (Phase 2, T2).
    Subtle sky furniture — never reads as a gameplay object."""
    s = make_surface(26, 26)
    if zone <= 1:                                     # sun: warm disc + halo
        pygame.draw.circle(s, (255, 236, 170), (13, 13), 12)
        pygame.draw.circle(s, (255, 248, 210), (13, 13), 8)
        pygame.draw.circle(s, (255, 255, 240), (11, 11), 2)
    else:                                             # moon: pale + craters
        pygame.draw.circle(s, (226, 232, 246), (13, 13), 10)
        pygame.draw.circle(s, (200, 208, 228), (10, 11), 2)
        pygame.draw.circle(s, (204, 212, 232), (15, 15), 1)
        pygame.draw.circle(s, (200, 208, 228), (14, 10), 1)
    return s


def _make_hills(width, base, amps, body, crest):
    """Tileable rolling-hills strip (integer-period sines wrap seamlessly).

    Phase 2 (T3): interior speckle texture, second crest tone, and sparse
    treeline bumps on the silhouette — all derived from body/crest (no new
    palette keys); accents wrap with the strip."""
    height = 110
    s = make_surface(width, height)
    dk = _shade(body, -34)                 # speckle dark
    lt = _shade(body, 26)                  # speckle light
    crest_dk = _shade(crest, -28)          # second crest tone
    tree = _shade(body, -52)               # treeline silhouette
    period = max(8, width // 10)
    for x in range(width):
        t = 2 * math.pi * x / width
        y = int(base + amps[0] * math.sin(t)
                + amps[1] * math.sin(2 * t + 1.3)
                + amps[2] * math.sin(3 * t + 2.1))
        pygame.draw.line(s, body, (x, y), (x, height - 1), 1)
        s.set_at((x, y), crest)
        if y + 1 < height:
            s.set_at((x, y + 1), crest_dk)
        # interior speckle (deterministic sparse dots below the crest)
        for k, off in ((dk, 5), (lt, 9), (dk, 14)):
            sy = y + off + ((x * 7 + off * 3) % 4)
            if sy < height and (x + off) % 3:
                s.set_at((x, sy), k)
    # treeline bumps (wrap-safe: doubled when they cross the seam)
    for x in range(0, width, period):
        bump_h = 4 + (x // period) % 3
        t = 2 * math.pi * x / width
        y = int(base + amps[0] * math.sin(t)
                + amps[1] * math.sin(2 * t + 1.3)
                + amps[2] * math.sin(3 * t + 2.1))
        for dx in (-1, 0, 1):
            for edge in {x + dx, x + dx - width, x + dx + width}:
                if 0 <= edge < width:
                    for dy in range(bump_h):
                        s.set_at((edge, max(0, y - bump_h + dy)), tree)
    return s



def _make_powerup(kind, frame):
    """Small original orb sprite per power-up kind; 2-frame glint accent."""
    s = make_surface(14, 14)
    body = POWERUP_COLORS[kind]
    edge = tuple(max(0, c - 100) for c in body)
    hi = tuple(min(255, c + 70) for c in body)
    pygame.draw.circle(s, body, (7, 7), 5)
    pygame.draw.circle(s, edge, (7, 7), 5, 1)
    pygame.draw.circle(s, hi, (5, 5), 1)
    pygame.draw.circle(s, edge, (7, 2), 1)          # seam dot on top
    if frame:                                       # blinking glint
        s.set_at((10, 4), (255, 255, 255))
    return s


def _make_attack(kind, frame):
    """Tiny original attack sprite (8x8) per form kind; 2-frame accent."""
    s = make_surface(8, 8)
    body = FORM_COLORS[kind]
    if kind == "fire":
        pygame.draw.circle(s, body, (4, 4), 3)
        pygame.draw.circle(s, (255, 224, 130), (3, 3), 1)   # hot core
    elif kind == "ice":
        pygame.draw.polygon(s, body, [(1, 4), (4, 1), (7, 4), (4, 7)])
        pygame.draw.polygon(s, (230, 250, 255),
                            [(2, 4), (4, 2), (6, 4), (4, 6)], 1)
    else:                                                   # lightning
        for i, px in enumerate(range(1, 7)):
            s.set_at((px, 4 + (1 if (i + frame) % 2 else -1)), body)
        s.set_at((4, 4), (255, 255, 255))
    return s


def _make_door():
    """Original door-slab tile: vertical planks with iron bands."""
    s = make_surface(TILE, TILE)
    wood = (124, 84, 56)
    wood_lt = (150, 106, 72)
    band = (88, 92, 108)
    s.fill(wood)
    s.fill(wood_lt, pygame.Rect(2, 0, 2, TILE))
    s.fill(wood_lt, pygame.Rect(9, 0, 2, TILE))
    s.fill(band, pygame.Rect(0, 3, TILE, 2))
    s.fill(band, pygame.Rect(0, 11, TILE, 2))
    pygame.draw.circle(s, (210, 214, 230), (12, 8), 1)   # handle
    s.fill(OUTLINE, pygame.Rect(0, 0, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
    s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
    return s


def _make_switch_plate(active):
    """Original floor switch: low plate, pressed (dark) or raised (bright)."""
    s = make_surface(TILE, 8)
    body = (150, 156, 176) if active else (208, 214, 232)
    edge = (88, 92, 108)
    h = 3 if active else 5
    pygame.draw.rect(s, body, pygame.Rect(1, 8 - h, TILE - 2, h))
    pygame.draw.rect(s, edge, pygame.Rect(1, 8 - h, TILE - 2, h), 1)
    return s


def _make_plate(active):
    """Original pressure plate: wider, darker when fired (3b-1)."""
    s = make_surface(TILE, 8)
    body = (188, 140, 60) if active else (224, 196, 120)
    edge = (110, 74, 30)
    h = 3 if active else 5
    pygame.draw.rect(s, body, pygame.Rect(0, 8 - h, TILE, h))
    pygame.draw.rect(s, edge, pygame.Rect(0, 8 - h, TILE, h), 1)
    return s


def _make_shard(frame):
    """Original objective shard (3c): cyan crystal, 2-frame glint."""
    s = make_surface(12, 14)
    body = (120, 230, 255)
    edge = (40, 120, 160)
    hi = (240, 255, 255)
    pygame.draw.polygon(s, body, [(6, 0), (11, 5), (6, 13), (1, 5)])
    pygame.draw.polygon(s, edge, [(6, 0), (11, 5), (6, 13), (1, 5)], 1)
    pygame.draw.line(s, hi, (6, 2), (6, 11), 1)          # facet
    if frame:
        s.set_at((4, 4), hi)                              # glint
    return s


def _make_spiker(frame):
    """Original spiked slab (3b-2): iron block with rotating spikes."""
    s = make_surface(16, 16)
    body = (120, 126, 146)
    edge = (64, 68, 84)
    spike = (176, 186, 202)
    pygame.draw.rect(s, body, pygame.Rect(3, 3, 10, 10))
    pygame.draw.rect(s, edge, pygame.Rect(3, 3, 10, 10), 1)
    if frame % 2 == 0:                          # spikes N/E/S/W
        for cx, cy, dx, dy in ((8, 1, 0, -1), (14, 8, 1, 0),
                               (8, 14, 0, 1), (1, 8, -1, 0)):
            pygame.draw.polygon(s, spike,
                                [(cx, cy), (cx + dy * 3 - dx * 2,
                                            cy + dx * 3 - dy * 2),
                                 (cx - dy * 3 - dx * 2,
                                  cy - dx * 3 - dy * 2)])
    else:                                       # spikes on the diagonals
        for cx, cy in ((4, 4), (11, 4), (4, 11), (11, 11)):
            pygame.draw.circle(s, spike, (cx, cy), 2)
    pygame.draw.circle(s, edge, (8, 8), 2)
    return s


def _make_lava(frame):
    """Original lava tile: molten surface, 4-frame pulse (3b-1; Phase 3 T3
    extended the cycle 2 -> 4 with a travelling glow)."""
    s = make_surface(TILE, TILE)
    hot = ((255, 170, 40), (255, 150, 34), (255, 140, 30), (255, 155, 36))[frame % 4]
    deep = (190, 48, 20)
    glow = (255, 220, 90)
    s.fill(deep)
    s.fill(hot, pygame.Rect(0, 0, TILE, 6))
    for x in range(TILE):                          # bubbling surface
        if (x * 7 + frame * 3) % 11 < 3:
            s.set_at((x, 6), deep)
        if (x * 5 + frame * 2) % 13 == 4:          # secondary crust wave
            s.set_at((x, 4), deep)
    s.set_at((3 + frame * 2, 2), glow)             # glow travels L -> R
    s.set_at((11 - frame * 2, 3), glow)
    if frame % 2 == 0:                             # bubble pop every other
        s.set_at((7, 1), (255, 240, 160))
    return s


def _make_clouds(pal=None):
    pal = pal or DEFAULT_PAL
    s = make_surface(VIEW_W + 80, VIEW_H)
    clusters = [(50, 40, 1.0), (170, 24, 0.8), (280, 60, 1.2),
                (360, 30, 0.7)]
    for cx, cy, scale in clusters:
        for dx in (cx - (VIEW_W + 80), cx, cx + (VIEW_W + 80)):
            if dx < -60 or dx > VIEW_W + 80:
                continue
            for ox, oy, r in ((0, 0, 10), (12, -4, 13), (26, 0, 10),
                              (10, 5, 12), (22, 6, 9)):
                rr = int(r * scale)
                pygame.draw.circle(s, pal["cloud"],
                                   (int(dx + ox * scale), int(cy + oy)), rr)
                pygame.draw.circle(s, pal["cloud_dk"],
                                   (int(dx + ox * scale), int(cy + oy)), rr, 1)
    return s


def _make_foreground(tint):
    """Bottom-edge silhouette strip (Phase 2, T5): near-black foliage/rock
    bumps, at most 16 px tall; per-zone fixed tint (not palette keys).
    Tileable across the strip width."""
    w, h = VIEW_W + 80, 16
    s = make_surface(w, h)
    body = (*tint, 110)
    edge = (*_shade(tint, 22), 110)
    for x in range(w):
        # two overlapping sine periods -> organic, wrapping bump profile
        t = 2 * math.pi * x / w
        top = h - 3 - int(4.5 * (1 + math.sin(t * 3 + 0.4))
                          + 2.5 * (1 + math.sin(t * 7 + 2.0))) // 2
        top = max(2, min(h - 2, top))
        pygame.draw.line(s, body, (x, top), (x, h - 1), 1)
        s.set_at((x, top), edge)
    return s


def _make_aurora():
    """Two wavy translucent bands (Phase 2, T4: Frost Peaks shimmer)."""
    w, h = VIEW_W + 80, 46
    s = make_surface(w, h)
    for col, y0, amp, ph in (((120, 220, 190), 12, 6, 0.0),
                             ((150, 170, 240), 26, 8, 1.7)):
        for x in range(w):
            t = 2 * math.pi * x / w
            y = int(y0 + amp * math.sin(2 * t + ph))
            for dy in range(3):
                if 0 <= y + dy < h:
                    s.set_at((x, y + dy), (*col, 70 - dy * 18))
    return s


def _make_rain_veil():
    """Faint diagonal streak strip (Phase 2, T4: Storm Keep distance)."""
    w, h = VIEW_W + 80, 120
    s = make_surface(w, h)
    for i in range(90):
        x = (i * 53) % w
        y = (i * 37) % h
        for k in range(4):
            if x + k < w and y + k < h:
                s.set_at((x + k, y + k), (170, 190, 230, 46))
    return s


# ------------------------------------------------------- decorations (T4)
# Purely cosmetic overlay sprites (Phase 3). Never solid, never hashed,
# never validated — see Level.decorations and generator._scatter.

def _make_decoration(kind, frame=0):
    """Small original 16px-grid decoration sprite (Phase 3, T4).

    Drawn on top of the tile layer at the decorated tile's position; each
    kind is anchored so it reads against its host surface (mushrooms sit
    ON grass, stalactites hang FROM ceilings, etc.)."""
    s = make_surface(TILE, TILE)
    if kind == "mushroom":
        stem = (226, 214, 190)
        cap = (200, 70, 60) if frame == 0 else (216, 96, 74)
        s.fill(stem, pygame.Rect(7, 10, 2, 5))
        pygame.draw.ellipse(s, cap, pygame.Rect(4, 6, 8, 5))
        s.set_at((6, 7), (245, 235, 220))          # cap shine
        s.set_at((4, 15), OUTLINE)                 # base anchor pixel
        s.set_at((11, 15), OUTLINE)
    elif kind == "vine":
        leaf = (56, 130, 60)
        leaf_lt = (96, 172, 88)
        for i in range(12):                        # hanging strand
            x = 7 + (1 if i % 4 < 2 else 0)
            s.set_at((x, i), (44, 100, 48))
            if i % 3 == 1:
                s.set_at((x + 1, i), leaf)
            if i % 5 == 2:
                s.set_at((x - 1, i), leaf_lt)
    elif kind == "banner":
        rod = (110, 114, 130)
        cloth = (140, 70, 150) if frame == 0 else (128, 62, 140)
        cloth_lt = (180, 110, 190)
        s.fill(rod, pygame.Rect(2, 2, 12, 1))      # rod
        s.fill(cloth, pygame.Rect(3, 3, 9, 10))
        s.fill(cloth_lt, pygame.Rect(4, 4, 2, 8))  # fold highlight
        for i in range(3):                         # pennant tail
            s.set_at((3 + i * 4 // 2, 13), cloth)
    elif kind == "stalactite":
        rock = (128, 118, 138)
        rock_dk = (96, 88, 106)
        tip = (168, 160, 180)
        for i in range(10):                        # tapering cone
            wdt = max(1, 6 - i * 2 // 3)
            x0 = 8 - wdt // 2
            s.fill(rock if (i + frame) % 2 else rock_dk,
                   pygame.Rect(x0, i, wdt, 1))     # banding shifts per frame
        s.set_at((8, 9), tip)                      # dripping tip
        if frame % 3 == 1:
            s.set_at((8, 12), (180, 200, 230))     # droplet forming
        elif frame % 3 == 2:
            s.set_at((8, 14), (180, 200, 230))     # droplet falling
    elif kind == "torch":
        s.fill((96, 66, 44), pygame.Rect(7, 8, 2, 7))   # handle
        s.fill((60, 42, 28), pygame.Rect(6, 14, 4, 2))  # bracket
        flame = ((255, 180, 60), (255, 210, 90))[frame % 2]
        core = (255, 240, 170)
        pygame.draw.polygon(s, flame, [(5, 8), (8, 1), (11, 8)])
        s.set_at((8, 3), core)
        if frame % 2:
            s.set_at((8, 0), (255, 160, 40))           # flicker tip
    elif kind == "icicle":
        ice = (180, 220, 248)
        ice_dk = (140, 190, 228)
        for i in range(8):
            wdt = max(1, 4 - i // 2)
            x0 = 8 - wdt // 2
            s.fill(ice if i % 2 else ice_dk, pygame.Rect(x0, i, wdt, 1))
        s.set_at((8, 8), (230, 246, 255))             # glint tip
        if frame % 3 == 1:
            s.set_at((8, 11), (200, 232, 252))        # drip forming
        elif frame % 3 == 2:
            s.set_at((8, 13), (200, 232, 252))        # drip falling
    return s


DECORATION_KINDS = ("mushroom", "vine", "banner",
                    "stalactite", "torch", "icicle")
# animated kinds -> frame count (others are single-frame)
DECORATION_FRAMES = {"torch": 2, "icicle": 3, "stalactite": 3,
                     "mushroom": 2, "banner": 2}


def _make_goal_glow():
    """Warm radial unlock glow (Phase 5 T5): concentric alpha rings built
    small, smoothscaled once for a soft falloff. Palette-independent."""
    small = make_surface(24, 24)
    for r, a in ((11, 48), (8, 104), (5, 168)):
        pygame.draw.circle(small, (255, 236, 170, a), (12, 12), r)
    return pygame.transform.smoothscale(small, (48, 48))



# ------------------------------------------------------------- asset cache

class AssetFactory:
    """Builds and caches every surface the game needs at startup."""

    def __init__(self, pal=None, zone=0):
        self._pal = pal or DEFAULT_PAL
        self._zone = max(0, zone)   # SI-H: enemy palette theme (0 = base)
        _build_player_frames()
        _build_enemy_frames()
        self._terrain = [_terrain_variant(m, self._pal, self._zone)
                         for m in range(16)]
        self._brick = _make_brick(self._pal)
        self._question = [_make_question(f) for f in range(4)]
        self._used = _make_used()
        self._pipes = {tid: _make_pipe(tid) for tid in
                       (T.PIPE_TL, T.PIPE_TR, T.PIPE_BL, T.PIPE_BR)}
        self._spike = _make_spike()
        self._door = _make_door()
        self._switch_plates = {False: _make_switch_plate(False),
                               True: _make_switch_plate(True)}
        self._plates = {False: _make_plate(False), True: _make_plate(True)}
        self._lava = [_make_lava(f) for f in range(4)]   # Phase 3 T3: 4 frames
        self._spiker = [_make_spiker(f) for f in range(2)]
        self._shards = [_make_shard(f) for f in range(2)]
        self._coins = [_make_coin(f) for f in range(4)]
        self._powerups = {(kind, f): _make_powerup(kind, f)
                          for kind in POWERUP_COLORS for f in range(2)}
        self._attacks = {(kind, f): _make_attack(kind, f)
                         for kind in FORM_COLORS for f in range(2)}
        self._checkpoints = {False: _make_checkpoint(False),
                             True: _make_checkpoint(True)}
        self._goal = _make_goal_gate()
        self._goal_glow = _make_goal_glow()   # unlock flourish (Phase 5 T5)
        self._platform = _make_platform_seg()
        self._projectiles = [_make_projectile(i * 5) for i in range(3)]
        self._sky = _make_sky(self._pal)
        self._mountains = _make_mountains(
            200, 46, (14, 8, 5),
            _shade(self._pal["hills_far_body"], -40),
            _shade(self._pal["hills_far_crest"], -30))
        self._celestial = _make_celestial(self._zone)
        self._hills_far = _make_hills(
            240, 62, (16, 7, 4),
            self._pal["hills_far_body"], self._pal["hills_far_crest"])
        self._hills_near = _make_hills(
            320, 72, (22, 9, 5),
            self._pal["hills_near_body"], self._pal["hills_near_crest"])
        self._clouds = _make_clouds(self._pal)
        self._foreground = _make_foreground(FG_TINTS[self._zone])
        # per-zone sky events (Phase 2 T4); other zones hold None
        self._aurora = _make_aurora() if self._zone == 2 else None
        self._rain_veil = _make_rain_veil() if self._zone == 3 else None
        # decoration overlay cache (Phase 3 T4): shared, palette-independent
        self._decorations = {
            (kind, f): _make_decoration(kind, f)
            for kind in DECORATION_KINDS
            for f in range(DECORATION_FRAMES.get(kind, 1))}
        self._flip = {}
        self._zone_factories = {}

    def for_zone(self, zone):
        """Themed factory for a zone (4b). Zone 0 returns SELF — the legacy
        palette IS zone 0, so identity is guaranteed by construction."""
        if zone <= 0:
            return self
        fac = self._zone_factories.get(zone)
        if fac is None:
            merged = dict(DEFAULT_PAL)
            merged.update(ZONES[zone]["palette"] or {})
            fac = AssetFactory(pal=merged, zone=zone)
            self._zone_factories[zone] = fac
        return fac

    @property
    def zone(self):
        """Theme zone this factory serves (0 = legacy identity)."""
        return self._zone

    # ------------------------------------------------------ tiles/objects
    def terrain(self, mask):
        return self._terrain[mask & 15]

    def brick(self):
        return self._brick

    def question(self, frame):
        return self._question[frame % 4]

    def used_block(self):
        return self._used

    def pipe(self, tid):
        return self._pipes[tid]

    def spike(self):
        return self._spike

    def door(self):
        return self._door

    def switch_plate(self, active):
        return self._switch_plates[bool(active)]

    def plate(self, active):
        return self._plates[bool(active)]

    def lava(self, frame):
        return self._lava[frame % 4]

    def spiker(self, frame):
        return self._spiker[frame % 2]

    def shard(self, frame):
        return self._shards[frame % 2]

    def coin(self, frame):
        return self._coins[frame % 4]

    def powerup(self, kind, frame):
        return self._powerups[(kind, frame % 2)]

    def attack_frame(self, kind, frame):
        return self._attacks[(kind, frame % 2)]

    def checkpoint(self, active):
        return self._checkpoints[bool(active)]

    def goal_gate(self):
        return self._goal

    def goal_glow(self):
        """Radial unlock glow (Phase 5 T5); caller sets alpha per frame."""
        return self._goal_glow

    def platform_seg(self):
        return self._platform

    def projectile(self, tick):
        return self._projectiles[(tick // 5) % 3]

    # -------------------------------------------------------- backgrounds
    def sky(self):
        return self._sky

    def hills_far(self):
        return self._hills_far

    def hills_near(self):
        return self._hills_near

    def clouds(self):
        return self._clouds

    def mountains(self):
        return self._mountains

    def celestial(self):
        return self._celestial

    def foreground(self):
        return self._foreground

    def aurora(self):
        """Frost Peaks shimmer strip (None outside zone 2)."""
        return self._aurora

    def rain_veil(self):
        """Storm Keep distance streaks (None outside zone 3)."""
        return self._rain_veil

    def decoration(self, kind, frame=0):
        """Cosmetic overlay sprite (Phase 3 T4); clamped to available frames."""
        n = DECORATION_FRAMES.get(kind, 1)
        return self._decorations[(kind, frame % n)]

    # ------------------------------------------------------------ sprites
    def _flipped(self, key, img):
        got = self._flip.get(key)
        if got is None:
            got = pygame.transform.flip(img, True, False)
            self._flip[key] = got
        return got

    def player_frame(self, state, anim_t, facing):
        frames = PLAYER_FRAMES.get(state) or PLAYER_FRAMES["idle"]
        if state == "run":
            idx = (anim_t // 5) % len(frames)
        else:
            idx = 0
        img = frames[idx]
        if facing < 0:
            return self._flipped(("p", state, idx), img)
        return img

    def enemy_frame(self, enemy):
        kind = enemy.KIND
        st = enemy.state
        if st == "dying":
            # SI-D: 6 ticks per phase across the 30-tick corpse window
            elapsed = max(0, getattr(enemy, "DEATH_TICKS", 30)
                          - enemy.death_timer)
            key = (kind, "dying", min(4, elapsed // 6))
        elif kind == "shellback" and st == "shell":
            slide = abs(enemy.vx) > 0.5
            frame = (enemy.anim_t // 5) % 3 if slide else 0
            key = (kind, "shell", frame, 1 if slide else 0)  # glow ring
        elif kind == "spitter":
            fl = getattr(enemy, "flash", 0)
            if fl > 5:
                key = (kind, "attack", 1)          # execute
            elif fl > 0:
                key = (kind, "attack", 2)          # recovery
            elif getattr(enemy, "windup", 0):
                key = (kind, "attack", 0)          # windup
            else:
                key = (kind, "patrol", 0)
        elif kind == "jumper":
            key = (kind, "patrol" if enemy.on_ground else "air", 0)
        elif kind == "chaser":
            pd = getattr(enemy, "pupil_dx", 2 if st == "chase" else 0)
            key = (kind, st, (enemy.anim_t // 8) % 2, max(-1, min(2, pd)))
        elif kind == "charger":
            if enemy.state == "attack":
                key = (kind, "attack", 0)
            elif getattr(enemy, "windup", 0) > 0:
                glow = max(1, min(3, getattr(enemy, "horn_glow", 1)))
                key = (kind, "windup", glow - 1)
            else:
                key = (kind, "patrol", (enemy.anim_t // 8) % 2)
        elif kind == "needler":
            fl = getattr(enemy, "flash", 0)
            glow = getattr(enemy, "barrel_glow", 0)
            if fl > 3:
                key = (kind, "attack", 2)          # execute: extended barrel
            elif fl > 0:
                key = (kind, "attack", 3)          # recovery
            elif glow:
                key = (kind, "attack", glow - 1)   # aim glow tiers
            else:
                key = (kind, "patrol", 0)
        elif kind == "bomber":
            step = 3 if getattr(enemy, "targeting", False) else 6
            key = (kind, "walk", (enemy.anim_t // step) % 4)
        elif kind == "wallcrawler":
            if enemy.state in ("climb", "ceiling"):
                key = (kind, "grip", (enemy.anim_t // 8) % 2)
            else:
                key = (kind, "walk", (enemy.anim_t // 6) % 4)
        elif kind in WALK_KINDS:                  # 4-frame stride (SI-B)
            key = (kind, "walk", (enemy.anim_t // 6) % 4)
        else:
            key = (kind, "patrol", (enemy.anim_t // 8) % 2)
        # SI-H: themed factories serve multiply-tinted zone copies; the
        # zone-0 factory serves the base dicts (identity preserved).
        frames = ENEMY_ZONE_FRAMES.get(self._zone, ENEMY_FRAMES)
        img = frames.get(key)
        if img is None:
            img = frames.get((kind, "patrol", 0),
                             ENEMY_FRAMES[(kind, "dying", 0)])
        flip_key = key
        if getattr(enemy, "hit_flash", 0) > 0:        # recoil (SI-A)
            hf = enemy.hit_flash
            hp = 0 if hf > 4 else 1 if hf > 2 else 2
            hit = ENEMY_ZONE_HIT_FRAMES.get(
                self._zone, ENEMY_HIT_FRAMES).get((key, hp))
            if hit is not None:
                img = hit
                flip_key = key + ("hit", hp)
        if enemy.facing < 0 and st != "dying":
            return self._flipped(("e",) + flip_key, img)
        return img






