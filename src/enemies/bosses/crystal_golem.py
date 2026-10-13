"""Crystal Golem (5c, Ember Caves): armored until the arena switches are
pressed — the core is exposed for a window, then it re-arms."""

import pygame

from src import config
from src.enemies.boss import Boss


class CrystalGolem(Boss):
    KIND = "crystal_golem"
    name = "CRYSTAL GOLEM"
    MAX_HP = config.GOLEM_HP
    W = 32
    H = 34

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
        r = self.rect
        body = (96, 200, 220) if self.exposed else (120, 128, 150)
        if self.exposed and (tick // 6) % 2 == 0:
            body = (170, 240, 250)
        pygame.draw.rect(surf, body,
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h))
        pygame.draw.rect(surf, (40, 50, 70),
                         pygame.Rect(r.x - cam.ix, r.y - cam.iy, r.w, r.h), 2)
        # crystal crest
        pygame.draw.polygon(surf, (200, 240, 250), [
            (r.x - cam.ix + 6, r.y - cam.iy),
            (r.x - cam.ix + 12, r.y - cam.iy - 8),
            (r.x - cam.ix + 18, r.y - cam.iy)])
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + 8, r.y - cam.iy + 12,
                                     5, 4))
        pygame.draw.rect(surf, (255, 240, 200),
                         pygame.Rect(r.x - cam.ix + r.w - 13,
                                     r.y - cam.iy + 12, 5, 4))