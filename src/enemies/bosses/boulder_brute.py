"""Boulder Brute (5c, Green Hills): slam jumps -> ground shockwaves,
rock throws (reuses the Bomber's arcing Bomb). Faster cycles per phase."""

import pygame

from src import config
from src.enemies.bomber import Bomb
from src.enemies.boss import Boss

WAVE_BODY = (150, 110, 70)


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
        r = self.rect
        body = (150, 110, 70)
        if self.telegraph > 0 and self.mode == "telegraph" \
                and (tick // 4) % 2 == 0:
            body = (210, 160, 90)
        pygame.draw.rect(surf, body,
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h))
        pygame.draw.rect(surf, (70, 48, 30),
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h), 2)
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + 7, r.y - cam.iy + 9, 5, 4))
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + r.w - 12,
                                     r.y - cam.iy + 9, 5, 4))