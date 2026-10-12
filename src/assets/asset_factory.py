"""
Runtime asset factory: generates every sprite/tile/background surface at
startup with pygame primitives (no external files, no downloaded art).

Art style: bold dark outlines, limited palette, light from top-left,
consistent 16px grid. Results are cached in dicts keyed by variant.
"""

import math

import pygame

from src.config import TILE, VIEW_W, VIEW_H
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


def make_surface(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _outline_rect(surf, rect, color=OUTLINE, width=1):
    pygame.draw.rect(surf, color, rect, width)


def _dotted(surf, color, points):
    for px, py in points:
        surf.set_at((px, py), color)


# ------------------------------------------------------------------- tiles

def _terrain_variant(mask):
    """Generate one 16x16 autotile variant for terrain (mask bits N/E/S/W)."""
    s = make_surface(TILE, TILE)
    n, e, so, w = mask & 1, mask & 2, mask & 4, mask & 8
    # dirt body
    s.fill(DIRT)
    _dotted(s, DIRT_DK, [(3, 7), (11, 4), (6, 12), (13, 11), (9, 9), (2, 13)])
    _dotted(s, DIRT_LT, [(5, 5), (12, 8), (8, 13), (14, 6), (1, 9)])
    # grass cap when no solid above
    if not n:
        s.fill(GRASS, pygame.Rect(0, 0, TILE, 4))
        for gx in range(0, TILE, 3):            # tufts
            s.set_at((gx, 4), GRASS_DK)
        s.fill(GRASS_DK, pygame.Rect(0, 4, TILE, 1))
        for gx in (1, 2, 6, 7, 11, 12):
            s.set_at((gx, 1), GRASS_LT)
    # exposed-side outlines
    if not w:
        s.fill(OUTLINE, pygame.Rect(0, 0, 1, TILE))
        if not n:
            s.fill(OUTLINE, pygame.Rect(1, 0, 1, 4))
    if not e:
        s.fill(OUTLINE, pygame.Rect(TILE - 1, 0, 1, TILE))
        if not n:
            s.fill(OUTLINE, pygame.Rect(TILE - 2, 0, 1, 4))
    if not so:
        s.fill(OUTLINE, pygame.Rect(0, TILE - 1, TILE, 1))
    if not n:
        for gx in range(TILE):            # top edge outline where exposed
            if s.get_at((gx, 0))[3] == 0:
                s.set_at((gx, 0), OUTLINE)
    return s


def _make_brick():
    s = make_surface(TILE, TILE)
    s.fill(BRICK)
    for row in range(4):
        y0 = row * 4
        s.fill(MORTAR, pygame.Rect(0, y0, TILE, 1))
        offset = 0 if row % 2 == 0 else 8
        for x in range(offset, TILE, 8):
            s.fill(MORTAR, pygame.Rect(x, y0, 1, 4))
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
    pygame.draw.ellipse(s, WALKER_BODY, pygame.Rect(1, 1, 14, 11))
    pygame.draw.ellipse(s, WALKER_DK, pygame.Rect(1, 7, 14, 5))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 1, 14, 11), 1)
    _eyes(s, 4, 4, 9, 1)
    s.fill(OUTLINE, pygame.Rect(4, 3, 3, 1))          # angry brows
    s.fill(OUTLINE, pygame.Rect(9, 3, 3, 1))
    s.set_at((6, 2), OUTLINE)
    s.set_at((9, 2), OUTLINE)
    if phase == 0:
        s.fill(WALKER_DK, pygame.Rect(2, 12, 5, 3))
        s.fill(WALKER_DK, pygame.Rect(9, 13, 5, 2))
    else:
        s.fill(WALKER_DK, pygame.Rect(3, 13, 5, 2))
        s.fill(WALKER_DK, pygame.Rect(8, 12, 5, 3))
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


def _mk_chaser(phase, chase=False):
    s = make_surface(16, 16)
    pygame.draw.ellipse(s, CHASER_RED, pygame.Rect(1, 3, 14, 10))
    pygame.draw.ellipse(s, CHASER_DK, pygame.Rect(1, 9, 14, 4))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(1, 3, 14, 10), 1)
    _eyes(s, 6, 4, 9, 2 if chase else 1)
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


