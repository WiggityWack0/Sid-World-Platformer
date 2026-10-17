"""Warden Owl (5c, Frost Peaks): flying boss — hovers, telegraphed dives,
and spawns flyers as reinforcements (drained by EnemyManager)."""

import math

import pygame

from src import config
from src.assets.asset_factory import _draw_boss_death
from src.enemies.boss import Boss


class WardenOwl(Boss):
    KIND = "warden_owl"
    name = "WARDEN OWL"
    MAX_HP = config.OWL_HP
    W = 28
    H = 24
    GRAVITY = False
    DEATH_SHAPE = "ellipse"        # inline defeat draw (SI-E 3.2)
    DEATH_FLAVOR = "wind"
    DEATH_BODY = (90, 96, 140)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.mode = "rise"         # rise -> hover -> telegraph -> dive -> recover
        self.hover_y = y - config.OWL_HOVER_RISE
        self.atk = 110
        self.hover_t = 0
        self.dive_t = 0
        self.pupil_dx = 1          # gaze column: 0 left / 1 neutral / 2 right
        self.reinforcements = []   # drained into the manager (5c)
        self._reinf_left = 2       # lifetime cap on spawned flyers

    def think(self, level, player):
        if not player.dead:                        # gaze tracks the player
            dx = player.cx - self.cx               # (SI-E 5.4, chaser idea)
            self.pupil_dx = 1 if abs(dx) <= 4 else 2 if dx > 0 else 0
        if self.mode == "rise":
            self.vy = -1.4
            self.vx = 0.0
            if self.y <= self.hover_y:
                self.mode = "hover"
            return
        if self.mode == "hover":
            self.hover_t += 1
            if not player.dead:
                self.vx = max(-1.5, min(1.5, (player.cx - self.cx) * 0.04))
                if abs(player.cx - self.cx) > 1:
                    self.facing = 1 if player.cx > self.cx else -1
            self.vy = math.sin(self.hover_t * 0.06) * 0.8
            self.atk -= 1
            if self.atk <= 0 and not player.dead:
                self.mode = "telegraph"
                self.telegraph = self.TELEGRAPH
            return
        if self.mode == "telegraph":
            self.vx *= 0.8
            self.vy *= 0.8
            if self.telegraph <= 0:
                self.mode = "dive"
                self.dive_t = 70
                dx = player.cx - self.cx
                dy = max(30.0, player.cy - self.cy)
                mag = math.hypot(dx, dy) or 1.0
                s = config.OWL_DIVE_SPEED + 0.6 * self.phase
                self.vx = dx / mag * s
                self.vy = dy / mag * s
            return
        if self.mode == "dive":
            self.dive_t -= 1
            if self.on_ground or self.dive_t <= 0:
                self.mode = "recover"
            return
        if self.mode == "recover":
            self.vx = 0.0
            self.vy = -3.4
            if self.y <= self.hover_y:
                self.mode = "hover"
                self.atk = max(50, 110 - 25 * self.phase)

    def take_damage(self, amount=1):
        phase_before = self.phase
        killed = super().take_damage(amount)
        if not killed and self.phase > phase_before \
                and self._reinf_left > 0:
            self._reinf_left -= 1
            self.reinforcements.append(
                ("flyer", int(self.cx // config.TILE), 8))
        return killed

    def draw(self, surf, cam, assets, tick):
        if self.state == "dying":
            _draw_boss_death(self, surf, cam, tick)   # staged defeat (3.2)
            return
        r = self.rect
        dx, dy, w, h = self.windup_pose(tick, dip=2)  # light bob (5.3)
        bx, by = r.x - cam.ix + dx, r.y - cam.iy + dy
        rect = pygame.Rect(bx, by, w, h)
        ph = min(2, self.phase)
        body = ((90, 96, 140), (84, 88, 132), (76, 78, 124))[ph]
        if self.mode == "telegraph" and (tick // 4) % 2 == 0:
            body = (150, 160, 220)                # wind-up flash (kept)
        pygame.draw.ellipse(surf, body, rect)
        self._feathers(surf, rect, tick)           # ruffle by mode (5.4)
        if self.mode in ("rise", "hover", "recover"):
            self._flap_wings(surf, rect, tick)     # idle cycle (SI-G)
        pygame.draw.ellipse(surf, (40, 44, 80), rect, 2)
        # wings during dive
        if self.mode == "dive":
            pygame.draw.polygon(surf, body, [
                (bx, by + 6),
                (bx - 8, by - 2),
                (bx + 4, by + 14)])
        # eyes: gaze pupil (5.4); brows narrow from phase 1 (5.2)
        pd = max(0, min(2, getattr(self, "pupil_dx", 1)))
        for ex in (bx + 5, bx + r.w - 9):
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(ex, by + 7, 4, 4))
            pygame.draw.rect(surf, (40, 44, 80),
                             pygame.Rect(ex + pd, by + 9, 1, 2))
            if ph >= 1:                          # narrowed, aggressive
                pygame.draw.line(surf, (40, 44, 80),
                                 (ex, by + 7), (ex + 3, by + 7), 1)
        if ph >= 2:                              # beak gapes + molt (5.2)
            self._beak(surf, rect, tick)
            fy = by + h + (tick // 8) % 7
            col = (150, 158, 210)
            pygame.draw.line(surf, col, (bx + 8, fy), (bx + 11, fy + 3), 1)
            pygame.draw.line(surf, col, (bx + w - 12, fy + 2),
                             (bx + w - 9, fy + 5), 1)

    def _feathers(self, surf, rect, tick):
        """Feather lines ruffle by mode: smooth in hover, raised on the
        wind-up, swept back during the dive (proposal 5.4)."""
        col = (158, 150, 196) if self.phase >= 2 else (140, 150, 200)
        fy = rect.bottom - 7
        for i in range(3):
            fx = rect.x + 5 + i * 6
            if self.mode == "dive":               # swept back 45°
                pygame.draw.line(surf, col, (fx + 3, fy), (fx, fy + 4), 1)
            elif self.mode == "telegraph":        # raised 15°
                pygame.draw.line(surf, col, (fx, fy + 2), (fx + 4, fy - 1), 1)
            else:                                 # smooth, aligned
                pygame.draw.line(surf, col, (fx, fy + 1), (fx + 4, fy + 1), 1)

    def _flap_wings(self, surf, rect, tick):
        """Idle wing-flap cycle (SI-G): small wings beat up/down every 8
        ticks while hovering; the wind-up and dive keep their own poses."""
        dy = rect.y + (3 if (tick // 8) % 2 == 0 else 11)
        col = (64, 68, 110)
        pygame.draw.polygon(surf, col, [
            (rect.x, rect.y + 6), (rect.x - 6, dy), (rect.x + 3, rect.y + 13)])
        pygame.draw.polygon(surf, col, [
            (rect.right, rect.y + 6), (rect.right + 6, dy),
            (rect.right - 3, rect.y + 13)])

    def _beak(self, surf, rect, tick):
        """Phase-2 beak gapes wide between the eyes (proposal 5.2)."""
        cx = rect.x + rect.w // 2
        top = rect.y + 13
        gape = 4 + ((tick // 6) % 2)
        pygame.draw.polygon(surf, (255, 196, 84),
                            [(cx - 4, top), (cx + 4, top), (cx, top + 4)])
        pygame.draw.polygon(surf, (232, 140, 60), [
            (cx - 3, top + 4), (cx + 3, top + 4), (cx, top + 4 + gape)])