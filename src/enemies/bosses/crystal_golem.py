"""Crystal Golem (5c, Ember Caves): armored until the arena switches are
pressed — the core is exposed for a window, then it re-arms."""

import pygame

from src import config
from src.assets.asset_factory import _draw_boss_death
from src.enemies.boss import Boss


class CrystalGolem(Boss):
    KIND = "crystal_golem"
    name = "CRYSTAL GOLEM"
    MAX_HP = config.GOLEM_HP
    W = 32
    H = 34
    DEATH_SHAPE = "rect"           # inline defeat draw (SI-E 3.2)
    DEATH_FLAVOR = "prism"
    DEATH_BODY = (120, 128, 150)

    def __init__(self, x, y):
        super().__init__(x, y)
        self.exposed = False
        self.expose_t = 0

    def think(self, level, player):
        self.vx = 0.0
        if not player.dead:
            dx = player.cx - self.cx
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        active = any(getattr(sw, "active", False) for sw in level.switches
                     if sw.tx >= getattr(level, "arena_x0", 0))
        if active and not self.exposed:
            self.exposed = True
            self.expose_t = config.GOLEM_EXPOSE_TICKS
        elif self.exposed:
            self.expose_t -= 1
            if 0 < self.expose_t <= 12:
                # shell bracing to re-arm — wind-up pose (5.3, visual only)
                self.telegraph = self.expose_t
            if self.expose_t <= 0:
                self.exposed = False
                for sw in level.switches:       # re-arm the arena switches
                    sw.active = False

    def take_damage(self, amount=1):
        if not self.exposed and self.state != "dying":
            return False                        # armored: deflects everything
        return super().take_damage(amount)

    def stomped(self, player=None):
        return "bounce"                         # never stompable; hit the core

    def reset(self):
        super().reset()
        self.exposed = False
        self.expose_t = 0

    def draw(self, surf, cam, assets, tick):
        if self.state == "dying":
            _draw_boss_death(self, surf, cam, tick)   # staged defeat (3.2)
            return
        r = self.rect
        dx, dy, w, h = self.windup_pose(tick, dip=4)  # brace (5.3)
        bx, by = r.x - cam.ix + dx, r.y - cam.iy + dy
        by += self.idle_bob(tick, 36)        # breathing dip (SI-G)
        rect = pygame.Rect(bx, by, w, h)
        ph = min(2, self.phase)
        shells = ((120, 128, 150), (110, 116, 142), (100, 106, 132))
        cores = ((96, 200, 220), (126, 222, 240), (170, 240, 250))
        if self.exposed:
            body = cores[ph]
            if ph == 2 and (tick // 4) % 2 == 0:
                body = (240, 252, 255)           # blinding glow (5.2)
        else:
            body = shells[ph]                    # shell darkens per phase
        pygame.draw.rect(surf, body, rect)
        if self.exposed:
            self._core(surf, rect, ph, tick)      # core layer (5.4)
        else:
            self._fractures(surf, rect, ph)       # shell detail (5.2)
        pygame.draw.rect(surf, (40, 50, 70), rect, 2)
        # crystal crest
        pygame.draw.polygon(surf, (200, 240, 250), [
            (bx + 6, by),
            (bx + 12, by - 8),
            (bx + 18, by)])
        if self.blinking(tick):              # idle blink (SI-G)
            for ox in (8, rect.w - 13):
                pygame.draw.line(surf, (40, 50, 70),
                                 (bx + ox, by + 14),
                                 (bx + ox + 4, by + 14), 1)
        else:
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + 8, by + 12, 5, 4))
            pygame.draw.rect(surf, (255, 240, 200),
                             pygame.Rect(bx + rect.w - 13, by + 12, 5, 4))

    def _core(self, surf, rect, ph, tick):
        """Exposed energy core: size/brightness scale with phase — the
        shell reads 30°/60° open as the glow grows (proposal 5.4)."""
        cx = rect.x + rect.w // 2
        cy = rect.y + rect.h // 2 + 2
        rad = (5, 7, 9)[ph]
        col = ((70, 220, 235), (170, 240, 250), (255, 255, 255))[ph]
        pygame.draw.polygon(surf, col, [
            (cx, cy - rad), (cx + rad, cy), (cx, cy + rad), (cx - rad, cy)])
        pygame.draw.polygon(surf, (40, 50, 70), [
            (cx, cy - rad), (cx + rad, cy), (cx, cy + rad), (cx - rad, cy)], 1)
        if ph >= 1 and (tick // 5) % 2 == 0:      # refraction sparkles (5.4)
            pygame.draw.rect(surf, (255, 255, 255),
                             pygame.Rect(rect.x + 4, rect.y + 5, 2, 2))
            pygame.draw.rect(surf, (255, 255, 255),
                             pygame.Rect(rect.right - 6, rect.bottom - 8,
                                         2, 2))

    def _fractures(self, surf, rect, ph):
        """Sealed shell: fracture lines spread as HP drops (proposal 5.2:
        blue shell / fractured shell / heavy cracks with core light)."""
        if ph == 0:
            return                              # phase 0: clean shell
        seams = (((16, 4), (13, 12)), ((16, 11), (20, 19)),
                 ((6, 16), (12, 23)), ((26, 14), (21, 25)))
        for a, b in seams[:2 if ph == 1 else 4]:
            pygame.draw.line(surf, (40, 50, 70),
                             (rect.x + a[0] * rect.w // 32,
                              rect.y + a[1] * rect.h // 34),
                             (rect.x + b[0] * rect.w // 32,
                              rect.y + b[1] * rect.h // 34), 1)
        if ph == 2:                             # core light leaks through
            cx = rect.x + rect.w // 2
            pygame.draw.line(surf, (150, 230, 245),
                             (cx, rect.y + 6), (cx, rect.bottom - 6), 1)