def _mk_shell(phase=0):
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
    return s


def _mk_shellback(phase):
    s = make_surface(16, 16)
    s.fill(SHELL_GREEN, pygame.Rect(9, 0, 6, 6))     # head, upper-right
    s.fill((196, 226, 140), pygame.Rect(10, 2, 4, 3))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(9, 0, 6, 6), 1)
    s.fill(WHITE, pygame.Rect(12, 1, 2, 2))
    s.set_at((13, 2), OUTLINE)
    s.blit(_mk_shell(0), (0, 4))
    if phase == 0:
        s.fill(SHELL_RIM, pygame.Rect(2, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(10, 14, 4, 2))
    else:
        s.fill(SHELL_RIM, pygame.Rect(3, 14, 4, 2))
        s.fill(SHELL_RIM, pygame.Rect(9, 13, 4, 2))
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
    wing_col = (198, 152, 232)
    if wing_up:
        pygame.draw.polygon(s, wing_col, [(4, 8), (0, 2), (7, 6)])
        pygame.draw.polygon(s, wing_col, [(12, 8), (16, 2), (9, 6)])
    else:
        pygame.draw.polygon(s, wing_col, [(4, 7), (0, 13), (7, 9)])
        pygame.draw.polygon(s, wing_col, [(12, 7), (16, 13), (9, 9)])
    pygame.draw.ellipse(s, (150, 88, 200), pygame.Rect(4, 4, 8, 9))
    pygame.draw.ellipse(s, (102, 54, 148), pygame.Rect(4, 9, 8, 4))
    pygame.draw.ellipse(s, OUTLINE, pygame.Rect(4, 4, 8, 9), 1)
    _eyes(s, 6, 5, 9, 1)
    s.fill(WHITE, pygame.Rect(6, 11, 1, 2))
    s.fill(WHITE, pygame.Rect(9, 11, 1, 2))
    return s


def _mk_spitter(open_mouth=False):
    s = make_surface(16, 20)
    pygame.draw.rect(s, (130, 138, 154), pygame.Rect(2, 6, 12, 13))
    pygame.draw.rect(s, (84, 90, 106), pygame.Rect(2, 15, 12, 4))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(2, 6, 12, 13), 1)
    pygame.draw.rect(s, (130, 138, 154), pygame.Rect(4, 2, 10, 5))
    pygame.draw.rect(s, OUTLINE, pygame.Rect(4, 2, 10, 5), 1)
    pygame.draw.rect(s, (84, 90, 106), pygame.Rect(11, 3, 3, 3))
    if open_mouth:
        pygame.draw.circle(s, (255, 150, 40), (13, 4), 2)
        pygame.draw.circle(s, OUTLINE, (13, 4), 2, 1)
    else:
        pygame.draw.rect(s, OUTLINE, pygame.Rect(12, 3, 2, 3))
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


def _build_enemy_frames():
    for phase in (0, 1):
        ENEMY_FRAMES[("walker", "patrol", phase)] = _mk_walker(phase)
        ENEMY_FRAMES[("chaser", "patrol", phase)] = _mk_chaser(phase)
        ENEMY_FRAMES[("chaser", "chase", phase)] = _mk_chaser(phase, True)
        ENEMY_FRAMES[("shellback", "patrol", phase)] = _mk_shellback(phase)
        ENEMY_FRAMES[("flyer", "patrol", phase)] = _mk_flyer(phase)
    ENEMY_FRAMES[("walker", "dying", 0)] = _mk_walker_squash()
    ENEMY_FRAMES[("chaser", "dying", 0)] = _mk_chaser_squash()
    ENEMY_FRAMES[("shellback", "dying", 0)] = _mk_shellback_squash()
    ENEMY_FRAMES[("flyer", "dying", 0)] = _mk_flyer(0)
    ENEMY_FRAMES[("jumper", "dying", 0)] = _mk_jumper(False)
    ENEMY_FRAMES[("spitter", "dying", 0)] = _mk_spitter(False)
    ENEMY_FRAMES[("jumper", "patrol", 0)] = _mk_jumper(False)
    ENEMY_FRAMES[("jumper", "air", 0)] = _mk_jumper(True)
    ENEMY_FRAMES[("spitter", "patrol", 0)] = _mk_spitter(False)
    ENEMY_FRAMES[("spitter", "attack", 0)] = _mk_spitter(True)
    for phase in (0, 1, 2):
        ENEMY_FRAMES[("shellback", "shell", phase)] = _mk_shell(phase)


