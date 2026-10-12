"""Jumper: idles until the player is close, then leaps toward them."""

from src import config
from src.enemies.base import Enemy


class Jumper(Enemy):
    KIND = "jumper"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.hop_timer = 30

    def think(self, level, player):
        if not self.on_ground:
            return                        # keep the leap's momentum
        self.vx = 0.0
        self.hop_timer -= 1
        if player.dead or self.hop_timer > 0:
            return
        dx = player.cx - self.cx
        if abs(dx) <= config.JUMPER_RANGE and abs(player.cy - self.cy) < 64:
            self.facing = 1 if dx > 0 else -1
            self.vx = self.facing * config.JUMPER_HOP_VX
            self.vy = config.JUMPER_HOP_VY
            self.hop_timer = config.JUMPER_HOP_COOLDOWN
        else:
            self.hop_timer = 12

    def on_wall_bump(self, hit):
        self.facing = -hit
        self.vx = 0.0

    def draw(self, surf, cam, assets, tick):
        surf.blit(assets.enemy_frame(self),
                  (int(self.x) - cam.ix, int(self.y) - cam.iy))
