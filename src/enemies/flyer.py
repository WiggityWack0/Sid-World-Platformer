"""Flyer: sine-wave hover around a spawn anchor; ignores gravity."""

import math

from src import config
from src.enemies.base import Enemy


class Flyer(Enemy):
    KIND = "flyer"
    GRAVITY = False

    def __init__(self, x, y):
        super().__init__(x, y)
        self.anchor_x = float(x)
        self.anchor_y = float(y)
        self.phase = (int(x) % 97) * 0.07

    def think(self, level, player):
        self.phase += config.FLYER_W
        target_x = self.anchor_x + math.sin(self.phase) * config.FLYER_AMP_X
        target_y = self.anchor_y + math.sin(self.phase * 1.7) * config.FLYER_AMP_Y
        dx = target_x - self.x
        dy = target_y - self.y
        if abs(dx) > 0.2:
            self.facing = 1 if dx > 0 else -1
        self.vx = dx
        self.vy = dy

    def stomped(self, player=None):
        self.start_dying(pop=True)
        return "stomp"

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))