# ------------------------------------------------------------- backgrounds

def _make_sky():
    s = make_surface(VIEW_W, VIEW_H)
    top = (92, 148, 250)
    bottom = (172, 214, 255)
    for y in range(VIEW_H):
        f = y / (VIEW_H - 1)
        col = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
        s.fill(col, pygame.Rect(0, y, VIEW_W, 1))
    return s


def _make_hills(width, base, amps, body, crest):
    """Tileable rolling-hills strip (integer-period sines wrap seamlessly)."""
    height = 110
    s = make_surface(width, height)
    for x in range(width):
        t = 2 * math.pi * x / width
        y = int(base + amps[0] * math.sin(t)
                + amps[1] * math.sin(2 * t + 1.3)
                + amps[2] * math.sin(3 * t + 2.1))
        pygame.draw.line(s, body, (x, y), (x, height - 1), 1)
        s.set_at((x, y), crest)
        if y + 1 < height:
            s.set_at((x, y + 1), crest)
    return s


def _make_clouds():
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
                pygame.draw.circle(s, (252, 253, 255),
                                   (int(dx + ox * scale), int(cy + oy)), rr)
                pygame.draw.circle(s, (216, 228, 248),
                                   (int(dx + ox * scale), int(cy + oy)), rr, 1)
    return s


# ------------------------------------------------------------- asset cache

class AssetFactory:
    """Builds and caches every surface the game needs at startup."""

    def __init__(self):
        _build_player_frames()
        _build_enemy_frames()
        self._terrain = [_terrain_variant(m) for m in range(16)]
        self._brick = _make_brick()
        self._question = [_make_question(f) for f in range(4)]
        self._used = _make_used()
        self._pipes = {tid: _make_pipe(tid) for tid in
                       (T.PIPE_TL, T.PIPE_TR, T.PIPE_BL, T.PIPE_BR)}
        self._spike = _make_spike()
        self._coins = [_make_coin(f) for f in range(4)]
        self._checkpoints = {False: _make_checkpoint(False),
                             True: _make_checkpoint(True)}
        self._goal = _make_goal_gate()
        self._platform = _make_platform_seg()
        self._projectiles = [_make_projectile(i * 5) for i in range(3)]
        self._sky = _make_sky()
        self._hills_far = _make_hills(
            240, 62, (16, 7, 4), (94, 150, 152), (130, 188, 178))
        self._hills_near = _make_hills(
            320, 72, (22, 9, 5), (56, 138, 74), (98, 180, 98))
        self._clouds = _make_clouds()
        self._flip = {}

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

    def coin(self, frame):
        return self._coins[frame % 4]

    def checkpoint(self, active):
        return self._checkpoints[bool(active)]

    def goal_gate(self):
        return self._goal

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
            key = (kind, "dying", 0)
        elif kind == "shellback" and st == "shell":
            frame = (enemy.anim_t // 5) % 3 if abs(enemy.vx) > 0.5 else 0
            key = (kind, "shell", frame)
        elif kind == "spitter":
            attack = getattr(enemy, "flash", 0) > 0
            key = (kind, "attack" if attack else "patrol", 0)
        elif kind == "jumper":
            key = (kind, "patrol" if enemy.on_ground else "air", 0)
        elif kind == "chaser" and st == "chase":
            key = (kind, "chase", (enemy.anim_t // 8) % 2)
        else:
            key = (kind, "patrol", (enemy.anim_t // 8) % 2)
        img = ENEMY_FRAMES.get(key)
        if img is None:
            img = ENEMY_FRAMES.get((kind, "patrol", 0),
                                   ENEMY_FRAMES[(kind, "dying", 0)])
        if enemy.facing < 0 and st != "dying":
            return self._flipped(("e",) + key, img)
        return img






