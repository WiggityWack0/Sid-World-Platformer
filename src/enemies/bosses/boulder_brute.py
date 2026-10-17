"""Boulder Brute (5c, Green Hills): slam jumps -> ground shockwaves,
rock throws (reuses the Bomber's arcing Bomb). Faster cycles per phase."""

import pygame

from src import config
from src.assets.asset_factory import _draw_boss_death
from src.enemies.bomber import Bomb
from src.enemies.boss import Boss

WAVE_BODY = (150, 110, 70)

# Crack network (SI-E 5.4), relative to the 32x32 canvas; phase gates how
# many are drawn — 2 minor / 6 spreading / full network + lava seep.
_CRACKS = (
    ((6, 4), (12, 10)), ((20, 5), (15, 12)),     # phase 0: minor cracks
    ((14, 13), (9, 18)), ((17, 15), (22, 20)),   # phase 1: spread from
    ((10, 16), (12, 24)), ((19, 12), (25, 16)),  #        the center
    ((7, 21), (12, 27)), ((23, 20), (18, 26)),   # phase 2: full network
)
_CRACK_N = (2, 6, 8)


class GroundWave:
    """Low shockwave that hugs the floor and dies on walls/timeout."""
    W = 14
    H = 8
    SPEED = 4.2
    LIFE = 90

    def __init__(self, x, y, direction):
        self.x = float(x)
        self.y = float(y)
        self.vx = self.SPEED * direction
        self.life = self.LIFE

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def dead(self):
        return self.life <= 0

    def update(self, level):
        self.life -= 1
        self.x += self.vx
        r = self.rect
        tx = int(r.centerx // config.TILE)
        ty = int(r.centery // config.TILE)
        if level.solid_at(tx, ty) or self.x < -32 \
                or self.x > level.width + 32:
            self.life = 0

    def draw(self, surf, cam, assets, tick):
        pygame.draw.rect(surf, WAVE_BODY,
                         pygame.Rect(int(self.x) - cam.ix,
                                     int(self.y) - cam.iy, self.W, self.H))
        pygame.draw.rect(surf, (70, 48, 30),
                         pygame.Rect(int(self.x) - cam.ix,
                                     int(self.y) - cam.iy, self.W, self.H), 1)


class BoulderBrute(Boss):
    KIND = "boulder_brute"
    name = "BOULDER BRUTE"
    MAX_HP = config.BOULDER_HP
    W = 32
    H = 32
    DEATH_SHAPE = "rect"           # inline defeat draw (SI-E 3.2)
    DEATH_FLAVOR = "dust"
    DEATH_BODY = (150, 110, 70)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.mode = "idle"          # idle -> telegraph -> airborne
        self.atk = 90               # opening grace before the first slam
        self.slams = 0
        self.shots = []             # drained by EnemyManager

    def think(self, level, player):
        self.vx = 0.0
        if self.stagger > 0:
            return                              # vulnerable: stands still
        if not player.dead:
            dx = player.cx - self.cx
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        if self.mode == "idle":
            self.atk -= 1
            if self.atk <= 0:
                self.mode = "telegraph"
                self.telegraph = self.TELEGRAPH
                if self.slams % 2 == 1 or self.phase >= 1:
                    t = max(18.0, abs(player.cx - self.cx) / 3.0)
                    self.shots.append(Bomb(
                        self.cx, self.y - 4,
                        (player.cx - self.cx) / t if not player.dead else 0.0,
                        config.BOULDER_ROCK_VY))
        elif self.mode == "telegraph":
            if self.telegraph <= 0:
                self.mode = "airborne"
                self.vy = -8.2                  # big telegraphed hop
                self.slams += 1
        # airborne -> handled by landed()

    def landed(self):
        if self.mode == "airborne":
            self.mode = "idle"
            self.atk = max(36, config.BOULDER_SLAM_CYCLE - 26 * self.phase)
            wave_y = self.rect.bottom - 8
            for d in (-1, 1):
                self.shots.append(GroundWave(self.cx, wave_y, d))
            if self.phase >= 2:                 # final phase: double wave
                self.shots.append(GroundWave(self.cx, wave_y, -1))

    def draw(self, surf, cam, assets, tick):
        if self.state == "dying":
            _draw_boss_death(self, surf, cam, tick)   # staged defeat (3.2)
            return
        r = self.rect
        dx, dy, w, h = self.windup_pose(tick, dip=6)  # crouch (5.3)
        bx, by = r.x - cam.ix + dx, r.y - cam.iy + dy
        by += self.idle_bob(tick, 32)        # breathing dip (SI-G)
        rect = pygame.Rect(bx, by, w, h)
        # phase palettes (5.2): rock darkens as the crack network spreads
        body = ((150, 110, 70), (132, 98, 64), (116, 86, 58))[min(2, self.phase)]
        if self.telegraph > 0 and self.mode == "telegraph" \
                and (tick // 4) % 2 == 0:
            body = (210, 160, 90)                # wind-up flash (5.3)
        elif self.stagger > 0 and (tick // 5) % 2 == 0:
            body = (206, 168, 120)               # vulnerable flash (5b)
        pygame.draw.rect(surf, body, rect)
        self._cracks(surf, rect, tick)           # detail layer (5.4)
        pygame.draw.rect(surf, (70, 48, 30), rect, 2)
        if self.blinking(tick):              # idle blink (SI-G)
            for ox in (7, rect.w - 12):
                pygame.draw.line(surf, (70, 48, 30),
                                 (bx + ox, by + 11),
                                 (bx + ox + 4, by + 11), 1)
        else:
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + 7, by + 9, 5, 4))
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + rect.w - 12, by + 9, 5, 4))
        if self.telegraph > 0:
            self._windup_fx(surf, rect, tick)    # arms + dust (5.3)

    def _cracks(self, surf, rect, tick):
        """Crack texture grows with phase; molten seams pulse at phase 2
        (proposal 5.4: 1-2 minor / 4-6 spreading / network + lava seep)."""
        n = _CRACK_N[min(2, self.phase)]
        for a, b in _CRACKS[:n]:
            pygame.draw.line(surf, (58, 40, 26),
                             (rect.x + a[0] * rect.w // 32,
                              rect.y + a[1] * rect.h // 32),
                             (rect.x + b[0] * rect.w // 32,
                              rect.y + b[1] * rect.h // 32), 1)
        if self.phase >= 2:                      # lava seeps through gaps
            lava = (255, 132, 40) if (tick // 6) % 2 == 0 else (196, 70, 28)
            for a, b in _CRACKS[:2]:
                pygame.draw.line(surf, lava,
                                 (rect.x + a[0] * rect.w // 32,
                                  rect.y + a[1] * rect.h // 32),
                                 (rect.x + b[0] * rect.w // 32,
                                  rect.y + b[1] * rect.h // 32), 1)

    def _windup_fx(self, surf, rect, tick):
        """Wind-up flourish (5.3): arms raised overhead, dust at the feet."""
        for ox in (1, rect.w - 7):
            arm = pygame.Rect(rect.x + ox, rect.y - 5, 6, 5)
            pygame.draw.rect(surf, (122, 90, 58), arm)
            pygame.draw.rect(surf, (70, 48, 30), arm, 1)
        for i in range(3):
            px = rect.x + 3 + ((tick // 3 + i * 7) % max(4, rect.w - 6))
            pygame.draw.circle(surf, (196, 176, 146),
                               (px, rect.bottom - 1), 1 + (i + tick // 3) % 2)