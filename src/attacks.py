"""Player attack projectiles (Phase 2c). Polymorphic per form kind.

Fireball and ice shard are moving projectiles owned by PlayingState (no
manager); lightning is instant and handled there. Visual/combat only —
never touched by the validator (D6).
"""

import pygame

from src import config


class AttackProjectile:
    """A fired attack. kind is "fire" or "ice" (lightning is instant)."""

    def __init__(self, kind, x, y, facing):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.facing = facing
        speed = (config.FIREBALL_SPEED if kind == "fire"
                 else config.ICE_SHARD_SPEED)
        self.vx = speed * facing
        self.life = config.FIREBALL_LIFE
        self.w = 8
        self.h = 8

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def dead(self):
        return self.life <= 0

    def update(self, level):
        """Advance one tick; dies on walls/terrain, bounds, or timeout."""
        self.life -= 1
        self.x += self.vx
        if self.dead:
            return
        r = self.rect
        if (r.left < 0 or r.right > level.width
                or level.tiles.any_solid_rect(r)):
            self.life = 0

    def draw(self, surf, cam, assets, tick):
        img = assets.attack_frame(self.kind, (tick // 6) % 2)
        surf.blit(img, (int(self.x) - cam.ix, int(self.y) - cam.iy))
