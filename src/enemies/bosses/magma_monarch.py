"""Magma Monarch (5c, Molten Keep): fireball volleys; the final phase adds
lava blobs that leave short-lived lava puddles (runtime tile edits with
deterministic cleanup — charger-brick precedent)."""

import pygame

from src import config
from src.config import TILE
from src.assets.asset_factory import _draw_boss_death
from src.enemies.boss import Boss
from src.level import tiles as T

FIRE_BODY = (255, 140, 40)


class MonarchFire:
    """Aimed fireball; final-phase lava blobs leave a lava puddle on
    impact with the floor."""
    W = 10
    H = 10
    LIFE = 140

    def __init__(self, x, y, vx, vy, lava=False):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.life = self.LIFE
        self.lava = lava
        self.owner = None                   # set by the monarch

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def dead(self):
        return self.life <= 0

    def update(self, level):
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        r = self.rect
        tx = int(r.centerx // TILE)
        ty = int(r.centery // TILE)
        floor_ty = int((r.bottom + 2) // TILE)
        hit_floor = level.solid_at(tx, floor_ty) \
            and not level.tiles.hazard_at(tx, floor_ty)
        if self.lava and self.owner is not None and self.vy > 0 \
                and hit_floor:
            self.life = 0
            self.owner.puddle_at(level, tx, floor_ty - 1)
        elif level.solid_at(tx, ty):
            self.life = 0
        if self.x < -32 or self.x > level.width + 32 \
                or self.y > level.height + 32:
            self.life = 0

    def draw(self, surf, cam, assets, tick):
        body = (255, 90, 30) if self.lava else FIRE_BODY
        pygame.draw.circle(surf, body,
                           (int(self.x) + 5 - cam.ix, int(self.y) + 5 - cam.iy),
                           5)
        pygame.draw.circle(surf, (140, 40, 20),
                           (int(self.x) + 5 - cam.ix, int(self.y) + 5 - cam.iy),
                           5, 1)


class MagmaMonarch(Boss):
    KIND = "magma_monarch"
    name = "MAGMA MONARCH"
    MAX_HP = config.MONARCH_HP
    W = 32
    H = 36
    DEATH_SHAPE = "rect"           # inline defeat draw (SI-E 3.2)
    DEATH_FLAVOR = "ember"
    DEATH_BODY = (200, 60, 40)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.volley_cd = 90
        self.shots = []
        self.puddles = []                   # [tx, ty, ticks_left]

    def think(self, level, player):
        self.vx = 0.0
        if not player.dead:
            dx = player.cx - self.cx
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        # tick down lava puddles (deterministic cleanup)
        if self.puddles:
            keep = []
            for p in self.puddles:
                p[2] -= 1
                if p[2] > 0:
                    keep.append(p)
                elif level.tiles.get(p[0], p[1]) == T.LAVA:
                    level.tiles.set(p[0], p[1], T.EMPTY)
            self.puddles = keep
        self.volley_cd -= 1
        if 0 <= self.volley_cd <= 12:
            # crouch wind-up before the volley (SI-E 5.3, visual only)
            self.telegraph = self.volley_cd
        if self.volley_cd <= 0 and not player.dead:
            n = 3 + min(2, self.phase)       # 3 / 4 / 5 shot fan
            spread = 0.9
            for i in range(n):
                t = -spread + (2 * spread) * (i / max(1, n - 1))
                speed = config.FIREBALL_SPEED * 0.62
                lava = self.phase >= 2 and i == n // 2
                fire = MonarchFire(self.cx, self.cy - 4,
                                   0.0, speed, lava=lava)
                # aim the fan at the player (pure math)
                import math
                dx = player.cx - self.cx
                dy = player.cy - (self.cy - 4)
                base = math.atan2(dy, dx)
                fire.vx = math.cos(base + t) * speed
                fire.vy = math.sin(base + t) * speed
                fire.owner = self if lava else None
                self.shots.append(fire)
            self.volley_cd = max(56, config.MONARCH_VOLLEY_CD
                                 - 24 * self.phase)

    def puddle_at(self, level, tx, ty):
        """Leave a short-lived lava puddle (runtime tile edit)."""
        if 0 <= tx < level.tiles.w and 0 <= ty < level.tiles.h \
                and level.tiles.get(tx, ty) == T.EMPTY:
            level.tiles.set(tx, ty, T.LAVA)
            self.puddles.append([tx, ty, config.MONARCH_PUDDLE_TICKS])

    def draw(self, surf, cam, assets, tick):
        if self.state == "dying":
            _draw_boss_death(self, surf, cam, tick)   # staged defeat (3.2)
            return
        r = self.rect
        dx, dy, w, h = self.windup_pose(tick, dip=5)  # crouch (5.3)
        bx, by = r.x - cam.ix + dx, r.y - cam.iy + dy
        by += self.idle_bob(tick, 40)        # breathing dip (SI-G)
        rect = pygame.Rect(bx, by, w, h)
        ph = min(2, self.phase)
        body = ((200, 60, 40), (230, 100, 50), (255, 140, 60))[ph]
        if ph >= 2 and (tick // 5) % 2 == 0:
            body = (255, 178, 84)               # molten churn (5.2)
        pygame.draw.rect(surf, body, rect)
        self._veins(surf, rect, ph, tick)       # pulsing lava veins (5.4)
        pygame.draw.rect(surf, (90, 24, 20), rect, 2)
        self._crown(surf, rect, ph)             # spikes break off (5.4)
        if self.blinking(tick):              # idle blink (SI-G)
            for ox in (7, rect.w - 12):
                pygame.draw.line(surf, (90, 24, 20),
                                 (bx + ox, by + 14),
                                 (bx + ox + 4, by + 14), 1)
        else:
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + 7, by + 12, 5, 4))
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + rect.w - 12, by + 12, 5, 4))

    def _veins(self, surf, rect, ph, tick):
        """Lava-vein pulse period tightens per phase: 12 / 8 / 4 ticks;
        the glow runs bright orange at phase 2 (proposal 5.4)."""
        period = (12, 8, 4)[ph]
        hot = (tick // period) % 2 == 0
        if ph >= 2:
            col = (255, 214, 96) if hot else (232, 110, 44)
        else:
            col = (255, 168, 70) if hot else (146, 44, 26)
        for i, vx in enumerate((8, 16, 24)):
            x = rect.x + vx * rect.w // 32
            mid = (x - 2 + 4 * (i % 2), rect.y + rect.h // 2)
            pygame.draw.line(surf, col, (x, rect.y + 6), mid, 1)
            pygame.draw.line(surf, col, mid,
                             (x, rect.bottom - 5), 1)

    def _crown(self, surf, rect, ph):
        """Crown spikes break off by phase: full / one missing / shattered
        into stubs (proposal 5.4)."""
        if ph == 0:
            spikes, tip = (4, 12, 20), 7         # full crown
        elif ph == 1:
            spikes, tip = (4, 20), 7             # middle spike gone
        else:
            spikes, tip = (4, 12, 20), 2         # shattered
        for ox in spikes:
            x = rect.x + ox * rect.w // 32
            pygame.draw.polygon(surf, (255, 210, 90), [
                (x, rect.y), (x + 3, rect.y - tip), (x + 6, rect.y)])